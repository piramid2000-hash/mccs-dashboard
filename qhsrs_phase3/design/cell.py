"""
The frozen Phase-3 exposure cell (one module of the R3 array) and its
complete electrical / thermal / hydraulic model.

ARCHITECTURE (see report S.21, S.36)
------------------------------------
One CELL = one independent opposed C-core.  Two pole faces look at each other
across a non-metallic (PVDF/PP) flow duct.  The core and both coils are DRY
and outside the wetted boundary; only the duct touches water.  This removes
the entire immersed-fork failure family (S.19) at the cost of ~6 mm of
additional magnetic gap taken by the duct walls.

Three identical cells are stacked along the flow path.  Each has its own
driver channel, so the array is modular, individually calibratable and
degrades gracefully.
"""
import math
from dataclasses import dataclass, field

from constants import (MU0, PI, CP_WATER, RHO_M_WATER, K_WATER, NU_WATER_20C,
                       CoreMaterial, NANOCRYSTALLINE, M350_50A)
from magnetics import ForkGeometry, Bmag
from architectures import BUILDERS
from optimize_geom import cell_stats
import coil_design as CD


# ============================================================================
# FROZEN GEOMETRY
# ============================================================================
POLE_W = 0.240      # m, along flow (x)
POLE_H = 0.240      # m, across flow (y)
DUCT_WALL = 0.003   # m, PVDF duct wall each side
WATER_GAP = 0.024   # m, clear water channel
MAG_GAP = WATER_GAP + 2 * DUCT_WALL     # 0.030 m total magnetic gap
LEG_LEN = 0.200     # m, pole leg length (coil window length)
WINDOW_H = 0.050    # m, radial build available for the winding
N_CELLS = 3

# ECV inset fractions taken from the Pareto optimisation (optimize_geom.py)
FX, FY, FZI = 0.85, 0.75, 0.10


def frozen_fork() -> ForkGeometry:
    return ForkGeometry(n_prong=1, prong_w=POLE_W, prong_h=POLE_H,
                        prong_len=LEG_LEN, prong_pitch=0.375,
                        yoke_w=POLE_W, yoke_h=POLE_H, gap=MAG_GAP,
                        name="Phase-3 frozen exposure cell (R3 module)")


def cell_field_stats(b_pole: float = 1.0):
    """Uniformity and field gain of the frozen cell (per unit pole B)."""
    fk = frozen_fork()
    return cell_stats(fk, "R3", b_pole, FX, FY, FZI, nx=13, ny=13, nz=9)


def ecv_geometry():
    fk = frozen_fork()
    xh = POLE_W * FX / 2
    yh = POLE_H * FY / 2
    z0 = MAG_GAP * FZI
    z1 = MAG_GAP * (1 - FZI)
    # clip the ECV to the WATER channel (the duct walls are not water)
    z0 = max(z0, DUCT_WALL)
    z1 = min(z1, MAG_GAP - DUCT_WALL)
    return dict(x_half=xh, y_half=yh, z_lo=z0, z_hi=z1,
                vol_L=(2 * xh) * (2 * yh) * (z1 - z0) * 1000.0)


# ============================================================================
# MAGNETIC CIRCUIT OF ONE CELL
# ============================================================================
def core_volume_cell() -> float:
    """C-core: 2 legs + 1 back-yoke + 2 pole shoes, cross-section POLE_W*POLE_H."""
    a = POLE_W * POLE_H
    leg = 2 * LEG_LEN * a
    yoke = (MAG_GAP + 2 * LEG_LEN) * a * 0.6   # back path, tapered allowance
    return leg + yoke


def core_path_length_cell() -> float:
    return 2 * LEG_LEN + (MAG_GAP + 2 * LEG_LEN) * 0.6


def cell_mmf(b_pole: float, mu_r_core: float):
    """
    Ampere-turns for ONE cell loop = gap drop (line integral, rigorous)
    + core drop (reluctance).  Returns (F_total, F_gap, F_core).
    """
    fk = frozen_fork()
    sheets = BUILDERS["R3"](fk, b_pole)
    # line integral of Hz across the gap on the axis
    n = 600
    z0, z1 = 1e-4, MAG_GAP - 1e-4
    acc = 0.0
    from magnetics import B_at
    for i in range(n + 1):
        z = z0 + (z1 - z0) * i / n
        w = 0.5 if i in (0, n) else 1.0
        acc += w * abs(B_at((0.0, 0.0, z), sheets)[2])
    f_gap = acc * (z1 - z0) / n / MU0
    f_core = b_pole * core_path_length_cell() / (MU0 * mu_r_core)
    return f_gap + f_core, f_gap, f_core


def stored_energy(b_pole: float, mmf: float) -> float:
    """U = 0.5 * Phi * F  [J] for one cell."""
    return 0.5 * (b_pole * POLE_W * POLE_H) * mmf


# ============================================================================
# HYDRAULICS AND DOSE
# ============================================================================
@dataclass
class Hydraulics:
    velocity: float = 0.50        # m/s in the duct
    tank_volume_L: float = 1000.0

    @property
    def duct_area(self) -> float:
        return POLE_H * WATER_GAP          # y * z  [m2]

    @property
    def flow_m3s(self) -> float:
        return self.velocity * self.duct_area

    @property
    def flow_m3h(self) -> float:
        return self.flow_m3s * 3600.0

    @property
    def hydraulic_diameter(self) -> float:
        a, b = POLE_H, WATER_GAP
        return 2 * a * b / (a + b)

    @property
    def reynolds(self) -> float:
        return self.velocity * self.hydraulic_diameter / NU_WATER_20C.value

    @property
    def regime(self) -> str:
        re = self.reynolds
        return "laminar" if re < 2300 else ("transitional" if re < 4000 else "turbulent")

    def residence_per_pass(self, n_cells=N_CELLS) -> float:
        return n_cells * POLE_W * FX / self.velocity

    def turnover_time(self) -> float:
        return (self.tank_volume_L / 1000.0) / self.flow_m3s

    def cumulative_exposure(self, run_time_s: float, n_cells=N_CELLS) -> float:
        """
        For a well-mixed recirculating batch the MEAN cumulative time each
        water parcel spends inside the ECV is

            t_exp = t_run * V_ECV / V_tank

        -- independent of flow rate.  Raising the pump does NOT raise the dose.
        This is the single most important process result in Section 16.
        """
        v_ecv = ecv_geometry()["vol_L"] * n_cells
        return run_time_s * v_ecv / self.tank_volume_L


def dose(b_rms: float, t_exp: float):
    """Two dose metrics, both reported; neither assumes a mechanism."""
    return dict(D_B_mTs=b_rms * 1e3 * t_exp, D_E_mT2s=(b_rms * 1e3) ** 2 * t_exp)
