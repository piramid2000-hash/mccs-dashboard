"""
Section 25 — R1 / R2 / R3 architecture definition and head-to-head evaluation
on a common basis (same water, same target B in the ECV, same frequency).

R1  Single 3-Prong Fork          — poles on ONE side only; flux returns
                                   through the water between adjacent prongs.
R2  Opposed Dual 3-Prong Fork    — two forks facing across a working gap,
                                   ONE shared yoke per fork.  Prong polarity
                                   must alternate (N,S,N) to close the
                                   circuit, which forces |B| nulls between
                                   prong pairs.
R3  Distributed Multi-Cell Array — each prong pair carries its OWN return
                                   yoke, so all cells may share polarity and
                                   the inter-cell nulls disappear.

The same charge-sheet field engine evaluates all three, so the uniformity
comparison is like-for-like.
"""
import math
from dataclasses import dataclass, replace
from typing import List

from constants import MU0, PI
from magnetics import (ForkGeometry, ECV, _rect_sheet_B, Bmag, B_at,
                       fringing_area, reluctances)


# ============================================================================
# GENERIC SHEET BUILDERS
# ============================================================================
def sheets_R1(fk: ForkGeometry, b_pole: float):
    """Poles at z=0 only, alternating polarity along x."""
    out = []
    for i, xc in enumerate(fk.pole_centres()):
        sgn = 1.0 if i % 2 == 0 else -1.0
        out.append((sgn * b_pole, xc - fk.prong_w / 2, xc + fk.prong_w / 2,
                    -fk.prong_h / 2, fk.prong_h / 2, 0.0))
    return out


def sheets_R2(fk: ForkGeometry, b_pole: float):
    """Opposed pair, shared yoke => alternating polarity along x (forced)."""
    out = []
    for i, xc in enumerate(fk.pole_centres()):
        sgn = 1.0 if i % 2 == 0 else -1.0
        x1, x2 = xc - fk.prong_w / 2, xc + fk.prong_w / 2
        y1, y2 = -fk.prong_h / 2, fk.prong_h / 2
        out.append((sgn * b_pole, x1, x2, y1, y2, 0.0))
        out.append((-sgn * b_pole, x1, x2, y1, y2, fk.gap))
    return out


def sheets_R3(fk: ForkGeometry, b_pole: float):
    """Independent C-cells => every cell may carry the SAME polarity."""
    out = []
    for xc in fk.pole_centres():
        x1, x2 = xc - fk.prong_w / 2, xc + fk.prong_w / 2
        y1, y2 = -fk.prong_h / 2, fk.prong_h / 2
        out.append((+b_pole, x1, x2, y1, y2, 0.0))
        out.append((-b_pole, x1, x2, y1, y2, fk.gap))
    return out


BUILDERS = {"R1": sheets_R1, "R2": sheets_R2, "R3": sheets_R3}


# ============================================================================
# STATISTICS OVER AN ECV
# ============================================================================
def stats_over(sheets, ecv: ECV, n=(11, 11, 7)):
    vals = []
    nx, ny, nz = n
    for ix in range(nx):
        x = ecv.x_half * (-1 + 2 * ix / (nx - 1)) if nx > 1 else 0.0
        for iy in range(ny):
            y = ecv.y_half * (-1 + 2 * iy / (ny - 1)) if ny > 1 else 0.0
            for iz in range(nz):
                z = ecv.z_lo + (ecv.z_hi - ecv.z_lo) * iz / (nz - 1) if nz > 1 else ecv.z_lo
                vals.append(Bmag((x, y, z), sheets))
    m = sum(vals) / len(vals)
    sd = math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals))
    return dict(mean=m, std=sd, mn=min(vals), mx=max(vals),
                cv=sd / m if m > 0 else float("inf"), n=len(vals))


# ECV inset fractions frozen by the Pareto optimisation (optimize_geom.py).
# The SAME fractions are used for R1/R2/R3 so the comparison is like-for-like.
FX, FY, FZI = 0.85, 0.75, 0.10


def channel_ecv(fk: ForkGeometry, xc: float, inset_frac=FZI, y_frac=FY):
    """
    ECV of ONE exposure channel: the water column facing one prong pair,
    inset from the pole faces (where the sheet model is singular) and from
    the prong top/bottom edges.
    """
    inset = fk.gap * inset_frac
    return ECV(x_half=fk.prong_w * FX / 2, y_half=fk.prong_h * y_frac / 2,
               z_lo=inset, z_hi=fk.gap - inset,
               label=f"channel@x={xc:+.3f}")


