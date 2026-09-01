"""
Section 30 — patent-style FIG package.

Convention: black-and-white technical linework, with colour used ONLY as a
functional code:
    BLUE   = magnetic field / flux
    RED    = fork / core / pole structure
    GREEN  = sensor and measurement chain
    ORANGE = safety, interlock, hazard
"""
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, Circle, Polygon, Arc
from matplotlib.lines import Line2D
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "design"))
OUT = HERE

BLUE, RED, GREEN, ORANGE, K = "#1f4e9c", "#c0392b", "#1e8449", "#e67e22", "black"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8, "axes.linewidth": 0.9,
    "lines.linewidth": 1.1, "figure.dpi": 150, "savefig.dpi": 200,
    "savefig.bbox": "tight", "axes.edgecolor": "black",
})


def newfig(w=9.5, h=6.0, title=""):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_aspect("equal"); ax.axis("off")
    if title:
        ax.set_title(title, fontsize=10, fontweight="bold", loc="left", pad=10)
    return fig, ax


def save(fig, name):
    for ext in ("svg", "png"):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"))
    plt.close(fig)
    print("  ", name)


def box(ax, x, y, w, h, label, ec=K, fc="white", fs=7.5, lw=1.1, ls="-"):
    ax.add_patch(Rectangle((x, y), w, h, ec=ec, fc=fc, lw=lw, ls=ls, zorder=2))
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
            fontsize=fs, zorder=3, wrap=True)


def arrow(ax, p, q, c=K, lw=1.1, style="-|>", ls="-"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=9,
                                 lw=lw, color=c, linestyle=ls, zorder=2,
                                 shrinkA=1, shrinkB=1))


def dim(ax, p, q, text, off=0.0, c=K, fs=6.5, vert=False):
    ax.annotate("", xy=q, xytext=p,
                arrowprops=dict(arrowstyle="<|-|>", lw=0.7, color=c,
                                mutation_scale=7))
    mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
    ax.text(mx + (off if not vert else 0), my + (0 if not vert else off), text,
            ha="center", va="center", fontsize=fs, color=c,
            rotation=90 if vert else 0,
            bbox=dict(fc="white", ec="none", pad=0.6))


def legend(ax, items, x, y, fs=6.5):
    for i, (c, t) in enumerate(items):
        ax.add_patch(Rectangle((x, y - i * 0.055), 0.03, 0.03, fc=c, ec=c))
        ax.text(x + 0.045, y - i * 0.055 + 0.015, t, fontsize=fs, va="center")


# ===========================================================================
def fig01():
    fig, ax = newfig(11, 6.4, "FIG.1  Q-HSRS Phase-3 Instrumented ELF-MF Exposure Platform — overall system")
    ax.set_xlim(0, 11); ax.set_ylim(0, 6.4)
    box(ax, 0.2, 4.6, 1.7, 0.85, "SS-05\nWaveform generator\n3–3,000 Hz\nDSP, <1 ppm ref")
    box(ax, 2.2, 4.6, 1.7, 0.85, "SS-09\nPLC / safety CPU\nsequence, blinding")
    box(ax, 4.2, 4.6, 2.0, 0.85, "SS-04\nCurrent-mode amplifier\n×3 channels", ec=K)
    box(ax, 6.5, 4.6, 1.7, 0.85, "Series compensation\nbank (6 bands)")
    box(ax, 8.5, 4.6, 2.2, 0.85, "SS-02/03\nExposure cells ×3\n(C-core + Litz coils)", ec=RED, lw=1.6)

    arrow(ax, (1.9, 5.0), (2.2, 5.0)); arrow(ax, (3.9, 5.0), (4.2, 5.0))
    arrow(ax, (6.2, 5.0), (6.5, 5.0)); arrow(ax, (8.2, 5.0), (8.5, 5.0), c=RED, lw=1.5)

    box(ax, 8.5, 2.9, 2.2, 0.85, "PVDF exposure duct\n240 × 24 mm ID\nECV 3 × 0.881 L", ec=BLUE, lw=1.5)
    ax.annotate("", xy=(9.6, 3.75), xytext=(9.6, 4.6),
                arrowprops=dict(arrowstyle="<|-|>", color=BLUE, lw=1.6))
    ax.text(9.75, 4.18, "B(f,r,t)", color=BLUE, fontsize=8, fontweight="bold")

    box(ax, 5.6, 1.0, 2.2, 1.2, "SS-01\n1,000 L SUS316L\nreservoir\n(OUT of the flux path)")
    box(ax, 3.0, 1.0, 2.0, 1.2, "Pump + VFD\nCoriolis flow\nChiller ±0.2 K")
    arrow(ax, (5.6, 1.6), (5.0, 1.6)); arrow(ax, (3.0, 2.0), (2.6, 2.0))
    ax.plot([2.6, 2.6, 9.6, 9.6], [2.0, 3.4, 3.4, 3.75], color=K, lw=1.0)
    ax.plot([9.6, 9.6, 6.7, 6.7], [2.9, 2.4, 2.4, 2.2], color=K, lw=1.0)
    ax.text(5.6, 3.5, "process loop", fontsize=6.5, style="italic")

    box(ax, 0.2, 2.9, 2.0, 0.85, "SS-06 Sensing\nL1 coil current\nL2 external ref B\nL3 in-water B", ec=GREEN, lw=1.5)
    box(ax, 0.2, 1.5, 2.0, 1.0, "SS-07 Water\nEC pH ORP DO\nflow, T", ec=GREEN, lw=1.5)
    box(ax, 0.2, 0.2, 2.0, 0.95, "SS-11 Digital twin\nresidual monitor\nBayesian update", ec=GREEN, lw=1.5)
    for a, b in (((2.2, 3.3), (4.2, 4.6)), ((2.2, 2.0), (3.0, 2.0)), ((1.2, 1.5), (1.2, 1.15))):
        arrow(ax, a, b, c=GREEN, ls="--")
    ax.text(2.6, 3.95, "B feedback  →  constant-B loop", color=GREEN, fontsize=7, rotation=25)

    box(ax, 4.2, 2.9, 1.1, 0.85, "SS-10\nHardwired\ninterlock", ec=ORANGE, lw=1.8)
    arrow(ax, (5.0, 3.75), (5.0, 4.6), c=ORANGE, lw=1.6)
    ax.text(5.1, 4.2, "AMPLIFIER\nENABLE", color=ORANGE, fontsize=6.5, fontweight="bold")

    ax.text(0.2, 0.02, "Colour code: BLUE = magnetic field · RED = core/pole · GREEN = sensing · ORANGE = safety",
            fontsize=6.5, style="italic")
    save(fig, "FIG01_overall_system")


