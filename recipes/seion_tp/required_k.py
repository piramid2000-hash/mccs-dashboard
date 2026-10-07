"""보정 방식별: 분포형 셀(k_cell 0.6)에서 인접 셀 표면 ≤ 150 ℃(여유 0 / 10 ℃)를 만족하는 코어 k0 상한 [P]."""
import json
from concurrent.futures import ProcessPoolExecutor
from tp_cellmodel import simulate
from run_cases import CALS, T_CORE_C

GEOM = {"비압축 (코어 0.90 mm)": dict(), "압축 0.25 MPa (코어 0.34 mm)": dict(t_core=T_CORE_C, compressed=True)}


def req(args):
    cal, geom, limit = args
    lo, hi = 0.0005, 0.12
    for _ in range(18):
        mid = 0.5 * (lo + hi)
        _, s, _ = simulate(mid, "distributed", k_cell=0.6, dt=1.0, t_end=7200.0, **CALS[cal], **GEOM[geom])
        lo, hi = (mid, hi) if s.max() <= limit else (lo, mid)
    return cal, geom, limit, lo


if __name__ == "__main__":
    jobs = [(c, g, L) for c in CALS for g in GEOM for L in (150.0, 140.0)]
    with ProcessPoolExecutor() as ex:
        out = list(ex.map(req, jobs))
    json.dump(out, open("required_k.json", "w"), ensure_ascii=False)
    for c, g, L, k in out:
        print(f"{c:30s} {g:28s} ≤{L:.0f}℃ → k0 ≤ {k:.4f}")
