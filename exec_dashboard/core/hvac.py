"""경리부 'HVAC 현황 — 매입매출현황' 시트 읽기.

시트 구조 (2026.11 기준 실제 양식):
  거래처 | 호정 | 계약일자 | 인도일자 | 계약금액 | 수금액 | 미수금 | 수금예정일 |
  매입금액 | 발주금액 | 총액 | 품목 | 발주처 | 대금 지급 | 대금 지급 총액 | 대금 미지급 |
  지급예정일 | 지급 금액 | 대금 미지급 총액 | 발주여부(O/X) | 비고

특징과 처리 방법
- 병합 셀이 많다 → 병합 범위의 왼쪽 위 값을 아래 행에도 적용.
- 금액이 수식(=204000000/2) → 엑셀이 저장해 둔 계산값을 읽는다 (data_only).
- 2척 묶음 발주: '매입금액' 병합 범위에 호정이 2개 있으면 그 범위의 외주 품목은 두 호정 공동.
  외주 행의 project 는 '200톤 10척 5·8호정' 같은 묶음 이름, projects 에 실제 공사명 목록.
- 수금예정일·지급예정일 칸에 여러 줄('선금:2026-11-15\\n잔금:2027-02-15'),
  지급 금액 칸에도 같은 순서로 여러 줄 → 회차별로 나눈다.
- 회차별 수금 금액은 적혀 있지 않다 → 미정 회차가 하나면 미수금 전액, 여러 개면 금액 미기재(None).
"""
from __future__ import annotations

import re

from . import config
from .dates import find_dates, normalize_cell, to_date

HEAD = {
    "거래처": "group", "호정": "hull", "계약일자": "contract_date", "인도일자": "handover",
    "계약금액": "contract", "수금액": "collected", "미수금": "receivable", "수금예정일": "collect_plan",
    "매입금액": "purchase_budget", "발주금액": "po_amount", "총액": "po_total", "품목": "item",
    "발주처": "vendor", "대금지급총액": "paid_total", "대금지급": "paid", "대금미지급총액": "unpaid_total",
    "대금미지급": "unpaid", "지급예정일": "pay_plan", "지급금액": "pay_amounts", "발주여부": "ordered",
    "비고": "note",
}


def _clean(v) -> str:
    return re.sub(r"\s+", " ", normalize_cell(v)).strip()


def _num(v):
    from .parser import to_amount
    if v is None or v == "":
        return None
    if isinstance(v, str) and v.startswith("="):
        return None  # 계산값이 저장되지 않은 수식
    return to_amount(v)


class _Grid:
    """병합 셀을 펼쳐서 읽는 도우미."""

    def __init__(self, ws):
        self.ws = ws
        self.top = {}
        for rg in ws.merged_cells.ranges:
            for r in range(rg.min_row, rg.max_row + 1):
                for c in range(rg.min_col, rg.max_col + 1):
                    self.top[(r, c)] = (rg.min_row, rg.min_col)

    def get(self, r, c):
        tr, tc = self.top.get((r, c), (r, c))
        return self.ws.cell(tr, tc).value

    def anchor(self, r, c):
        """이 셀이 속한 병합 블록의 시작 행 (병합 아니면 자기 행)."""
        return self.top.get((r, c), (r, c))[0]

    def span(self, r, c):
        tr, tc = self.top.get((r, c), (r, c))
        for rg in self.ws.merged_cells.ranges:
            if rg.min_row == tr and rg.min_col == tc:
                return rg.min_row, rg.max_row
        return r, r


def _lines(v) -> list[str]:
    s = normalize_cell(v) if not isinstance(v, str) else v
    return [x.strip() for x in re.split(r"[\n\r]+", s or "") if x.strip()]


def _label_date(line: str):
    """'선금:2026-11-15' / '1차중도금 : 26.11.30' / '26.12.31' -> (라벨, 날짜, 완료여부)"""
    ds = find_dates(line)
    label = re.split(r"[:：]", line, 1)[0].strip() if re.search(r"[:：]", line) else ""
    label = re.sub(r"\d.*$", "", label).strip() if not ds else label
    done = "완료" in line
    return label, (ds[0].date if ds else None), done


