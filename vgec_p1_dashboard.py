# -*- coding: utf-8 -*-
"""
VGEC-HP/VTE P1-Hybrid — CAD 상세설계 사양서 v0.1 대시보드
FIG.2 → STEP/STL → LPBF/CNC → Assembly → Inspection

실행: streamlit run vgec_p1_dashboard.py
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.interpolate import CubicSpline

st.set_page_config(
    page_title="VGEC-P1 CAD 설계 대시보드",
    page_icon="🌀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------- Palette
# 고정 카테고리 순서 (순환 금지): blue, amber, teal, purple
C_BLUE = "#2563EB"
C_AMBER = "#D97706"
C_TEAL = "#0D9488"
C_PURPLE = "#7C3AED"
C_INK = "#1E293B"
C_MUTED = "#64748B"
C_GRID = "#E2E8F0"
C_SURFACE = "#FFFFFF"

PROC_COLOR = {"LPBF": C_BLUE, "CNC": C_AMBER, "구매품": C_TEAL, "Laser-cut": C_PURPLE, "SLS": C_PURPLE}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=Noto+Sans+KR:wght@300;400;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', 'Noto Sans KR', sans-serif !important; }
.stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown li,
label, [data-testid="stMarkdownContainer"] * { color: #1e293b !important; }
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], .block-container {
    background-color: #F8FAFC !important;
}
.vgec-header {
    background: rgba(255,255,255,0.9); border: 1px solid rgba(0,0,0,0.05);
    border-radius: 16px; padding: 22px 30px; margin-bottom: 1.2rem;
    box-shadow: 0 8px 30px rgba(0,0,0,0.04);
}
.vgec-title {
    margin: 0; font-size: 2.0rem; font-weight: 800; letter-spacing: -0.5px;
    background: linear-gradient(90deg, #2563EB, #0D9488);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.vgec-sub { margin: 6px 0 0 0; color: #64748b !important; font-size: 1.0rem; font-weight: 600; }
.kpi-card {
    background: #fff; border: 1px solid #E2E8F0; border-radius: 12px;
    padding: 14px 16px; text-align: center; height: 100%;
    box-shadow: 0 2px 8px rgba(0,0,0,0.03);
}
.kpi-label { color: #64748b !important; font-size: 0.78rem; font-weight: 600; letter-spacing: 0.4px; }
.kpi-value { color: #1e293b !important; font-size: 1.45rem; font-weight: 800; margin-top: 2px; }
.kpi-unit { color: #94a3b8 !important; font-size: 0.75rem; }
.flow-chip {
    display: inline-block; background: #EFF6FF; border: 1px solid #BFDBFE;
    color: #1D4ED8 !important; border-radius: 999px; padding: 5px 13px;
    font-size: 0.82rem; font-weight: 700; margin: 3px 1px;
}
.flow-arrow { color: #94a3b8 !important; font-weight: 800; margin: 0 2px; }
.stTabs [data-baseweb="tab"] { font-weight: 700; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="vgec-header">
  <p class="vgec-title">VGEC-HP/VTE P1-Hybrid · CAD 상세설계 대시보드</p>
  <p class="vgec-sub">사양서 v0.1 — FIG.2 → STEP/STL → LPBF/CNC → Assembly → Inspection · 모든 기준치는 [DESIGN-0]</p>
  <div style="margin-top:10px;">
    <span class="flow-chip">TEC / Heater</span><span class="flow-arrow">→</span>
    <span class="flow-chip">Cu Spreader</span><span class="flow-arrow">→</span>
    <span class="flow-chip">Vapor Chamber</span><span class="flow-arrow">→</span>
    <span class="flow-chip">Radial Heat Pipes ×6</span><span class="flow-arrow">→</span>
    <span class="flow-chip">Gradient Wavy Fin ×36</span><span class="flow-arrow">→</span>
    <span class="flow-chip">Thermal Chimney</span><span class="flow-arrow">→</span>
    <span class="flow-chip">Passive Entrainment</span><span class="flow-arrow">→</span>
    <span class="flow-chip">Ambient</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- Sidebar: Parametric Design Kernel (§52)
st.sidebar.markdown("## 🌀 Parametric Design Kernel")
st.sidebar.caption("§52 — DOE / Bayesian Optimization center point. 값을 바꾸면 모든 곡선·3D가 즉시 갱신됩니다.")

N_f = st.sidebar.slider("Fin 개수  N_f", 24, 48, 36, 2)
H = st.sidebar.slider("Fin 유효높이  H (mm)", 50, 80, 60, 5)
t_f = st.sidebar.select_slider("Fin 두께  t_f (mm) — DOE", options=[0.9, 1.0, 1.2], value=1.0)
R_m = st.sidebar.slider("중간 반경  R_m (mm)", 40, 60, 50, 1)
dR = st.sidebar.slider("반경 변화량  ΔR (mm)", 10, 30, 20, 1)
D_ch = st.sidebar.slider("Chimney ID  D (mm)", 48, 55, 50, 1)
root_R = st.sidebar.select_slider("Fin Root R (mm) — DOE", options=[0.5, 1.0, 1.5], value=1.0)
phase_mode = st.sidebar.radio("위상차 ψᵢ (§14)", ["P1: ψᵢ = 0 (동일 위상)", "차세대: 교대 위상 0 / π"])
theta_dif = st.sidebar.select_slider("Diffuser 반각 (°) — DOE", options=[5, 7, 10], value=7)
slot_h = st.sidebar.select_slider("Entrainment slot (mm) — DOE", options=[5.0, 7.5, 10.0], value=7.5)
st.sidebar.markdown("---")
st.sidebar.caption("N_HP = 6 × Ø6.0 mm (고정) · Heater 50/75/100/125 W")

# ---------------------------------------------------------------- Gradient functions (§9–14)
xi = np.linspace(0.0, 1.0, 241)
z = xi * H

def R_o(x):
    """§10 Hourglass outer envelope: R_o = R_m + ΔR(2ξ-1)²"""
    return R_m + dR * (2.0 * x - 1.0) ** 2

# §12 진폭: C2 연속 spline 권장 → natural cubic spline through (0,0.6),(0.5,2.0),(1,0.8)
A_spline = CubicSpline([0.0, 0.5, 1.0], [0.6, 2.0, 0.8], bc_type="natural")
def A_pw(x):
    return np.where(x < 0.5, 0.6 + 2.8 * x, 3.4 - 2.6 * x)

# §13 파장: spline through (0,28),(0.5,20),(1,28)
lam_spline = CubicSpline([0.0, 0.5, 1.0], [28.0, 20.0, 28.0], bc_type="natural")

P_theta = 2.0 * np.pi * R_o(xi) / N_f          # §11 local pitch
A_z = A_spline(xi)
lam_z = lam_spline(xi)

def camber(psi):
    """§14 fin camber: r = R_base + A sin(2πz/λ + ψ)"""
    return R_o(xi) + A_z * np.sin(2.0 * np.pi * z / lam_z + psi)

# ---------------------------------------------------------------- Tabs
tab_ov, tab_geo, tab_bom, tab_gdt, tab_doe, tab_gate = st.tabs(
    ["📐 설계 개요", "🌀 Gradient Fin 기하", "🔧 BOM · 공정", "📏 GD&T · CTQ", "🧪 DOE · 인과검증", "✅ Freeze Gate"]
)

# ================================================================ TAB 1 — 개요
with tab_ov:
    st.markdown("### P1 기준 Envelope (§2)")
    kpis = [
        ("최대 외경", "Ø160", "mm"), ("전체 높이", "≈145", "mm"),
        ("Fin 유효높이", f"{H}", "mm"), ("Fin 개수", f"{N_f}", "EA"),
        ("Fin 두께", f"{t_f}", "mm"), ("Chimney ID", f"Ø{D_ch}", "mm"),
        ("Heat Pipe", "6 × Ø6", "mm"), ("Heater 검증", "50–125", "W"),
    ]
    cols = st.columns(8)
    for c, (label, val, unit) in zip(cols, kpis):
        c.markdown(
            f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{val}</div><div class="kpi-unit">{unit}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("")
    c1, c2 = st.columns([1.15, 1.0])

    with c1:
        st.markdown("#### 제조전략 (§1) — 첫 시제품에서 2상 열수송장치는 개발하지 않는다")
        strat = pd.DataFrame({
            "구분": ["금속 AM (LPBF)", "CNC 정밀가공", "구매품"],
            "대상 부품": [
                "Gradient Wavy Fin · Thermal Chimney · Entrainment Ring · Top Diffuser",
                "Copper Spreader · Cold Plate · 정밀 datum/interface",
                "Vapor Chamber · Heat Pipe · TEC",
            ],
        })
        st.dataframe(strat, hide_index=True, use_container_width=True)

        st.markdown("#### Thermal Contact Stack (§33–34) — TIM은 절대 0 mm로 모델링하지 않는다")
        stack = [
            ("Gradient Fin / HP Interface", C_BLUE), ("Vapor Chamber (구매품)", C_TEAL),
            ("Copper Spreader 90×90×3", C_AMBER), ("TIM-1 (BLT 0.10–0.20 mm)", C_MUTED),
            ("TEC / Heater 40×40", C_PURPLE), ("TIM-2 (BLT 0.10–0.20 mm)", C_MUTED),
            ("Cold Plate 60×60×5", C_AMBER),
        ]
        fig_stack = go.Figure()
        for i, (name, color) in enumerate(stack):
            y = len(stack) - i
            fig_stack.add_shape(type="rect", x0=0.06, x1=0.94, y0=y - 0.36, y1=y + 0.36,
                                fillcolor=color, opacity=0.16, line=dict(color=color, width=1.5))
            fig_stack.add_annotation(x=0.5, y=y, text=f"<b>{name}</b>", showarrow=False,
                                     font=dict(size=12, color=C_INK))
        fig_stack.update_xaxes(visible=False, range=[0, 1])
        fig_stack.update_yaxes(visible=False, range=[0.3, len(stack) + 0.7])
        fig_stack.update_layout(height=310, margin=dict(l=8, r=8, t=6, b=6),
                                paper_bgcolor=C_SURFACE, plot_bgcolor=C_SURFACE)
        st.plotly_chart(fig_stack, use_container_width=True)

    with c2:
        st.markdown("#### 치수 고정 우선순위 (§51) — 외형은 내부 열저항 네트워크의 결과")
        prio = ["1. Heat Source footprint", "2. Vapor Chamber active area", "3. Heat Pipe routing",
                "4. HP–Fin interface", "5. Gradient functions", "6. Pressure-flow path",
                "7. Outer envelope (Ø160)"]
        fig_p = go.Figure(go.Bar(
            x=list(range(len(prio), 0, -1)), y=prio, orientation="h",
            marker=dict(color=[C_BLUE] * 4 + ["#93C5FD"] * 3, cornerradius=4),
            text=["최우선", "", "", "", "", "", "최후순위"], textposition="outside",
            hovertemplate="%{y}<extra></extra>",
        ))
        fig_p.update_yaxes(autorange="reversed", tickfont=dict(size=12, color=C_INK))
        fig_p.update_xaxes(visible=False, range=[0, 8.6])
        fig_p.update_layout(height=250, margin=dict(l=8, r=8, t=6, b=6),
                            paper_bgcolor=C_SURFACE, plot_bgcolor=C_SURFACE, showlegend=False)
        st.plotly_chart(fig_p, use_container_width=True)

        st.markdown("#### 좌표계 · Datum (§3–4)")
        st.markdown(f"""
