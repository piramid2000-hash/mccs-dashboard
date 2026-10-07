"""Fig.16 — (좌) 셀 모델·압축별 인접 셀 표면온도 [Cal-1], (우) 총두께별 통과 k0 상한."""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

for f in fm.findSystemFonts():
    if "NotoSansCJK" in f.replace(" ", "") or "NotoSansKR" in f:
        fm.fontManager.addfont(f); plt.rcParams["font.family"] = fm.FontProperties(fname=f).get_name(); break
plt.rcParams["axes.unicode_minus"] = False

res = json.load(open("results.json"))
thick = json.load(open("thick_option.json"))
fig, ax = plt.subplots(1, 2, figsize=(12, 4.6), dpi=150)

cal = "Cal-1 Fig.1 형상 (셀 방열 h=120)"
sel = [("A 집중용량", "#1f4e79", "-", "A 집중용량 (Rev.0 조건 재현)"),
       ("E 집중 + 압축", "#1f4e79", "--", "E 집중용량 + 압축 0.25 MPa"),
       ("C 분포형 k0.6", "#c0392b", "-", "C 분포형 셀 (k_cell 0.6)"),
       ("F 분포형0.6 + 압축", "#c0392b", "--", "F 분포형 셀 + 압축"),
       ("H 구조 k0 + 분포형0.6", "#7d3c98", ":", "H 구조 기반 k0 0.025 + 분포형")]
for key, c, ls, lab in sel:
    r = res[cal]["cases"][key]
    ax[0].plot(np.array(r["t"]) / 60, r["surf"], color=c, ls=ls, lw=1.8, label=lab)
ax[0].axhline(150, color="k", ls=":", lw=1)
ax[0].text(60, 140, "판정 150 ℃", ha="center", fontsize=8)
ax[0].set(xlabel="시간 [min]", ylabel="인접 셀 표면온도 [℃]", xlim=(0, 120), ylim=(20, 400),
          title="(a) 인접 셀 표면온도 — Fig.1 형상 보정(Cal-1)")
ax[0].legend(fontsize=7.5, loc="upper right")

for c_, col, lab in [("Cal-1 Fig.1 형상 (셀 방열 h=120)", "#c0392b", "Cal-1 (Fig.1 형상 보정)"),
                     ("Cal-2 표 5-1 문언 (단열 셀)", "#1f4e79", "Cal-2 (표 5-1 문언, 단열 셀)")]:
    pts = [(t * 1e3, k) for c, t, tc, k in thick if c == c_]
    x, y = zip(*pts)
    ax[1].plot(x, y, "o-", color=col, lw=1.8, label=lab)
ax[1].axhspan(0.012, 0.015, color="#2e8b57", alpha=0.15)
ax[1].text(1.52, 0.0135, "실리카 에어로겔 (0.012~0.015)", fontsize=7.5, va="center")
ax[1].axhline(0.025, color="#7d3c98", ls=":", lw=1.2)
ax[1].text(1.52, 0.0236, "본 레시피 구조 기반 추정 0.025", fontsize=7.5, color="#7d3c98")
ax[1].axhline(0.026, color="gray", ls="--", lw=0.8)
ax[1].text(2.98, 0.0268, "정지 공기 0.026", fontsize=7.5, color="gray", ha="right")
ax[1].set(xlabel="패드 총두께 (비압축) [mm]", ylabel="통과 가능한 코어 k0 상한 [W/m·K]", xlim=(1.45, 3.05), ylim=(0, 0.036),
          title="(b) 압축 0.25 MPa·분포형 셀에서 ≤150 ℃ 통과 조건")
ax[1].legend(fontsize=7.5, loc="lower right")
fig.tight_layout()
fig.savefig("tp_cellmodel_compare.png")
print("saved")