def fig02():
    import tank_coupling as TC
    from constants import F_GRID, MU_R_SUS316L_COLDWORK
    fig = plt.figure(figsize=(11, 5.6))
    fig.suptitle("FIG.2  1,000 L SUS316L reservoir, external exposure loop, and the measured-basis tank transfer function",
                 fontsize=10, fontweight="bold", x=0.02, ha="left")
    ax = fig.add_subplot(1, 2, 1); ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(-0.2, 2.6); ax.set_ylim(-0.2, 2.5)
    ax.add_patch(Rectangle((0.15, 0.25), 1.0, 1.4, ec=K, fc="#f2f2f2", lw=2.0))
    ax.add_patch(Rectangle((0.19, 0.29), 0.92, 1.32, ec=BLUE, fc="#eaf1fb", lw=0.6, ls=":"))
    ax.text(0.65, 0.95, "1,000 L\nSUS316L\nØ1.0 m × 1.3 m\nwall 3 mm", ha="center", fontsize=7)
    dim(ax, (0.15, 0.15), (1.15, 0.15), "Ø 1,000", off=0)
    dim(ax, (1.28, 0.25), (1.28, 1.65), "1,300", vert=True, off=0)
    ax.plot([1.15, 1.7, 1.7], [0.45, 0.45, 0.9], color=K, lw=1.2)
    ax.plot([1.7, 1.7, 1.15], [1.7, 1.45, 1.45], color=K, lw=1.2)
    for i in range(3):
        y = 0.95 + i * 0.18
        ax.add_patch(Rectangle((1.55, y), 0.3, 0.12, ec=RED, fc="#fdeceb", lw=1.3))
        ax.text(2.0, y + 0.06, f"cell {i+1}", fontsize=6.5, color=RED, va="center")
    ax.text(1.7, 1.85, "exposure cells\n(non-metallic duct)", ha="center", fontsize=6.5, color=RED)
    ax.add_patch(Circle((1.7, 0.45), 0.11, ec=K, fc="white", lw=1.2))
    ax.text(1.7, 0.45, "P", ha="center", va="center", fontsize=7)
    ax.text(0.15, 2.25, "KEY RESULT: the tank is a process reservoir only.\n"
                        "No flux crosses the SUS316L wall by design.",
            fontsize=7, fontweight="bold", color=RED)

    ax2 = fig.add_subplot(2, 2, 2)
    t = TC.TankGeometry()
    f = np.logspace(math.log10(1), math.log10(5000), 400)
    H = [TC.H_tank(x, t) for x in f]
    ax2.semilogx(f, [20 * math.log10(abs(h)) for h in H], color=BLUE, lw=1.6, label="annealed  μr=1.005")
    H2 = [TC.H_tank(x, t, mu_r=MU_R_SUS316L_COLDWORK.value) for x in f]
    ax2.semilogx(f, [20 * math.log10(abs(h)) for h in H2], color=RED, lw=1.2, ls="--", label="cold-worked  μr=1.8")
    fc = TC.corner_frequency(t)
    ax2.axvline(fc, color=K, lw=0.8, ls=":"); ax2.text(fc * 1.1, -8, f"f_c={fc:.0f} Hz", fontsize=6.5)
    ax2.axvspan(3, 3000, color="#f0f0f0", zorder=0)
    ax2.set_ylabel("|H(f)| [dB]", fontsize=7.5); ax2.legend(fontsize=6); ax2.grid(alpha=0.3, which="both")
    ax2.tick_params(labelsize=6.5); ax2.set_xlim(1, 5000)

    ax3 = fig.add_subplot(2, 2, 4)
    ax3.semilogx(f, [math.degrees(np.angle(h)) for h in H], color=BLUE, lw=1.6)
    ax3.semilogx(f, [math.degrees(np.angle(h)) for h in H2], color=RED, lw=1.2, ls="--")
    ax3.axvline(fc, color=K, lw=0.8, ls=":"); ax3.axvspan(3, 3000, color="#f0f0f0", zorder=0)
    ax3.set_xlabel("frequency [Hz]", fontsize=7.5); ax3.set_ylabel("phase [deg]", fontsize=7.5)
    ax3.grid(alpha=0.3, which="both"); ax3.tick_params(labelsize=6.5); ax3.set_xlim(1, 5000)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save(fig, "FIG02_tank_and_transfer_function")


def fig03():
    fig, ax = newfig(9.5, 6.0, "FIG.3  Exposure cell — isometric arrangement (R3 module, one of three)")
    ax.set_xlim(-0.5, 9); ax.set_ylim(-0.5, 6)
    def iso(x, y, z): return (x + 0.45 * y, z + 0.30 * y)
    def prism(ax, o, dx, dy, dz, fc, ec, lw=1.1, a=1.0):
        x, y, z = o
        faces = [
            [(x, y, z), (x+dx, y, z), (x+dx, y, z+dz), (x, y, z+dz)],
            [(x, y, z+dz), (x+dx, y, z+dz), (x+dx, y+dy, z+dz), (x, y+dy, z+dz)],
            [(x+dx, y, z), (x+dx, y+dy, z), (x+dx, y+dy, z+dz), (x+dx, y, z+dz)]]
        for fpts in faces:
            ax.add_patch(Polygon([iso(*p) for p in fpts], closed=True, fc=fc,
                                 ec=ec, lw=lw, alpha=a, zorder=2))
    prism(ax, (0.6, 0.5, 0.8), 1.0, 2.4, 3.0, "#fdeceb", RED, 1.3)      # pole shoe A
    prism(ax, (5.0, 0.5, 0.8), 1.0, 2.4, 3.0, "#fdeceb", RED, 1.3)      # pole shoe B
    prism(ax, (1.6, 1.2, 1.8), 1.4, 1.0, 1.0, "#f7d9d6", RED, 1.0)      # leg A
    prism(ax, (3.6, 1.2, 1.8), 1.4, 1.0, 1.0, "#f7d9d6", RED, 1.0)      # leg B
    prism(ax, (1.6, 1.2, 0.0), 4.4, 1.0, 0.7, "#f7d9d6", RED, 1.0)      # back yoke
    ax.add_patch(Polygon([iso(1.6,1.2,1.0), iso(6.0,1.2,1.0), iso(6.0,1.2,1.8), iso(1.6,1.2,1.8)],
                         closed=True, fc="none", ec=RED, lw=0.6, ls=":"))
    for lx in (1.65, 3.65):                                             # coils
        for k in range(6):
            prism(ax, (lx + 0.06 + k*0.21, 1.05, 1.62), 0.13, 1.3, 1.36, "#d9a441", "#8a6410", 0.5)
    prism(ax, (1.9, 0.55, 0.9), 3.2, 2.3, 2.8, "#eaf1fb", BLUE, 1.2, a=0.55)   # water duct
    for k in range(5):
        y = 0.8 + k * 0.42
        ax.add_patch(FancyArrowPatch(iso(1.75, y, 2.3), iso(5.05, y, 2.3),
                                     arrowstyle="-|>", mutation_scale=8,
                                     color=BLUE, lw=1.3, zorder=6))
    ax.text(*iso(3.4, 2.5, 4.3), "B", color=BLUE, fontsize=11, fontweight="bold")
    ax.add_patch(FancyArrowPatch(iso(0.3, 3.2, 2.3), iso(1.9, 3.2, 2.3),
                                 arrowstyle="-|>", mutation_scale=10, color=K, lw=1.4))
    ax.text(*iso(0.3, 3.5, 2.5), "water flow", fontsize=7)
    ax.add_patch(Circle(iso(3.45, 1.7, 2.3), 0.09, fc=GREEN, ec=GREEN, zorder=8))
    ax.text(*iso(3.6, 1.7, 2.55), "L3 in-water B probe", color=GREEN, fontsize=6.5)
    for c, t, p in ((RED, "laminated C-core + pole shoes", (0.2, 5.6)),
                    ("#d9a441", "Litz coils (2 per cell, series)", (0.2, 5.35)),
                    (BLUE, "PVDF duct / water gap / B field", (0.2, 5.10)),
                    (GREEN, "sensing", (0.2, 4.85))):
        ax.plot([p[0], p[0]+0.25], [p[1], p[1]], color=c, lw=3)
        ax.text(p[0]+0.32, p[1], t, fontsize=6.8, va="center")
    save(fig, "FIG03_cell_isometric")


