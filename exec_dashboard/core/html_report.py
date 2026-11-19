"""카톡·메일로 보낼 수 있는 '파일 한 개' HTML 보고서.

- 외부 파일·인터넷 없이 열림 (폰트·차트 모두 내장, 카톡 인앱 브라우저 OK)
- 휴대폰 화면 우선, PC에서도 보기 좋게
- 외주업체 담당자 전화·메일은 넣지 않음 (전달·유출 대비)
"""
from __future__ import annotations

import datetime as dt
import html
import re

import pandas as pd

from . import analytics as A
from . import config
from .parser import Workbook

E = html.escape

STATUS_CLS = {"위험": "crit", "주의": "warn", "정상": "good", "완료": "done"}
STATUS_ICON = {"위험": "⛔", "주의": "⚠️", "정상": "●", "완료": "✓"}
SEG = {"설계·승인": "s1", "외주 발주→납품": "s2", "설치·시운전": "s3", "인도 준비": "s4"}
OUT_CLS = {"발주 전": "o0", "발주·제작중": "o1", "완료": "o2"}


def short_name(n: str) -> str:
    s = re.sub(r"^\d+톤\s*", "", n).replace("호정", "호")
    if s != n:
        return s
    w = n.split()
    return (w[0][:2] + " " + w[1]) if len(w) >= 2 else n[:8]


