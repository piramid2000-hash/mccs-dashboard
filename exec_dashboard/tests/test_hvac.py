"""경리부 '매입매출현황' 양식 읽기 (실제 파일은 공개 저장소에 올리지 않으므로 같은 구조의 가짜 시트로 검증)."""
import datetime as dt
import io
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.parser import parse_workbook  # noqa: E402

HEAD = ["거래처", "", "호정", "계약일자", "인도일자", "계약금액", " 수금액", "미수금", "수금예정일", "매입금액",
        "발주금액", "총액", "품목", "발주처", "대금 지급", "대금 지급 총액", "대금 미지급", "지급예정일", "지급 금액",
        "대금 미지급 총액", "발주여부 ( O / X )", "비고"]


def make():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "매입매출현황"
    ws["A1"] = "HVAC 현황"
    ws["V2"] = "2026.11.05 기준"
    for i, h in enumerate(HEAD, 1):
        ws.cell(3, i, h)
    # 2척 묶음: 3호정(4~5행) + 4호정(6~7행), 매입금액 J4:J7 병합
    ws["A4"] = "강남 (200톤10척)"; ws.merge_cells("A4:B7")
    ws["C4"] = "3호정"; ws.merge_cells("C4:C5"); ws["C6"] = "4호정"; ws.merge_cells("C6:C7")
    for r, hull in ((4, 3), (6, 4)):
        ws.cell(r, 4, "26.04.01"); ws.cell(r, 5, "27.05.31")
        ws.cell(r, 6, 97000000); ws.cell(r, 7, 9700000); ws.cell(r, 8, 87300000)
        ws.cell(r, 9, "1차중도금 : 26.11.30\n2차중도금 및 잔금 : 27.06.30")
        for c in (4, 5, 6, 7, 8, 9):
            ws.merge_cells(start_row=r, start_column=c, end_row=r + 1, end_column=c)
    ws["J4"] = 122000000; ws.merge_cells("J4:J7")
    rows = [  # 발주금액, 품목, 발주처, 지급, 미지급, 지급예정일, 지급금액, 발주여부
        (62000000, "에어컨", "에이스기공", 18600000, 43400000, dt.datetime(2026, 11, 30), 43400000, "O"),
        (32300000, "에어컨 설치", "나라냉열기", 0, 32300000, "선금:2026-11-15\n중도금:2027-01-15\n잔금:2027-04-15",
         "10,000,000\n19,000,000\n3,300,000", "O"),
        (19400000, "실외기 하우징", "탈렌트엘엔지", 5820000, 13580000, "잔금:2027-02-15", 13580000, "O"),
        (92000, "실외기 가이드", "하이시스이엔지", 0, 92000, dt.datetime(2026, 12, 15), 92000, "X"),
    ]
    for i, (k, m, n, o, q, r_, s, u) in enumerate(rows):
        r = 4 + i
        for c, v in ((11, k), (13, m), (14, n), (15, o), (17, q), (18, r_), (19, s), (21, u)):
            ws.cell(r, c, v)
    # 3줄 병합된 한 품목 (같은 금액을 세 번 세면 안 됨) + 계약자 3곳
    ws["A8"] = "영광  (냉동기)\n총: 64,000,000"; ws.merge_cells("A8:A10")
    for r, (who, f, g, h) in enumerate([("영광", 12000000, 8400000, 3600000), ("드림공조", 27000000, 27000000, 0),
                                         ("제이에스", 25000000, 25000000, 0)], start=8):
        ws.cell(r, 2, who); ws.cell(r, 6, f); ws.cell(r, 7, g); ws.cell(r, 8, h)
    ws["I8"] = "26.11.30"
    ws["J8"] = 45000000; ws.merge_cells("J8:J10")
    for c, v in ((11, 45000000), (13, "CO2 냉동기"), (14, "레프코리아"), (15, 40500000), (17, 4500000),
                 (18, dt.datetime(2026, 11, 30)), (19, 4500000), (21, "O")):
        ws.cell(8, c, v); ws.merge_cells(start_row=8, start_column=c, end_row=10, end_column=c)
    ws["A11"] = "합    계"
    b = io.BytesIO(); wb.save(b); return b.getvalue()


def test_hvac_sheet():
    wb = parse_workbook(make(), "HVAC.xlsx")
    assert wb.projects == [] and wb.has_finance
    assert wb.finance_as_of == dt.date(2026, 11, 5)
    # 계약: 호정 2건 + 영광 3곳
    assert sorted(o["project"] for o in wb.orders)[:2] == ["200톤 10척 3호정", "200톤 10척 4호정"]
    assert sum(o["amount"] for o in wb.orders) == 97e6 * 2 + 64e6
    # 미정 회차가 2개면 금액 미기재, 1개면 미수 전액
    c3 = [c for c in wb.collections if c["project"] == "200톤 10척 3호정" and c["due_date"]]
    assert [c["billed"] for c in c3] == [None, None] and c3[0]["kind"] == "1차중도금"
    yg = [c for c in wb.collections if c["project"] == "영광 냉동기" and c["due_date"]]
    assert yg[0]["billed"] == 3.6e6
    # 외주: 2척 묶음 이름, 회차 분할, 표기 통일, 병합 품목 1회만
    out = wb.outsourcing
    assert {o["project"] for o in out} == {"200톤 10척 3·4호정", "영광 냉동기"}
    assert out[0]["projects"] == ["200톤 10척 3호정", "200톤 10척 4호정"]
    inst = [o for o in out if o["vendor"] == "나라냉열기"]
    assert [o["amount"] for o in inst] == [10e6, 19e6, 3.3e6] and inst[0]["item"] == "에어컨 설치 선금"
    assert all(o["vendor"] != "탈렌트엘엔지" for o in out)
    assert sum(o["amount"] for o in out if o["vendor"] == "레프코리아") == 45e6
    unpaid = sum(o["amount"] - o["paid"] for o in out)
    assert unpaid == 43.4e6 + 32.3e6 + 13.58e6 + 92e3 + 4.5e6
