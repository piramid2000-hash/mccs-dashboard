"""보정 방식 3종 × 셀 모델·압축 케이스 — 결론의 보정 의존성 점검 [P]."""
import json
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from tp_cellmodel import simulate, calibrate

T_CORE_C = 0.9e-3 - 0.377 * 1.5e-3  # 0.25 MPa 평균 변형률 37.7 % 를 코어가 전담 → 0.335 mm
K_STRUCT = 1 / (0.3 / 0.015 + 0.7 / 0.035)  # 구조 기반 코어 k0 추정 0.025
CALS = {
    "Cal-1 Fig.1 형상 (셀 방열 h=120)": dict(h_loss=120.0),
    "Cal-2 표 5-1 문언 (단열 셀)": dict(),
    "Cal-3 잔류열원 감쇠 τ=1200 s": dict(tau_r=1200.0),
}
CASES = {
    "A 집중용량": dict(cell="lumped"),
    "C 분포형 k0.6": dict(cell="distributed", k_cell=0.6),
    "D 분포형 k0.3": dict(cell="distributed", k_cell=0.3),
    "E 집중 + 압축": dict(cell="lumped", t_core=T_CORE_C, compressed=True),
    "F 분포형0.6 + 압축": dict(cell="distributed", k_cell=0.6, t_core=T_CORE_C, compressed=True),
    "H 구조 k0 + 분포형0.6": dict(cell="distributed", k_cell=0.6, k0=K_STRUCT),
    "I 구조 k0 + 분포형0.6 + 압축": dict(cell="distributed", k_cell=0.6, k0=K_STRUCT, t_core=T_CORE_C, compressed=True),
}


def run(args):
    cal, k0c, case = args
    kw = dict(CASES[case]); k0 = kw.pop("k0", k0c)
    t, s, _ = simulate(k0, t_end=7200.0, dt=1.0, **CALS[cal], **kw)
    i = np.argmax(s >= 150)
    return cal, case, dict(t=t.tolist(), surf=s.tolist(), max=float(s.max()), tmax=float(t[s.argmax()]),
                           t150=float(t[i]) if s[i] >= 150 else None, k0=k0)


def cal_k0(cal):
    return cal, calibrate(**CALS[cal])


if __name__ == "__main__":
    with ProcessPoolExecutor() as ex:
        k0s = dict(ex.map(cal_k0, CALS))
    jobs = [(c, k0s[c], n) for c in CALS for n in CASES]
    with ProcessPoolExecutor() as ex:
        out = list(ex.map(run, jobs))
    res = {c: {"k0": k0s[c], "cases": {}} for c in CALS}
    for c, n, r in out:
        res[c]["cases"][n] = r
    json.dump(res, open("results.json", "w"))
    for c in CALS:
        print(f"\n## {c}  (보정 k0 = {k0s[c]:.4f} W/m·K)")
        print(f"{'케이스':26s} {'최고':>7s} {'시점':>7s} {'여유':>7s} {'150℃도달':>9s}")
        for n in CASES:
            r = res[c]["cases"][n]
            t150 = f"{r['t150']/60:.0f} min" if r["t150"] else "—"
            print(f"{n:26s} {r['max']:7.1f} {r['tmax']/60:5.0f}분 {150-r['max']:7.1f} {t150:>9s}")
