"""기준일 기준으로 공정 진척·외주 진척·자금 현황을 계산한다."""
from __future__ import annotations

import datetime as dt
from collections import defaultdict

import pandas as pd

from . import config
from .parser import Project, Workbook


# ---------------------------------------------------------------- 공정 진척
def milestone_done(p: Project, key: str, asof: dt.date) -> bool:
    m = p.milestones.get(key)
    return bool(m and m.date <= asof)


def progress_pct(p: Project, asof: dt.date) -> float:
    total = done = 0.0
    for key, (_, _, w) in config.MILESTONES.items():
        m = p.milestones.get(key)
        if not m:
            continue
        total += w
        if key == "INSTALL_END" and "INSTALL_START" in p.milestones:
            s, e = p.milestones["INSTALL_START"].date, m.date
            if asof >= e:
                done += w
            elif asof > s and e > s:
                done += w * (asof - s).days / (e - s).days
        elif m.date <= asof:
            done += w
    return round(100 * done / total, 1) if total else 0.0


def current_stage(p: Project, asof: dt.date) -> str:
    m = p.milestones
    if milestone_done(p, "HANDOVER", asof):
        return "인도 완료"
    if milestone_done(p, "INSTALL_END", asof):
        return "시운전 완료·인도 대기" if "HANDOVER" in m else "완료"
    if milestone_done(p, "INSTALL_START", asof):
        return "설치·시운전 중"
    if any(milestone_done(p, k, asof) for k in ("DLV_EQUIP", "DLV_HOUSING", "DLV_SUPPORT")):
        return "외주 납품 중"
    if any(milestone_done(p, k, asof) for k in ("PO_EQUIP", "PO_SUPPORT", "PO_HOUSING", "PO_INSTALL")):
        return "외주 발주·제작 중"
    if milestone_done(p, "DWG_APPROVAL", asof):
        return "설계(도면) 승인"
    return "착수 전"


STAGE_ORDER = ["착수 전", "설계(도면) 승인", "외주 발주·제작 중", "외주 납품 중", "설치·시운전 중",
               "시운전 완료·인도 대기", "완료", "인도 완료"]


def next_milestone(p: Project, asof: dt.date):
    future = [m for m in p.milestones.values() if m.date > asof]
    return min(future, key=lambda m: m.date) if future else None


def risk_level(p: Project, asof: dt.date) -> tuple[str, str]:
    """(등급, 사유). 등급: 위험/주의/정상/완료"""
    m = p.milestones
    if milestone_done(p, "HANDOVER", asof) or (not m.get("HANDOVER") and milestone_done(p, "INSTALL_END", asof)):
        return "완료", ""
    reasons = []
    level = "정상"
    ho = m.get("HANDOVER")
    if ho:
        d = (ho.date - asof).days
        if d <= config.HANDOVER_RISK_DAYS and not milestone_done(p, "DLV_EQUIP", asof) and "DLV_EQUIP" in m:
            level = "위험"; reasons.append(f"인도 D-{d}인데 장비 미납품")
        if "INSTALL_END" in m and m["INSTALL_END"].date > ho.date:
            level = "위험"; reasons.append("시운전 완료 예정이 인도일보다 늦음")
        elif "INSTALL_END" in m and (ho.date - m["INSTALL_END"].date).days < 14 and d <= 60:
            level = "주의" if level == "정상" else level
            reasons.append(f"시운전→인도 여유 {(ho.date - m['INSTALL_END'].date).days}일")
        if 0 <= d <= config.DUE_SOON_DAYS:
            level = "주의" if level == "정상" else level
            reasons.append(f"인도 임박 D-{d}")
    if "DLV_EQUIP" in m and "INSTALL_START" in m and m["DLV_EQUIP"].date > m["INSTALL_START"].date:
        level = "주의" if level == "정상" else level
        reasons.append("장비 납품이 설치 착수보다 늦음")
    if "인도일 추후 변경" in " ".join(p.timeline_notes):
        level = "주의" if level == "정상" else level
        reasons.append("인도일 변경 예정(비고)")
    return level, " · ".join(reasons)


