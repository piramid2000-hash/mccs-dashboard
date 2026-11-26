"""복셀(정육면체 8절점 요소) 유한요소 — 다공 구조의 유효 탄성계수·열전도도.

모든 요소가 같은 정육면체이므로 요소 행렬을 한 번만 적분하고 전역 조립은 인덱스로 한다
(위상최적화 top3d 방식). 풀이는 pyamg 대수 다중격자, 실패 시 직접법.

경계조건(균질화가 아닌 '시편 시험' 방식)
  탄성: 아랫면 uz=0, 윗면 uz=δ, 옆면 자유, 강체운동은 아랫면 두 절점으로만 고정 → 꽉 찬 블록이면 정확히 E.
  열  : 아랫면 T=0, 윗면 T=1, 옆면 단열 → 꽉 찬 블록이면 정확히 k.
결과는 꽉 찬 재료 대비 비율(E_rel, k_rel).
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp
from scipy import ndimage

_GP = np.array([-1, 1]) / np.sqrt(3.0)
# 8 절점 국소 좌표(ξ,η,ζ ∈ {-1,1}) — 순서: x 가 가장 빨리 변함
_NODES = np.array([[i, j, k] for k in (-1, 1) for j in (-1, 1) for i in (-1, 1)], float)
_OFF = ((_NODES + 1) / 2).astype(int)          # 격자 오프셋 (di, dj, dk)


def _dN(xi, eta, zeta):
    """국소 좌표 미분 (8×3)."""
    n = _NODES
    return np.stack([
        n[:, 0] * (1 + eta * n[:, 1]) * (1 + zeta * n[:, 2]),
        n[:, 1] * (1 + xi * n[:, 0]) * (1 + zeta * n[:, 2]),
        n[:, 2] * (1 + xi * n[:, 0]) * (1 + eta * n[:, 1]),
    ], axis=1) / 8.0


def element_matrices(nu=0.25, h=1.0):
    """E=1, k=1, 한 변 h 정육면체의 탄성 Ke(24×24, dof=3·node+comp)와 열전도 Ce(8×8)."""
    lam = nu / ((1 + nu) * (1 - 2 * nu))
    mu = 1 / (2 * (1 + nu))
    D = np.zeros((6, 6))
    D[:3, :3] = lam
    D[np.arange(3), np.arange(3)] += 2 * mu
    D[3:, 3:] = np.eye(3) * mu
    Ke = np.zeros((24, 24)); Ce = np.zeros((8, 8))
    J = h / 2.0
    detJ = J ** 3
    for xi in _GP:
        for eta in _GP:
            for zeta in _GP:
                G = _dN(xi, eta, zeta) / J            # 실좌표 미분 (8×3)
                B = np.zeros((6, 24))
                for a in range(8):
                    gx, gy, gz = G[a]
                    c = 3 * a
                    B[0, c] = gx; B[1, c + 1] = gy; B[2, c + 2] = gz
                    B[3, c] = gy; B[3, c + 1] = gx
                    B[4, c + 1] = gz; B[4, c + 2] = gy
                    B[5, c] = gz; B[5, c + 2] = gx
                Ke += B.T @ D @ B * detJ
                Ce += G @ G.T * detJ
    return Ke, Ce


def largest_component(solid):
    """면 연결 기준 가장 큰 덩어리만 남긴다(떠 있는 조각은 출력도, 하중 전달도 안 됨)."""
    lab, n = ndimage.label(solid)
    if n == 0:
        return solid, 0.0
    sizes = ndimage.sum(solid, lab, range(1, n + 1))
    keep = lab == (1 + int(np.argmax(sizes)))
    return keep, float(keep.sum() / max(solid.sum(), 1))


def _assemble(solid, Ke_or_Ce, ndof_per_node):
    nx, ny, nz = solid.shape
    ex, ey, ez = np.nonzero(solid)
    node_id = lambda i, j, k: i + (nx + 1) * (j + (ny + 1) * k)  # noqa: E731
    conn = np.stack([node_id(ex + o[0], ey + o[1], ez + o[2]) for o in _OFF], axis=1)  # (ne, 8)
    used, inv = np.unique(conn, return_inverse=True)
    conn = inv.reshape(conn.shape)
    if ndof_per_node == 3:
        edof = (3 * conn[:, :, None] + np.arange(3)).reshape(len(conn), 24)
    else:
        edof = conn
    m = edof.shape[1]
    rows = np.repeat(edof, m, axis=1).ravel()
    cols = np.tile(edof, (1, m)).ravel()
    vals = np.tile(Ke_or_Ce.ravel(), len(edof))
    n = ndof_per_node * len(used)
    K = sp.csr_matrix((vals, (rows, cols)), shape=(n, n))
    k_idx = used // ((nx + 1) * (ny + 1))
    return K, used, k_idx, nx


def _solve(K, free, fixed, ufix):
    Kff = K[free][:, free].tocsr()
    rhs = -K[free][:, fixed] @ ufix
    try:
        import pyamg
        ml = pyamg.smoothed_aggregation_solver(Kff, max_coarse=500)
        x = ml.solve(rhs, tol=1e-10, maxiter=300, accel="cg")
        if np.linalg.norm(Kff @ x - rhs) > 1e-6 * max(np.linalg.norm(rhs), 1e-30):
            raise RuntimeError
        return x
    except Exception:  # noqa: BLE001 — AMG 실패 시 직접법
        return sp.linalg.spsolve(Kff.tocsc(), rhs)


def effective_modulus(solid, nu=0.25):
    """z 방향 압축 유효 탄성계수 E_rel (꽉 찬 재료 = 1)."""
    solid, frac = largest_component(solid)
    if solid.sum() == 0:
        return 0.0, frac
    nz = solid.shape[2]
    Ke, _ = element_matrices(nu)
    K, used, k_idx, _ = _assemble(solid, Ke, 3)
    nn = len(used)
    bot = np.where(k_idx == 0)[0]; top = np.where(k_idx == nz)[0]
    if len(top) == 0 or len(bot) == 0:
        return 0.0, frac                                    # 위아래를 잇지 못함
    delta = 1e-3 * nz
    fixed = list(3 * bot + 2) + list(3 * top + 2)
    vals = [0.0] * len(bot) + [delta] * len(top)
    fixed += [3 * bot[0], 3 * bot[0] + 1, 3 * bot[-1] + 1]   # 강체 병진·회전 제거
    vals += [0.0, 0.0, 0.0]
    fixed = np.array(fixed); vals = np.array(vals)
    order = np.argsort(fixed); fixed, vals = fixed[order], vals[order]
    fixed, uidx = np.unique(fixed, return_index=True); vals = vals[uidx]
    free = np.setdiff1d(np.arange(3 * nn), fixed)
    u = np.zeros(3 * nn); u[fixed] = vals
    u[free] = _solve(K, free, fixed, vals)
    F = K @ u
    force = F[3 * top + 2].sum()
    area = solid.shape[0] * solid.shape[1]
    return float(force / area / (delta / nz)), frac


def effective_conductivity(solid):
    """z 방향 유효 열전도도 k_rel (꽉 찬 재료 = 1)."""
    solid, frac = largest_component(solid)
    if solid.sum() == 0:
        return 0.0, frac
    nz = solid.shape[2]
    _, Ce = element_matrices()
    K, used, k_idx, _ = _assemble(solid, Ce, 1)
    bot = np.where(k_idx == 0)[0]; top = np.where(k_idx == nz)[0]
    if len(top) == 0 or len(bot) == 0:
        return 0.0, frac
    fixed = np.concatenate([bot, top]); vals = np.concatenate([np.zeros(len(bot)), np.ones(len(top))])
    free = np.setdiff1d(np.arange(len(used)), fixed)
    T = np.zeros(len(used)); T[fixed] = vals
    T[free] = _solve(K, free, fixed, vals)
    q = (K @ T)[top].sum()
    area = solid.shape[0] * solid.shape[1]
    return float(q / area * nz), frac
