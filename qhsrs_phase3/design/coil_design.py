"""
SS-02 / SS-04 — Coil reverse design, AC winding loss, core loss, drive
impedance and reactive-power compensation.

CENTRAL RESULT OF THIS MODULE
-----------------------------
The reactive volt-amperes demanded of the driver are

        Q = omega * L * I_rms^2 = omega * Phi_rms * F_rms = 2*omega*U_field

which is INDEPENDENT of the turns count N.  N trades voltage against current
but cannot reduce Q.  Q is fixed by (target B) x (gap volume) x (frequency).
This is the wall that governs the whole 3-3,000 Hz specification and it is
why a swept-frequency compensation network -- not a bigger amplifier -- is
the correct answer.
"""
import math
from dataclasses import dataclass
from typing import List, Optional

from constants import (MU0, PI, RHO_CU_20C, ALPHA_CU, RHO_M_CU,
                       CoreMaterial)


# ============================================================================
# WIRE TABLE
# ============================================================================
@dataclass
class Wire:
    label: str
    d_cu: float            # m, bare copper diameter (single strand)
    strands: int = 1       # >1 => litz
    insulation_t: float = 0.06e-3   # m, grade-2 enamel build (radial)

    @property
    def a_strand(self) -> float:
        return PI * (self.d_cu / 2) ** 2

    @property
    def a_cu(self) -> float:
        return self.strands * self.a_strand

    @property
    def d_outer(self) -> float:
        if self.strands == 1:
            return self.d_cu + 2 * self.insulation_t
        # bundle: packing factor ~0.75 for served litz
        return math.sqrt(self.strands / 0.75) * (self.d_cu + 2 * self.insulation_t) * 1.10


WIRES = [
    Wire("AWG 10 solid (2.588 mm)", 2.588e-3),
    Wire("AWG 8 solid (3.264 mm)", 3.264e-3),
    Wire("AWG 6 solid (4.115 mm)", 4.115e-3),
    Wire("Litz 400x0.20 mm", 0.20e-3, strands=400),
    Wire("Litz 1000x0.20 mm", 0.20e-3, strands=1000),
    Wire("Litz 2000x0.20 mm", 0.20e-3, strands=2000),
    Wire("Litz 1600x0.10 mm", 0.10e-3, strands=1600),
]


def rho_cu(temp_c: float) -> float:
    return RHO_CU_20C.value * (1 + ALPHA_CU.value * (temp_c - 20.0))


def skin_depth_cu(f: float, temp_c: float = 20.0) -> float:
    if f <= 0:
        return float("inf")
    return math.sqrt(rho_cu(temp_c) / (PI * f * MU0))


# ============================================================================
# AC RESISTANCE  (Dowell, porosity-corrected, litz-aware)
# ============================================================================
def dowell_FR(f: float, wire: Wire, n_layers: int, turns_per_layer: int,
              window_w: float, temp_c: float = 20.0) -> float:
    """
    Ratio R_ac/R_dc for a layered winding.
    Round conductors are mapped to equivalent foil via the porosity factor
    eta = (turns_per_layer * d) / window_width, h_eff = d*sqrt(pi/4)*sqrt(eta).
    For litz the calculation is run on the STRAND and the effective layer
    count is the strand-level layer count (conservative bundle treatment).
    """
    if f <= 0:
        return 1.0
    d = wire.d_cu
    delta = skin_depth_cu(f, temp_c)
    eta = min(1.0, max(1e-3, turns_per_layer * wire.d_outer / max(window_w, 1e-6)))
    h_eff = d * math.sqrt(PI / 4.0) * math.sqrt(eta)
    D = h_eff / delta
    if D < 1e-6:
        return 1.0
    m = n_layers if wire.strands == 1 else max(1.0, n_layers * math.sqrt(wire.strands))
    ch, sh = math.cosh(2 * D), math.sinh(2 * D)
    cc, ss = math.cos(2 * D), math.sin(2 * D)
    t1 = (sh + ss) / max(ch - cc, 1e-12)
    t2 = (2.0 / 3.0) * (m * m - 1.0) * (math.sinh(D) - math.sin(D)) / max(
        math.cosh(D) + math.cos(D), 1e-12)
    fr = D * (t1 + t2)
    return max(1.0, fr)