| 기준 | 정의 | 기능 |
|---|---|---|
| **Origin O** | TEC 중심축 ∩ Spreader 중심축 | 전 부품 공통 |
| **+Z** | Chimney 배출방향 | 적층/조립축 |
| **+X** | HP No.1 (161) 방사방향 | 각도 기준 0° |
| **Datum A** | VC/Fin 하부 mounting plane (CNC) | Z·조립높이·열접촉 |
| **Datum B** | System central axis | 동심도·Chimney축 |
| **Datum C** | HP-1 locating slot/dowel | 회전 indexing |

주요 부품 DRF = **A \\| B \\| C** 통일 · 정렬은 screw가 아니라 **dowel/pilot** (§31)
""")

    st.markdown("#### Zone 정의 (§18) — CAD feature tree에서 별도 parameter group")
    fig_zone = go.Figure()
    zones = [(0.00, 0.25, "ZONE 1 · Intake", C_TEAL),
             (0.25, 0.75, "ZONE 2 · Heat-transfer intensification", C_BLUE),
             (0.75, 1.00, "ZONE 3 · Exhaust recovery", C_AMBER)]
    for lo, hi, name, color in zones:
        fig_zone.add_shape(type="rect", x0=lo * H, x1=hi * H, y0=0, y1=1,
                           fillcolor=color, opacity=0.15, line=dict(color=color, width=1.5))
        fig_zone.add_annotation(x=(lo + hi) / 2 * H, y=0.5, text=f"<b>{name}</b><br>ξ = {lo:.2f} – {hi:.2f}",
                                showarrow=False, font=dict(size=12, color=C_INK))
    fig_zone.update_yaxes(visible=False)
    fig_zone.update_xaxes(title_text="z (mm)  —  ξ = z/H", color=C_MUTED, gridcolor=C_GRID)
    fig_zone.update_layout(height=150, margin=dict(l=8, r=8, t=6, b=6),
                           paper_bgcolor=C_SURFACE, plot_bgcolor=C_SURFACE)
    st.plotly_chart(fig_zone, use_container_width=True)

# ================================================================ TAB 2 — 기하
with tab_geo:
    st.markdown("### Gradient Wavy Fin — 수학적 정의 (§9–17)")
    st.latex(r"R_o(z)=R_m+\Delta R\,(2\xi-1)^2 \qquad "
             r"r_i(z)=R_{base}(z)+A(z)\sin\!\Big[\tfrac{2\pi z}{\lambda(z)}+\psi_i\Big] \qquad \xi=\tfrac{z}{H}")

    g1, g2 = st.columns(2)

    with g1:
        # Hourglass envelope
        fig_env = go.Figure()
        fig_env.add_trace(go.Scatter(x=R_o(xi), y=z, mode="lines", name="Outer envelope",
                                     line=dict(color=C_BLUE, width=2.5),
                                     hovertemplate="R_o = %{x:.1f} mm @ z = %{y:.0f} mm<extra></extra>"))
        fig_env.add_trace(go.Scatter(x=-R_o(xi), y=z, mode="lines", showlegend=False,
                                     line=dict(color=C_BLUE, width=2.5), hoverinfo="skip"))
        for s in (1, -1):
            fig_env.add_trace(go.Scatter(x=[s * D_ch / 2, s * D_ch / 2], y=[0, H], mode="lines",
                                         name="Chimney ID" if s == 1 else None, showlegend=(s == 1),
                                         line=dict(color=C_AMBER, width=2, dash="dash"), hoverinfo="skip"))
        for xx, yy, txt in [(R_o(0), 0, f"Ø{2*R_o(0):.0f}"), (R_m, H / 2, f"Ø{2*R_m:.0f}"), (R_o(1), H, f"Ø{2*R_o(1):.0f}")]:
            fig_env.add_annotation(x=xx, y=yy, text=f"<b>{txt}</b>", showarrow=True, arrowhead=0,
                                   ax=34, ay=0, font=dict(size=12, color=C_INK))
        fig_env.update_xaxes(title_text="r (mm)", gridcolor=C_GRID, zerolinecolor=C_GRID, color=C_MUTED)
        fig_env.update_yaxes(title_text="z (mm)", gridcolor=C_GRID, color=C_MUTED)
        fig_env.update_layout(title=dict(text="§10 Hourglass Envelope — Wide → Narrow → Wide (sharp transition 금지)",
                                         font=dict(size=13, color=C_INK)),
                              height=360, margin=dict(l=8, r=8, t=40, b=8), legend=dict(orientation="h", y=-0.18),
                              paper_bgcolor=C_SURFACE, plot_bgcolor=C_SURFACE, hovermode="y unified")
        st.plotly_chart(fig_env, use_container_width=True)

        # Pitch
        fig_pitch = go.Figure(go.Scatter(
            x=z, y=P_theta, mode="lines", line=dict(color=C_TEAL, width=2.5),
            hovertemplate="P_θ = %{y:.2f} mm @ z = %{x:.0f} mm<extra></extra>"))
        fig_pitch.add_annotation(x=0, y=P_theta[0], text=f"<b>{P_theta[0]:.1f} mm</b>", showarrow=True, ax=28, ay=-18)
        fig_pitch.add_annotation(x=H / 2, y=P_theta.min(), text=f"<b>{P_theta.min():.1f} mm</b>", showarrow=True, ax=0, ay=24)
        fig_pitch.update_xaxes(title_text="z (mm)", gridcolor=C_GRID, color=C_MUTED)
        fig_pitch.update_yaxes(title_text="pitch (mm)", gridcolor=C_GRID, color=C_MUTED)
        fig_pitch.update_layout(title=dict(text=f"§11 Local Circumferential Pitch  P_θ = 2πR_o/N_f  (N_f = {N_f})",
                                           font=dict(size=13, color=C_INK)),
                                height=280, margin=dict(l=8, r=8, t=40, b=8),
                                paper_bgcolor=C_SURFACE, plot_bgcolor=C_SURFACE)
        st.plotly_chart(fig_pitch, use_container_width=True)

    with g2:
        # Amplitude & wavelength — 서로 다른 스케일 → 이중축 대신 차트 2개
        fig_amp = go.Figure()
        fig_amp.add_trace(go.Scatter(x=z, y=A_z, mode="lines", name="C2 spline (권장)",
                                     line=dict(color=C_PURPLE, width=2.5),
                                     hovertemplate="A = %{y:.2f} mm @ z = %{x:.0f} mm<extra></extra>"))
        fig_amp.add_trace(go.Scatter(x=z, y=A_pw(xi), mode="lines", name="piecewise linear (초기식)",
                                     line=dict(color="#C4B5FD", width=1.5, dash="dot"), hoverinfo="skip"))
        fig_amp.update_xaxes(title_text="z (mm)", gridcolor=C_GRID, color=C_MUTED)
        fig_amp.update_yaxes(title_text="A (mm)", gridcolor=C_GRID, color=C_MUTED)
        fig_amp.update_layout(title=dict(text="§12 Wave Amplitude A(z) — Low → High → Low (0.6 / 2.0 / 0.8 mm)",
                                         font=dict(size=13, color=C_INK)),
                              height=280, margin=dict(l=8, r=8, t=40, b=8), legend=dict(orientation="h", y=-0.25),
                              paper_bgcolor=C_SURFACE, plot_bgcolor=C_SURFACE, hovermode="x unified")
        st.plotly_chart(fig_amp, use_container_width=True)

        fig_lam = go.Figure(go.Scatter(
            x=z, y=lam_z, mode="lines", line=dict(color=C_AMBER, width=2.5),
            hovertemplate="λ = %{y:.1f} mm @ z = %{x:.0f} mm<extra></extra>"))
        fig_lam.update_xaxes(title_text="z (mm)", gridcolor=C_GRID, color=C_MUTED)
        fig_lam.update_yaxes(title_text="λ (mm)", gridcolor=C_GRID, color=C_MUTED)
        fig_lam.update_layout(title=dict(text="§13 Wavelength λ(z) — Long → Short → Long (28 / 20 / 28 mm)",
                                         font=dict(size=13, color=C_INK)),
                              height=280, margin=dict(l=8, r=8, t=40, b=8),
                              paper_bgcolor=C_SURFACE, plot_bgcolor=C_SURFACE)
        st.plotly_chart(fig_lam, use_container_width=True)

        # Camber
        alternating = phase_mode.startswith("차세대")
        fig_cam = go.Figure()
        fig_cam.add_trace(go.Scatter(x=camber(0.0), y=z, mode="lines", name="fin i = even (ψ=0)",
                                     line=dict(color=C_BLUE, width=2.5),
                                     hovertemplate="r = %{x:.1f} mm @ z = %{y:.0f} mm<extra></extra>"))
        if alternating:
            fig_cam.add_trace(go.Scatter(x=camber(np.pi), y=z, mode="lines", name="fin i = odd (ψ=π)",
                                         line=dict(color=C_AMBER, width=2.5),
                                         hovertemplate="r = %{x:.1f} mm @ z = %{y:.0f} mm<extra></extra>"))
        fig_cam.add_trace(go.Scatter(x=R_o(xi), y=z, mode="lines", name="envelope R_o(z)",
                                     line=dict(color=C_MUTED, width=1.2, dash="dash"), hoverinfo="skip"))
        fig_cam.update_xaxes(title_text="r (mm)", gridcolor=C_GRID, color=C_MUTED)
        fig_cam.update_yaxes(title_text="z (mm)", gridcolor=C_GRID, color=C_MUTED)
        fig_cam.update_layout(title=dict(text="§14 Fin Camber r_i(z) — P1은 전 fin ψᵢ=0 통일", font=dict(size=13, color=C_INK)),
                              height=360, margin=dict(l=8, r=8, t=40, b=8), legend=dict(orientation="h", y=-0.16),
                              paper_bgcolor=C_SURFACE, plot_bgcolor=C_SURFACE)
        st.plotly_chart(fig_cam, use_container_width=True)

    # ---- 3D preview
    st.markdown("#### 3D Preview — Fin Array · Chimney · Envelope")
    with st.spinner("3D 모델 생성 중..."):
        theta_i = 2.0 * np.pi * np.arange(N_f) / N_f
        fig3d = go.Figure()
        # chimney cylinder
        tt = np.linspace(0, 2 * np.pi, 40)
        Tm, Zm = np.meshgrid(tt, np.linspace(0, H, 2))
        fig3d.add_trace(go.Surface(
            x=(D_ch / 2) * np.cos(Tm), y=(D_ch / 2) * np.sin(Tm), z=Zm,
            colorscale=[[0, "#FCD34D"], [1, "#FCD34D"]], opacity=0.35, showscale=False, hoverinfo="skip"))
        # fins: outer wavy edge lines
        for i, th in enumerate(theta_i):
            psi = np.pi if (alternating and i % 2 == 1) else 0.0
            r_edge = camber(psi)
            color = C_BLUE if psi == 0.0 else C_AMBER
            fig3d.add_trace(go.Scatter3d(
                x=r_edge * np.cos(th), y=r_edge * np.sin(th), z=z,
                mode="lines", line=dict(color=color, width=3.2),
                showlegend=False, hovertemplate=f"Fin {i:02d} · φ = {np.degrees(th):.0f}°<extra></extra>"))
        # envelope rings
        for x0 in (0.0, 0.5, 1.0):
            rr = R_o(x0)
            fig3d.add_trace(go.Scatter3d(
                x=rr * np.cos(tt), y=rr * np.sin(tt), z=np.full_like(tt, x0 * H),
                mode="lines", line=dict(color=C_MUTED, width=1.6, dash="dash"),
                showlegend=False, hoverinfo="skip"))
        fig3d.update_layout(
            height=560, margin=dict(l=0, r=0, t=6, b=0), paper_bgcolor=C_SURFACE,
            scene=dict(
                xaxis=dict(visible=False), yaxis=dict(visible=False),
                zaxis=dict(title="z (mm)", color=C_MUTED),
                aspectmode="data", camera=dict(eye=dict(x=1.5, y=1.5, z=0.9)),
            ))
        st.plotly_chart(fig3d, use_container_width=True)
    st.caption(f"Fin {N_f} EA · t_f {t_f} mm · Root R{root_R} (§15–16: sharp corner 금지, base taper 1.5→1.0 mm 권장) · "
               f"Chimney Ø{D_ch} bell-mouth R2–R4 (§17)")

# ================================================================ TAB 3 — BOM
with tab_bom:
    st.markdown("### Part List & 제조공정 (§6–8, §19–30)")
    bom = pd.DataFrame([
        ["001", "Top Diffuser", "LPBF", "AlSi10Mg (P0: PA12)", f"Ø155 × H15, outlet Ø55, 반각 {theta_dif}°", "DOE 5/7/10° · tool-less 교환"],
        ["002", "Top Retaining Ring", "LPBF", "AlSi10Mg", "Ø148 / ID Ø105–115 × t3", "rigid clamp 금지 — radial compliance"],
        ["003", "Thermal Chimney", "LPBF", "AlSi10Mg", f"ID Ø{D_ch}, H60–70", "Version S (Split) 필수 보존"],
        ["004", "Gradient Wavy Fin Array", "LPBF", "AlSi10Mg", f"{N_f} EA × t{t_f}, Ø140→100→140", "Version M (Mono)도 제작"],
        ["005", "Lower Support Ring", "LPBF + CNC", "AlSi10Mg", "Ø145 × t5", "하면 CNC → Datum A"],
        ["007", "Vapor Chamber", "구매품", "vendor", "110 × 110 × 3–4", "envelope만 CAD 반영"],
        ["008", "Copper Spreader", "CNC", "C1100 / OFHC", "90 × 90 × 3 (DOE 2/3/4)", "TEC면 flatness 0.05"],
        ["009", "TEC / Heater Dummy", "구매품", "—", "40 × 40, 50–125 W", "중앙+corner 온도점"],
        ["010", "Cold Plate", "CNC", "Al6061 / Cu", "60 × 60 × 5↑", "TEC면 flatness 0.05"],
        ["011", "Insulation Pad", "Laser-cut", "단열재", "—", "하부 열 bypass 차단 · sensor 채널"],
        ["013", "Base Housing", "SLS", "PA12", "—", "비열적 — controller/DAQ 수납"],
        ["161–166", "Heat Pipe ×6", "구매품", "Cu", "Ø6.0, 60° 간격", "161 = 0° = Datum C 기준"],
    ], columns=["Part No.", "부품명", "공정", "재료", "기준치수 (mm)", "비고"])
    st.dataframe(bom, hide_index=True, use_container_width=True, height=460)

    b1, b2 = st.columns([1, 1])
    with b1:
        st.markdown("#### Heat Pipe 배치 (§20–23) — 60° × 6, HP-161 = 0° (Datum C)")
        fig_hp = go.Figure()
        tt = np.linspace(0, 2 * np.pi, 120)
        for rr, cc, dash in [(80, C_MUTED, "dot"), (D_ch / 2, C_AMBER, "dash")]:
            fig_hp.add_trace(go.Scatter(x=rr * np.cos(tt), y=rr * np.sin(tt), mode="lines",
                                        line=dict(color=cc, width=1.4, dash=dash),
                                        showlegend=False, hoverinfo="skip"))
        hp_r = 45
        for k in range(6):
            ang = np.radians(60 * k)
            xh, yh = hp_r * np.cos(ang), hp_r * np.sin(ang)
            fig_hp.add_trace(go.Scatter(
                x=[D_ch / 2 * np.cos(ang), 72 * np.cos(ang)], y=[D_ch / 2 * np.sin(ang), 72 * np.sin(ang)],
                mode="lines", line=dict(color=C_BLUE, width=5), showlegend=False,
                hovertemplate=f"HP-{161+k} · {60*k}°<extra></extra>"))
            fig_hp.add_annotation(x=xh * 1.42, y=yh * 1.42, text=f"<b>{161+k}</b><br>{60*k}°",
                                  showarrow=False, font=dict(size=11, color=C_INK))
        fig_hp.add_annotation(x=0, y=0, text="<b>Ø" + str(D_ch) + "<br>chimney</b>", showarrow=False,
                              font=dict(size=10, color=C_AMBER))
        fig_hp.update_xaxes(visible=False, scaleanchor="y")
        fig_hp.update_yaxes(visible=False)
        fig_hp.update_layout(height=400, margin=dict(l=8, r=8, t=8, b=8),
                             paper_bgcolor=C_SURFACE, plot_bgcolor=C_SURFACE)
        st.plotly_chart(fig_hp, use_container_width=True)

    with b2:
        st.markdown("#### HP Groove & Clamp 규격 (§21–22) — P1은 brazing 없음")
        st.markdown(f"""
