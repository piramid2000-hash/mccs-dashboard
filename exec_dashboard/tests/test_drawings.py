"""도면 배포: 최신 판 판정, 수령 집계, 링크·서명, 도면 파일 암호화."""
import base64
import datetime as dt
import hashlib
import hmac
import io
import json
import sys
from pathlib import Path

import openpyxl
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import doclinks as L  # noqa: E402
from core.drawings import parse_receipts, parse_register, status  # noqa: E402
from core.drawings_build import build_docs  # noqa: E402

SECRET = "unit-test-secret-1234567890"


def register_bytes():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "도면대장"
    ws.append(["도면번호", "도면명", "공사명", "Rev", "승인일", "개정내용", "파일", "배포처", "상태"])
    ws.append(["D-1", "승인도", "10척 3호정", "A", dt.date(2025, 12, 10), "최초", "", "talent", ""])
    ws.append(["D-1", "승인도", "10척 3호정", "C", dt.date(2026, 11, 20), "실외기 위치", "d1c.pdf", "talent, nara", ""])
    ws.append(["D-1", "승인도", "10척 3호정", "B", dt.date(2026, 6, 20), "치수", "", "talent", ""])  # 순서가 뒤섞여도 날짜로
    ws.append(["D-2", "공사도", "병원선", "1", dt.date(2026, 1, 1), "", "", "ghost", "폐기"])
    rs = wb.create_sheet("배포처")
    rs.append(["키", "이름", "회사", "역할"])
    rs.append(["talent", "김부장", "탤런트", "하우징"])
    rs.append(["nara", "", "나라냉열기", "설치"])
    b = io.BytesIO(); wb.save(b); return b.getvalue()


def receipts_bytes():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "수령확인"
    ws.append(["시각", "도면번호", "Rev", "수신자", "확인"])
    ws.append([dt.datetime(2026, 11, 21, 9, 0), "D-1", "C", "talent", "확인"])
    ws.append([dt.datetime(2026, 11, 23, 9, 0), "D-1", "C", "talent", "확인"])  # 두 번 눌러도 1명
    ws.append([dt.datetime(2026, 7, 1, 9, 0), "D-1", "B", "nara", "확인"])     # 옛 판 확인은 최신 판에 안 셈
    b = io.BytesIO(); wb.save(b); return b.getvalue()


def test_latest_and_receipts():
    warns = []
    drawings, recips = parse_register(register_bytes(), warns)
    d1 = next(d for d in drawings if d.no == "D-1")
    assert d1.latest.rev == "C" and d1.latest.recipients == ["talent", "nara"]
    assert recips["nara"].name == "nara"  # 이름이 비면 키
    d2 = next(d for d in drawings if d.no == "D-2")
    assert d2.withdrawn and any("ghost" in m for _, m in warns)
    st = status(drawings, recips, parse_receipts(receipts_bytes()), dt.date(2026, 11, 24))
    row = next(r for r in st["rows"] if r["drawing"].no == "D-1")
    who = {w["key"]: w for w in row["recipients"]}
    assert who["talent"]["acked"] and who["talent"]["at"] == dt.datetime(2026, 11, 21, 9, 0)  # 처음 확인 시각
    assert not who["nara"]["acked"]
    assert st["pending"] == 1 and len(st["recent"]) == 1


def test_signature_matches_apps_script_formula():
    sig = L.ack_sig(SECRET, "200톤10척3호정-승인도", "C", "나라냉열기")
    expect = hmac.new(SECRET.encode(), "ack|200톤10척3호정-승인도|C|나라냉열기".encode("utf-8"), hashlib.sha256).hexdigest()[:24]
    assert sig == expect and len(sig) == 24


def test_link_shape_hides_doc_number():
    url = L.link("https://x.github.io/app/", SECRET, "D-1", "C", "nara")
    frag = url.split("#", 1)[1].split("/")
    assert url.startswith("https://x.github.io/app/d.html#v1/")
    assert frag[1] == L.public_id(SECRET, "D-1") and "D-1" not in url
    assert frag[4] == "nara" and frag[5] == L.ack_sig(SECRET, "D-1", "C", "nara")


def test_doc_file_opens_only_with_its_key(tmp_path):
    drawings, recips = parse_register(register_bytes(), [])
    pdf = b"%PDF-1.4 test"
    res = build_docs(tmp_path, drawings, recips, parse_receipts(receipts_bytes()), secret=SECRET,
                     base_url="https://x/app/", ack_url="", find_file=lambda n: pdf if n == "d1c.pdf" else None,
                     company="테스트", asof=dt.date(2026, 11, 24), generated="2026-11-24T07:05", warnings=[])
    box = json.loads((tmp_path / "docs" / f"{L.public_id(SECRET, 'D-1')}.enc").read_text())
    body = json.loads(AESGCM(L.doc_key(SECRET, "D-1")).decrypt(base64.b64decode(box["iv"]), base64.b64decode(box["ct"]), None))
    assert body["latest"]["rev"] == "C" and [r["rev"] for r in body["revisions"]] == ["A", "B", "C"]
    assert base64.b64decode(body["pdf"]) == pdf
    try:
        AESGCM(L.doc_key(SECRET, "D-2")).decrypt(base64.b64decode(box["iv"]), base64.b64decode(box["ct"]), None)
        assert False, "다른 도면 열쇠로 열리면 안 됨"
    except Exception:
        pass
    assert "카톡 보내기" in res["html"] and res["summary"]["pending"] == 1
    assert res["html"].count("class='label'") == 1  # 폐기 도면은 라벨 없음