def stats_channels(arch: str, fk: ForkGeometry, b_pole: float):
    """Uniformity within each channel and across the union of channels."""
    sheets = BUILDERS[arch](fk, b_pole)
    per = []
    allvals = []
    for xc in fk.pole_centres():
        e = channel_ecv(fk, xc)
        vals = []
        for ix in range(11):
            x = xc + e.x_half * (-1 + 2 * ix / 10)
            for iy in range(11):
                y = e.y_half * (-1 + 2 * iy / 10)
                for iz in range(7):
                    z = e.z_lo + (e.z_hi - e.z_lo) * iz / 6
                    vals.append(Bmag((x, y, z), sheets))
        m = sum(vals) / len(vals)
        sd = math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals))
        per.append(dict(xc=xc, mean=m, std=sd, mn=min(vals), mx=max(vals),
                        cv=sd / m, n=len(vals)))
        allvals += vals
    M = sum(allvals) / len(allvals)
    SD = math.sqrt(sum((v - M) ** 2 for v in allvals) / len(allvals))
    union = dict(mean=M, std=SD, mn=min(allvals), mx=max(allvals),
                 cv=SD / M, n=len(allvals))
    return per, union


def ecv_volume_L(fk: ForkGeometry, n_channels: int = None):
    n_channels = fk.n_prong if n_channels is None else n_channels
    e = channel_ecv(fk, 0.0)
    return n_channels * (2 * e.x_half) * (2 * e.y_half) * (e.z_hi - e.z_lo) * 1000.0


# ============================================================================
# RIGOROUS MMF: LINE INTEGRAL OF H THROUGH THE GAP
# ============================================================================
def gap_mmf_line_integral(arch: str, fk: ForkGeometry, b_pole: float,
                          x_off=0.0, y_off=0.0, n=400):
    """
    Magnetic potential drop across ONE gap [A-turns], evaluated as
    (1/mu0) * integral(Bz dz) along a straight path from pole A to pole B.
    For R1 the 'gap' is the water return path between adjacent prongs, which
    is handled separately.
    """
    sheets = BUILDERS[arch](fk, b_pole)
    xc = fk.pole_centres()[len(fk.pole_centres()) // 2]
    z0, z1 = 1e-4, fk.gap - 1e-4
    acc = 0.0
    for i in range(n + 1):
        z = z0 + (z1 - z0) * i / n
        w = 0.5 if i in (0, n) else 1.0
        acc += w * abs(B_at((xc + x_off, y_off, z), sheets)[2])
    acc *= (z1 - z0) / n
    return acc / MU0


def mmf_path_spread(arch: str, fk: ForkGeometry, b_pole: float):
    """
    Model self-consistency check: with ideal (infinite-mu) poles the potential
    drop must be identical on every path.  The spread across paths is a direct
    measure of charge-sheet model error and is reported as such.
    """
    paths = [(0.0, 0.0), (fk.prong_w * 0.35, 0.0), (0.0, fk.prong_h * 0.35),
             (fk.prong_w * 0.35, fk.prong_h * 0.35)]
    vals = [gap_mmf_line_integral(arch, fk, b_pole, dx, dy) for dx, dy in paths]
    m = sum(vals) / len(vals)
    return m, (max(vals) - min(vals)) / m, vals


def loop_mmf(arch: str, fk: ForkGeometry, b_pole: float, mu_r_core: float):
    """
    Total ampere-turns linking one flux loop.
    R2: two gaps in series in the loop.
    R3: two gaps in series (out and back through the same cell's own yoke)
        -> also two gap crossings? No: an independent C-cell has ONE gap in
        its loop.  This is a decisive efficiency difference and is modelled.
    R1: the return path is entirely in water; the effective gap is taken as
        the prong pitch, which is why R1 is so expensive.
    """
    _, r_core, _ = reluctances(fk, mu_r_core)
    flux = b_pole * fk.pole_area
    core_drop = flux * r_core
    if arch == "R2":
        f_gap, _, _ = mmf_path_spread(arch, fk, b_pole)
        return 2 * f_gap + core_drop, 2 * f_gap, core_drop
    if arch == "R3":
        f_gap, _, _ = mmf_path_spread(arch, fk, b_pole)
        return 1 * f_gap + core_drop, f_gap, core_drop
    # R1: water return path of length ~pitch, area ~ pole area (generous)
    f_gap = b_pole * fk.gap / MU0            # forward leg through the water
    f_ret = b_pole * fk.prong_pitch / MU0 * 0.5   # diffuse return leg
    return f_gap + f_ret + core_drop, f_gap + f_ret, core_drop


def field_energy(arch: str, fk: ForkGeometry, b_pole: float, mmf: float):
    """Stored magnetic energy U = 0.5*Phi*F [J] -- sets the reactive VA."""
    flux = b_pole * fk.pole_area
    n_loops = {"R1": fk.n_prong, "R2": fk.n_prong - 1, "R3": fk.n_prong}[arch]
    return 0.5 * flux * mmf * n_loops, n_loops
