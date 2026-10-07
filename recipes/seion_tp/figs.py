import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from tp_cellmodel import simulate, hot_face
for f in fm.findSystemFonts():
    if "Noto" in f and ("CJK" in f or "KR" in f):
        fm.fontManager.addfont(f); plt.rcParams["font.family"] = fm.FontProperties(fname=f).get_name(); break
plt.rcParams["axes.unicode_minus"] = False
res = json.load(open("results.json"))
# 현실 k0: 나노 0.3×0.015 + 매크로 0.7×0.035 직렬
k_real = 1 / (0.3 / 0.015 + 0.7 / 0.035)
extra = {}
for n, kw in [("G 현실 k0, 집중용량", dict(cell="lumped")), ("H 현실 k0, 분포형 0.6", dict(cell="distributed", k_cell=0.6))]:
    t, s, a = simulate(k_real, t_end=10800.0, **kw)
    m = t <= 7200
    i = np.argmax(s >= 150)
    extra[n] = dict(t=t.tolist(), surf=s.tolist(), max2h=float(s[m].max()), t150=float(t[i]) if s[i] >= 150 else None)
    print(f"{n}: k0={k_real:.4f}, 2h 최고 {s[m].max():.1f}, 150 도달 {t[i]/60 if s[i]>=150 else float('nan'):.0f} min")
json.dump(extra, open("results_real_k.json", "w"))

fig, ax = plt.subplots(1, 2, figsize=(12, 4.6), dpi=150)
sel = ["A 집중용량 (계획서 조건)", "C 분포형 k_cell=0.6", "D 분포형 k_cell=0.3", "F 분포형 0.6 + 압축(0.25 MPa)"]
cols = ["#1f4e79", "#2e8b57", "#d4a017", "#c0392b"]
for n, c in zip(sel, cols):
    r = res[n]; t = np.array(r["t"]) / 60
    ax[0].plot(t, r["surf"], color=c, lw=1.8, label=n)
r = extra["H 현실 k0, 분포형 0.6"]; ax[0].plot(np.array(r["t"]) / 60, r["surf"], color="#7d3c98", lw=1.8, ls="--", label="H 현실 k0(0.025) + 분포형 0.6")
for a_ in ax:
    a_.axhline(150, color="k", ls=":", lw=1)
ax[0].axvline(120, color="gray", ls="--", lw=0.8)
ax[0].set(xlabel="시간 [min]", ylabel="인접 셀 표면온도 [℃]", title="인접 셀 표면온도 — 셀 모델·압축 조건별", xlim=(0, 180), ylim=(20, 220))
ax[0].text(122, 205, "GB 38031 2 h", fontsize=8, color="gray"); ax[0].legend(fontsize=7.5, loc="lower right")
for n, c in zip(sel[:3], cols[:3]):
    r = res[n]; t = np.array(r["t"])
    ax[1].plot(t, r["surf"], color=c, lw=1.8, label=n)
ax[1].set(xlabel="시간 [s]", ylabel="인접 셀 표면온도 [℃]", title="초기 30분 확대 — 분포형 모델의 표면 스파이크", xlim=(0, 1800), ylim=(20, 160))
ax[1].legend(fontsize=7.5)
fig.tight_layout(); fig.savefig("tp_cellmodel_compare.png")
print("saved")
