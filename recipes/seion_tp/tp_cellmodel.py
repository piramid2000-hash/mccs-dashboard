"""SEION C2C 패드 — 인접 셀 모델(집중 vs 분포형) 민감도 해석 [P].

계획서(SEION-C2CPAD-RNDPLAN-2026-001 Rev.0) 표 5-1 조건을 따르는 대리(surrogate) 모델.
원 해석 코드가 없으므로 실시예 1(집중용량, 122.2 ℃)에 코어 k 를 보정한 뒤,
셀 모델만 바꿔 판정 여유 변화를 본다. 삭마·벤트 대류·Knudsen 상세는 보정값에 흡수됨.
"""
import numpy as np
from scipy.linalg import solve_banded

SIG = 5.670e-8
T0 = 25.0


def hot_face(t):
    # 표 5-1: 최고 780 ℃, 상승 τ 12 s, 감쇠 τ 260 s, 잔류 185 ℃
    return T0 + (1 - np.exp(-t / 12)) * ((185 - T0) + (780 - 185) * np.exp(-t / 260))


def pad_layers(core_k0, t_core=0.9e-3, compressed=False):
    """(두께, ρ, cp, k(T)함수, 유기물분율) 리스트. hot face → cell 순."""
    def k_armor(T):  # 세라믹화 420→620 ℃: 0.30 → 0.95
        s = np.clip((T - 420) / 200, 0, 1)
        return 0.30 + 0.65 * s

    rho_core = 160.0
    if compressed:  # 변형을 코어가 전담, 질량 보존
        rho_core *= 0.9e-3 / t_core
    d_macro = 150e-6 * (t_core / 0.9e-3)

    def k_core(T):  # 고체·기체(보정) + 대형기공 복사 4σ d T³ (0.7 분율)
        Tk = T + 273.15
        return core_k0 + 0.7 * 4 * SIG * d_macro * Tk**3

    def k_tr(T):
        return 0.5 * (k_armor(T) + k_core(T))

    A = (0.10e-3, 1427, 1100, k_armor, 0.54)
    Tr = (0.20e-3, 794, 1150, k_tr, 0.60)
    C = (t_core, rho_core, 1200, k_core, 0.70)
    return [A, Tr, C, Tr, A]


def simulate(core_k0, cell="lumped", k_cell=0.6, t_core=0.9e-3, compressed=False,
             t_end=7200.0, dt=0.5, h_c=2000.0, m_cell=90.0, cp_cell=1050.0):
    layers = pad_layers(core_k0, t_core, compressed)
    # 패드 격자
    xs, rho, cp, kf, worg = [], [], [], [], []
    for L, r, c, k, w in layers:
        n = max(4, int(round(L / 20e-6)))
        xs += [L / n] * n; rho += [r] * n; cp += [c] * n; kf += [k] * n; worg += [w] * n
    npad = len(xs)
    # 셀 격자 (분포형): Al can 0.8 mm + 젤리롤, 총 90 kg/m², 후면 단열
    if cell == "distributed":
        can = (0.8e-3, 2700, 900, 200.0)
        L_jr = (m_cell - can[0] * can[1]) / 2550
        ncan, njr = 4, 60
        cxs = [can[0] / ncan] * ncan + [L_jr / njr] * njr
        crho = [can[1]] * ncan + [2550] * njr
        ccp = [can[2]] * ncan + [cp_cell] * njr
        ck = [can[3]] * ncan + [k_cell] * njr
    else:
        cxs, crho, ccp, ck = [1.0], [m_cell], [cp_cell], [1e9]  # 집중용량: 면적당 열용량만
    dx = np.array(xs + cxs)
    N = len(dx)
    T = np.full(N, T0)
    surf_hist, avg_hist = [], []
    nsteps = int(t_end / dt)
    for s in range(nsteps):
        t = (s + 1) * dt
        Tp = T[:npad]
        kp = np.array([kf[i](Tp[i]) for i in range(npad)])
        cpp = np.array(cp, float)
        # 열분해 흡열 6.5e5 J/kg (420~620 ℃) → 겉보기 비열
        win = (Tp > 420) & (Tp < 620)
        cpp = cpp + np.where(win, 6.5e5 * np.array(worg) / 200, 0)
        C = np.r_[np.array(rho) * cpp * dx[:npad], np.array(crho) * np.array(ccp) * dx[npad:]]
        if cell == "lumped":
            C[-1] = m_cell * cp_cell
        kall = np.r_[kp, np.array(ck, float)]
        # 면 컨덕턴스 G[i] between i,i+1
        R = 0.5 * dx[:-1] / kall[:-1] + 0.5 * dx[1:] / kall[1:]
        if cell == "lumped":
            R[-1] = 0.5 * dx[npad - 1] / kall[npad - 1]
        R[npad - 1] += 1 / h_c  # 패드–셀 접촉
        G = 1 / R
        G0 = kall[0] / (0.5 * dx[0])  # hot face Dirichlet
        ab = np.zeros((3, N))
        diag = C / dt
        diag[0] += G0
        diag[:-1] += G; diag[1:] += G
        ab[1] = diag; ab[0, 1:] = -G; ab[2, :-1] = -G
        rhs = C / dt * T
        rhs[0] += G0 * hot_face(t)
        T = solve_banded((1, 1), ab, rhs)
        if s % 20 == 19:
            cell_T = T[npad:]
            surf_hist.append((t, cell_T[0]))
            avg_hist.append(np.sum(cell_T * dx[npad:]) / np.sum(dx[npad:]) if cell != "lumped" else cell_T[0])
    sh, ah = np.array(surf_hist), np.array(avg_hist)
    return sh[:, 0], sh[:, 1], ah


def calibrate(target=122.2):
    lo, hi = 0.005, 0.2
    for _ in range(25):
        mid = 0.5 * (lo + hi)
        _, s, _ = simulate(mid, "lumped", dt=1.0)
        lo, hi = (mid, hi) if s.max() < target else (lo, mid)
    return 0.5 * (lo + hi)