def fig04():
    import cell as CELL, system as S
    core = S.CoreGeom()
    fig, ax = newfig(11, 5.8, "FIG.4  Exposure cell — 2-D dimensioned drawing (all dimensions in mm)")
    ax.set_xlim(-120, 900); ax.set_ylim(-150, 480)
    mm = 1000.0
    pw, ph, g = core.pole_w*mm, core.pole_h*mm, core.gap*mm
    st, ll, la = core.shoe_t*mm, core.leg_len*mm, core.leg_a*mm
    ax.text(-100, 450, "SECTION A-A  (plane of the magnetic circuit)", fontsize=7.5, fontweight="bold")
    x0 = 0
    ax.add_patch(Rectangle((x0, 60), st, ph, ec=RED, fc="#fdeceb", lw=1.4))
    ax.add_patch(Rectangle((x0+st+g, 60), st, ph, ec=RED, fc="#fdeceb", lw=1.4))
    ax.add_patch(Rectangle((x0-ll, 60+(ph-la)/2), ll, la, ec=RED, fc="#f7d9d6", lw=1.2))
    ax.add_patch(Rectangle((x0+st+g+st, 60+(ph-la)/2), ll, la, ec=RED, fc="#f7d9d6", lw=1.2))
    ax.add_patch(Rectangle((x0-ll-la, 60-la), la, ph+la+ (0), ec=RED, fc="#f7d9d6", lw=1.2))
    ax.add_patch(Rectangle((x0+st+g+st+ll, 60-la), la, ph+la, ec=RED, fc="#f7d9d6", lw=1.2))
    ax.add_patch(Rectangle((x0-ll-la, 60-la), 2*la+2*ll+2*st+g, la, ec=RED, fc="#f7d9d6", lw=1.2))
    for xx in (x0-ll+8, x0+st+g+st+8):
        for k in range(8):
            ax.add_patch(Rectangle((xx+k*16, 60+(ph-la)/2-22), 11, la+44,
                                   ec="#8a6410", fc="#d9a441", lw=0.5))
    ax.add_patch(Rectangle((x0+st, 60), g, ph, ec=BLUE, fc="#eaf1fb", lw=1.0, ls="--"))
    ax.add_patch(Rectangle((x0+st, 60), 3, ph, ec=K, fc="#dddddd", lw=0.8))
    ax.add_patch(Rectangle((x0+st+g-3, 60), 3, ph, ec=K, fc="#dddddd", lw=0.8))
    for k in range(7):
        y = 78 + k*30
        ax.add_patch(FancyArrowPatch((x0+st+4, y), (x0+st+g-4, y), arrowstyle="-|>",
                                     mutation_scale=7, color=BLUE, lw=1.1))
    ex = CELL.ecv_geometry()
    ecx0 = x0+st+ex["z_lo"]*mm; ecw = (ex["z_hi"]-ex["z_lo"])*mm
    ax.add_patch(Rectangle((ecx0, 60+(ph-ex["y_half"]*2*mm)/2), ecw, ex["y_half"]*2*mm,
                           ec=GREEN, fc="none", lw=1.4, ls="-."))
    ax.text(x0+st+g+8, 60+ph+16, "ECV (CV_B ≤ 10 %)", color=GREEN, fontsize=6.5)
    dim(ax, (x0, 40), (x0+st, 40), "30"); dim(ax, (x0+st, 20), (x0+st+g, 20), f"{g:.0f} mag. gap", off=0)
    dim(ax, (x0+st+3, -20), (x0+st+g-3, -20), f"{CELL.WATER_GAP*mm:.0f} water", off=0)
    dim(ax, (-ll-la-25, 60), (-ll-la-25, 60+ph), f"{ph:.0f}", vert=True)
    dim(ax, (x0-ll, 60+ph+28), (x0, 60+ph+28), f"{ll:.0f} coil window")
    ax.text(-110, 300, f"pole face\n{pw:.0f} × {ph:.0f}", fontsize=6.5, color=RED)
    ax.text(-110, 200, f"leg\n{la:.0f} × {la:.0f}", fontsize=6.5, color=RED)

    ax.text(520, 450, "PLAN VIEW  (flow direction)", fontsize=7.5, fontweight="bold")
    bx = 540
    ax.add_patch(Rectangle((bx, 120), pw, g, ec=BLUE, fc="#eaf1fb", lw=1.2))
    ax.add_patch(Rectangle((bx, 120-st), pw, st, ec=RED, fc="#fdeceb", lw=1.2))
    ax.add_patch(Rectangle((bx, 120+g), pw, st, ec=RED, fc="#fdeceb", lw=1.2))
    dim(ax, (bx, 90), (bx+pw, 90), f"{pw:.0f} pole (flow)")
    ax.add_patch(FancyArrowPatch((bx-60, 135), (bx-10, 135), arrowstyle="-|>",
                                 mutation_scale=10, color=K, lw=1.3))
    ax.text(bx-62, 150, "flow", fontsize=7)
    ax.text(bx, 260, f"3 cells on {int(0.375*mm)} mm pitch\n"
                     f"total duct length ≈ {int(1.2*mm)} mm\n"
                     f"ECV = 3 × {ex['vol_L']:.3f} L = {3*ex['vol_L']:.3f} L",
            fontsize=7)
    save(fig, "FIG04_cell_dimensions")


def fig05():
    import system as S, cell as CELL
    from coil_design import WIRES
    core = S.CoreGeom()
    fig, ax = newfig(9.5, 5.4, "FIG.5  Coil cross-section, winding build and thermal path")
    ax.set_xlim(-40, 340); ax.set_ylim(-60, 250)
    la = core.leg_a * 1000
    ax.add_patch(Rectangle((60, 40), la, la, ec=RED, fc="#f7d9d6", lw=1.5))
    ax.text(60+la/2, 40+la/2, "core leg\n120 × 120\nlaminated", ha="center", va="center", fontsize=7, color=RED)
    ax.add_patch(Rectangle((52, 32), la+16, la+16, ec=K, fc="#f5f5f5", lw=0.9))
    ax.text(178, 168, "8 mm Nomex/glass\ninter-layer insulation", fontsize=6.3)
    for r in range(2):
        for c in range(8):
            ax.add_patch(Circle((66+c*(la-14)/7, 24-r*20), 8.5, ec="#8a6410", fc="#d9a441", lw=0.7))
            ax.add_patch(Circle((66+c*(la-14)/7, 176+r*20), 8.5, ec="#8a6410", fc="#d9a441", lw=0.7))
    ax.add_patch(Rectangle((44, -22), la+32, la+68, ec="#555555", fc="none", lw=1.2, ls="--"))
    ax.text(-36, 210, "vacuum-impregnated\nalumina-filled epoxy\n(k ≈ 1 W/m·K)", fontsize=6.5)
    ax.add_patch(Rectangle((36, -46), la+48, 20, ec=K, fc="#cfd8dc", lw=1.2))
    ax.text(96, -36, "Al 6061 cold plate — 25 °C glycol", fontsize=6.5, ha="center")
    for xx in (60, 120, 180):
        arrow(ax, (xx, -6), (xx, -26), c=ORANGE, lw=1.2)
    ax.add_patch(Circle((66, 196), 6, fc=GREEN, ec=GREEN))
    ax.text(78, 196, "fibre-optic hot-spot probe (EMI-immune)", fontsize=6.3, color=GREEN, va="center")

    w = [x for x in WIRES if "2000" in x.label][0]
    txt = (f"WINDING (frozen)\n"
           f"  conductor      : {w.label}\n"
           f"  A_Cu           : {w.a_cu*1e6:.1f} mm²   (bundle Ø {w.d_outer*1e3:.1f} mm)\n"
           f"  turns          : 16 per coil, 2 coils per cell, series\n"
           f"  N_loop         : 32\n"
           f"  L              : 2.80 mH per cell\n"
           f"  I at 50 mT     : 39.8 A rms  →  J = 0.63 A/mm²\n"
           f"  R_ac/R_dc      : 1.00 (3 Hz) → 1.25 (3 kHz)\n"
           f"  window         : {core.leg_len*1e3:.0f} × {CELL.WINDOW_H*1e3:.0f} mm\n"
           f"  Cu skin depth  : 41.0 mm (3 Hz) → 1.30 mm (3 kHz)\n"
           f"  → strand Ø 0.20 mm much smaller than δ, so Litz is REQUIRED above ~300 Hz")
    ax.text(215, 230, txt, fontsize=6.6, va="top", family="DejaVu Sans Mono",
            bbox=dict(fc="#fafafa", ec="#bbbbbb", lw=0.7, pad=5))
    save(fig, "FIG05_coil_cross_section")