# ---------------------------------------------------------------- 외주 업체 매칭
def vendor_for(p: Project, category: str, vendors) -> str:
    cands = []
    for v in vendors:
        if v.category != category:
            continue
        if v.scope_clients and p.client not in v.scope_clients:
            continue
        if v.scope_tokens and not any(t in p.name for t in v.scope_tokens):
            continue
        specificity = len(v.scope_tokens) * 2 + len(v.scope_clients)
        cands.append((specificity, v))
    if not cands:
        return ""
    cands.sort(key=lambda x: -x[0])
    v = cands[0][1]
    return v.name + (" (거래중지)" if "거래중지" in v.risk_flags else "")


PKG_ITEM_KEYWORDS = {"서포트": ["서포트", "관통"], "하우징": ["하우징", "케이싱"],
                     "장비": ["에어컨", "냉동기", "장비"], "보온재·설치": ["설치", "보온재"]}


def outsourcing_matrix(wb: Workbook, asof: dt.date) -> pd.DataFrame:
    rows = []
    for p in wb.projects:
        for pkg, po, dlv, cat in config.WORK_PACKAGES:
            if po not in p.milestones and dlv not in p.milestones:
                continue
            if milestone_done(p, dlv, asof):
                status, score = "완료", 2
            elif milestone_done(p, po, asof):
                status, score = "발주·제작중", 1
            else:
                status, score = "발주 전", 0
            vend = vendor_for(p, cat, wb.vendors)
            if pkg == "보온재·설치":
                ins = vendor_for(p, "INSULATION", wb.vendors)
                vend = " / ".join(x for x in (ins, vend) if x)
            # 경리부 자료가 있으면 실제 업체명으로 덮어쓰기
            kws = PKG_ITEM_KEYWORDS[pkg]
            real = []
            for o in wb.outsourcing:
                item_ = o.get("item") or ""
                if p.name in (o.get("projects") or [o.get("project")]) and any(k in item_ for k in kws) \
                        and not ("설치" in item_ and pkg != "보온재·설치") and o.get("vendor") not in real:
                    real.append(o.get("vendor"))
            if real:
                vend = " / ".join(x for x in real if x)
            rows.append({
                "공사명": p.name, "패키지": pkg, "상태": status, "점수": score, "업체": vend,
                "발주일": p.milestones[po].date if po in p.milestones else None,
                "납품일": p.milestones[dlv].date if dlv in p.milestones else None,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 요약 표
def project_table(wb: Workbook, asof: dt.date) -> pd.DataFrame:
    order_amt = defaultdict(float)
    for o in wb.orders:
        order_amt[o["project"]] += o.get("amount") or 0
    billed, paid = defaultdict(float), defaultdict(float)
    for c in wb.collections:
        billed[c["project"]] += c.get("billed") or 0
        paid[c["project"]] += c.get("paid") or 0
    cost = defaultdict(float)
    for o in wb.outsourcing:  # 2척 묶음 발주는 반씩 배분
        members = o.get("projects") or [o["project"]]
        for m_ in members:
            cost[m_] += (o.get("amount") or 0) / len(members)
    rows = []
    for p in wb.projects:
        nm = next_milestone(p, asof)
        lvl, why = risk_level(p, asof)
        ho = p.milestones.get("HANDOVER")
        rows.append({
            "공사명": p.name, "고객사": p.client,
            "현재 단계": current_stage(p, asof), "진척도": progress_pct(p, asof),
            "다음 일정": f"{nm.name} ({nm.date:%y.%m.%d})" if nm else "-",
            "D-day": (nm.date - asof).days if nm else None,
            "인도일": ho.date if ho else None,
            "인도까지": (ho.date - asof).days if ho else None,
            "상태": lvl, "사유": why,
            "수주금액": order_amt.get(p.name) or None,
            "수금액": paid.get(p.name) or None,
            "미수금": (order_amt[p.name] - paid[p.name]) if p.name in order_amt else None,
            "외주비": cost.get(p.name) or None,
            "비고": p.remark,
        })
    return pd.DataFrame(rows)


def gantt_frame(wb: Workbook) -> pd.DataFrame:
    """공사별 단계 막대: 설계 → 외주(발주~납품) → 설치·시운전 → 인도 대기"""
    rows = []
    for p in wb.projects:
        m = {k: v.date for k, v in p.milestones.items()}
        po = [m[k] for k in ("PO_SUPPORT", "PO_HOUSING", "PO_EQUIP") if k in m]
        dl = [m[k] for k in ("DLV_SUPPORT", "DLV_HOUSING", "DLV_EQUIP") if k in m]
        segs = []
        if "DWG_APPROVAL" in m and po:
            s, e = sorted([m["DWG_APPROVAL"], min(po)])
            segs.append(("설계·승인", s, e))
        if po and dl:
            segs.append(("외주 발주→납품", min(po), max(dl)))
        if "INSTALL_START" in m and "INSTALL_END" in m:
            segs.append(("설치·시운전", m["INSTALL_START"], m["INSTALL_END"]))
        elif "INSTALL_END" in m and dl:
            segs.append(("설치·시운전", max(dl), m["INSTALL_END"]))
        if "INSTALL_END" in m and "HANDOVER" in m and m["HANDOVER"] > m["INSTALL_END"]:
            segs.append(("인도 준비", m["INSTALL_END"], m["HANDOVER"]))
        for name, s, e in segs:
            if e <= s:
                e = s + dt.timedelta(days=3)
            rows.append({"공사명": p.name, "단계": name, "시작": s, "종료": e})
    return pd.DataFrame(rows)


def milestone_events(wb: Workbook) -> pd.DataFrame:
    rows = []
    for p in wb.projects:
        for k, m in p.milestones.items():
            rows.append({"공사명": p.name, "key": k, "일정": m.name,
                         "단계": config.MILESTONES.get(k, ("", "기타"))[1],
                         "날짜": m.date, "정밀도": "월" if m.precision == "month" else "일", "원문": m.source})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 자금
def finance_summary(wb: Workbook, asof: dt.date) -> dict:
    total_order = sum(o.get("amount") or 0 for o in wb.orders)
    collected = sum(c.get("paid") or 0 for c in wb.collections)
    billed = sum(c.get("billed") or 0 for c in wb.collections)
    overdue = [c for c in wb.collections if c.get("due_date") and c["due_date"] < asof and not c.get("paid_date")]
    soon = [c for c in wb.collections if c.get("due_date") and asof <= c["due_date"] <= asof + dt.timedelta(days=config.DUE_SOON_DAYS)
            and not c.get("paid_date")]
    out_total = sum(o.get("amount") or 0 for o in wb.outsourcing)
    out_paid = sum(o.get("paid") or 0 for o in wb.outsourcing)
    out_soon = [o for o in wb.outsourcing if o.get("due_date") and asof <= o["due_date"] <= asof + dt.timedelta(days=config.DUE_SOON_DAYS)
                and not o.get("paid_date")]
    return {
        "total_order": total_order, "collected": collected, "billed": billed,
        "receivable": total_order - collected,
        "collect_rate": (collected / total_order * 100) if total_order else None,
        "overdue": overdue, "overdue_amt": sum(c.get("billed") or 0 for c in overdue),
        "soon": soon, "soon_amt": sum(c.get("billed") or 0 for c in soon),
        "out_total": out_total, "out_paid": out_paid, "out_unpaid": out_total - out_paid,
        "out_soon": out_soon, "out_soon_amt": sum((o.get("amount") or 0) - (o.get("paid") or 0) for o in out_soon),
        "gross_margin": total_order - out_total if total_order else None,
    }


def cashflow_frame(wb: Workbook) -> pd.DataFrame:
    """월별 수금(유입) vs 외주 지급(유출). 실적은 실제일, 미수/미지급은 예정일 기준."""
    rows = []
    for c in wb.collections:
        if c.get("paid_date") and c.get("paid"):
            rows.append({"월": c["paid_date"].replace(day=1), "구분": "수금 실적", "금액": c["paid"]})
        remain = (c.get("billed") or 0) - (c.get("paid") or 0)
        if c.get("due_date") and remain > 0:
            rows.append({"월": c["due_date"].replace(day=1), "구분": "수금 예정", "금액": remain})
    for o in wb.outsourcing:
        if o.get("paid_date") and o.get("paid"):
            rows.append({"월": o["paid_date"].replace(day=1), "구분": "외주 지급 실적", "금액": -o["paid"]})
        remain = (o.get("amount") or 0) - (o.get("paid") or 0)
        if o.get("due_date") and remain > 0:
            rows.append({"월": o["due_date"].replace(day=1), "구분": "외주 지급 예정", "금액": -remain})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 버전 비교
def diff_snapshots(old: dict, new: dict) -> pd.DataFrame:
    rows = []
    op, np_ = old.get("projects", {}), new.get("projects", {})
    for name in sorted(set(op) | set(np_)):
        if name not in op:
            rows.append({"공사명": name, "항목": "신규 공사", "이전": "-", "변경": "추가", "차이(일)": None}); continue
        if name not in np_:
            rows.append({"공사명": name, "항목": "공사 삭제", "이전": "있음", "변경": "-", "차이(일)": None}); continue
        for k in config.MILESTONE_ORDER:
            a, b = op[name].get(k), np_[name].get(k)
            if a != b:
                diff = (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days if a and b else None
                rows.append({"공사명": name, "항목": config.MILESTONES[k][0], "이전": a or "-", "변경": b or "-", "차이(일)": diff})
    for name in sorted(set(old.get("orders", {})) | set(new.get("orders", {}))):
        a, b = old.get("orders", {}).get(name), new.get("orders", {}).get(name)
        if a != b:
            rows.append({"공사명": name, "항목": "수주금액", "이전": a, "변경": b, "차이(일)": None})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 외주업체 결제
def vendor_payables(wb: Workbook, asof: dt.date) -> pd.DataFrame:
    """업체별 발주액·지급액·미지급·다음 지급예정 (외주비 시트 기준)."""
    rows = []
    for o in wb.outsourcing:
        amt, paid = o.get("amount") or 0, o.get("paid") or 0
        due = o.get("due_date")
        open_ = amt - paid > 0
        rows.append({"업체": o.get("vendor") or "(업체 미기재)", "발주액": amt, "지급액": paid,
                     "미지급": max(amt - paid, 0),
                     "다음 지급": due if open_ and due and due >= asof else None,
                     "연체": max(amt - paid, 0) if open_ and due and due < asof else 0,
                     "건수": 1})
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["다음 지급"] = pd.to_datetime(df["다음 지급"])
    g = df.groupby("업체").agg({"발주액": "sum", "지급액": "sum", "미지급": "sum", "연체": "sum", "건수": "sum",
                               "다음 지급": "min"}).reset_index()
    g["다음 지급"] = g["다음 지급"].dt.date
    return g.sort_values("미지급", ascending=False)


# ---------------------------------------------------------------- 아침 브리핑
def _won_eok(v) -> str:
    return f"{(v or 0) / 1e8:,.2f}억"


def morning_brief(prev: dict | None, cur: dict, wb: Workbook, asof: dt.date) -> dict:
    """어제(직전 버전) 대비 오늘 아침에 대표가 알아야 할 것.

    new_in   : 새로 들어온 수금  [(공사, 구분, 금액, 수금일)]
    new_out  : 새로 나간 외주 결제 [(공사, 업체, 품목, 금액, 지급일)]
    delays   : 늦춰진 일정 [(공사, 항목, 이전, 변경, 일수)]
    pulled   : 앞당겨진 일정
    due_in / due_out : 7일 내 수금·지급 예정 (미완료)
    handover : 7일 내 인도
    """
    def key_c(r):
        return (r.get("p"), r.get("k"), r.get("due"))

    def key_o(r):
        return (r.get("p"), r.get("v"), r.get("i"), r.get("due"))

    new_in, new_out = [], []
    if prev is not None:
        pc = {key_c(r): r for r in prev.get("collections", [])}
        for r in cur.get("collections", []):
            before = pc.get(key_c(r), {})
            got = (r.get("paid") or 0) - (before.get("paid") or 0)
            if got > 0:
                new_in.append((r["p"], r["k"], got, r.get("pd")))
        po = {key_o(r): r for r in prev.get("payments", [])}
        for r in cur.get("payments", []):
            before = po.get(key_o(r), {})
            out = (r.get("paid") or 0) - (before.get("paid") or 0)
            if out > 0:
                new_out.append((r["p"], r["v"], r["i"], out, r.get("pd")))

    delays, pulled = [], []
    if prev is not None:
        d = diff_snapshots(prev, cur)
        if not d.empty:
            for _, r in d[d["차이(일)"].notna()].iterrows():
                item = (r["공사명"], r["항목"], r["이전"], r["변경"], int(r["차이(일)"]))
                (delays if r["차이(일)"] > 0 else pulled).append(item)
    delays.sort(key=lambda x: -x[4])

    week = asof + dt.timedelta(days=7)
    due_in = [(c["project"], c.get("kind") or "",
               None if c.get("billed") is None else (c.get("billed") or 0) - (c.get("paid") or 0), c["due_date"])
              for c in wb.collections if c.get("due_date") and not c.get("paid_date") and c["due_date"] <= week]
    due_out = [(o["project"], o.get("vendor") or "", o.get("item") or "",
                (o.get("amount") or 0) - (o.get("paid") or 0), o["due_date"])
               for o in wb.outsourcing if o.get("due_date") and not o.get("paid_date") and o["due_date"] <= week]
    handover = [(p.name, p.milestones["HANDOVER"].date) for p in wb.projects
                if "HANDOVER" in p.milestones and asof <= p.milestones["HANDOVER"].date <= week]

    lines = []
    fa = getattr(wb, "finance_as_of", None)
    if fa and (asof - fa).days > 3:
        lines.append(f"금액 자료는 {fa:%m.%d} 기준입니다 ({(asof - fa).days}일 전). 그 뒤 수금·지급은 반영 전.")
    if prev is None:
        lines.append("비교할 이전 보고가 없어 오늘 현황만 보여 드립니다.")
    else:
        lines.append(f"수금 {len(new_in)}건 {_won_eok(sum(x[2] for x in new_in))} 입금"
                     if new_in else "어제 이후 새 수금 없음")
        lines.append(f"외주 결제 {len(new_out)}건 {_won_eok(sum(x[3] for x in new_out))} 지급"
                     if new_out else "어제 이후 외주 결제 없음")
        if delays:
            lines.append(f"일정 지연 {len(delays)}건 (최대 {delays[0][4]}일)")
    over_in = [x for x in due_in if x[3] < asof]
    if over_in:
        lines.append(f"⛔ 수금 예정일 지남 {len(over_in)}건" + (f" {_won_eok(sum(x[2] or 0 for x in over_in))}"
                                                           if any(x[2] for x in over_in) else ""))
    over_out = [x for x in due_out if x[4] < asof]
    if over_out:
        lines.append(f"⚠️ 외주 지급 예정일 지남 {len(over_out)}건 {_won_eok(sum(x[3] or 0 for x in over_out))} (지급 여부 확인)")
    if handover:
        lines.append("이번 주 인도: " + ", ".join(n for n, _ in handover))
    return {"has_prev": prev is not None, "prev_name": (prev or {}).get("file_name"),
            "prev_saved": (prev or {}).get("saved_at"),
            "new_in": new_in, "new_out": new_out, "delays": delays, "pulled": pulled,
            "due_in": sorted(due_in, key=lambda x: x[3]), "due_out": sorted(due_out, key=lambda x: x[4]),
            "handover": handover, "headline": lines}