| 항목 | 값 |
|---|---|
| HP OD | Ø6.00 mm |
| Groove width / radius / depth | 6.3 / R3.10 / 3.0–3.1 mm |
| Diametral clearance | ≈0.2 mm 시작 |
| Groove profile tol. | 0.10–0.15 (after machining) |
| Clamp | bridge + 2×M3 + 얇은 TIM, 폭 10–12 mm |
| M3 center distance | 12–16 mm |
| 보호 | **mechanical stop** — 원형단면 찌그러짐 방지 |

**체결 표준화 (§31–32)**: M3(thermal core) + M4(main) 2종 한정 ·
M3 clearance Ø3.4 / M4 Ø4.5 · Dowel Ø3–4 ·
LPBF 나사산 직출력 대신 **pilot print → drill → tap** (§32)

**AM 제약 (§35–37)**: BUILD_DATUM 별도 생성 · Support Forbidden Zones
SFZ-1 fin 공기접촉면 / SFZ-2 chimney 내벽 / SFZ-3 HP groove ·
가공 stock: Datum A +0.5 / groove +0.2–0.3 / pilot bore undersize→ream
""")

# ================================================================ TAB 4 — GD&T · CTQ
with tab_gdt:
    st.markdown("### GD&T 기본 규칙 (§5) — 열접촉면만 정밀가공한다")
    g1, g2 = st.columns([1.05, 1])
    with g1:
        gdt = pd.DataFrame([
            ["Thermal interface surface", "Flatness", 0.05, "CNC/연삭"],
            ["일반 CNC mating surface", "Flatness", 0.10, "CNC"],
            ["HP groove", "Profile", 0.125, "0.10–0.15"],
            ["Chimney 수직도", "Perp. / 60mm", 0.20, "vs Datum A"],
            ["Fin profile", "Profile |A|B", 0.30, "시작치"],
            ["LPBF 외형", "Profile", 0.40, "0.30–0.50, 업체 협의"],
        ], columns=["대상", "특성", "공차 (mm)", "비고"])
        fig_gdt = go.Figure(go.Bar(
            y=gdt["대상"], x=gdt["공차 (mm)"], orientation="h",
            marker=dict(color=[C_TEAL, C_TEAL, C_BLUE, C_BLUE, C_AMBER, C_AMBER], cornerradius=4),
            text=[f"{v:.2f}" for v in gdt["공차 (mm)"]], textposition="outside",
            customdata=gdt["비고"], hovertemplate="%{y}: %{x:.2f} mm (%{customdata})<extra></extra>"))
        fig_gdt.update_yaxes(autorange="reversed", tickfont=dict(size=12, color=C_INK))
        fig_gdt.update_xaxes(title_text="공차 (mm) — 작을수록 정밀", gridcolor=C_GRID, color=C_MUTED, range=[0, 0.52])
        fig_gdt.update_layout(height=330, margin=dict(l=8, r=8, t=8, b=8),
                              paper_bgcolor=C_SURFACE, plot_bgcolor=C_SURFACE)
        st.plotly_chart(fig_gdt, use_container_width=True)
        st.caption("정밀(청록) → 표준(파랑) → AM 협의(주황). 실제 공차는 공급업체 DfAM review 후 조정.")

    with g2:
        st.markdown("#### Critical-to-Quality — CTQ 10항목 (§39)")
        st.markdown("""
