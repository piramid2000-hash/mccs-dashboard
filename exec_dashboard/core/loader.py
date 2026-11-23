"""폴더(동기화 폴더 또는 구글 드라이브)의 엑셀들 → 대시보드용 Workbook 하나.

- 가장 최근 '업무 현황' 엑셀 = 일정
- 가장 최근 금액 엑셀 (경리부 '매입매출현황' 또는 수주·수금·외주비 양식) = 금액
- 두 파일의 공사명을 맞추고(띄어쓰기·표기 차이 흡수), 인도일 등 서로 다른 값을 점검한다.
"""
from __future__ import annotations

import re

from .parser import Workbook, parse_workbook


def _norm(s: str) -> str:
    return re.sub(r"[\s·()\-]", "", s or "")


def match_project(name: str, known: list[str]) -> str | None:
    """'200톤10척 3호정' -> '200톤 10척 3호정', '동일조선 병원선' -> '동일조선 병원선 1척'"""
    if not name:
        return None
    n = _norm(name)
    for k in known:
        if _norm(k) == n:
            return k
    toks = [t for t in re.split(r"\s+", name) if t]
    hits = [k for k in known if all(t in k for t in toks)]
    if len(hits) == 1:
        return hits[0]
    return None


def merge_finance(wb: Workbook, fin: Workbook | None) -> Workbook:
    """일정 Workbook(wb)에 금액 Workbook(fin)을 붙인다. fin 이 None 이면 wb 자체의 금액 시트를 정리만 한다."""
    if fin is not None and fin is not wb:
        wb.orders, wb.collections, wb.outsourcing = fin.orders, fin.collections, fin.outsourcing
        wb.finance_as_of, wb.finance_file = fin.finance_as_of, fin.finance_file
        wb.warnings = wb.warnings + [w for w in fin.warnings if "업무 현황" not in w[1]]
    known = [p.name for p in wb.projects]
    if not known:
        return wb
    unknown = set()

    def fix(n):
        m = match_project(n, known)
        if m is None:
            unknown.add(n)
        return m or n

    for r in wb.orders + wb.collections:
        r["project"] = fix(r.get("project"))
    for r in wb.outsourcing:
        members = r.get("projects") or [r.get("project")]
        r["projects"] = [fix(x) for x in members]
        if len(r["projects"]) == 1:
            r["project"] = r["projects"][0]
    for n in sorted(x for x in unknown if x):
        wb.warnings.append(("warn", f"[금액] '{n}' 공사를 업무 현황에서 찾지 못했습니다 (공사명 표기 확인)."))

    # 인도일: 경리부 자료 vs 업무 현황
    by = {p.name: p for p in wb.projects}
    for o in wb.orders:
        p, ho = by.get(o["project"]), o.get("handover")
        if p and ho and "HANDOVER" in p.milestones and p.milestones["HANDOVER"].date != ho:
            wb.warnings.append(("check", f"[{p.name}] 인도일이 다릅니다: 업무현황 {p.milestones['HANDOVER'].date:%y.%m.%d}"
                                         f" / 매입매출 {ho:%y.%m.%d}"))
    return wb


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
    fin, fin_name = (wb, name) if wb.has_finance else next(((w, n) for w, n in parsed if w.has_finance), (None, ""))
    merge_finance(wb, fin)
    return wb, name, fin_name
