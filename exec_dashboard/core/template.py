"""수주·수금·외주비 입력 양식 생성 (+ 화면 미리보기용 예시 데이터)."""
from __future__ import annotations

import datetime as dt
import io
import random

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

HEAD_FILL = PatternFill("solid", fgColor="DCE7F7")
THIN = Side(style="thin", color="B7C2D0")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

SHEETS = {
    "수주": (["공사명", "고객사", "수주일", "수주금액(원)", "계약조건", "비고"], [26, 12, 12, 16, 30, 20]),
    "수금": (["공사명", "구분", "청구예정일", "청구금액(원)", "수금일", "수금액(원)", "비고"], [26, 10, 12, 16, 12, 16, 20]),
    "외주비": (["공사명", "업체", "품목", "발주금액(원)", "지급예정일", "지급일", "지급액(원)", "비고"], [26, 14, 14, 16, 12, 12, 16, 20]),
}
GUIDE = [
    "■ 작성 방법 (이 시트는 지워도 됩니다)",
    "1. '공사명'은 업무 현황 시트의 공사명과 똑같이 적어 주세요. (대시보드가 이름으로 연결합니다)",
    "2. 금액은 숫자만 (예: 125000000). '1.2억', '3,500만원'도 인식합니다. VAT 포함 여부는 회사 기준으로 통일.",
    "3. 날짜는 2026-11-30 또는 26.11.30 형식.",
    "4. 수금: 공사마다 선금/중도금/잔금을 한 줄씩. 돈이 들어오면 '수금일'과 '수금액'을 채우면 됩니다.",
    "5. 외주비: 외주업체 발주 1건당 한 줄. 지급하면 '지급일'·'지급액'을 채웁니다.",
    "6. 이 시트들은 업무 현황 엑셀에 추가해도 되고, 별도 파일(예: 수주수금.xlsx)로 같은 폴더에 올려도 됩니다.",
]


def build_finance_template(project_names: list[str], clients: dict | None = None) -> bytes:
    wb = openpyxl.Workbook()
    g = wb.active
    g.title = "작성안내"
    for i, line in enumerate(GUIDE, 1):
        g.cell(i, 1, line).font = Font(bold=(i == 1), size=11)
    g.column_dimensions["A"].width = 110
    for name, (heads, widths) in SHEETS.items():
        ws = wb.create_sheet(name)
        for c, (h, w) in enumerate(zip(heads, widths), 1):
            cell = ws.cell(1, c, h)
            cell.font, cell.fill, cell.border = Font(bold=True), HEAD_FILL, BOX
            cell.alignment = Alignment(horizontal="center")
            ws.column_dimensions[openpyxl.utils.get_column_letter(c)].width = w
        ws.freeze_panes = "A2"
        r = 2
        for p in project_names:
            kinds = ["선금", "중도금", "잔금"] if name == "수금" else [""]
            for k in kinds:
                ws.cell(r, 1, p)
                if name == "수주" and clients:
                    ws.cell(r, 2, clients.get(p, ""))
                if name == "수금":
                    ws.cell(r, 2, k)
                for c in range(1, len(heads) + 1):
                    ws.cell(r, c).border = BOX
                    if "금액" in heads[c - 1] or "액(원)" in heads[c - 1]:
                        ws.cell(r, c).number_format = "#,##0"
                    if "일" in heads[c - 1] and "금액" not in heads[c - 1]:
                        ws.cell(r, c).number_format = "yyyy-mm-dd"
                r += 1
        if name == "수금":
            dv = DataValidation(type="list", formula1='"계약금,선금,중도금,기성,잔금,기타"', allow_blank=True)
            ws.add_data_validation(dv)
            dv.add(f"B2:B{max(r, 200)}")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def demo_finance(projects, asof: dt.date, seed: int = 7):
    """⚠ 화면 미리보기 전용 가상 금액. 실제 데이터가 아님."""
    rnd = random.Random(seed)
    orders, cols, outs = [], [], []
    for p in projects:
        m = {k: v.date for k, v in p.milestones.items()}
        base = rnd.choice([1.8, 2.1, 2.4, 2.6]) * 1e8 if "200톤" in p.name else rnd.choice([0.9, 1.3]) * 1e8
        start = m.get("DWG_APPROVAL") or min(m.values())
        end = m.get("HANDOVER") or m.get("INSTALL_END") or max(m.values())
        orders.append({"project": p.name, "client": p.client, "order_date": start - dt.timedelta(days=30),
                       "amount": base, "terms": "선금30/중도40/잔금30", "note": "예시"})
        for kind, ratio, due in (("선금", .3, start), ("중도금", .4, m.get("DLV_EQUIP", start)), ("잔금", .3, end + dt.timedelta(days=30))):
            paid = due <= asof - dt.timedelta(days=rnd.choice([0, 0, 0, 20, 45]))
            cols.append({"project": p.name, "kind": kind, "due_date": due, "billed": base * ratio,
                         "paid_date": due + dt.timedelta(days=rnd.randint(3, 25)) if paid else None,
                         "paid": base * ratio if paid else None, "note": "예시"})
        for item, key, ratio in (("장비", "PO_EQUIP", .35), ("서포트·하우징", "PO_HOUSING", .12), ("설치", "PO_INSTALL", .15)):
            if key in m:
                due = m[key] + dt.timedelta(days=20)
                paid = due <= asof
                outs.append({"project": p.name, "vendor": "", "item": item, "amount": base * ratio, "due_date": due,
                             "paid_date": due if paid else None, "paid": base * ratio if paid else None, "note": "예시"})
    return orders, cols, outs
