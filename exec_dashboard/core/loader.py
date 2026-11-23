"""폴더(동기화 폴더 또는 구글 드라이브)의 엑셀들 → 대시보드용 Workbook 하나.

- 가장 최근 '업무 현황' 엑셀 = 일정
- 가장 최근 수주·수금·외주비 시트가 있는 엑셀 = 금액 (경리부 파일이 따로 와도 합쳐짐)
"""
from __future__ import annotations

from .parser import Workbook, parse_workbook


def combine(files) -> tuple[Workbook | None, str, str]:
    parsed = []
    for f in files[:20]:  # files 는 최신순
        try:
            parsed.append((parse_workbook(f.load(), f.name), f.name))
        except Exception:  # noqa: BLE001 - 깨진 파일 하나 때문에 전체가 멈추지 않게
            continue
    wb, name = next(((w, n) for w, n in parsed if w.projects), (None, ""))
    if wb is None:
        return None, "", ""
    fin_name = name if wb.has_finance else ""
    if not wb.has_finance:
        fin = next(((w, n) for w, n in parsed if w.has_finance), None)
        if fin:
            wb.orders, wb.collections, wb.outsourcing = fin[0].orders, fin[0].collections, fin[0].outsourcing
            fin_name = fin[1]
    return wb, name, fin_name