| CTQ | 항목 | 관련 Datum/부품 |
|---|---|---|
| CTQ-01 | Datum A flatness | 005 하면 (CNC) |
| CTQ-02 | Chimney axis 수직도 | 003 vs A |
| CTQ-03 | Fin 최소두께 | 004 |
| CTQ-04 | Fin envelope profile | 004 vs A\\|B |
| CTQ-05 | HP groove 직경/profile | 005 |
| CTQ-06 | HP 각도위치 | 161–166 vs C |
| CTQ-07 | VC interface flatness | 007 접촉면 |
| CTQ-08 | Spreader flatness | 008 (0.05) |
| CTQ-09 | TEC stack height | 조립체 |
| CTQ-10 | 2차공기 흡입 유효면적 | E-RING |

**검사도면 원칙 (§38)**: 부품별 DESIGN + INSPECTION 2종 —
Gradient 곡선 전체를 CMM 측정하지 않고 **CTQ만** 검사한다.
""")

# ================================================================ TAB 5 — DOE
with tab_doe:
    st.markdown("### A/B/C/D 인과검증 전략 (§43–44) — 효과를 분리 가능한 구조로 설계")
    d1, d2 = st.columns([1.1, 1])
    with d1:
        fig_doe = go.Figure()
        cfgs = [("CFG-A", "Straight Fin", 0), ("CFG-B", "Uniform Wavy", 1),
                ("CFG-C", "Gradient Wavy", 2), ("CFG-D", "Gradient + Entrainment", 3)]
        effects = [("Wavy 효과", 0, 1), ("Gradient 효과", 1, 2), ("Entrainment 효과", 2, 3)]
        for name, sub, i in cfgs:
            fig_doe.add_shape(type="rect", x0=i - 0.38, x1=i + 0.38, y0=0, y1=1,
                              fillcolor=C_BLUE, opacity=0.10 + 0.09 * i, line=dict(color=C_BLUE, width=1.5))
            fig_doe.add_annotation(x=i, y=0.5, text=f"<b>{name}</b><br>{sub}", showarrow=False,
                                   font=dict(size=12, color=C_INK))
        for name, a, b in effects:
            fig_doe.add_annotation(x=(a + b) / 2, y=1.22, text=f"<b>Δ = {name}</b>", showarrow=False,
                                   font=dict(size=11, color=C_AMBER))
            fig_doe.add_annotation(x=b - 0.38, y=1.08, ax=a + 0.38, ay=1.08, xref="x", yref="y",
                                   axref="x", ayref="y", showarrow=True, arrowhead=2, arrowcolor=C_AMBER, arrowwidth=2)
        fig_doe.update_xaxes(visible=False, range=[-0.6, 3.6])
        fig_doe.update_yaxes(visible=False, range=[-0.15, 1.45])
        fig_doe.update_layout(height=240, margin=dict(l=8, r=8, t=8, b=8),
                              paper_bgcolor=C_SURFACE, plot_bgcolor=C_SURFACE)
        st.plotly_chart(fig_doe, use_container_width=True)
        st.latex(r"Effect_{Gradient}=Perf_C-Perf_B")
        st.latex(r"Effect_{Entrainment}=Perf_D-Perf_C")
        st.caption("4개 CFG는 동일 envelope · material · base · heater · VC · HP 공유 — 순수 기하효과만 분리")

        st.markdown("#### 교환형 부품 전략 (§40–42) — 본체 재출력 없이 DOE")
        st.markdown(f"""
