import json, sys
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from tp_cellmodel import simulate

K0 = 0.008
T_CORE_C = 0.9e-3 - 0.377 * 1.5e-3  # 0.25 MPa 변형률 37.7 % 를 코어가 전담
CASES = {
    "A 집중용량 (계획서 조건)": dict(cell="lumped"),
    "B 분포형 k_cell=1.0": dict(cell="distributed", k_cell=1.0),
    "C 분포형 k_cell=0.6": dict(cell="distributed", k_cell=0.6),
    "D 분포형 k_cell=0.3": dict(cell="distributed", k_cell=0.3),
    "E 집중용량 + 압축(0.25 MPa)": dict(cell="lumped", t_core=T_CORE_C, compressed=True),
    "F 분포형 0.6 + 압축(0.25 MPa)": dict(cell="distributed", k_cell=0.6, t_core=T_CORE_C, compressed=True),
}


def first_cross(t, y, th):
    i = np.argmax(y >= th)
    return float(t[i]) if y[i] >= th else None


def run(name):
    t, s, a = simulate(K0, t_end=10800.0, **CASES[name])
    m = t <= 7200
    return name, dict(t=t.tolist(), surf=s.tolist(), avg=list(map(float, a)),
                      max2h=float(s[m].max()), avg2h=float(np.max(np.array(a)[m])),
                      t150=first_cross(t, s, 150), t120=first_cross(t, s, 120),
                      t_max_early=float(t[np.argmax(s[t <= 1800])]), max_early=float(s[t <= 1800].max()))


if __name__ == "__main__":
    with ProcessPoolExecutor() as ex:
        res = dict(ex.map(run, CASES))
    json.dump(res, open("results.json", "w"))
    print(f"{'케이스':32s} {'셀표면최고(2h)':>12s} {'여유@150':>9s} {'셀평균최고':>9s} {'150℃도달':>9s} {'120℃도달':>9s} {'초기30분최고':>11s}")
    for n, r in res.items():
        f = lambda v: f"{v/60:.0f} min" if v else ">3 h"
        print(f"{n:32s} {r['max2h']:12.1f} {150-r['max2h']:9.1f} {r['avg2h']:9.1f} {f(r['t150']):>9s} {f(r['t120']):>9s} {r['max_early']:8.1f}@{r['t_max_early']:.0f}s")