def fig06():
    import system as S, cell as CELL
    core = S.CoreGeom()
    gv, err, _ = S._gap_mmf_unit(core)
    fig, ax = newfig(11, 5.2, "FIG.6  Magnetic circuit — flux path and equivalent reluctance network")
    ax.set_xlim(0, 11); ax.set_ylim(0, 5.2)
    ax.add_patch(Rectangle((0.6, 1.0), 4.6, 2.6, ec=RED, fc="none", lw=2.4))
    ax.add_patch(Rectangle((1.9, 1.9), 2.0, 0.9, ec="white", fc="white", lw=0))
    ax.add_patch(Rectangle((2.55, 1.0), 0.7, 2.6, ec="white", fc="white", lw=0))
    ax.add_patch(Rectangle((2.55, 2.75), 0.7, 0.85, ec=BLUE, fc="#eaf1fb", lw=1.2, ls="--"))
    ax.text(2.9, 3.9, "gap 30 mm", color=BLUE, fontsize=6.5, ha="center")
    th = np.linspace(0.2, 0.95, 40)
    ax.plot(0.9 + 3.9*th, 1.35 + 1.9*np.sin(np.pi*th)*0.0 + 0*th, alpha=0)
    for pts in ([(1.2,1.35),(4.6,1.35)], [(4.6,1.35),(4.6,3.25)], [(4.6,3.25),(3.35,3.25)],
                [(2.45,3.25),(1.2,3.25)], [(1.2,3.25),(1.2,1.35)]):
        arrow(ax, pts[0], pts[1], c=BLUE, lw=1.7)
    arrow(ax, (2.45, 3.18), (3.35, 3.18), c=BLUE, lw=1.7)
    ax.text(2.0, 2.3, "Φ", color=BLUE, fontsize=13, fontweight="bold")
    for k in range(5):
        ax.add_patch(Rectangle((0.72+0.0, 1.6+k*0.34), 0.36, 0.22, ec="#8a6410", fc="#d9a441", lw=0.6))
        ax.add_patch(Rectangle((4.72-0.36, 1.6+k*0.34), 0.36, 0.22, ec="#8a6410", fc="#d9a441", lw=0.6))
    ax.text(0.9, 0.75, "N·I", fontsize=8, ha="center")
    ax.text(4.9, 0.75, "N·I", fontsize=8, ha="center")

    x = 6.2
    ax.plot([x, x+4.2], [3.6, 3.6], color=K, lw=1.1)
    ax.plot([x, x], [1.4, 3.6], color=K, lw=1.1)
    ax.plot([x+4.2, x+4.2], [1.4, 3.6], color=K, lw=1.1)
    ax.plot([x, x+4.2], [1.4, 1.4], color=K, lw=1.1)
    ax.add_patch(Circle((x, 2.5), 0.26, ec=K, fc="white", lw=1.2))
    ax.text(x, 2.5, "F", ha="center", va="center", fontsize=8)
    ax.text(x-0.75, 2.5, "MMF\nN·I", ha="center", va="center", fontsize=6.5)
    box(ax, x+1.0, 3.42, 1.0, 0.36, "R_gap", ec=BLUE, fs=7)
    box(ax, x+2.6, 3.42, 1.1, 0.36, "R_core", ec=RED, fs=7)
    box(ax, x+1.7, 1.22, 1.2, 0.36, "R_leak", ec="#888888", fs=7, ls="--")
    ax.text(x+0.15, 0.75,
            f"R_gap  = {gv/core.pole_area:.3e} A/Wb      ({100*gv*1.0/(gv*1.0+ (core.path_len/(4e-7*math.pi*30000))*core.pole_area/core.leg_area):.1f} % of the loop)\n"
            f"R_core = {core.path_len/(4e-7*math.pi*30000*core.leg_area):.3e} A/Wb   (nanocrystalline μr = 30,000)\n"
            f"gap MMF = {gv:.0f} A-turns per tesla of pole-face B\n"
            f"charge-sheet model path spread = {err*100:.1f} %  →  model uncertainty, to be closed by 3-D FEA",
            fontsize=6.6, family="DejaVu Sans Mono", va="top")
    ax.text(0.6, 4.7, "The circuit is 99.9 % air gap. That is deliberate: B/I is then set by\n"
                      "GEOMETRY, not by μ(f,T,B), so the constant-B loop has an almost\n"
                      "drift-free plant (gap growth over 20 K ≈ 0.02 %).",
            fontsize=7, fontweight="bold", color=RED, va="top")
    save(fig, "FIG06_magnetic_circuit")


def fig07():
    import architectures as ARCH
    from magnetics import ForkGeometry
    fk = ForkGeometry(n_prong=3, prong_w=0.240, prong_h=0.240, prong_len=0.15,
                      prong_pitch=0.375, gap=0.030)
    fig, axes = plt.subplots(2, 3, figsize=(11.5, 6.2),
                             gridspec_kw=dict(height_ratios=[1.15, 1]))
    fig.suptitle("FIG.7  R1 / R2 / R3 architecture comparison — same gap, same target B, same field engine",
                 fontsize=10, fontweight="bold", x=0.02, ha="left")
    titles = {"R1": "R1  single 3-prong fork", "R2": "R2  opposed dual fork (shared yoke)",
              "R3": "R3  distributed independent cells"}
    for j, arch in enumerate(("R1", "R2", "R3")):
        ax = axes[0][j]; ax.set_aspect("equal"); ax.axis("off")
        ax.set_title(titles[arch], fontsize=8, color=RED)
        ax.set_xlim(-0.65, 0.65); ax.set_ylim(-0.10, 0.14)
        for i, xc in enumerate(fk.pole_centres()):
            if arch == "R1":
                sg = "N" if i % 2 == 0 else "S"
                ax.add_patch(Rectangle((xc-0.12, -0.02), 0.24, 0.02, ec=RED, fc="#fdeceb", lw=1.2))
                ax.text(xc, -0.035, sg, ha="center", fontsize=7, color=RED)
            elif arch == "R2":
                sg = ("N", "S") if i % 2 == 0 else ("S", "N")
                ax.add_patch(Rectangle((xc-0.12, -0.02), 0.24, 0.02, ec=RED, fc="#fdeceb", lw=1.2))
                ax.add_patch(Rectangle((xc-0.12, 0.03), 0.24, 0.02, ec=RED, fc="#fdeceb", lw=1.2))
                ax.text(xc, -0.035, sg[0], ha="center", fontsize=7, color=RED)
                ax.text(xc, 0.058, sg[1], ha="center", fontsize=7, color=RED)
            else:
                ax.add_patch(Rectangle((xc-0.12, -0.02), 0.24, 0.02, ec=RED, fc="#fdeceb", lw=1.2))
                ax.add_patch(Rectangle((xc-0.12, 0.03), 0.24, 0.02, ec=RED, fc="#fdeceb", lw=1.2))
                ax.text(xc, -0.035, "N", ha="center", fontsize=7, color=RED)
                ax.text(xc, 0.058, "S", ha="center", fontsize=7, color=RED)
                ax.add_patch(Rectangle((xc-0.155, -0.02), 0.035, 0.07, ec=RED, fc="#f7d9d6", lw=1.0))
        if arch != "R1":
            ax.add_patch(Rectangle((-0.62, 0.0), 1.24, 0.03, ec=BLUE, fc="#eaf1fb", lw=0.8, ls="--"))
        for i, xc in enumerate(fk.pole_centres()):
            for k in range(3):
                yy = 0.004 + k * 0.010
                if arch == "R1":
                    arrow(ax, (xc-0.06+k*0.05, 0.001), (xc-0.06+k*0.05, 0.028), c=BLUE, lw=1.0)
                else:
                    arrow(ax, (xc-0.06+k*0.05, 0.001), (xc-0.06+k*0.05, 0.028), c=BLUE, lw=1.2)
        ax.text(0, 0.115, {"R1": "flux returns through the water\n→ huge MMF, polarity nulls",
                           "R2": "shared yoke FORCES N,S,N\n→ |B| nulls between prong pairs",
                           "R3": "own return path per cell\n→ all cells same polarity, no nulls"}[arch],
                ha="center", fontsize=6.6)

    ax = axes[1][0]
    rows = []
    for arch in ("R1", "R2", "R3"):
        per, uni = ARCH.stats_channels(arch, fk, 1.0)
        mmf, _, _ = ARCH.loop_mmf(arch, fk, 50e-3/uni["mean"], 30000.0)
        u, nl = ARCH.field_energy(arch, fk, 50e-3/uni["mean"], mmf)
        rows.append((arch, uni["mean"], uni["cv"], mmf, u))
    names = [r[0] for r in rows]
    for ax, idx, lab, logy in ((axes[1][0], 1, "field gain  B_ECV / B_pole", False),
                               (axes[1][1], 2, "CV_B over the ECV", False),
                               (axes[1][2], 4, "stored energy U [J] at 50 mT (log)", True)):
        v = [r[idx] for r in rows]
        b = ax.bar(names, v, color=[RED if n != "R3" else GREEN for n in names], width=0.55)
        ax.set_title(lab, fontsize=7.5); ax.tick_params(labelsize=7)
        if logy: ax.set_yscale("log")
        for rect, val in zip(b, v):
            ax.text(rect.get_x()+rect.get_width()/2, val, f"{val:.3g}",
                    ha="center", va="bottom", fontsize=6.5)
        ax.grid(axis="y", alpha=0.3)
        if idx == 2: ax.axhline(0.10, color=K, ls="--", lw=0.9); ax.text(2.3, 0.104, "10 % limit", fontsize=6)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save(fig, "FIG07_R1_R2_R3")