| 교환부품 | 변형 | 현재 선택 |
|---|---|---|
| **E-RING** (Entrainment) | 05 / 075 / 10 (slot 5 / 7.5 / 10 mm) | slot {slot_h} mm |
| **DIF** (Diffuser) | 05 / 07 / 10 (반각 5 / 7 / 10°) | 반각 {theta_dif}° |

절대치수보다 **AR = A_secondary / A_primary** 를 관리 파라미터로 사용 (§40)
""")

    with d2:
        st.markdown("#### DOE Factor 요약")
        doe_tbl = pd.DataFrame([
            ["Fin 두께 t_f", "0.9 / 1.0 / 1.2 mm", f"{t_f}"],
            ["Fin Root R", "0.5 / 1.0 / 1.5 mm", f"{root_R}"],
            ["Diffuser 반각", "5 / 7 / 10°", f"{theta_dif}°"],
            ["Entrainment slot", "5 / 7.5 / 10 mm", f"{slot_h}"],
            ["Spreader 두께", "2 / 3 / 4 mm", "3"],
            ["위상차 ψᵢ", "0 통일 / 교대 0·π", "0 (P1)"],
            ["Heater 전력", "50 / 75 / 100 / 125 W", "sweep"],
        ], columns=["Factor", "수준", "Center point"])
        st.dataframe(doe_tbl, hide_index=True, use_container_width=True)

        st.markdown("#### 첫 금속 출력 세트 (§53) — 완제품 1개가 아니라")
        st.markdown("""
