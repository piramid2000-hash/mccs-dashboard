"""
Section 26 — Multi-objective geometry optimisation of the exposure cell.

OBJECTIVE: maximise the Exposure Control Volume (litres of water actually
inside spec) SUBJECT TO CV_B <= 10 %, while minimising the stored magnetic
energy per litre (which is what sets amplifier VA and therefore feasibility
at 3 kHz).

The decision variables are the pole-face aspect ratios and the ECV inset
fractions.  This is a coarse enumerated search; the Pareto set it produces
is the input to 3-D FEA refinement, not a substitute for it.
"""
import itertools
import math
from dataclasses import replace

from constants import MU0
from magnetics import ForkGeometry, Bmag
from architectures import BUILDERS


def cell_stats(fk, arch, b_pole, fx, fy, fz_inset, nx=11, ny=11, nz=7):
    """Uniformity over ONE cell's ECV, parameterised by inset fractions."""
    sheets = BUILDERS[arch](fk, b_pole)
    xc = 0.0
    xh = fk.prong_w * fx / 2
    yh = fk.prong_h * fy / 2
    z0 = fk.gap * fz_inset
    z1 = fk.gap * (1 - fz_inset)
    vals = []
    for ix in range(nx):
        x = xc + xh * (-1 + 2 * ix / (nx - 1))
        for iy in range(ny):
            y = yh * (-1 + 2 * iy / (ny - 1))
            for iz in range(nz):
                z = z0 + (z1 - z0) * iz / (nz - 1)
                vals.append(Bmag((x, y, z), sheets))
    m = sum(vals) / len(vals)
    sd = math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals))
    vol_L = (2 * xh) * (2 * yh) * (z1 - z0) * 1000.0
    return dict(mean=m, cv=sd / m, mn=min(vals), mx=max(vals),
                vol_L=vol_L, xh=xh, yh=yh, z0=z0, z1=z1)


def energy_per_litre(fk, arch, b_target, st):
    """
    Stored energy per litre of ECV at the target ECV field [J/L].
    U = (B^2 / 2 mu0) * V_gap  scaled by the gap/ECV volume ratio.
    """
    b_pole = b_target / st["mean"]          # linear model
    v_gap = fk.prong_w * fk.prong_h * fk.gap * fk.n_prong
    # energy density uses the actual mean field in the gap volume,
    # conservatively taken as the pole-face value
    u = (b_pole ** 2 / (2 * MU0)) * v_gap
    return u / max(st["vol_L"] * fk.n_prong, 1e-9), b_pole, u


def sweep(arch="R3", b_target=50e-3, cv_limit=0.10):
    results = []
    for w in (0.10, 0.12, 0.15, 0.20, 0.25):
        for h in (0.20, 0.25, 0.30, 0.40):
            for g in (0.030, 0.040, 0.050, 0.060, 0.080):
                if g > 0.6 * w:
                    continue           # keep the cell plate-like
                pitch = w + max(0.06, 0.5 * w)
                fk = ForkGeometry(prong_w=w, prong_h=h, gap=g, prong_pitch=pitch,
                                  prong_len=0.25, yoke_w=w, yoke_h=h)
                for fx in (0.55, 0.65, 0.75, 0.85):
                    for fy in (0.45, 0.55, 0.65, 0.75):
                        for fzi in (0.10, 0.15, 0.20):
                            st = cell_stats(fk, arch, 1.0, fx, fy, fzi, 9, 9, 5)
                            if st["cv"] > cv_limit:
                                continue
                            epl, b_pole, u = energy_per_litre(fk, arch, b_target, st)
                            results.append(dict(
                                w=w, h=h, g=g, pitch=pitch, fx=fx, fy=fy, fzi=fzi,
                                cv=st["cv"], ecv_L_cell=st["vol_L"],
                                ecv_L_total=st["vol_L"] * fk.n_prong,
                                gain=st["mean"], b_pole_req=b_pole,
                                U_J=u, J_per_L=epl))
    return results


if __name__ == "__main__":
    for arch in ("R2", "R3"):
        res = sweep(arch)
        print(f"\n===== {arch}:  {len(res)} feasible points with CV_B <= 10% =====")
        if not res:
            print("  NONE — CV_B<=10% infeasible in this search space")
            continue
        # Pareto: maximise ECV litres, minimise J per litre
        pareto = []
        for r in res:
            dominated = any((o["ecv_L_total"] >= r["ecv_L_total"] and
                             o["J_per_L"] <= r["J_per_L"] and o is not r and
                             (o["ecv_L_total"] > r["ecv_L_total"] or
                              o["J_per_L"] < r["J_per_L"])) for o in res)
            if not dominated:
                pareto.append(r)
        pareto.sort(key=lambda r: -r["ecv_L_total"])
        print(f"  Pareto front: {len(pareto)} points")
        print("  %6s %6s %6s %6s %6s %6s %6s %8s %9s %9s %9s" % (
            "w[mm]", "h[mm]", "g[mm]", "fx", "fy", "fzi", "CV_B",
            "ECV[L]", "gain", "Bpole[T]", "J/L"))
        for r in pareto[:14]:
            print("  %6.0f %6.0f %6.0f %6.2f %6.2f %6.2f %6.3f %8.2f %9.3f %9.4f %9.1f" % (
                r["w"] * 1e3, r["h"] * 1e3, r["g"] * 1e3, r["fx"], r["fy"],
                r["fzi"], r["cv"], r["ecv_L_total"], r["gain"],
                r["b_pole_req"], r["J_per_L"]))