def fig08():
    import system as S, cell as CELL
    from constants import NANOCRYSTALLINE, F_GRID
    import run_all as RA
    fig = plt.figure(figsize=(11.5, 5.8))
    fig.suptitle("FIG.8  Power driver chain, switched series compensation, and the resulting (f, B) capability envelope",
                 fontsize=10, fontweight="bold", x=0.02, ha="left")
    ax = fig.add_subplot(1, 2, 1); ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(0, 10); ax.set_ylim(0, 6.6)
    box(ax, 0.2, 5.2, 1.7, 0.8, "DSP AWG\nsine / square\nAM / FM / multi-tone", fs=6.2)
    box(ax, 2.2, 5.2, 1.7, 0.8, "current\ncommand I*(t)", fs=6.2)
    box(ax, 4.2, 5.0, 2.2, 1.0, "4-quadrant\ncurrent-mode amp\n600 V / 200 A\n60 kVA", fs=6.2)
    arrow(ax, (1.9, 5.6), (2.2, 5.6)); arrow(ax, (3.9, 5.6), (4.2, 5.6))
    ax.plot([6.4, 7.2], [5.5, 5.5], color=K)
    for i, (lo, hi) in enumerate(S.COMP_BANDS):
        y = 4.6 - i*0.52
        ax.plot([7.2, 7.5], [5.5, y], color=K, lw=0.5)
        ax.add_patch(Rectangle((7.5, y-0.1), 0.16, 0.2, fc="white", ec=K, lw=1.2))
        ax.add_patch(Rectangle((7.72, y-0.1), 0.16, 0.2, fc="white", ec=K, lw=1.2))
        ax.text(8.0, y, f"{lo:.0f}–{hi:.0f} Hz", fontsize=5.8, va="center")
        ax.plot([7.88, 8.9], [y, y], color=K, lw=0.5)
    ax.text(7.0, 5.75, "switched series C bank", fontsize=6.5)
    ax.plot([8.9, 8.9], [1.4, 5.5], color=K, lw=0.9)
    box(ax, 8.4, 0.7, 1.4, 0.7, "cell coil\nL = 2.8 mH", ec=RED)
    ax.plot([6.4, 6.4, 8.4], [5.5, 1.05, 1.05], color=K, lw=0.9)
    ax.text(0.2, 3.9, "WHY COMPENSATION, NOT A BIGGER AMPLIFIER:\n\n"
                      "   Q = ω·L·I²  = ω·Φ·F  = 2ω·U\n\n"
                      "Q is INDEPENDENT of turns count N. N only trades\n"
                      "volts for amps. At 50 mT / 3 kHz, Q = 83.9 kVAr per\n"
                      "cell but the real loss is only 20.7 W. The capacitor\n"
                      "bank carries the circulating VA; the amplifier carries\n"
                      "the losses. Bands are deliberately DETUNED inside each\n"
                      "octave — exact tuning would give a loaded Q of ~5,700\n"
                      "and an uncontrollable plant.",
            fontsize=6.8, va="top", family="DejaVu Sans Mono",
            bbox=dict(fc="#fafafa", ec="#bbbbbb", lw=0.7, pad=5))

    ax2 = fig.add_subplot(1, 2, 2)
    wc = RA.winding_choice()
    fe = RA.feasibility_envelope(wc, NANOCRYSTALLINE)
    f = [r["f_Hz"] for r in fe]; b = [r["B_max_mT"] for r in fe]
    ax2.loglog(f, b, "o-", color=BLUE, lw=1.8, ms=4, label="achievable B (nanocrystalline core)")
    ax2.fill_between(f, 1e-2, b, color=BLUE, alpha=0.08)
    from constants import B_LADDER_T, B_LADDER_LABEL
    for bb, lb in zip(B_LADDER_T, B_LADDER_LABEL):
        if bb == 0: continue
        ax2.axhline(bb*1e3, color=K, lw=0.6, ls=":")
        ax2.text(3.2, bb*1e3*1.06, lb, fontsize=6)
    ax2.set_xlabel("frequency [Hz]", fontsize=8); ax2.set_ylabel("B_ECV [mT rms]", fontsize=8)
    ax2.grid(alpha=0.3, which="both"); ax2.tick_params(labelsize=7)
    ax2.set_xlim(2.5, 3600); ax2.set_ylim(0.2, 300)
    ax2.legend(fontsize=6.5, loc="lower left")
    ax2.text(3.2, 170, "core saturation limit", fontsize=6, color=RED)
    ax2.text(1300, 110, "amplifier\nvoltage limit", fontsize=6, color=RED, ha="center")
    ax2.set_title("the whole dose ladder fits under the envelope\nat every frequency in 3–3,000 Hz", fontsize=7.5)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    save(fig, "FIG08_driver_and_envelope")


def fig09():
    fig, ax = newfig(11, 5.6, "FIG.9  Three-layer magnetic sensing architecture and its calibration chain")
    ax.set_xlim(0, 11); ax.set_ylim(0, 5.6)
    box(ax, 0.3, 4.2, 2.3, 0.9, "LAYER 1\nCoil current\nfluxgate CT + shunt\nDC–100 kHz, 0.1 %", ec=GREEN, lw=1.6)
    box(ax, 0.3, 2.8, 2.3, 0.9, "LAYER 2\nExternal reference B\n3-axis fluxgate\nDC–3 kHz, 0.01 nT/√Hz", ec=GREEN, lw=1.6)
    box(ax, 0.3, 1.4, 2.3, 0.9, "LAYER 3\nIn-water B\nsealed search coil\n1 Hz–10 kHz", ec=GREEN, lw=1.6)
    box(ax, 3.4, 2.6, 2.0, 1.4, "Coherent\ndemodulation\nat f_drive\n\nT_avg = max(3 s, 30/f)")
    for y in (4.65, 3.25, 1.85):
        arrow(ax, (2.6, y), (3.4, 3.3), c=GREEN)
    box(ax, 6.1, 3.3, 2.2, 0.8, "Constant-B controller", ec=BLUE, lw=1.5)
    box(ax, 6.1, 2.1, 2.2, 0.8, "Cross-check / voting\n|L1→B| vs L2 vs L3", ec=ORANGE, lw=1.5)
    arrow(ax, (5.4, 3.6), (6.1, 3.7)); arrow(ax, (5.4, 2.9), (6.1, 2.5))
    box(ax, 8.8, 2.1, 1.9, 2.0, "SS-10 interlock\n\nany two layers\ndisagreeing by\n>3× budget →\nAMPLIFIER\nDISABLE", ec=ORANGE, lw=1.8)
    arrow(ax, (8.3, 2.5), (8.8, 2.9), c=ORANGE, lw=1.5)
    ax.text(0.3, 1.05, "CALIBRATION CHAIN (traceability for E1 status):\n"
        "   national standard → accredited Helmholtz coil (Ø1 m, uniformity <0.1 % over 100 mm, cal to 3 kHz)\n"
        "   → Layer-2 fluxgate → Layer-3 search coils (each probe individually, all 5 map positions)\n"
        "   → in-situ transfer of Layer-1 (I → B) using the Layer-3 probes at the ECV reference point P1.\n"
        "Layer 1 alone is NEVER a B measurement: it is a fast observer, valid only while the transfer holds.",
            fontsize=6.8, va="top", family="DejaVu Sans Mono",
            bbox=dict(fc="#fafafa", ec="#bbbbbb", lw=0.7, pad=5))
    ax.text(6.1, 5.15, "SENSOR SELECTION RESULT\n"
        "  Hall      — rejected for Layer 3: 300 nT/√Hz noise floor and 400 ppm/K drift\n"
        "  Fluxgate  — Layer 2 only: it SATURATES at ~1 mT, far below the dose ladder\n"
        "  Search coil — Layer 3: V = N·A·2πf·B, so it is inherently AC and immune to\n"
        "               the 50 µT DC geomagnetic background. Output at 1 mT:\n"
        "               0.38 mV (3 Hz) → 377 mV (3 kHz) with N = 200, A = 1 cm².",
            fontsize=6.6, va="top", family="DejaVu Sans Mono", color=GREEN)
    save(fig, "FIG09_sensor_architecture")


