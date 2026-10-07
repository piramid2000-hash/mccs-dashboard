"""C2C 스페이서 열전파(TP) 1D 과도 전도 모델 [P].

모델: 트리거 셀 표면(hot face) 계단 승온 → 압축된 패드 → 인접 셀(유한 두께, 후면 단열).
k_pad(T) = k25 * (1 + a*(T-25)), a 는 AG-6.0 문서 [P] 값(0.55 MPa, 25→200°C)에서 보정.
판정: 인접 셀 표면 온도가 T_limit 에 도달하는 시간 t_fail.
"""
import numpy as np

A_KT = (0.1476 / 0.0985 - 1) / 175  # 1/K, 문서 8.2절 0.55 MPa 예측값에서 산출


def simulate(k25, L_mm, T_hot=800.0, t_end=900.0, T0=25.0, T_limit=150.0,
             rho_pad=425.0, cp_pad=1000.0, a=A_KT,
             k_cell=0.8, rho_cell=2400.0, cp_cell=1050.0, L_cell_mm=13.0):
    L, Lc = L_mm / 1000, L_cell_mm / 1000
    n_p, n_c = 40, 40
    dx_p, dx_c = L / n_p, Lc / n_c
    T = np.full(n_p + n_c + 1, T0)
    T[0] = T_hot
    rc = np.r_[np.full(n_p, rho_pad * cp_pad), np.full(n_c + 1, rho_cell * cp_cell)]
    dx = np.r_[np.full(n_p, dx_p), np.full(n_c + 1, dx_c)]
    k_max = k25 * (1 + a * (T_hot - 25))
    dt = 0.4 * min(rho_pad * cp_pad * dx_p**2 / k_max, rho_cell * cp_cell * dx_c**2 / k_cell)
    t, t_fail, iface = 0.0, None, n_p
    hist = []
    while t < t_end:
        kp = k25 * (1 + a * (0.5 * (T[:n_p] + T[1:n_p + 1]) - 25))
        k_face = np.r_[kp / dx_p, np.full(n_c, k_cell / dx_c)]
        q = k_face * (T[:-1] - T[1:])           # 면 열유속 W/m2
        dT = np.zeros_like(T)
        dT[1:-1] = (q[:-1] - q[1:]) / (rc[1:-1] * dx[1:-1])
        dT[-1] = q[-1] / (rc[-1] * dx[-1] * 0.5)
        T += dt * dT
        T[0] = T_hot
        t += dt
        if t_fail is None and T[iface] >= T_limit:
            t_fail = t
        hist.append((t, T[iface]))
    return t_fail, np.array(hist)


def required_k25(L_mm, t_req, **kw):
    """t_req 초 동안 인접셀 ≤ T_limit 를 만족하는 최대 k25 (이분법)."""
    lo, hi = 0.005, 0.3
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        tf, _ = simulate(mid, L_mm, t_end=t_req * 1.01, **kw)
        lo, hi = (mid, hi) if tf is None else (lo, mid)
    return lo


if __name__ == "__main__":
    print("AG-6.0 [P] 물성(k25=0.0985, 0.55MPa 두께 2.177mm), hot face 800°C")
    tf, _ = simulate(0.0985, 2.177)
    print(f"  인접셀 150°C 도달: {tf:.0f} s" if tf else "  15분 내 미도달")
    for L in (2.0, 2.5, 3.0):
        for t_req in (300, 600):
            print(f"  두께 {L} mm(압축 후), {t_req//60}분 차단 요구 k25 ≤ {required_k25(L, t_req):.4f} W/m·K")