1. **Gradient Fin/Chimney Rev.A** ×1
2. **Straight Fin baseline** ×1
3. **Uniform Wavy baseline** ×1
4. **Entrainment Ring** ×3 (05/075/10)
5. **Diffuser** ×3 (05/07/10)

VC·HP·Spreader·Heater는 **공통 사용** →
고가 금속 AM 부품 최소화 + Geometry × Gradient × Entrainment × Diffuser
인과효과 분리 = **시제품 개발과 특허 데이터 확보 동시 만족**
""")
        st.markdown("#### 파일명 규칙 (§45–46)")
        st.code(f"VGEC-P1-004-FIN-GRAD-N{N_f}-T{int(t_f*10)}-R{int(root_R*10)}-REV_A.step\n"
                "Master: parametric CAD · 교환: STEP AP242 · AM: 3MF 우선 (STL은 Master 금지)",
                language=None)

# ================================================================ TAB 6 — Freeze Gate
with tab_gate:
    st.markdown("### Design Freeze Gate (§50) — 전 항목 통과 후에만 REV A 릴리즈")
    gate_items = [
        "Actual TEC STEP 확보", "Actual Vapor Chamber STEP 확보", "Heat Pipe bend radius 확보",
        "Heat Pipe thermal rating 확인", "VC mounting limit 확인", "Fin LPBF DfAM review 완료",
        "HP groove 제작검토 완료", "Powder escape 검토 완료", "Datum A/B/C 확정",
        "CTQ drawing 완료", "A/B/C/D configurations 생성", "Heater fixture 완료", "Sensor positions 완료",
    ]
    gc1, gc2 = st.columns([1, 1])
    checked = 0
    with gc1:
        st.markdown("#### 체크리스트")
        for idx, item in enumerate(gate_items):
            if st.checkbox(item, key=f"gate_{idx}"):
                checked += 1
        pct = checked / len(gate_items)
        st.progress(pct, text=f"**{checked} / {len(gate_items)}** 통과 ({pct*100:.0f}%)")
        if checked == len(gate_items):
            st.success("✅ 전 항목 통과 — **REV A · RELEASE FOR PROTOTYPE** 변경 가능")
        else:
            st.warning(f"⏳ {len(gate_items) - checked}개 항목 미완 — STEP Release 보류")

    with gc2:
        st.markdown("#### 조립 순서 (§48) · 15단계")
        seq = ["Base Housing", "Insulation", "Cold Plate", "Heater/TEC", "TIM", "Copper Spreader",
               "Vapor Chamber", "Thermal Hub", "Heat Pipes ×6", "HP Bridge Clamps",
               "Gradient Fin Body", "Entrainment Ring", "Top Retaining Ring", "Diffuser", "Sensors"]
        st.markdown("\n".join(f"{i+1:02d}. {s}" for i, s in enumerate(seq)))
        st.markdown("""
**Torque 철학 (§49)**: TEC·VC·HP의 정확한 torque는 지금 고정하지 않는다 —
CAD에 mechanical stop 설계 → vendor data + contact-pressure test 후 확정.

**도면 패키지 (§47)**: DWG-001 GA ~ DWG-010 Inspection CTQ, 총 10종.
""")

st.markdown("---")
st.caption("VGEC-HP/VTE P1-Hybrid CAD 상세설계 사양서 v0.1 · 모든 수치는 [DESIGN-0] — TEC/VC 선정 후 업데이트 · "
           "이 값들은 설계 '정답'이 아니라 DOE·Bayesian Optimization center point이다 (§52)")