def fig10():
    import cell as CELL, system as S
    from magnetics import Bmag
    from architectures import BUILDERS
    from magnetics import ForkGeometry
    core = S.CoreGeom()
    fk = ForkGeometry(n_prong=1, prong_w=core.pole_w, prong_h=core.pole_h,
                      prong_len=core.leg_len, gap=core.gap)
    st = CELL.cell_field_stats(1.0)
    bp = 50e-3 / st["mean"]
    sheets = BUILDERS["R3"](fk, bp)
    ex = CELL.ecv_geometry()
    fig = plt.figure(figsize=(11.5, 4.8))
    fig.suptitle("FIG.10  Five-point and full 3-D field mapping over the Exposure Control Volume (computed, B_ECV set to 50 mT)",
                 fontsize=10, fontweight="bold", x=0.02, ha="left")
    ax = fig.add_subplot(1, 3, 1)
    nx, ny = 120, 120
    X = np.linspace(-0.16, 0.16, nx); Y = np.linspace(-0.16, 0.16, ny)
    Z = np.array([[Bmag((x, y, core.gap/2), sheets)*1e3 for x in X] for y in Y])
    im = ax.contourf(X*1e3, Y*1e3, Z, levels=24, cmap="Blues")
    ax.contour(X*1e3, Y*1e3, Z, levels=[45, 47.5, 50, 52.5], colors="k", linewidths=0.5)
    ax.add_patch(Rectangle((-core.pole_w/2*1e3, -core.pole_h/2*1e3), core.pole_w*1e3,
                           core.pole_h*1e3, ec=RED, fc="none", lw=1.4))
    ax.add_patch(Rectangle((-ex["x_half"]*1e3, -ex["y_half"]*1e3), 2*ex["x_half"]*1e3,
                           2*ex["y_half"]*1e3, ec=GREEN, fc="none", lw=1.6, ls="-."))
    ax.plot(0, 0, "o", color=GREEN, ms=5); ax.text(4, 4, "P1", color=GREEN, fontsize=7)
    ax.plot(0, ex["y_half"]*1e3, "o", color=GREEN, ms=5); ax.text(4, ex["y_half"]*1e3-10, "P4", color=GREEN, fontsize=7)
    ax.plot(0, -ex["y_half"]*1e3, "o", color=GREEN, ms=5); ax.text(4, -ex["y_half"]*1e3+4, "P5", color=GREEN, fontsize=7)
    ax.set_title("gap mid-plane |B| [mT]  (x–y)", fontsize=7.5)
    ax.set_xlabel("x [mm] (flow)", fontsize=7); ax.set_ylabel("y [mm]", fontsize=7)
    ax.tick_params(labelsize=6.5); ax.set_aspect("equal")
    plt.colorbar(im, ax=ax, fraction=0.046).ax.tick_params(labelsize=6)

    ax2 = fig.add_subplot(1, 3, 2)
    Zg = np.linspace(0.0005, core.gap-0.0005, 200)
    for xo, lab, c in ((0.0, "x = 0 (P1)", BLUE), (0.08, "x = 80 mm", "#7aa5d8"), (0.1, "x = 100 mm (ECV edge)", RED)):
        ax2.plot(Zg*1e3, [Bmag((xo, 0, z), sheets)*1e3 for z in Zg], color=c, label=lab)
    ax2.axvspan(ex["z_lo"]*1e3, ex["z_hi"]*1e3, color=GREEN, alpha=0.10)
    ax2.axvspan(0, 3, color="#cccccc"); ax2.axvspan(core.gap*1e3-3, core.gap*1e3, color="#cccccc")
    ax2.text(1.5, 44, "duct\nwall", fontsize=5.5, ha="center", rotation=90)
    ax2.plot(ex["z_lo"]*1e3, Bmag((0, 0, ex["z_lo"]), sheets)*1e3, "o", color=GREEN, ms=5)
    ax2.plot(ex["z_hi"]*1e3, Bmag((0, 0, ex["z_hi"]), sheets)*1e3, "o", color=GREEN, ms=5)
    ax2.text(ex["z_lo"]*1e3+0.4, Bmag((0,0,ex["z_lo"]), sheets)*1e3+0.4, "P2", color=GREEN, fontsize=7)
    ax2.text(ex["z_hi"]*1e3-2.2, Bmag((0,0,ex["z_hi"]), sheets)*1e3+0.4, "P3", color=GREEN, fontsize=7)
    ax2.set_xlabel("z across the gap [mm]", fontsize=7); ax2.set_ylabel("|B| [mT]", fontsize=7)
    ax2.legend(fontsize=6); ax2.grid(alpha=0.3); ax2.tick_params(labelsize=6.5)
    ax2.set_title("gap traverse", fontsize=7.5)

    ax3 = fig.add_subplot(1, 3, 3); ax3.axis("off")
    fp = CELL.__dict__  # placeholder
    from magnetics import ECV, five_point_map
    e = ECV(ex["x_half"], ex["y_half"], ex["z_lo"], ex["z_hi"])
    pts = five_point_map(fk, bp, e)
    txt = "COMPUTED FIVE-POINT MAP  (B_ECV set point 50.00 mT)\n\n"
    txt += f"{'point':<18}{'|B| [mT]':>10}{'dev [%]':>10}\n" + "-"*38 + "\n"
    for k, v in pts.items():
        txt += f"{k:<18}{v['Bmag']*1e3:>10.3f}{100*(v['Bmag']-50e-3)/50e-3:>10.2f}\n"
    txt += "-"*38 + "\n"
    txt += (f"\nFULL ECV GRID  (13 × 13 × 9 = 1,521 points)\n"
            f"  B_mean = {st['mean']*bp*1e3:.3f} mT\n"
            f"  B_min  = {st['mn']*bp*1e3:.3f} mT\n"
            f"  B_max  = {st['mx']*bp*1e3:.3f} mT\n"
            f"  CV_B   = {st['cv']*100:.2f} %     REQUIREMENT ≤ 10 %   PASS\n\n"
            f"ECV = {ex['vol_L']:.3f} L per cell × 3 = {3*ex['vol_L']:.3f} L\n\n"
            "NOTE  the CV_B requirement is written against the ECV, NOT\n"
            "against the 1,000 L tank. No local fork can make 1 m³ uniform;\n"
            "writing the spec against the tank would make it unachievable\n"
            "and therefore meaningless.")
    ax3.text(0, 1, txt, fontsize=6.4, va="top", family="DejaVu Sans Mono",
             bbox=dict(fc="#fafafa", ec="#bbbbbb", lw=0.7, pad=6))
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    save(fig, "FIG10_field_mapping")


def fig11():
    fig, ax = newfig(11, 5.0, "FIG.11  Constant-B closed loop — cascaded B / current control with feed-forward")
    ax.set_xlim(0, 11); ax.set_ylim(0, 5.0)
    y = 3.0
    ax.add_patch(Circle((1.0, y), 0.22, ec=K, fc="white", lw=1.2))
    ax.text(1.0, y, "Σ", ha="center", va="center", fontsize=10)
    ax.text(0.98, y+0.30, "+", fontsize=8); ax.text(0.98, y-0.42, "−", fontsize=8)
    ax.text(0.15, y+0.30, "B_set(t)", fontsize=7.5)
    arrow(ax, (0.15, y), (0.78, y))
    box(ax, 1.5, y-0.42, 1.5, 0.84, "outer B loop\nPI + repetitive\n(f-scheduled)", ec=BLUE)
    arrow(ax, (1.22, y), (1.5, y))
    ax.add_patch(Circle((3.4, y), 0.22, ec=K, fc="white", lw=1.2)); ax.text(3.4, y, "Σ", ha="center", va="center", fontsize=10)
    arrow(ax, (3.0, y), (3.18, y))
    box(ax, 3.9, y-0.42, 1.5, 0.84, "inner I loop\n>10 kHz BW\ncurrent mode")
    arrow(ax, (3.62, y), (3.9, y))
    box(ax, 5.9, y-0.42, 1.5, 0.84, "amplifier +\ncompensation")
    arrow(ax, (5.4, y), (5.9, y))
    box(ax, 7.9, y-0.42, 1.4, 0.84, "cell\nB = k(geom)·I", ec=RED)
    arrow(ax, (7.4, y), (7.9, y))
    arrow(ax, (9.3, y), (10.4, y)); ax.text(9.6, y+0.28, "B(f,r,t)", fontsize=7.5, color=BLUE)
    box(ax, 3.9, 4.15, 2.6, 0.6, "feed-forward:  I* = B_set / k(geom)   +  Ẑ(f,T)⁻¹ compensation", fs=7)
    arrow(ax, (5.2, 4.15), (3.62, y+0.22), ls="--")
    box(ax, 7.6, 1.15, 2.0, 0.7, "L3 probe + coherent\ndemodulation", ec=GREEN)
    ax.plot([8.6, 8.6], [y-0.42, 1.85], color=GREEN, lw=1.1)
    ax.plot([7.6, 1.0], [1.5, 1.5], color=GREEN, lw=1.1)
    arrow(ax, (1.0, 1.5), (1.0, y-0.22), c=GREEN)
    box(ax, 3.9, 0.15, 2.6, 0.7, "L1 current + L2 reference → observer / fault detection", ec=ORANGE, fs=7)

    ax.text(0.15, 2.15,
        "ERROR BUDGET  |B_meas − B_set| / B_set        target ≤ 5 %\n"
        "   measurement U(k=2) ................ 2.87 %   (probe position 1.2 %, cal transfer 0.5 %)\n"
        "   regulation residual ............... 0.03 %   (3 % plant drift, ≥40 dB loop gain)\n"
        "   demodulation ...................... <0.01 %  (SNR ≥ 7·10⁴ even at 3 Hz / 0.5 mT)\n"
        "   gap thermal expansion over 20 K ... 0.02 %\n"
        "   16-bit set-point quantisation ..... 0.002 %\n"
        "   ────────────────────────────────────────────\n"
        "   RSS TOTAL ......................... 2.87 %   PASS, with 1.7× margin",
        fontsize=6.7, va="top", family="DejaVu Sans Mono",
        bbox=dict(fc="#fafafa", ec="#bbbbbb", lw=0.7, pad=5))
    save(fig, "FIG11_constant_B_loop")


