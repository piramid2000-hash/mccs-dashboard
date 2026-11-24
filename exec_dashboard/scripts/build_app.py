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
from core.drawings import load_from_files, memoize, status as dstatus  # noqa: E402
from core.drawings_build import build_docs                         # noqa: E402
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
    ap.add_argument("--base-url", default=os.environ.get("APP_URL", ""),
                    help="앱 주소 (QR·카톡 링크에 들어감). 기본: 환경변수 APP_URL")
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
    files = memoize(src.list_files())
    wb, name, fin_name = combine(files)
    if wb is None:
        sys.exit("업무 현황 엑셀을 찾지 못했습니다.")

    # 도면 배포 (도면대장 엑셀이 폴더에 있고 DOC_SECRET 이 있을 때)
    doc_secret = os.environ.get("DOC_SECRET", "")
    drawings, recipients, receipts = load_from_files(files, wb.warnings)
    if drawings and len(doc_secret) < 16:
        print("도면대장이 있지만 DOC_SECRET(16자 이상)이 없어 도면 배포 기능을 건너뜁니다.")
        drawings = []
    if drawings and not a.base_url:
        sys.exit("도면 링크·QR 에 넣을 앱 주소가 필요합니다: APP_URL 환경변수 또는 --base-url")
    dstat = dstatus(drawings, recipients, receipts, asof) if drawings else None

    hist = HistoryStore(os.environ.get("HISTORY_DIR", str(HERE / ".history")))
    snap = to_snapshot(wb)
    prev = hist.previous_of(snap["file_hash"])
    hist.save(snap)
    brief = A.morning_brief(prev, snap, wb, asof)
    if dstat and (dstat["recent"] or dstat["pending"]):
        brief["headline"].append(f"도면 개정 {len(dstat['recent'])}건(14일) · 수령 미확인 {dstat['pending']}명")

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
    if drawings:
        docs = build_docs(out, drawings, recipients, receipts, secret=doc_secret, base_url=a.base_url,
                          ack_url=os.environ.get("ACK_URL", ""), find_file=getattr(src, "find_file", lambda n: None),
                          company=wb.company, asof=asof, generated=payload["generated"], warnings=wb.warnings)
        head, sep, tail = payload["body"].rpartition("<footer")  # 도면 탭은 맨 아래 안내줄보다 위에
        payload["body"] = (head + docs["html"] + sep + tail) if sep else payload["body"] + docs["html"]
        payload["css"] += docs["css"]
        payload["docs_pending"] = docs["summary"]["pending"]
        print(f"drawings: {docs['count']} docs, {docs['pdfs']} pdf, pending={docs['summary']['pending']}")
    box = encrypt(payload, password)
    (out / "data.enc").write_text(json.dumps(box), encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    assert decrypt(box, password)["generated"] == payload["generated"]

    # 심사·시연용 예시 자료 (DEMO_PASSWORD 가 있을 때만): 공사명·업체명·금액 모두 가짜
    demo_pw = os.environ.get("DEMO_PASSWORD", "")
    if demo_pw:
        if demo_pw == password:
            sys.exit("DEMO_PASSWORD 는 APP_PASSWORD 와 달라야 합니다.")
        import copy
        from core.demo import anonymize, assert_anonymous
        dwb = anonymize(copy.deepcopy(wb), asof)
        dparts = build_html(dwb, asof, "예시 자료", brief=A.morning_brief(None, to_snapshot(dwb), dwb, asof),
                            notice="심사·시연용 예시 화면입니다. 공사명·업체명·금액은 모두 가짜입니다.", parts=True)
        assert_anonymous(dparts["body"])
        demo = {**dparts, "company": wb.company, "asof": asof.isoformat(), "generated": payload["generated"],
                "finance_as_of": asof.isoformat(), "check_count": 2, "headline": [], "demo": True}
        (out / "demo.enc").write_text(json.dumps(encrypt(demo, demo_pw)), encoding="utf-8")
    print(f"app built: projects={len(wb.projects)} finance={'yes' if wb.has_finance else 'no'} "
          f"checks={len(checks)} size={(out / 'data.enc').stat().st_size // 1024}KB demo={'yes' if demo_pw else 'no'}")


if __name__ == "__main__":
    main()
