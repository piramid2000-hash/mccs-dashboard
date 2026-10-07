"""두께 상향 대안: 총두께별(압축 0.25 MPa, 평균 변형률 37.7 % 코어 전담) 분포형 셀 통과 k0 상한 [P]."""
import json
from concurrent.futures import ProcessPoolExecutor
from tp_cellmodel import simulate
from run_cases import CALS

CAL_SEL = ["Cal-1 Fig.1 형상 (셀 방열 h=120)", "Cal-2 표 5-1 문언 (단열 셀)"]
TOTALS = [1.5e-3, 2.0e-3, 2.5e-3, 3.0e-3]


def req(args):
    cal, tot = args
    tc0 = tot - 0.6e-3
    tc = tc0 - 0.377 * tot
    lo, hi = 0.0005, 0.12
    for _ in range(18):
        mid = 0.5 * (lo + hi)
        _, s, _ = simulate(mid, "distributed", k_cell=0.6, dt=1.0, **CALS[cal], t_core=tc, compressed=True, t_core0=tc0)
        lo, hi = (mid, hi) if s.max() <= 150 else (lo, mid)
    return cal, tot, tc, lo


if __name__ == "__main__":
    with ProcessPoolExecutor() as ex:
        out = list(ex.map(req, [(c, t) for c in CAL_SEL for t in TOTALS]))
    json.dump(out, open("thick_option.json", "w"), ensure_ascii=False)
    for c, tot, tc, k in out:
        print(f"{c:28s} 총두께 {tot*1e3:.1f} mm (압축 코어 {tc*1e3:.2f} mm) → k0 ≤ {k:.4f}")