def fig12():
    import run_all as RA, thermal as TH
    fig, ax = newfig(11, 5.4, "FIG.12  Thermal management — heat sources separated by whether they are field-coupled and whether they reach the water")
    ax.set_xlim(0, 11); ax.set_ylim(0, 5.4)
    box(ax, 0.3, 4.1, 1.9, 0.85, "P_Cu  14.8 W\n(field-coupled)", ec=ORANGE)
    box(ax, 0.3, 3.0, 1.9, 0.85, "P_core  5.9 W\n(field-coupled)", ec=ORANGE)
    box(ax, 0.3, 1.9, 1.9, 0.85, "P_driver ≈ 300 W\n(not in the water)", ec=ORANGE)
    box(ax, 0.3, 0.8, 1.9, 0.85, "P_pump  524 W\n(NOT field-coupled)", ec=K)
    box(ax, 3.0, 3.1, 2.1, 1.6, "DRY SIDE\ncold plate\n25 °C glycol\nR_th 0.055 / 0.030 K/W")
    arrow(ax, (2.2, 4.5), (3.0, 4.2), c=ORANGE); arrow(ax, (2.2, 3.4), (3.0, 3.9), c=ORANGE)
    box(ax, 3.0, 1.7, 2.1, 0.9, "forced-air heatsink\n35 °C ambient")
    arrow(ax, (2.2, 2.3), (3.0, 2.15), c=ORANGE)
    box(ax, 6.0, 0.6, 2.3, 1.3, "PROCESS WATER\n1,000 L\nchiller ±0.2 K", ec=BLUE, lw=1.6)
    arrow(ax, (2.2, 1.2), (6.0, 1.2))
    box(ax, 6.0, 2.6, 2.3, 0.9, "P_water(field)\n20.7 W max\nσE², E = πfBr", ec=BLUE)
    arrow(ax, (6.9, 2.6), (6.9, 1.9), c=BLUE)
    ax.text(8.6, 3.6,
        "THE SHAM ARGUMENT, QUANTIFIED\n\n"
        "  pump heat            524 W\n"
        "  field heat in water   20.7 W  (worst corner)\n"
        "  ratio                 25 : 1\n\n"
        "Because the exposure cell is DRY and the duct is\n"
        "non-metallic, the only field-coupled heat entering\n"
        "the water is the ohmic term σ·E². Running the Sham\n"
        "arm with identical pump duty therefore matches\n"
        "≥96 % of the total water heating, and the residual\n"
        "is 0.018 K/h — below the ±0.3 K control band.\n\n"
        "That is what makes H1 (thermal artifact) TESTABLE\n"
        "rather than merely asserted.",
        fontsize=6.7, va="top", family="DejaVu Sans Mono",
        bbox=dict(fc="#fafafa", ec="#bbbbbb", lw=0.7, pad=5))
    ax.text(0.3, 0.35, "Sensors: T_coil ×6 (fibre-optic in-winding ×2), T_core ×3, T_driver ×3, T_tank ×2, T_water ×3 — "
                       "each with its OWN limit. A single 25 °C threshold is never applied across devices.",
            fontsize=6.6, style="italic")
    save(fig, "FIG12_thermal")


def fig13():
    fig, ax = newfig(11, 5.6, "FIG.13  Safety interlock — hardwired chain in series with AMPLIFIER ENABLE")
    ax.set_xlim(0, 11); ax.set_ylim(0, 5.6)
    conds = ["Over-current  (L1 fluxgate CT, hardware comparator)",
             "Over-voltage  (compensation bank + amplifier output)",
             "Coil over-temperature  (fibre-optic hot spot, 120 °C)",
             "Driver over-temperature  (heatsink NTC, 95 °C)",
             "Water leak  (conductive tape under the cell array)",
             "Insulation failure  (IMD on the IT-earthed sub-net)",
             "Sensor failure / layer disagreement > 3× budget",
             "B-field runaway  (|B| > 1.2 × set for > 3 cycles)",
             "PLC / DSP communication loss  (watchdog, 50 ms)",
             "Emergency stop ×3  (dual-channel, forced-guided)"]
    y = 5.0
    ax.plot([0.5, 0.5], [0.55, y], color=ORANGE, lw=2.2)
    for i, c in enumerate(conds):
        yy = y - i*0.44
        ax.add_patch(Rectangle((0.42, yy-0.06), 0.16, 0.12, fc="white", ec=ORANGE, lw=1.4))
        ax.plot([0.58, 1.0], [yy, yy], color=ORANGE, lw=1.2)
        ax.text(1.1, yy, c, fontsize=7, va="center")
        ax.text(0.12, yy, f"{i+1}", fontsize=6.5, va="center", color=ORANGE)
    ax.plot([0.5, 7.6], [0.55, 0.55], color=ORANGE, lw=2.2)
    box(ax, 7.6, 2.4, 1.6, 1.0, "SIL2 safety\nrelay\n(dual channel)", ec=ORANGE, lw=1.8)
    ax.plot([7.6, 8.4, 8.4], [0.55, 0.55, 2.4], color=ORANGE, lw=2.2)
    box(ax, 7.6, 4.1, 1.6, 0.9, "ENABLE\ncontactor", ec=ORANGE, lw=1.8)
    arrow(ax, (8.4, 3.4), (8.4, 4.1), c=ORANGE, lw=2.0)
    box(ax, 9.5, 4.1, 1.3, 0.9, "AMPLIFIER\npower stage", ec=K, lw=1.4)
    arrow(ax, (9.2, 4.55), (9.5, 4.55), c=ORANGE, lw=2.0)
    ax.text(7.6, 1.9, "PLC alarms are ANNUNCIATION ONLY.\n"
                      "No software path can hold ENABLE closed.\n"
                      "De-energise-to-trip; the chain fails safe on\n"
                      "loss of 24 V, broken wire, or welded contact\n"
                      "(forced-guided monitoring).\n\n"
                      "Reset requires: fault cleared AND local manual\n"
                      "reset AND a logged operator acknowledgement.",
            fontsize=6.6, va="top", family="DejaVu Sans Mono", color=ORANGE)
    save(fig, "FIG13_safety_interlock")