def project_name(group: str, hull: str) -> str:
    """'강남 (200톤10척)' + '3호정' -> '200톤 10척 3호정' / '동일조선 (병원선)' -> '동일조선 병원선'"""
    first = _lines(group)[0] if group else ""
    inner = re.search(r"\(([^)]*)\)", first)
    head = re.split(r"[\s(]", first, 1)[0]
    if hull:
        base = inner.group(1) if inner else first
        base = re.sub(r"톤\s*(\d)", r"톤 \1", base).strip()
        return f"{base} {hull}".strip()
    return f"{head} {inner.group(1).strip()}" if inner else head


def parse_hvac_sheet(ws, warnings: list) -> dict:
    g = _Grid(ws)
    hdr_row, cols = None, {}
    for r in range(1, min(ws.max_row, 15) + 1):
        heads = {c.column: _clean(c.value).replace(" ", "") for c in ws[r] if c.value}
        if "호정" in heads.values() and "계약금액" in heads.values():
            hdr_row = r
            for c, h in heads.items():
                h = re.sub(r"\(.*\)", "", h)
                for k in sorted(HEAD, key=len, reverse=True):  # 긴 이름 먼저 ('대금지급총액' vs '대금지급')
                    if h.startswith(k):
                        cols[HEAD[k]] = c
                        break
            break
    if hdr_row is None:
        warnings.append(("error", f"'{ws.title}' 시트에서 머리글(호정·계약금액)을 찾지 못했습니다."))
        return {"orders": [], "collections": [], "outsourcing": [], "as_of": None}

    as_of = None
    for r in range(1, hdr_row):
        for c in ws[r]:
            if isinstance(c.value, str) and "기준" in c.value:
                as_of = to_date(c.value)

    C = lambda r, k: g.get(r, cols[k]) if k in cols else None  # noqa: E731
    last = hdr_row
    for r in range(hdr_row + 1, ws.max_row + 1):
        if "합계" in _clean(C(r, "group")).replace(" ", ""):
            break
        last = r

    orders, collections, outsourcing = [], [], []
    seen_contract = set()
    for r in range(hdr_row + 1, last + 1):
        group = normalize_cell(C(r, "group"))
        if not group.strip():
            continue
        hull = _clean(C(r, "hull"))
        sub_client = _clean(ws.cell(r, cols["group"] + 1).value) if cols.get("group") else ""
        name = project_name(group, hull)
        is_extra = "추가" in group

        # ---- 계약(수주) 블록: 계약금액 칸의 병합 시작 행마다 1건
        if "contract" in cols and g.anchor(r, cols["contract"]) == r and C(r, "contract") not in (None, ""):
            key = (r, cols["contract"])
            if key not in seen_contract:
                seen_contract.add(key)
                amt, got = _num(C(r, "contract")), _num(C(r, "collected")) or 0
                client = sub_client or _clean(group).split(" ")[0]
                kind = "추가 계약" if is_extra else ("계약" if not sub_client else f"계약({sub_client})")
                orders.append({"project": name, "client": client, "order_date": to_date(C(r, "contract_date")),
                               "amount": amt, "terms": "", "note": kind,
                               "handover": to_date(C(r, "handover"))})
                c0, c1 = g.span(r, cols["contract"])
                # 수금 누계
                done_dates = []
                pending = []
                bad = []
                for rr in sorted({g.anchor(x, cols["collect_plan"]) for x in range(c0, c1 + 1)}) if "collect_plan" in cols else []:
                    for line in _lines(C(rr, "collect_plan")):
                        lab, d, done = _label_date(line)
                        if d is None:
                            bad.append(line)
                        elif done:
                            done_dates.append(d)
                        else:
                            pending.append((lab or "수금", d))
                for line in bad:
                    warnings.append(("check", f"[매입매출 {name}] 수금예정일 '{line}' 날짜를 읽을 수 없습니다 (오타 확인)."))
                collections.append({"project": name, "kind": f"{kind} 수금 누계", "due_date": None,
                                    "billed": got, "paid_date": max(done_dates) if done_dates else None,
                                    "paid": got, "note": "매입매출현황"})
                # 미수금: 블록 안 미수금 칸들의 합 (회차별로 나뉘어 있을 수 있음)
                recv = 0.0
                for rr in sorted({g.anchor(x, cols["receivable"]) for x in range(c0, c1 + 1)}) if "receivable" in cols else []:
                    recv += _num(C(rr, "receivable")) or 0
                if amt is not None and abs((amt - got) - recv) > 1:
                    warnings.append(("check", f"[매입매출 {name}] 계약 {amt:,.0f} − 수금 {got:,.0f} ≠ 미수 {recv:,.0f} "
                                              f"(차이 {amt - got - recv:,.0f}원)."))
                if recv > 0:
                    if len(pending) == 1:
                        lab, d = pending[0]
                        collections.append({"project": name, "kind": lab, "due_date": d, "billed": recv,
                                            "paid_date": None, "paid": None, "note": ""})
                    elif pending:
                        for lab, d in pending:
                            collections.append({"project": name, "kind": lab, "due_date": d, "billed": None,
                                                "paid_date": None, "paid": None,
                                                "note": f"회차별 금액 미기재 · 미수 잔액 {recv:,.0f}원"})
                    else:
                        collections.append({"project": name, "kind": "미수 잔액", "due_date": None, "billed": recv,
                                            "paid_date": None, "paid": None, "note": "수금예정일 미기재"})

        # ---- 외주(매입) 품목 행
        item = _clean(C(r, "item"))
        if not item or g.anchor(r, cols["item"]) != r:  # 병합된 품목 칸은 첫 행에서 한 번만
            continue
        b0, b1 = g.span(r, cols["purchase_budget"]) if "purchase_budget" in cols else (r, r)
        hulls = []
        for x in range(b0, b1 + 1):
            h = _clean(C(x, "hull"))
            if h and h not in hulls:
                hulls.append(h)
        members = [project_name(group, h) for h in hulls] or [name]
        if len(members) > 1:
            nums = "·".join(re.sub(r"호정$", "", h) for h in hulls)
            label = project_name(group, f"{nums}호정")
        else:
            label = members[0]
        po = _num(C(r, "po_amount"))
        paid = _num(C(r, "paid")) or 0
        unpaid = _num(C(r, "unpaid"))
        if unpaid is None:
            unpaid = max((po or 0) - paid, 0)
        vendor = _clean(C(r, "vendor"))
        vendor = config.VENDOR_ALIASES.get(vendor, vendor)
        ordered = _clean(C(r, "ordered")).upper() != "X"
        if po is not None and abs(po - paid - unpaid) > 1:
            warnings.append(("check", f"[매입매출 {label} {item}/{vendor}] 발주 {po:,.0f} − 지급 {paid:,.0f} ≠ 미지급 "
                                      f"{unpaid:,.0f} (차이 {po - paid - unpaid:,.0f}원). 지급 기록 확인."))
        settled = max((po or 0) - unpaid, 0)  # 경리부 '대금 미지급'을 기준으로 이미 정산된 금액
        base = {"project": label, "projects": members, "vendor": vendor, "item": item, "ordered": ordered,
                "note": _clean(C(r, "note"))}
        if settled > 0 or unpaid == 0:
            outsourcing.append({**base, "amount": settled, "due_date": None,
                                "paid_date": None, "paid": settled})
        if unpaid > 0:
            plans = [_label_date(x) for x in _lines(C(r, "pay_plan"))]
            plans = [(lab or "지급", d) for lab, d, _ in plans if d]
            amts = _lines(C(r, "pay_amounts")) if isinstance(C(r, "pay_amounts"), str) else (
                [C(r, "pay_amounts")] if C(r, "pay_amounts") not in (None, "") else [])
            amts = [_num(a) for a in amts]
            if plans and len(amts) == len(plans) and all(a is not None for a in amts) \
                    and abs(sum(amts) - unpaid) <= 1:
                for (lab, d), a in zip(plans, amts):
                    outsourcing.append({**base, "item": f"{item} {lab}".strip() if len(plans) > 1 else item,
                                        "amount": a, "due_date": d, "paid_date": None, "paid": 0})
            else:
                if plans and amts and abs(sum(a or 0 for a in amts) - unpaid) > 1:
                    warnings.append(("warn", f"[매입매출 {label} {item}/{vendor}] 지급 금액 합계가 미지급 "
                                             f"{unpaid:,.0f}원과 다릅니다."))
                outsourcing.append({**base, "amount": unpaid, "due_date": plans[0][1] if plans else None,
                                    "paid_date": None, "paid": 0})
        if not ordered and unpaid > 0:
            pass  # 발주 전 품목: 대시보드에서 '발주 전'으로 표시
    return {"orders": orders, "collections": collections, "outsourcing": outsourcing, "as_of": as_of}