def won(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "-"
    return f"{v / 1e8:,.2f}억"


CSS = """
:root{
 /* 공사 일정표 느낌: 청사진 블루 + 따뜻한 회색 종이, 상태색은 별도 */
 --bg:#f6f5f2;--card:#ffffff;--ink:#16181d;--ink2:#555a63;--ink3:#8a8f98;--line:#e3e1dc;
 --accent:#1f5fbf;--accent-soft:#dfe9f8;
 --s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;
 --o0:#ebe9e4;--o1:#9ec5f4;--o2:#256abf;--o2-ink:#ffffff;--o1-ink:#0d2d57;--o0-ink:#6b6f76;
 --good:#0ca30c;--warn:#d99100;--crit:#d03b3b;--done:#8a8f98;
 --crit-soft:#fbe9e9;--warn-soft:#fdf3dc;
 --font:"Pretendard","Apple SD Gothic Neo","Noto Sans KR","Malgun Gothic",system-ui,sans-serif;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
 --bg:#141518;--card:#1d1f23;--ink:#eceef1;--ink2:#b3b8c0;--ink3:#80868f;--line:#2e3137;
 --accent:#6aa5f0;--accent-soft:#1f2c40;
 --s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;
 --o0:#2a2d33;--o1:#2f5d93;--o2:#5598e7;--o2-ink:#0b1626;--o1-ink:#e6efff;--o0-ink:#9aa0a8;
 --crit-soft:#3a1f1f;--warn-soft:#3a3020;color-scheme:dark}}
:root[data-theme="dark"]{
 --bg:#141518;--card:#1d1f23;--ink:#eceef1;--ink2:#b3b8c0;--ink3:#80868f;--line:#2e3137;
 --accent:#6aa5f0;--accent-soft:#1f2c40;
 --s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;
 --o0:#2a2d33;--o1:#2f5d93;--o2:#5598e7;--o2-ink:#0b1626;--o1-ink:#e6efff;--o0-ink:#9aa0a8;
 --crit-soft:#3a1f1f;--warn-soft:#3a3020;color-scheme:dark}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 var(--font);
 padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:20px 48px}
.wrap{max-width:980px;margin:0 auto;display:grid;grid-template-columns:minmax(0,1fr);gap:22px}
.wrap>*{min-width:0}
header h1{font-size:1.45rem;margin:0;letter-spacing:-.01em;text-wrap:balance}
header .meta{color:var(--ink2);font-size:.82rem;margin-top:4px}
.badge{display:inline-block;font-size:.72rem;padding:2px 8px;border-radius:999px;background:var(--accent-soft);color:var(--accent);font-weight:600;margin-right:6px}
h2{font-size:1.05rem;margin:0 0 10px;display:flex;align-items:baseline;gap:8px}
h2 small{font-weight:400;color:var(--ink3);font-size:.78rem}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;min-width:0}
.kpi .l{font-size:.76rem;color:var(--ink2)}
.kpi .v{font-size:1.45rem;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.25;margin-top:2px}
.kpi .s{font-size:.74rem;color:var(--ink3);margin-top:2px}
.kpi.na .v{color:var(--ink3);font-size:1.1rem}
.list{display:grid;gap:8px}
.alert{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--warn);border-radius:10px;padding:9px 12px;font-size:.9rem}
.alert.crit{border-left-color:var(--crit);background:var(--crit-soft)}
.alert.warn{background:var(--warn-soft)}
.alert b{font-weight:700}
.alert .why{color:var(--ink2);font-size:.84rem}
.cal{display:grid;grid-template-columns:auto 1fr;gap:6px 12px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.cal .d{font-variant-numeric:tabular-nums;font-weight:700;white-space:nowrap}
.cal .d span{display:block;font-weight:400;color:var(--ink3);font-size:.72rem}
.cal .t{font-size:.9rem;min-width:0}
.cal .t em{font-style:normal;color:var(--ink2)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:10px}
details.pc{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:0;min-width:0}
details.pc>summary{list-style:none;cursor:pointer;padding:11px 14px 12px;display:grid;gap:4px}
details.pc>summary::-webkit-details-marker{display:none}
details.pc>summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:12px}
.pc .top{display:flex;justify-content:space-between;gap:8px;align-items:center}
.pc .nm{font-weight:700;min-width:0}
.chip{font-size:.72rem;padding:2px 8px;border-radius:999px;white-space:nowrap;font-weight:600;border:1px solid currentColor}
.chip.crit{color:var(--crit)}.chip.warn{color:var(--warn)}.chip.good{color:var(--good)}.chip.done{color:var(--done)}
.pc .st{font-size:.82rem;color:var(--ink2)}
.bar{height:6px;background:var(--o0);border-radius:3px;overflow:hidden}
.bar i{display:block;height:100%;background:var(--accent);border-radius:3px}
.pc .why{font-size:.8rem;color:var(--crit)}
.pc .more{font-size:.74rem;color:var(--accent)}
details[open] .more{display:none}
.ms{margin:0;padding:0 14px 12px;list-style:none;display:grid;gap:3px;font-size:.82rem;border-top:1px dashed var(--line);padding-top:8px}
.ms li{display:grid;grid-template-columns:72px 1fr;gap:8px;color:var(--ink2)}
.ms li.ok{color:var(--ink3);text-decoration:line-through;text-decoration-color:var(--line)}
.ms li .dt{font-variant-numeric:tabular-nums}
.ms li.next{color:var(--ink);font-weight:700}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;background:var(--card);border:1px solid var(--line);border-radius:12px}
.legend{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:.78rem;color:var(--ink2);margin:8px 2px 0}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
svg text{font-family:var(--font)}
.gantt .lab{fill:var(--ink2);font-size:12px}
.gantt .tick{fill:var(--ink3);font-size:11px}
.gantt .grid{stroke:var(--line);stroke-width:1}
.gantt .today{stroke:var(--crit);stroke-width:2;stroke-dasharray:4 3}
.gantt .todayl{fill:var(--crit);font-size:11px;font-weight:700}
.gantt rect.seg{stroke:var(--card);stroke-width:1.5}
.gantt .s1{fill:var(--s1)}.gantt .s2{fill:var(--s2)}.gantt .s3{fill:var(--s3)}.gantt .s4{fill:var(--s4)}
.gantt .ho{fill:var(--ink);stroke:var(--card);stroke-width:1.5}
.gwrap{display:flex;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.glabels{flex:0 0 auto;border-right:1px solid var(--line);padding-left:8px;padding-right:8px;background:var(--card)}
.gl{height:var(--rh);line-height:var(--rh);font-size:12px;color:var(--ink2);white-space:nowrap;text-align:right}
.gl.on{color:var(--accent);font-weight:700}
.gscroll{flex:1 1 auto;min-width:0;border:0;border-radius:0}
.gantt g.row{cursor:pointer}.gantt g.row.on rect[fill='transparent']{fill:var(--accent-soft)}
#tip{min-height:1.4em;font-size:.82rem;color:var(--ink2);margin:6px 4px 0}
table.mx{border-collapse:separate;border-spacing:3px;width:100%;min-width:420px;font-size:.78rem}
table.mx th{font-weight:600;color:var(--ink2);text-align:center;padding:6px 4px}
table.mx th.r{text-align:left;white-space:nowrap;padding-right:8px}
table.mx td{text-align:center;border-radius:5px;padding:7px 4px;white-space:nowrap}
td.o0{background:var(--o0);color:var(--o0-ink)}td.o1{background:var(--o1);color:var(--o1-ink)}td.o2{background:var(--o2);color:var(--o2-ink);font-weight:600}
td.na{background:transparent;color:var(--ink3)}
.vend{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px}
.vend div{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:9px 12px;font-size:.85rem;min-width:0}
.vend b{display:block}
.vend .it{color:var(--ink3);font-size:.75rem}
.flag{display:inline-block;font-size:.7rem;color:var(--crit);border:1px solid var(--crit);border-radius:999px;padding:0 6px;margin:4px 4px 0 0}
table.fin{border-collapse:collapse;width:100%;font-size:.84rem;min-width:520px}
table.fin th,table.fin td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:right;font-variant-numeric:tabular-nums}
table.fin th:first-child,table.fin td:first-child{text-align:left}
table.fin th{color:var(--ink2);font-weight:600}
.note{font-size:.8rem;color:var(--ink3)}
.checks{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 14px;margin:0;list-style:none;display:grid;gap:6px;font-size:.86rem}
footer{color:var(--ink3);font-size:.75rem;text-align:center}
@media (max-width:480px){header h1{font-size:1.25rem}.kpi .v{font-size:1.2rem}.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""

JS = """
(function(){var t=document.querySelector('.gantt .today'),sc=t&&t.closest('.scroll');
if(sc){var x=parseFloat(t.getAttribute('x1'));sc.scrollLeft=Math.max(0,x-sc.clientWidth*0.35);}})();
(function(){var tip=document.getElementById('tip');if(!tip)return;
document.querySelectorAll('.gantt g.row').forEach(function(g){g.addEventListener('click',function(){
document.querySelectorAll('.gantt g.row.on,.gl.on').forEach(function(x){x.classList.remove('on')});g.classList.add('on');
var i=Array.prototype.indexOf.call(g.parentNode.querySelectorAll('g.row'),g);var l=document.querySelector('.gl[data-i="'+i+'"]');if(l)l.classList.add('on');
tip.textContent=g.getAttribute('data-info');});});})();
"""


def _gantt_svg(wb: Workbook, asof: dt.date, names: list[str]) -> str:
    g = A.gantt_frame(wb)
    g = g[g["공사명"].isin(names)]
    ev = A.milestone_events(wb)
    ho = {r["공사명"]: r["날짜"] for _, r in ev[ev["key"] == "HANDOVER"].iterrows()}
    if g.empty:
        return "<p class='note'>일정 데이터가 없습니다.</p>"
    start = min(g["시작"].min(), asof).replace(day=1)
    end_raw = max(g["종료"].max(), max(ho.values()) if ho else asof, asof)
    end = (end_raw.replace(day=28) + dt.timedelta(days=5)).replace(day=1)
    LW, W, RH, TOP = 6, 680, 26, 30
    days = (end - start).days or 1
    x = lambda d: LW + (d - start).days / days * (W - LW - 10)  # noqa: E731
    H = TOP + RH * len(names) + 8
    out = [f"<svg class='gantt' width='{W}' height='{H}' viewBox='0 0 {W} {H}' role='img' "
           f"aria-label='공사별 공정 일정표'>"]
    m = start
    while m <= end:
        xx = x(m)
        out.append(f"<line class='grid' x1='{xx:.1f}' y1='{TOP - 6}' x2='{xx:.1f}' y2='{H - 6}'/>")
        if m.month in (1, 4, 7, 10):
            out.append(f"<text class='tick' x='{xx + 3:.1f}' y='{TOP - 12}'>{m:%y.%m}</text>")
        m = (m.replace(day=28) + dt.timedelta(days=5)).replace(day=1)
    for i, n in enumerate(names):
        y = TOP + i * RH
        segs = g[g["공사명"] == n]
        info = [f"{n}"] + [f"{r['단계']} {r['시작']:%y.%m.%d}~{r['종료']:%y.%m.%d}" for _, r in segs.iterrows()]
        if n in ho:
            info.append(f"인도 {ho[n]:%y.%m.%d}")
        out.append(f"<g class='row' data-info='{E(' · '.join(info))}'>")
        out.append(f"<rect x='0' y='{y}' width='{W}' height='{RH}' fill='transparent'/>")
        for _, r in segs.iterrows():
            x1, x2 = x(r["시작"]), x(r["종료"])
            out.append(f"<rect class='seg {SEG[r['단계']]}' x='{x1:.1f}' y='{y + 5}' width='{max(x2 - x1, 3):.1f}' "
                       f"height='{RH - 10}' rx='3'/>")
        if n in ho:
            hx, hy = x(ho[n]), y + RH / 2
            out.append(f"<path class='ho' d='M{hx:.1f} {hy - 6:.1f} L{hx + 6:.1f} {hy:.1f} L{hx:.1f} {hy + 6:.1f} "
                       f"L{hx - 6:.1f} {hy:.1f} Z'/>")
        out.append("</g>")
    tx = x(asof)
    out.append(f"<line class='today' x1='{tx:.1f}' y1='{TOP - 4}' x2='{tx:.1f}' y2='{H - 4}'/>")
    anchor = "end" if tx > W - 80 else "start"
    out.append(f"<text class='todayl' x='{tx + (-4 if anchor == 'end' else 4):.1f}' y='{TOP - 1}' "
               f"text-anchor='{anchor}'>오늘 {asof:%m.%d}</text>")
    out.append("</svg>")
    labels = "".join(f"<div class='gl' data-i='{i}'>{E(short_name(n))}</div>" for i, n in enumerate(names))
    # 공사명 칸은 고정, 막대 영역만 옆으로 스크롤
    return (f"<div class='gwrap'><div class='glabels' style='padding-top:{TOP}px;--rh:{RH}px'>{labels}</div>"
            f"<div class='scroll gscroll'>{''.join(out)}</div></div>")


def build_html(wb: Workbook, asof: dt.date, source_label: str = "") -> str:
    t = A.project_table(wb, asof)
    fin = A.finance_summary(wb, asof)
    rank = {"위험": 0, "주의": 1, "정상": 2, "완료": 3}
    t = t.assign(_r=t["상태"].map(rank), _d=t["인도까지"].fillna(99999)).sort_values(["_r", "_d"])
    active = t[t["상태"] != "완료"]
    month_end = (asof.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    ho_month = t[t["인도일"].notna() & (t["인도일"] >= asof) & (t["인도일"] <= month_end)]
    P = []

    # ---- header
    P.append(f"<header><span class='badge'>업무 현황 보고</span><span class='badge'>기준 {asof:%Y.%m.%d}</span>"
             f"<h1>{E(wb.company or '')} 공사·외주 현황</h1>"
             f"<div class='meta'>엑셀 작성일 {wb.report_date or '-'} · REV {E(wb.revision or '-')}"
             f"{' · ' + E(source_label) if source_label else ''}</div></header>")

    # ---- KPI
    k = [("진행 중 공사", f"{len(active)}건", f"전체 {len(t)}건 · 평균 진척 {active['진척도'].mean():.0f}%" if len(active) else "", ""),
         ("이번 달 인도", f"{len(ho_month)}건", ", ".join(short_name(n) for n in ho_month["공사명"]) or "없음", ""),
         ("위험 · 주의", f"{(t['상태'] == '위험').sum()} · {(t['상태'] == '주의').sum()}", "일정 충돌·임박", "")]
    if wb.orders:
        k += [("총 수주액", won(fin["total_order"]), f"{len(wb.orders)}건", ""),
              ("수금 (수금률)", won(fin["collected"]), f"{fin['collect_rate']:.0f}%" if fin["collect_rate"] is not None else "", ""),
              ("미수금", won(fin["receivable"]), f"연체 {len(fin['overdue'])}건 {won(fin['overdue_amt'])}", "")]
    else:
        k += [("수주 · 수금", "미입력", "수주·수금 시트 추가 후 표시", "na")]
    P.append("<section class='kpis'>" + "".join(
        f"<div class='kpi {c}'><div class='l'>{E(a)}</div><div class='v'>{E(b)}</div><div class='s'>{E(s)}</div></div>"
        for a, b, s, c in k) + "</section>")

    # ---- 확인 필요
    flagged = t[t["상태"].isin(["위험", "주의"])]
    items = [f"<div class='alert {STATUS_CLS[r['상태']]}'>{STATUS_ICON[r['상태']]} <b>{E(r['공사명'])}</b>"
             f"<div class='why'>{E(r['사유'])}</div></div>" for _, r in flagged.iterrows()]
    items += [f"<div class='alert crit'>⛔ <b>수금 연체 · {E(c['project'])} {E(c.get('kind') or '')}</b>"
              f"<div class='why'>예정 {c['due_date']:%y.%m.%d} · {won(c.get('billed'))}</div></div>" for c in fin["overdue"]]
    P.append("<section><h2>확인 필요 <small>" + str(len(items)) + "건</small></h2><div class='list'>"
             + ("".join(items) or "<div class='note'>특이사항 없음</div>") + "</div></section>")

    # ---- 30일
    ev = A.milestone_events(wb)
    ev = ev[(ev["날짜"] >= asof) & (ev["날짜"] <= asof + dt.timedelta(days=30))].sort_values("날짜")
    rows = [(r["날짜"], r["공사명"], ("인도 🚢" if r["key"] == "HANDOVER" else r["일정"])) for _, r in ev.iterrows()]
    rows += [(c["due_date"], c["project"], f"{c.get('kind') or ''} 수금 예정 {won(c.get('billed'))}")
             for c in wb.collections if c.get("due_date") and not c.get("paid_date")
             and asof <= c["due_date"] <= asof + dt.timedelta(days=30)]
    rows.sort(key=lambda r: r[0])
    cal = "".join(f"<div class='d'>{d:%m.%d}<span>D-{(d - asof).days}</span></div>"
                  f"<div class='t'>{E(n)} <em>· {E(w)}</em></div>" for d, n, w in rows)
    P.append("<section><h2>앞으로 30일 <small>" + f"{asof:%m.%d}–{asof + dt.timedelta(days=30):%m.%d}</small></h2>"
             + (f"<div class='cal'>{cal}</div>" if rows else "<div class='note'>예정된 일정이 없습니다.</div>") + "</section>")

    # ---- 공사 카드
    by_name = {p.name: p for p in wb.projects}
    cards = []
    for _, r in t.iterrows():
        p = by_name[r["공사명"]]
        st = r["상태"]
        dd = r["인도까지"]
        chip = f"인도 D-{int(dd)}" if pd.notna(dd) and dd >= 0 else st
        nxt = A.next_milestone(p, asof)
        ms = []
        for m in sorted(p.milestones.values(), key=lambda m: m.date):
            cls = "ok" if m.date <= asof else ("next" if nxt and m.key == nxt.key else "")
            ms.append(f"<li class='{cls}'><span class='dt'>{m.date:%y.%m.%d}</span><span>{E(m.name)}</span></li>")
        money = ""
        if pd.notna(r.get("수주금액")):
            money = f"<div class='st'>수주 {won(r['수주금액'])} · 수금 {won(r['수금액'])} · 미수 {won(r['미수금'])}</div>"
        cards.append(
            f"<details class='pc'><summary><div class='top'><span class='nm'>{E(r['공사명'])}</span>"
            f"<span class='chip {STATUS_CLS[st]}'>{E(chip)}</span></div>"
            f"<div class='st'>{E(r['현재 단계'])} · <b>{r['진척도']:.0f}%</b> · 다음: {E(r['다음 일정'])}</div>"
            f"<div class='bar'><i style='width:{r['진척도']:.0f}%'></i></div>{money}"
            + (f"<div class='why'>{E(r['사유'])}</div>" if r["사유"] else "")
            + "<div class='more'>눌러서 전체 일정 보기</div></summary>"
            f"<ul class='ms'>{''.join(ms)}</ul></details>")
    P.append("<section><h2>공사별 현황 <small>위험·임박 순 · 카드를 누르면 상세</small></h2>"
             f"<div class='cards'>{''.join(cards)}</div></section>")

    # ---- 간트
    order = [p.name for p in wb.projects]
    leg = "".join(f"<span><i style='background:var(--{c})'></i>{E(s)}</span>" for s, c in SEG.items())
    P.append("<section><h2>공정 일정 <small>옆으로 밀어서 보기 · 줄을 누르면 날짜</small></h2>"
             f"{_gantt_svg(wb, asof, order)}"
             f"<div class='legend'>{leg}<span>◆ 인도</span><span style='color:var(--crit)'>┆ 오늘</span></div>"
             "<div id='tip'></div></section>")

    # ---- 외주 진척
    mx = A.outsourcing_matrix(wb, asof)
    if not mx.empty:
        pk = [w[0] for w in config.WORK_PACKAGES]
        head = "<tr><th></th>" + "".join(f"<th>{E(x)}</th>" for x in pk) + "</tr>"
        body = []
        for n in order:
            sub = mx[mx["공사명"] == n]
            if sub.empty:
                continue
            tds = []
            for pkg in pk:
                c = sub[sub["패키지"] == pkg]
                if c.empty:
                    tds.append("<td class='na'>–</td>")
                else:
                    s = c.iloc[0]["상태"]
                    label = {"발주 전": "발주 전", "발주·제작중": "제작 중", "완료": "완료"}[s]
                    tds.append(f"<td class='{OUT_CLS[s]}'>{label}</td>")
            body.append(f"<tr><th class='r'>{E(short_name(n))}</th>{''.join(tds)}</tr>")
        done = (mx["상태"] == "완료").mean() * 100
        P.append(f"<section><h2>외주 진척 <small>납품 완료 {done:.0f}% · 제작 중 {(mx['상태'] == '발주·제작중').sum()}건"
                 f" · 발주 전 {(mx['상태'] == '발주 전').sum()}건</small></h2>"
                 f"<div class='scroll' style='padding:6px'><table class='mx'>{head}{''.join(body)}</table></div>"
                 "<div class='legend'><span><i style='background:var(--o0)'></i>발주 전</span>"
                 "<span><i style='background:var(--o1)'></i>발주·제작 중</span>"
                 "<span><i style='background:var(--o2)'></i>납품 완료</span></div></section>")

    # ---- 외주업체 (연락처 제외)
    main_v = [v for v in wb.vendors if v.category != "MISC"]
    if main_v:
        vs = "".join(f"<div><span class='it'>{E(v.item)}</span><b>{E(v.name)}</b>"
                     + "".join(f"<span class='flag'>{E(f)}</span>" for f in v.risk_flags) + "</div>" for v in main_v)
        P.append("<section><h2>주요 외주업체 <small>주의 표시는 엑셀 '특성' 기준 · 연락처 생략</small></h2>"
                 f"<div class='vend'>{vs}</div></section>")

    # ---- 자금
    if wb.orders or wb.collections:
        fr = t[t["수주금액"].notna()]
        trs = "".join(f"<tr><td>{E(r['공사명'])}</td><td>{won(r['수주금액'])}</td><td>{won(r['수금액'])}</td>"
                      f"<td>{won(r['미수금'])}</td></tr>" for _, r in fr.iterrows())
        P.append("<section><h2>수주 · 수금 <small>"
                 f"수금률 {fin['collect_rate']:.0f}% · 30일 내 수금 예정 {won(fin['soon_amt'])}</small></h2>"
                 "<div class='scroll'><table class='fin'><tr><th>공사</th><th>수주</th><th>수금</th><th>미수</th></tr>"
                 f"{trs}</table></div></section>" if fin["collect_rate"] is not None else "")
    else:
        P.append("<section><h2>수주 · 수금</h2><p class='note'>현재 엑셀에는 수주금액·수금일이 없습니다. "
                 "수주·수금 입력 양식을 채워 올리면 다음 보고부터 표시됩니다.</p></section>")

    # ---- 점검
    chk = [m for lvl, m in wb.warnings if lvl in ("check", "warn", "error")]
    if chk:
        P.append("<section><h2>엑셀 확인 요청 <small>담당자 확인 필요</small></h2><ul class='checks'>"
                 + "".join(f"<li>🔍 {E(m)}</li>" for m in chk) + "</ul></section>")

    P.append(f"<footer>기준일 이전 날짜는 완료로 간주 · 생성 {dt.datetime.now():%Y-%m-%d %H:%M}</footer>")

    title = f"{wb.company or ''} 업무 현황 {asof:%m.%d}".strip()
    return ("<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
            f"<title>{E(title)}</title><style>{CSS}</style></head><body><main class='wrap'>"
            + "".join(P) + f"</main><script>{JS}</script></body></html>")
