"""GoogleDriveSource 를 가짜 Drive 서비스로 검증 (네트워크 없이)."""
import io
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.sources import GoogleDriveSource, load_service_account  # noqa: E402


def _xlsx():
    wb = openpyxl.Workbook()
    wb.active["A1"] = "hi"
    b = io.BytesIO(); wb.save(b); return b.getvalue()


class _Req:
    def __init__(self, data=None, payload=None):
        self.data, self.payload = data, payload

    def execute(self):
        return self.payload


class _Files:
    def __init__(self):
        self.calls = []

    def list(self, **kw):
        self.calls.append(kw)
        return _Req(payload={"files": [
            {"id": "a", "name": "업무현황.xlsx", "modifiedTime": "2026-11-18T01:02:03.000Z", "size": "10",
             "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "version": "3"},
            {"id": "b", "name": "수주수금", "modifiedTime": "2026-11-17T01:02:03.000Z",
             "mimeType": "application/vnd.google-apps.spreadsheet", "version": "1"}]})

    def get_media(self, fileId, **kw):
        return _Req(data=_xlsx())

    def export_media(self, fileId, mimeType):
        return _Req(data=_xlsx())


class _Svc:
    def __init__(self):
        self._f = _Files()

    def files(self):
        return self._f


def test_list_and_load(monkeypatch):
    import googleapiclient.http as gh

    class _DL:
        def __init__(self, buf, req):
            self.buf, self.req = buf, req

        def next_chunk(self):
            self.buf.write(self.req.data); return None, True

    monkeypatch.setattr(gh, "MediaIoBaseDownload", _DL)
    src = GoogleDriveSource("FOLDER", {"client_email": "x"})
    src._svc = _Svc()
    files = src.list_files()
    assert [f.name for f in files] == ["업무현황.xlsx", "수주수금.xlsx"]   # 구글시트는 .xlsx 로 내보냄
    assert "'FOLDER' in parents" in src._svc._f.calls[0]["q"]
    assert files[0].uid == "a:3"
    assert files[1].load()[:2] == b"PK"


def test_load_service_account_forms(tmp_path):
    p = tmp_path / "k.json"; p.write_text('{"client_email": "a@b"}')
    assert load_service_account(str(p))["client_email"] == "a@b"
    assert load_service_account('{"client_email": "c@d"}')["client_email"] == "c@d"
    assert load_service_account({"client_email": "e@f"})["client_email"] == "e@f"
