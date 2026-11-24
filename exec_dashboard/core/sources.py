"""엑셀을 가져오는 곳(클라우드 폴더)을 추상화한다.

1) LocalFolderSource  : 구글드라이브/원드라이브/드롭박스/NAS '동기화 폴더' 경로.
                        직원이 클라우드에 올리면 PC의 동기화 폴더에 자동으로 내려온다. (가장 간단)
2) GoogleDriveSource  : 구글 드라이브 폴더를 API로 직접 읽음 (서버/Streamlit Cloud 배포용).
                        서비스계정 JSON + 폴더 ID 필요. 폴더를 서비스계정 이메일에 '뷰어'로 공유.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

EXCEL_EXT = (".xlsx", ".xlsm")


@dataclass
class FileEntry:
    name: str
    modified: dt.datetime
    size: int
    uid: str               # 변경 감지용 (경로+수정시각 또는 drive id+버전)
    load: Callable[[], bytes]


class LocalFolderSource:
    label = "동기화 폴더"

    def __init__(self, folder: str):
        self.folder = Path(os.path.expanduser(folder))

    def available(self) -> bool:
        return self.folder.is_dir()

    def list_files(self) -> list[FileEntry]:
        if not self.available():
            return []
        out = []
        for p in self.folder.rglob("*"):
            if p.suffix.lower() in EXCEL_EXT and not p.name.startswith(("~$", ".")) and ".history" not in p.parts:
                st = p.stat()
                out.append(FileEntry(p.name, dt.datetime.fromtimestamp(st.st_mtime), st.st_size,
                                     f"{p}:{st.st_mtime_ns}", (lambda q=p: q.read_bytes())))
        return sorted(out, key=lambda f: f.modified, reverse=True)


def _local_find(self, name: str):
    """폴더(하위 폴더 포함)에서 이름이 같은 파일의 내용. 없으면 None."""
    if not name or not self.available():
        return None
    for p in self.folder.rglob("*"):
        if p.is_file() and p.name == name and ".history" not in p.parts:
            return p.read_bytes()
    return None


LocalFolderSource.find_file = _local_find


class GoogleDriveSource:
    label = "Google Drive"

    def __init__(self, folder_id: str, service_account_info: dict):
        self.folder_id = folder_id
        self.info = service_account_info
        self._svc = None

    def _service(self):
        if self._svc is None:
            from google.oauth2 import service_account          # noqa: WPS433
            from googleapiclient.discovery import build         # noqa: WPS433
            creds = service_account.Credentials.from_service_account_info(
                self.info, scopes=["https://www.googleapis.com/auth/drive.readonly"])
            self._svc = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self._svc

    def available(self) -> bool:
        return bool(self.folder_id and self.info)

    def list_files(self) -> list[FileEntry]:
        svc = self._service()
        q = (f"'{self.folder_id}' in parents and trashed=false and ("
             "mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or "
             "mimeType='application/vnd.google-apps.spreadsheet')")
        res = svc.files().list(q=q, fields="files(id,name,modifiedTime,size,mimeType,version)",
                               orderBy="modifiedTime desc", pageSize=50,
                               supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        out = []
        for f in res.get("files", []):
            fid, mime = f["id"], f["mimeType"]

            def _load(fid=fid, mime=mime):
                from googleapiclient.http import MediaIoBaseDownload  # noqa: WPS433
                import io
                if mime == "application/vnd.google-apps.spreadsheet":
                    req = svc.files().export_media(
                        fileId=fid, mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    req = svc.files().get_media(fileId=fid, supportsAllDrives=True)
                buf = io.BytesIO()
                dl = MediaIoBaseDownload(buf, req)
                done = False
                while not done:
                    _, done = dl.next_chunk()
                return buf.getvalue()

            mod = dt.datetime.fromisoformat(f["modifiedTime"].replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
            name = f["name"] if f["name"].lower().endswith(EXCEL_EXT) else f["name"] + ".xlsx"
            out.append(FileEntry(name, mod, int(f.get("size", 0) or 0), f"{fid}:{f.get('version')}", _load))
        return out


def _drive_find(self, name: str):
    """드라이브 폴더에서 이름이 같은 파일(PDF 도면 등)의 내용. 없으면 None."""
    if not name:
        return None
    import io
    from googleapiclient.http import MediaIoBaseDownload  # noqa: WPS433
    svc = self._service()
    safe = name.replace("\\", "\\\\").replace("'", "\\'")
    res = svc.files().list(q=f"'{self.folder_id}' in parents and trashed=false and name='{safe}'",
                           fields="files(id,name,mimeType)", pageSize=5,
                           supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
    files = [f for f in res.get("files", []) if not f["mimeType"].startswith("application/vnd.google-apps")]
    if not files:
        return None
    buf = io.BytesIO()
    dl = MediaIoBaseDownload(buf, svc.files().get_media(fileId=files[0]["id"], supportsAllDrives=True))
    done = False
    while not done:
        _, done = dl.next_chunk()
    return buf.getvalue()


GoogleDriveSource.find_file = _drive_find


def load_service_account(raw) -> dict:
    """서비스계정 키: JSON 문자열 / JSON 파일 경로 / secrets.toml 의 [GDRIVE_SERVICE_ACCOUNT] 표 모두 허용."""
    from collections.abc import Mapping
    if not raw:
        return {}
    if isinstance(raw, Mapping):
        return {k: raw[k] for k in raw}
    raw = str(raw).strip()
    if os.path.isfile(raw):
        return json.loads(Path(raw).read_text(encoding="utf-8"))
    return json.loads(raw)
