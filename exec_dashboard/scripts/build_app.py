"""스마트폰 앱(PWA) 만들기: 최신 엑셀 → 보고서 → 비밀번호로 암호화 → 배포 폴더(dist)

사용:
  APP_PASSWORD=... python exec_dashboard/scripts/build_app.py                 # 구글 드라이브 (GDRIVE_* 환경변수)
  APP_PASSWORD=... python exec_dashboard/scripts/build_app.py --folder inbox  # 로컬 폴더
옵션: --out dist  --asof 2026-11-23

배포 폴더는 공개 웹(GitHub Pages)에 올라가도 된다. 자료는 data.enc 안에 AES-256-GCM 으로 암호화되어 있고
비밀번호 없이는 열 수 없다. 로그에는 건수만 찍는다.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import secrets
import shutil
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from core import analytics as A                                   # noqa: E402
from core.history import HistoryStore                             # noqa: E402
from core.html_report import build_html                           # noqa: E402
from core.loader import combine                                    # noqa: E402
from core.parser import to_snapshot                                # noqa: E402
from core.sources import GoogleDriveSource, LocalFolderSource, load_service_account  # noqa: E402

KST = ZoneInfo("Asia/Seoul")
KDF_SALT = b"wonieng-ceo-app-v1"   # pwa/app.js 와 같아야 함
ITERATIONS = 310_000


def encrypt(payload: dict, password: str) -> dict:
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=KDF_SALT, iterations=ITERATIONS).derive(
        password.encode("utf-8"))
    iv = secrets.token_bytes(12)
    ct = AESGCM(key).encrypt(iv, json.dumps(payload, ensure_ascii=False).encode("utf-8"), None)
    return {"v": 1, "alg": "AES-256-GCM", "kdf": "PBKDF2-SHA256", "iter": ITERATIONS,
            "iv": base64.b64encode(iv).decode(), "ct": base64.b64encode(ct).decode(),
            "generated": payload["generated"]}


def decrypt(box: dict, password: str) -> dict:
    """시험용 (앱과 같은 방식으로 풀리는지 확인)."""
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=KDF_SALT, iterations=box["iter"]).derive(
        password.encode("utf-8"))
    return json.loads(AESGCM(key).decrypt(base64.b64decode(box["iv"]), base64.b64decode(box["ct"]), None))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder")
    ap.add_argument("--out", default="dist")
    ap.add_argument("--asof")
    a = ap.parse_args()

    password = os.environ.get("APP_PASSWORD", "")
    if len(password) < 8:
        sys.exit("APP_PASSWORD 가 없거나 8자보다 짧습니다. (12자 이상 권장)")
    now = dt.datetime.now(KST)
    asof = dt.date.fromisoformat(a.asof) if a.asof else now.date()

    if a.folder:
        src = LocalFolderSource(a.folder)
    elif os.environ.get("GDRIVE_FOLDER_ID"):
        src = GoogleDriveSource(os.environ["GDRIVE_FOLDER_ID"], load_service_account(os.environ.get("GDRIVE_SERVICE_ACCOUNT")))
    else:
        sys.exit("--folder 또는 GDRIVE_FOLDER_ID 가 필요합니다.")
    wb, name, fin_name = combine(src.list_files())
    if wb is None:
        sys.exit("업무 현황 엑셀을 찾지 못했습니다.")

    hist = HistoryStore(os.environ.get("HISTORY_DIR", str(HERE / ".history")))
    snap = to_snapshot(wb)
    prev = hist.previous_of(snap["file_hash"])
    hist.save(snap)
    brief = A.morning_brief(prev, snap, wb, asof)

    label = name + (f" + {fin_name}" if fin_name and fin_name != name else "")
    parts = build_html(wb, asof, label, brief=brief, parts=True)
    checks = [m for lvl, m in wb.warnings if lvl in ("check", "warn", "error")]
    payload = {**parts, "company": wb.company, "asof": asof.isoformat(), "generated": now.isoformat(timespec="minutes"),
               "finance_as_of": wb.finance_as_of.isoformat() if wb.finance_as_of else None,
               "check_count": len(checks), "headline": brief["headline"]}

    out = Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(HERE / "pwa", out)
    sw = out / "sw.js"
    sw.write_text(sw.read_text(encoding="utf-8").replace("__BUILD__", now.strftime("%Y%m%d%H%M")), encoding="utf-8")
    box = encrypt(payload, password)
    (out / "data.enc").write_text(json.dumps(box), encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    assert decrypt(box, password)["generated"] == payload["generated"]
    print(f"app built: projects={len(wb.projects)} finance={'yes' if wb.has_finance else 'no'} "
          f"checks={len(checks)} size={(out / 'data.enc').stat().st_size // 1024}KB")


if __name__ == "__main__":
    main()
