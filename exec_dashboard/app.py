"""㈜원이엔지 대표 대시보드 — 수주·수금·공정·외주 진척을 한 화면에서.

실행:  streamlit run exec_dashboard/app.py
직원은 클라우드 폴더(구글드라이브/원드라이브/드롭박스/NAS 동기화 폴더)에 '업무 현황' 엑셀을 올리기만 하면 된다.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from core import analytics as A                       # noqa: E402
from core.history import HistoryStore                  # noqa: E402
from core.parser import parse_workbook, to_snapshot    # noqa: E402
from core.sources import GoogleDriveSource, LocalFolderSource, load_service_account  # noqa: E402
from core.template import build_finance_template, demo_finance  # noqa: E402

st.set_page_config(page_title="원이엔지 경영 대시보드", page_icon="📊", layout="wide")

# ------------------------------------------------------------------ 스타일 / 색
SERIES = {"설계·승인": "#2a78d6", "외주 발주→납품": "#eb6834", "설치·시운전": "#1baf7a", "인도 준비": "#eda100"}
STATUS = {"위험": ("#d03b3b", "⛔"), "주의": ("#fab219", "⚠️"), "정상": ("#0ca30c", "✅"), "완료": ("#8a8984", "🏁")}
OUT_STATUS = {"발주 전": "#e9e8e4", "발주·제작중": "#86b6ef", "완료": "#256abf"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e1"

st.markdown("""
<style>
.block-container{padding-top:1.4rem;max-width:1500px}
.kpi{background:#fff;border:1px solid #e6e5e1;border-radius:12px;padding:14px 16px;height:100%}
.kpi .l{font-size:.82rem;color:#52514e;margin-bottom:4px}
.kpi .v{font-size:1.65rem;font-weight:700;color:#0b0b0b;line-height:1.2}
.kpi .s{font-size:.78rem;color:#6b6a66;margin-top:4px}
.hdr{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;flex-wrap:wrap;margin-bottom:.6rem}
.hdr h1{font-size:1.6rem;margin:0}
.hdr .meta{color:#52514e;font-size:.85rem}
.pill{display:inline-block;padding:2px 8px;border-radius:10px;font-size:.78rem;background:#f1f0ec;color:#33322f;margin-right:4px}
.alert{border-left:4px solid;padding:8px 12px;margin:6px 0;background:#fff;border-radius:6px;font-size:.9rem}
</style>""", unsafe_allow_html=True)


def won(v, unit="억") -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "-"
    if unit == "억":
        return f"{v / 1e8:,.2f}억"
    return f"{v / 1e4:,.0f}만"


def kpi(col, label, value, sub=""):
    col.markdown(f"<div class='kpi'><div class='l'>{label}</div><div class='v'>{value}</div>"
                 f"<div class='s'>{sub}</div></div>", unsafe_allow_html=True)


def base_layout(fig, height):
    fig.update_layout(height=height, margin=dict(l=8, r=8, t=36, b=8), plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb",
                      font=dict(family="Noto Sans KR, sans-serif", color=INK2, size=12),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None),
                      hoverlabel=dict(bgcolor="#fff", font_color=INK))
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID)
    return fig


# ------------------------------------------------------------------ 설정 (secrets > 환경변수 > 기본값)
def setting(key, default=""):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:  # secrets.toml 없음
        pass
    return os.environ.get(key, default)


DEFAULT_DIR = setting("WATCH_DIR", str(HERE / "inbox"))
HISTORY_DIR = setting("HISTORY_DIR", str(HERE / ".history"))

# ------------------------------------------------------------------ 사이드바
with st.sidebar:
    st.header("📁 데이터")
    has_drive = bool(setting("GDRIVE_FOLDER_ID")) and bool(setting("GDRIVE_SERVICE_ACCOUNT"))
    modes = (["Google Drive 폴더"] if has_drive else []) + ["동기화 폴더", "파일 직접 올리기"]
    mode = st.radio("엑셀 가져올 곳", modes, label_visibility="collapsed")
    folder = DEFAULT_DIR
    if mode == "동기화 폴더":
        folder = st.text_input("폴더 경로", DEFAULT_DIR,
                               help="구글드라이브·원드라이브·드롭박스·NAS 동기화 폴더. 직원이 여기에 올리면 자동 반영됩니다.")
    uploaded = st.file_uploader("엑셀 업로드", type=["xlsx", "xlsm"], accept_multiple_files=True) \
        if mode == "파일 직접 올리기" else None

    st.header("📅 기준일")
    asof_mode = st.radio("기준일", ["오늘", "보고서 작성일", "직접 선택"], horizontal=True, label_visibility="collapsed")
    asof_pick = st.date_input("날짜", dt.date.today()) if asof_mode == "직접 선택" else None
    refresh = st.select_slider("새 파일 확인 주기", ["끔", "1분", "5분", "15분"], value="5분")
    demo = st.toggle("금액 예시로 미리보기", value=False,
                     help="수주·수금 시트가 아직 없을 때 화면 구성을 보기 위한 가상 금액입니다.")


# ------------------------------------------------------------------ 파일 수집
def get_source():
    if mode == "Google Drive 폴더":
        return GoogleDriveSource(setting("GDRIVE_FOLDER_ID"), load_service_account(setting("GDRIVE_SERVICE_ACCOUNT")))
    return LocalFolderSource(folder)


@st.cache_data(show_spinner=False, max_entries=64)
def parse_cached(uid: str, name: str, _loader):
    return parse_workbook(_loader(), name)


entries = []
if mode == "파일 직접 올리기":
    for f in uploaded or []:
        data = f.getvalue()
        entries.append((f"up:{f.name}:{len(data)}:{hash(data)}", f.name, dt.datetime.now(), (lambda d=data: d)))
else:
    src = get_source()
    try:
        files = src.list_files() if src.available() else []
    except Exception as e:  # 드라이브 권한 등
        st.error(f"{src.label} 읽기 실패: {e}")
        files = []
    entries = [(f.uid, f.name, f.modified, f.load) for f in files]

if not entries:
    st.title("원이엔지 경영 대시보드")
    st.info("아직 읽을 엑셀이 없습니다. 왼쪽에서 폴더를 지정하거나 파일을 올려 주세요.\n\n"
            f"현재 폴더: `{folder}`")
    st.stop()

parsed = []
for uid, name, mod, loader in entries[:20]:
    try:
        parsed.append((parse_cached(uid, name, loader), name, mod))
    except Exception as e:
        st.warning(f"'{name}' 읽기 실패: {e}")

status_files = [x for x in parsed if x[0].projects]
fin_files = [x for x in parsed if x[0].has_finance]
if not status_files:
    st.error("'업무 현황' 형식의 엑셀을 찾지 못했습니다. (공사명/승인도/발주/납품 머리글 필요)")
    st.stop()
wb, wb_name, wb_mod = status_files[0]  # 가장 최근 수정본
fin_src = None
if not wb.has_finance and fin_files:
    fin_src = fin_files[0]
    wb.orders, wb.collections, wb.outsourcing = fin_src[0].orders, fin_src[0].collections, fin_src[0].outsourcing

if asof_mode == "보고서 작성일" and wb.report_date:
    asof = wb.report_date
elif asof_mode == "직접 선택":
    asof = asof_pick
else:
    asof = dt.date.today()

is_demo = False
if demo and not wb.has_finance:
    wb.orders, wb.collections, wb.outsourcing = demo_finance(wb.projects, asof)
    is_demo = True

# 버전 이력 저장
hist = HistoryStore(HISTORY_DIR)
snap = to_snapshot(wb)
try:
    hist.save(snap)
except OSError:
    pass

# 자동 새로고침: 폴더의 최신 파일이 바뀌면 전체 다시 그리기
if refresh != "끔" and mode != "파일 직접 올리기":
    secs = {"1분": 60, "5분": 300, "15분": 900}[refresh]
    first_uid = entries[0][0]

    @st.fragment(run_every=secs)
    def _watch():
        try:
            fl = get_source().list_files()
            if fl and fl[0].uid != first_uid:
                st.rerun(scope="app")
        except Exception:
            pass
    _watch()

# ------------------------------------------------------------------ 계산
clients = sorted({p.client for p in wb.projects})
with st.sidebar:
    st.header("🔎 필터")
    sel_clients = st.multiselect("고객사", clients, default=clients)
    hide_done = st.checkbox("인도 완료 공사 숨기기", value=False)

table = A.project_table(wb, asof)
table = table[table["고객사"].isin(sel_clients)]
if hide_done:
    table = table[table["상태"] != "완료"]
names = set(table["공사명"])
fin = A.finance_summary(wb, asof)

# ------------------------------------------------------------------ 헤더
src_txt = f"{wb_name} · 수정 {wb_mod:%Y-%m-%d %H:%M}"
if fin_src:
    src_txt += f" · 금액: {fin_src[1]}"
st.markdown(f"<div class='hdr'><h1>{wb.company or '경영'} 대시보드</h1>"
            f"<div class='meta'>기준일 <b>{asof:%Y-%m-%d}</b> · 보고서 작성일 {wb.report_date or '-'} · REV {wb.revision or '-'}"
            f"<br>{src_txt}</div></div>", unsafe_allow_html=True)
if is_demo:
    st.warning("⚠️ 금액은 **예시 데이터**입니다. 실제 수주·수금 시트를 올리면 자동으로 대체됩니다.")

# ------------------------------------------------------------------ KPI
active = table[table["상태"] != "완료"]
n_risk = int((table["상태"] == "위험").sum())
n_warn = int((table["상태"] == "주의").sum())
month_end = (asof.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
ho_month = table[table["인도일"].notna() & (table["인도일"] >= asof) & (table["인도일"] <= month_end)]
c = st.columns(6)
kpi(c[0], "진행 중 공사", f"{len(active)}건", f"전체 {len(table)}건 · 평균 진척 {active['진척도'].mean():.0f}%" if len(active) else "")
kpi(c[1], "이번 달 인도 예정", f"{len(ho_month)}건", ", ".join(ho_month["공사명"].head(2)) or "없음")
kpi(c[2], "⛔ 위험 / ⚠️ 주의", f"{n_risk} / {n_warn}", "일정 충돌·임박 기준")
if wb.orders:
    kpi(c[3], "총 수주액", won(fin["total_order"]), f"{len(wb.orders)}건")
    kpi(c[4], "수금액 (수금률)", won(fin["collected"]),
        f"{fin['collect_rate']:.0f}% 수금" if fin["collect_rate"] is not None else "")
    kpi(c[5], "미수금 · 연체", won(fin["receivable"]),
        f"연체 {len(fin['overdue'])}건 {won(fin['overdue_amt'])} · 30일내 {won(fin['soon_amt'])}")
else:
    for col, lab in zip(c[3:], ["총 수주액", "수금액", "미수금"]):
        kpi(col, lab, "미입력", "수주·수금 시트를 추가하세요")

st.write("")
tab_over, tab_gantt, tab_out, tab_fin, tab_hist, tab_check = st.tabs(
    ["🏠 한눈에 보기", "🗓️ 공정 일정", "🏭 외주 진척", "💰 수주·수금", "🔁 변경 이력", "🩺 데이터 점검"])

# ------------------------------------------------------------------ 1. 한눈에 보기
with tab_over:
    left, right = st.columns([2.3, 1])
    with left:
        st.subheader("공사별 현황")
        view = table.copy()
        view["상태"] = view["상태"].map(lambda s: f"{STATUS[s][1]} {s}")
        cols = ["상태", "공사명", "현재 단계", "진척도", "다음 일정", "인도일", "인도까지", "사유"]
        if wb.orders:
            cols[5:5] = ["수주금액", "수금액", "미수금"]
            for k in ("수주금액", "수금액", "미수금"):
                view[k] = view[k] / 1e6
        st.dataframe(view[cols], hide_index=True, use_container_width=True, height=min(640, 38 + 35 * len(view)),
                     column_config={
                         "진척도": st.column_config.ProgressColumn("진척도", format="%.0f%%", min_value=0, max_value=100),
                         "인도일": st.column_config.DateColumn("인도일", format="YY.MM.DD"),
                         "인도까지": st.column_config.NumberColumn("인도까지", format="D-%d"),
                         "수주금액": st.column_config.NumberColumn("수주(백만)", format="%,.0f"),
                         "수금액": st.column_config.NumberColumn("수금(백만)", format="%,.0f"),
                         "미수금": st.column_config.NumberColumn("미수(백만)", format="%,.0f"),
                         "사유": st.column_config.TextColumn("확인 사유", width="medium"),
                     })
    with right:
        st.subheader("앞으로 30일")
        ev = A.milestone_events(wb)
        ev = ev[ev["공사명"].isin(names) & (ev["날짜"] >= asof) & (ev["날짜"] <= asof + dt.timedelta(days=30))]
        fin_ev = [(c_["due_date"], c_["project"], f"💰 {c_['kind']} 수금 예정 {won(c_.get('billed'))}")
                  for c_ in wb.collections if c_.get("due_date") and not c_.get("paid_date")
                  and asof <= c_["due_date"] <= asof + dt.timedelta(days=30)]
        items = [(r["날짜"], r["공사명"], ("🚢 " if r["key"] == "HANDOVER" else "• ") + r["일정"]) for _, r in ev.iterrows()]
        items = sorted(items + fin_ev)
        if not items:
            st.caption("예정된 일정이 없습니다.")
        for d, pn, what in items[:18]:
            st.markdown(f"<div class='alert' style='border-color:#2a78d6'><b>{d:%m/%d}</b> "
                        f"<span class='pill'>D-{(d - asof).days}</span> {pn}<br>{what}</div>", unsafe_allow_html=True)

        st.subheader("대표 확인 필요")
        flagged = table[table["상태"].isin(["위험", "주의"])].sort_values("상태", key=lambda s: s.map({"위험": 0, "주의": 1}))
        for _, r in flagged.iterrows():
            colr, ic = STATUS[r["상태"]]
            st.markdown(f"<div class='alert' style='border-color:{colr}'>{ic} <b>{r['상태']}</b> · {r['공사명']}"
                        f"<br><span style='color:#52514e'>{r['사유']}</span></div>", unsafe_allow_html=True)
        for c_ in fin["overdue"]:
            st.markdown(f"<div class='alert' style='border-color:#d03b3b'>⛔ <b>수금 연체</b> · {c_['project']} {c_['kind']}"
                        f"<br><span style='color:#52514e'>예정 {c_['due_date']:%y.%m.%d} · {won(c_.get('billed'))}</span></div>",
                        unsafe_allow_html=True)
        if flagged.empty and not fin["overdue"]:
            st.caption("특이사항 없음 ✅")

    st.subheader("단계별 공사 분포")
    stage_counts = table["현재 단계"].value_counts().reindex(A.STAGE_ORDER).dropna()
    fig = go.Figure(go.Bar(x=stage_counts.values, y=stage_counts.index, orientation="h", marker_color="#2a78d6",
                           text=stage_counts.values.astype(int), textposition="outside",
                           hovertemplate="%{y}: %{x}건<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(base_layout(fig, 60 + 34 * len(stage_counts)), use_container_width=True)

# ------------------------------------------------------------------ 2. 공정 일정 (간트)
with tab_gantt:
    g = A.gantt_frame(wb)
    g = g[g["공사명"].isin(names)]
    order = [p.name for p in wb.projects if p.name in names]
    fig = go.Figure()
    for stage, color in SERIES.items():
        d = g[g["단계"] == stage]
        if d.empty:
            continue
        fig.add_trace(go.Bar(
            name=stage, y=d["공사명"], base=pd.to_datetime(d["시작"]),
            x=(pd.to_datetime(d["종료"]) - pd.to_datetime(d["시작"])).dt.total_seconds() * 1000,
            orientation="h", marker=dict(color=color, line=dict(color="#fcfcfb", width=2)),
            customdata=list(zip(d["시작"].astype(str), d["종료"].astype(str))),
            hovertemplate="<b>%{y}</b><br>" + stage + ": %{customdata[0]} ~ %{customdata[1]}<extra></extra>"))
    ev = A.milestone_events(wb)
    ho = ev[(ev["key"] == "HANDOVER") & ev["공사명"].isin(names)]
    fig.add_trace(go.Scatter(name="인도", x=pd.to_datetime(ho["날짜"]), y=ho["공사명"], mode="markers",
                             marker=dict(symbol="diamond", size=11, color=INK, line=dict(color="#fcfcfb", width=2)),
                             hovertemplate="<b>%{y}</b><br>인도 %{x|%Y-%m-%d}<extra></extra>"))
    fig.add_vline(x=pd.Timestamp(asof).value / 1e6, line=dict(color="#d03b3b", width=2, dash="dot"))
    fig.add_annotation(x=pd.Timestamp(asof), y=1.0, yref="paper", text=f"기준일 {asof:%y.%m.%d}", showarrow=False,
                       font=dict(color="#d03b3b"), yanchor="bottom")
    fig.update_layout(barmode="overlay", xaxis_type="date")
    fig.update_yaxes(categoryorder="array", categoryarray=order[::-1])
    st.plotly_chart(base_layout(fig, 120 + 34 * len(order)), use_container_width=True)
    st.caption("막대: 설계(승인도)→외주 발주→납품→설치·시운전→인도 준비 / ◆ 인도일 / 빨간 점선: 기준일")

    with st.expander("공사별 전체 일정표 (엑셀 원문 포함)"):
        pick = st.selectbox("공사 선택", order)
        p = next(x for x in wb.projects if x.name == pick)
        rows = sorted(p.milestones.values(), key=lambda m: m.date)
        st.dataframe(pd.DataFrame([{"일정": m.name, "날짜": m.date, "상태": "완료" if m.date <= asof else f"D-{(m.date - asof).days}",
                                    "원문": m.source} for m in rows]), hide_index=True, use_container_width=True)
        if p.timeline_notes:
            st.markdown("**엑셀 타임라인 메모**")
            for t in p.timeline_notes:
                st.markdown(f"- {t}")

# ------------------------------------------------------------------ 3. 외주 진척
with tab_out:
    mx = A.outsourcing_matrix(wb, asof)
    mx = mx[mx["공사명"].isin(names)] if not mx.empty else mx
    if mx.empty:
        st.info("외주 발주/납품 일정이 없습니다.")
    else:
        pk = ["서포트", "하우징", "장비", "보온재·설치"]
        a, b, cc = st.columns(3)
        kpi(a, "외주 패키지", f"{len(mx)}건", "공사 × (서포트·하우징·장비·설치)")
        kpi(b, "발주·제작 중", f"{(mx['상태'] == '발주·제작중').sum()}건", "납품 대기")
        kpi(cc, "납품 완료율", f"{(mx['상태'] == '완료').mean() * 100:.0f}%", f"발주 전 {(mx['상태'] == '발주 전').sum()}건")
        st.write("")
        piv = mx.pivot_table(index="공사명", columns="패키지", values="점수", aggfunc="first").reindex(columns=pk)
        piv = piv.reindex([n for n in order if n in piv.index])
        lab = mx.pivot_table(index="공사명", columns="패키지", values="상태", aggfunc="first").reindex(index=piv.index, columns=pk)
        ven = mx.pivot_table(index="공사명", columns="패키지", values="업체", aggfunc="first").reindex(index=piv.index, columns=pk)
        po = mx.assign(d=mx["발주일"].astype(str)).pivot_table(index="공사명", columns="패키지", values="d", aggfunc="first").reindex(index=piv.index, columns=pk)
        dl = mx.assign(d=mx["납품일"].astype(str)).pivot_table(index="공사명", columns="패키지", values="d", aggfunc="first").reindex(index=piv.index, columns=pk)
        custom = [[[lab.iat[i, j] if pd.notna(lab.iat[i, j]) else "해당 없음", ven.iat[i, j] if pd.notna(ven.iat[i, j]) else "-",
                    po.iat[i, j] if pd.notna(po.iat[i, j]) else "-", dl.iat[i, j] if pd.notna(dl.iat[i, j]) else "-"]
                   for j in range(len(pk))] for i in range(len(piv))]
        text = [[(lab.iat[i, j] if pd.notna(lab.iat[i, j]) else "") for j in range(len(pk))] for i in range(len(piv))]
        fig = go.Figure(go.Heatmap(
            z=piv.values, x=pk, y=piv.index, zmin=0, zmax=2, xgap=3, ygap=3,
            colorscale=[[0, OUT_STATUS["발주 전"]], [.33, OUT_STATUS["발주 전"]], [.34, OUT_STATUS["발주·제작중"]],
                        [.66, OUT_STATUS["발주·제작중"]], [.67, OUT_STATUS["완료"]], [1, OUT_STATUS["완료"]]],
            showscale=False, text=text, texttemplate="%{text}", textfont=dict(size=11),
            customdata=custom,
            hovertemplate="<b>%{y}</b> · %{x}<br>%{customdata[0]}<br>업체: %{customdata[1]}"
                          "<br>발주 %{customdata[2]} → 납품 %{customdata[3]}<extra></extra>"))
        fig.update_yaxes(autorange="reversed")
        fig.update_xaxes(side="top")
        st.plotly_chart(base_layout(fig, 80 + 32 * len(piv)), use_container_width=True)
        st.caption("■ 연회색 발주 전 · ■ 하늘색 발주·제작 중 · ■ 파랑 납품 완료 (칸에 마우스를 올리면 업체·일자 표시)")

        st.subheader("업체별 진행 물량")
        vv = mx.assign(업체=mx["업체"].replace("", "미지정")).groupby(["업체", "상태"]).size().unstack(fill_value=0)
        vv = vv.reindex(columns=["완료", "발주·제작중", "발주 전"], fill_value=0)
        fig = go.Figure()
        for stt in vv.columns:
            fig.add_trace(go.Bar(name=stt, y=vv.index, x=vv[stt], orientation="h",
                                 marker=dict(color=OUT_STATUS[stt], line=dict(color="#fcfcfb", width=2)),
                                 hovertemplate="%{y} · " + stt + ": %{x}건<extra></extra>"))
        fig.update_layout(barmode="stack")
        st.plotly_chart(base_layout(fig, 90 + 36 * len(vv)), use_container_width=True)

    st.subheader("외주업체 특성 · 리스크")
    if not wb.vendors:
        st.caption("'발주업체 현황과 특성' 시트가 없습니다.")
    main_v = [v for v in wb.vendors if v.category != "MISC"]
    cols3 = st.columns(3)
    for i, v in enumerate(main_v):
        flags = " ".join(f"<span class='pill' style='background:#fde7e7;color:#8f1f1f'>⚠ {f}</span>" for f in v.risk_flags)
        traits = v.traits.replace("\n", "<br>")
        cols3[i % 3].markdown(
            f"<div class='kpi' style='margin-bottom:10px'><div class='l'>{v.item}</div>"
            f"<div class='v' style='font-size:1.15rem'>{v.name}</div>"
            f"<div class='s'>{v.contact} · {v.phone_mail.splitlines()[0] if v.phone_mail else ''}</div>"
            f"<div class='s' style='color:#33322f;margin-top:6px'>{traits}</div><div style='margin-top:6px'>{flags}</div></div>",
            unsafe_allow_html=True)
    misc = [v for v in wb.vendors if v.category == "MISC"]
    if misc:
        with st.expander(f"소모품·인터넷 구매처 {len(misc)}곳"):
            st.dataframe(pd.DataFrame([{"품목": v.item, "구매처": v.name, "비고": v.traits} for v in misc]),
                         hide_index=True, use_container_width=True)

# ------------------------------------------------------------------ 4. 수주·수금
with tab_fin:
    tpl = build_finance_template([p.name for p in wb.projects], {p.name: p.client for p in wb.projects})
    if not wb.orders and not wb.collections:
        st.info("현재 엑셀에는 **수주금액·수금일 정보가 없습니다.** 아래 양식을 내려받아 직원이 채운 뒤 "
                "같은 클라우드 폴더에 올리면(별도 파일 또는 업무 현황 엑셀에 시트 추가) 이 화면이 자동으로 채워집니다. "
                "왼쪽 **[금액 예시로 미리보기]** 를 켜면 완성된 화면을 미리 볼 수 있습니다.")
        st.download_button("📥 수주·수금·외주비 입력 양식 받기 (공사명 자동 기입)", tpl, "수주수금_입력양식.xlsx")
    else:
        a, b, c_, d = st.columns(4)
        kpi(a, "총 수주액", won(fin["total_order"]), f"외주비 {won(fin['out_total'])}")
        kpi(b, "예상 매출총이익", won(fin["gross_margin"]),
            f"{fin['gross_margin'] / fin['total_order'] * 100:.0f}% (수주-외주비)" if fin["total_order"] else "")
        kpi(c_, "수금 / 미수금", f"{won(fin['collected'])} / {won(fin['receivable'])}",
            f"수금률 {fin['collect_rate']:.0f}%" if fin["collect_rate"] is not None else "")
        kpi(d, "30일 내 자금", f"+{won(fin['soon_amt'])} / -{won(fin['out_soon_amt'])}", "수금 예정 / 외주 지급 예정")
        st.write("")

        l, r = st.columns([1.3, 1])
        with l:
            st.subheader("공사별 수주 대비 수금")
            t = table[table["수주금액"].notna()].copy()
            fig = go.Figure()
            fig.add_trace(go.Bar(name="수금", y=t["공사명"], x=t["수금액"].fillna(0) / 1e8, orientation="h",
                                 marker=dict(color="#2a78d6", line=dict(color="#fcfcfb", width=2)),
                                 hovertemplate="%{y}<br>수금 %{x:.2f}억<extra></extra>"))
            fig.add_trace(go.Bar(name="미수", y=t["공사명"], x=t["미수금"].fillna(0) / 1e8, orientation="h",
                                 marker=dict(color="#cde2fb", line=dict(color="#fcfcfb", width=2)),
                                 hovertemplate="%{y}<br>미수 %{x:.2f}억<extra></extra>"))
            fig.update_layout(barmode="stack", xaxis_title="억원")
            fig.update_yaxes(categoryorder="array", categoryarray=list(t["공사명"])[::-1])
            st.plotly_chart(base_layout(fig, 90 + 30 * len(t)), use_container_width=True)
        with r:
            st.subheader("월별 자금 흐름")
            cf = A.cashflow_frame(wb)
            if cf.empty:
                st.caption("수금/지급 일자가 없습니다.")
            else:
                cf = cf.groupby(["월", "구분"], as_index=False)["금액"].sum()
                cf["월"] = pd.to_datetime(cf["월"]).dt.strftime("%y.%m")
                months = sorted(cf["월"].unique())
                colors = {"수금 실적": "#2a78d6", "수금 예정": "#9ec5f4", "외주 지급 실적": "#eb6834", "외주 지급 예정": "#f5b89f"}
                fig = go.Figure()
                for k, col in colors.items():
                    d_ = cf[cf["구분"] == k]
                    if not d_.empty:
                        fig.add_trace(go.Bar(name=k, x=d_["월"], y=d_["금액"] / 1e8, marker=dict(color=col, line=dict(color="#fcfcfb", width=1)),
                                             hovertemplate="%{x} " + k + " %{y:.2f}억<extra></extra>"))
                net = cf.groupby("월")["금액"].sum().reindex(months)
                fig.add_trace(go.Scatter(name="순현금", x=net.index, y=net.values / 1e8, mode="lines+markers",
                                         line=dict(color=INK, width=2), marker=dict(size=8, line=dict(color="#fcfcfb", width=2)),
                                         hovertemplate="%{x} 순현금 %{y:.2f}억<extra></extra>"))
                cur = asof.strftime("%y.%m")
                if cur in months:
                    fig.add_vline(x=months.index(cur), line=dict(color="#d03b3b", width=1, dash="dot"))
                fig.update_layout(barmode="relative", yaxis_title="억원", bargap=0.25)
                fig.update_xaxes(type="category", categoryorder="array", categoryarray=months)
                st.plotly_chart(base_layout(fig, 420), use_container_width=True)

        st.subheader("수금 일정")
        cdf = pd.DataFrame(wb.collections)
        if not cdf.empty:
            cdf = cdf[cdf["project"].isin(names)]

            def _st(r_):
                if r_.get("paid_date"):
                    return "✅ 수금완료"
                if r_.get("due_date") and r_["due_date"] < asof:
                    return f"⛔ 연체 {(asof - r_['due_date']).days}일"
                if r_.get("due_date") and r_["due_date"] <= asof + dt.timedelta(days=30):
                    return "⚠️ 30일 내"
                return "예정"
            cdf["상태"] = cdf.apply(_st, axis=1)
            only_open = st.checkbox("미수금만 보기", value=True)
            if only_open:
                cdf = cdf[~cdf["상태"].str.startswith("✅")]
            cdf = cdf.sort_values("due_date")
            for dc in ("due_date", "paid_date"):
                cdf[dc] = pd.to_datetime(cdf[dc])
            for ac in ("billed", "paid"):
                cdf[ac] = pd.to_numeric(cdf[ac], errors="coerce")
            cdf["note"] = cdf["note"].fillna("")
            st.dataframe(cdf.rename(columns={"project": "공사명", "kind": "구분", "due_date": "청구예정일", "billed": "청구금액",
                                             "paid_date": "수금일", "paid": "수금액", "note": "비고"})
                         [["상태", "공사명", "구분", "청구예정일", "청구금액", "수금일", "수금액", "비고"]],
                         hide_index=True, use_container_width=True,
                         column_config={"청구예정일": st.column_config.DateColumn(format="YY.MM.DD"),
                                        "수금일": st.column_config.DateColumn(format="YY.MM.DD"),
                                        "청구금액": st.column_config.NumberColumn(format="%,.0f"),
                                        "수금액": st.column_config.NumberColumn(format="%,.0f")})
        st.download_button("📥 입력 양식 다시 받기", tpl, "수주수금_입력양식.xlsx")

# ------------------------------------------------------------------ 5. 변경 이력
with tab_hist:
    prev = hist.previous_of(snap["file_hash"])
    snaps = hist.all()
    st.caption(f"저장된 버전 {len(snaps)}개 · 직원이 파일을 올릴 때마다 일정 요약이 자동 저장되어 이전 버전과 비교합니다.")
    if not prev:
        st.info("비교할 이전 버전이 아직 없습니다. 다음 업로드부터 '무엇이 바뀌었는지'가 여기에 표시됩니다.")
    else:
        st.markdown(f"**이전 버전** {prev.get('file_name')} (저장 {prev.get('saved_at', '')}) → **현재** {wb_name}")
        df = A.diff_snapshots(prev, snap)
        if df.empty:
            st.success("이전 버전과 일정 변화 없음")
        else:
            late = df[df["차이(일)"].fillna(0) > 0]
            if not late.empty:
                st.error(f"⛔ 일정이 늦춰진 항목 {len(late)}건 — 최대 {int(late['차이(일)'].max())}일 지연")
            st.dataframe(df, hide_index=True, use_container_width=True)

# ------------------------------------------------------------------ 6. 데이터 점검
with tab_check:
    st.caption("엑셀 작성 실수나 시트 간 불일치를 자동으로 찾아냅니다. 담당 직원에게 확인을 요청하세요.")
    icon = {"error": "⛔", "check": "🔍", "warn": "⚠️", "info": "ℹ️"}
    order_w = {"error": 0, "check": 1, "warn": 2, "info": 3}
    if not wb.warnings:
        st.success("발견된 문제 없음")
    for lvl, msg in sorted(wb.warnings, key=lambda w: order_w.get(w[0], 9)):
        st.markdown(f"{icon.get(lvl, '•')} {msg}")
    with st.expander("읽어 들인 파일 목록"):
        st.dataframe(pd.DataFrame([{"파일": n, "수정": m, "공사 수": len(w.projects), "금액 시트": w.has_finance,
                                    "시트": ", ".join(w.sheets)} for w, n, m in parsed]),
                     hide_index=True, use_container_width=True)