# ============================================================================
# COIL
# ============================================================================
@dataclass
class Coil:
    """One prong coil."""
    turns: int
    wire: Wire
    mean_turn_length: float     # m
    window_w: float             # m, axial winding length available
    window_h: float             # m, radial build available
    n_coils_series: int = 4     # coils electrically in series in one loop

    @property
    def turns_per_layer(self) -> int:
        return max(1, int(self.window_w / self.wire.d_outer))

    @property
    def n_layers(self) -> int:
        return math.ceil(self.turns / self.turns_per_layer)

    @property
    def radial_build(self) -> float:
        return self.n_layers * self.wire.d_outer

    @property
    def fits(self) -> bool:
        return self.radial_build <= self.window_h

    @property
    def fill_factor(self) -> float:
        return (self.turns * self.wire.a_cu) / max(self.window_w * self.window_h, 1e-12)

    @property
    def cu_mass(self) -> float:
        return self.turns * self.mean_turn_length * self.wire.a_cu * RHO_M_CU.value

    def r_dc(self, temp_c: float = 20.0) -> float:
        return rho_cu(temp_c) * self.turns * self.mean_turn_length / self.wire.a_cu

    def r_ac(self, f: float, temp_c: float = 20.0) -> float:
        fr = dowell_FR(f, self.wire, self.n_layers, self.turns_per_layer,
                       self.window_w, temp_c)
        return self.r_dc(temp_c) * fr

    def current_density(self, i_rms: float) -> float:
        """A/mm^2"""
        return i_rms / (self.wire.a_cu * 1e6)


# ============================================================================
# CORE LOSS
# ============================================================================
def core_loss(mat: CoreMaterial, f: float, b_peak: float, volume_m3: float) -> float:
    """Steinmetz hysteresis+excess term plus the classical eddy term [W]."""
    if mat.k_steinmetz == 0.0 or f <= 0:
        p_st = 0.0
    else:
        p_st = mat.k_steinmetz * (f ** mat.alpha) * (b_peak ** mat.beta)
    # classical eddy in a lamination of thickness d:
    #   Pv = (pi^2 * d^2 * f^2 * Bpk^2 * sigma) / 6   [W/m3]
    if mat.sigma > 1e3 and mat.lam_t < 0.01:
        p_ed = (PI ** 2) * (mat.lam_t ** 2) * (f ** 2) * (b_peak ** 2) * mat.sigma / 6.0
    else:
        p_ed = 0.0
    return (p_st + p_ed) * volume_m3 * mat.stacking


# ============================================================================
# DRIVE POINT
# ============================================================================
@dataclass
class DrivePoint:
    f: float
    b_ecv: float           # T, rms field in the ECV
    b_pole: float          # T
    mmf_rms: float         # A-turns per loop
    flux_rms: float        # Wb
    n_loop: int
    L: float
    i_rms: float
    r_ac: float
    p_cu: float
    p_core: float
    v_r: float
    v_x: float
    v_uncomp: float
    q_var: float
    va_uncomp: float
    v_comp: float          # driver voltage with tuned series compensation
    va_comp: float
    c_series: Optional[float]
    j_cu: float
    fr: float


def drive_point(f, b_ecv, b_pole, mmf_rms, flux_rms, coil: Coil, mat: CoreMaterial,
                reluctance_loop: float, core_volume: float, temp_c: float = 60.0,
                compensate_above: float = 100.0) -> DrivePoint:
    n_loop = coil.turns * coil.n_coils_series
    L = n_loop ** 2 / reluctance_loop
    i_rms = mmf_rms / n_loop
    r_total = coil.r_ac(f, temp_c) * coil.n_coils_series
    fr = coil.r_ac(f, temp_c) / coil.r_dc(temp_c)
    w = 2 * PI * f
    x = w * L
    p_cu = i_rms ** 2 * r_total
    p_core = core_loss(mat, f, b_pole * math.sqrt(2), core_volume)
    v_r = i_rms * r_total
    v_x = i_rms * x
    v_unc = i_rms * math.sqrt(r_total ** 2 + x ** 2)
    q = i_rms ** 2 * x
    # Tuned series compensation: C cancels X at this f.  Only physically
    # sensible above ~100 Hz (below that C becomes farad-scale).
    if f >= compensate_above and x > 0:
        c_ser = 1.0 / (w * w * L)
        v_comp = v_r
    else:
        c_ser = None
        v_comp = v_unc
    return DrivePoint(f=f, b_ecv=b_ecv, b_pole=b_pole, mmf_rms=mmf_rms,
                      flux_rms=flux_rms, n_loop=n_loop, L=L, i_rms=i_rms,
                      r_ac=r_total, p_cu=p_cu, p_core=p_core, v_r=v_r, v_x=v_x,
                      v_uncomp=v_unc, q_var=q, va_uncomp=i_rms * v_unc,
                      v_comp=v_comp, va_comp=i_rms * v_comp, c_series=c_ser,
                      j_cu=coil.current_density(i_rms), fr=fr)