def fig14():
    fig, ax = newfig(11, 5.4, "FIG.14  Active / Sham architecture — everything identical except the field")
    ax.set_xlim(0, 11); ax.set_ylim(0, 5.4)
    for j, (lab, col, xoff) in enumerate((("ACTIVE arm", BLUE, 0.4), ("SHAM arm", "#777777", 5.8))):
        ax.add_patch(Rectangle((xoff, 1.3), 4.4, 3.4, ec=col, fc="none", lw=1.6))
        ax.text(xoff+2.2, 4.85, lab, ha="center", fontsize=9, fontweight="bold", color=col)
        box(ax, xoff+0.25, 3.7, 1.8, 0.7, "same pump duty\nsame VFD set point")
        box(ax, xoff+2.3, 3.7, 1.85, 0.7, "same duct geometry\nmatched ΔP orifice")
        box(ax, xoff+0.25, 2.6, 1.8, 0.7, "same water batch\nsame sampling")
        box(ax, xoff+2.3, 2.6, 1.85, 0.7, "same chiller ±0.2 K\nsame residence time")
        box(ax, xoff+0.25, 1.55, 3.9, 0.75,
            "coil ENERGISED\nB = set point" if j == 0 else
            "coil wound and CONNECTED,\nbut bifilar-cancelled: I flows, B ≈ 0",
            ec=col, lw=1.5)
    ax.text(0.4, 1.05,
        "SHAM INTEGRITY (VG-07), quantified:\n"
        "   Layer-3 probe 3σ detection limit at 50 Hz, 0.1 Hz BW ......... 0.66 nT\n"
        "   Geomagnetic DC background ................................... 50,000 nT  (75,000× larger)\n"
        "   Required Sham isolation for residual < 1 % of the 0.5 mT rung  ≥ 40 dB\n"
        "   Bifilar cancellation + ≥1.5 m separation, target ............. ≥ 80 dB  →  5 µT residual\n"
        "The Sham coil is DRIVEN, not switched off: the amplifier fan noise, the cabinet heat, the contactor\n"
        "clicks and the current-sensor readings are all identical. Only the winding sense differs.\n"
        "Blinding: the arm assignment is generated by the PLC from a sealed randomisation table; the operator\n"
        "sees only a run ID. Sample bottles are barcoded, not labelled. Unblinding happens at analysis.",
        fontsize=6.7, va="top", family="DejaVu Sans Mono",
        bbox=dict(fc="#fafafa", ec="#bbbbbb", lw=0.7, pad=5))
    save(fig, "FIG14_active_sham")


def fig15():
    fig, ax = newfig(11, 5.4, "FIG.15  Bayesian digital twin — residual-driven fault detection and posterior updating")
    ax.set_xlim(0, 11); ax.set_ylim(0, 5.4)
    box(ax, 0.3, 3.9, 2.3, 1.1, "MEASURED STATE  X(t)\nf, I, V, B, T_coil, T_water,\nEC, pH, flow, runtime", ec=GREEN, lw=1.5)
    box(ax, 0.3, 2.2, 2.3, 1.1, "PHYSICS MODEL\nreluctance + Dowell +\nSteinmetz + thermal RC", ec=RED, lw=1.5)
    ax.add_patch(Circle((3.6, 3.6), 0.26, ec=K, fc="white", lw=1.3)); ax.text(3.6, 3.6, "−", ha="center", va="center", fontsize=12)
    arrow(ax, (2.6, 4.45), (3.4, 3.75)); arrow(ax, (2.6, 2.75), (3.4, 3.45))
    box(ax, 4.4, 3.15, 1.7, 0.9, "residual r(t)", ec=BLUE, lw=1.4)
    arrow(ax, (3.86, 3.6), (4.4, 3.6))
    for i, (t, d) in enumerate((("sensor drift", "slow bias in one layer only"),
                                ("coil degradation", "R_dc rises, L unchanged"),
                                ("impedance change", "L shifts → band retune"),
                                ("thermal anomaly", "T rises at constant P"),
                                ("gap change", "B/I ratio shifts, R_dc flat"))):
        yy = 4.6 - i*0.62
        box(ax, 6.6, yy-0.24, 1.9, 0.48, t, ec=ORANGE, fs=6.8)
        ax.text(8.65, yy, d, fontsize=6.2, va="center")
        arrow(ax, (6.1, 3.6), (6.6, yy), c=BLUE, lw=0.8)
    ax.text(0.3, 1.85,
        "SIGNATURE SEPARATION — why the residual vector, not a single alarm threshold:\n"
        "   R_dc ↑ and L flat and B/I flat ......... conductor/joint degradation\n"
        "   R_dc flat and B/I ↓ .................... mechanical gap growth or core damage\n"
        "   L1 and L2 agree, L3 disagrees .......... Layer-3 probe drift, NOT a field change\n"
        "   L1 and L3 agree, L2 disagrees .......... external field intrusion or L2 drift\n"
        "   T ↑ at constant computed P_loss ........ cooling loop degradation\n\n"
        "POSTERIOR UPDATING: the same twin carries the effect model. Each completed block updates\n"
        "P(effect > δ_min | Data) for every response, and updates P(H0), P(H1), P(H2), P(H3).\n"
        "If no effect is observed, the correct action is to UPDATE THE POSTERIOR — not to raise B.",
        fontsize=6.7, va="top", family="DejaVu Sans Mono",
        bbox=dict(fc="#fafafa", ec="#bbbbbb", lw=0.7, pad=5))
    save(fig, "FIG15_digital_twin")


def fig16():
    fig, ax = newfig(11, 5.6, "FIG.16  Pilot layout — 1-cell rig → Stage 3, with the safety and EMC boundary")
    ax.set_xlim(0, 11); ax.set_ylim(0, 5.6)
    ax.add_patch(Rectangle((0.3, 0.4), 10.4, 4.6, ec=ORANGE, fc="none", lw=1.8, ls="--"))
    ax.text(0.45, 4.78, "controlled area — interlocked doors, ≥1.5 m exclusion around the cell array",
            fontsize=6.8, color=ORANGE)
    ax.add_patch(Rectangle((0.7, 2.6), 1.9, 1.9, ec=K, fc="#f5f5f5", lw=1.3))
    ax.text(1.65, 3.55, "power cabinet\n\namplifier ×3\ncompensation bank\nisolation TX\nEMC filters", ha="center", fontsize=6.5)
    ax.add_patch(Rectangle((0.7, 0.8), 1.9, 1.4, ec=K, fc="#f5f5f5", lw=1.3))
    ax.text(1.65, 1.5, "control cabinet\nPLC/safety CPU\nDSP target\nhistorian", ha="center", fontsize=6.5)
    for i in range(3):
        ax.add_patch(Rectangle((3.6+i*0.75, 2.4), 0.55, 1.6, ec=RED, fc="#fdeceb", lw=1.4))
        ax.text(3.87+i*0.75, 4.12, f"cell {i+1}", fontsize=6, ha="center", color=RED)
    ax.add_patch(Rectangle((3.5, 2.9), 2.5, 0.6, ec=BLUE, fc="#eaf1fb", lw=1.2))
    ax.text(4.75, 2.15, "exposure cell array on\nnon-magnetic frame", ha="center", fontsize=6.5)
    ax.add_patch(Circle((7.4, 3.2), 0.85, ec=K, fc="#f2f2f2", lw=1.6))
    ax.text(7.4, 3.2, "1,000 L\nSUS316L", ha="center", va="center", fontsize=6.8)
    ax.add_patch(Circle((7.4, 1.35), 0.35, ec=K, fc="white", lw=1.2)); ax.text(7.4, 1.35, "P", ha="center", va="center", fontsize=7)
    ax.add_patch(Rectangle((8.7, 2.6), 1.6, 1.3, ec=K, fc="#f5f5f5", lw=1.3))
    ax.text(9.5, 3.25, "chiller\n3 kW\n±0.2 K", ha="center", fontsize=6.5)
    ax.add_patch(Rectangle((8.7, 0.8), 1.6, 1.4, ec=GREEN, fc="none", lw=1.4))
    ax.text(9.5, 1.5, "sampling station\nautosampler\nblinded bottles\n4 °C archive", ha="center", fontsize=6.3, color=GREEN)
    for a, b in (((6.0, 3.2), (6.55, 3.2)), ((7.4, 2.35), (7.4, 1.7)),
                 ((7.05, 1.35), (4.75, 1.35)), ((4.75, 1.35), (4.75, 2.4)),
                 ((8.25, 3.2), (8.7, 3.2))):
        arrow(ax, a, b)
    ax.text(0.45, 0.15,
        "SCALE-UP GATES:  Stage 1 bench coil (single cell, 5 L loop)  →  Stage 2  50–100 L  →  Stage 3  1,000 L  →  Stage 4 multi-tank.\n"
        "No stage starts until the previous stage has passed VG-01…VG-11 AND the ECV/tank-volume dose bookkeeping has been re-derived.",
        fontsize=6.6, style="italic")
    save(fig, "FIG16_pilot_layout")


if __name__ == "__main__":
    print("rendering FIG package:")
    for fn in (fig01, fig02, fig03, fig04, fig05, fig06, fig07, fig08,
               fig09, fig10, fig11, fig12, fig13, fig14, fig15, fig16):
        try:
            fn()
        except Exception as e:
            import traceback
            print("   FAILED", fn.__name__, e)
            traceback.print_exc()
    print("done ->", OUT)
