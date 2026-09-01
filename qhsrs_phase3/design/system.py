"""
Complete electro-magneto-thermal model of ONE Phase-3 exposure cell,
plus the driver and compensation network.

Everything downstream of `solve_cell()` is derived, never asserted.
"""
import math
from dataclasses import dataclass, field
from typing import Optional, List

from constants import (MU0, PI, CP_WATER, RHO_M_WATER, CoreMaterial,
                       M350_50A, NO10_THIN, NANOCRYSTALLINE, FERRITE_N87,
                       SIGMA_ELECTROLYTE_MAX, SIGMA_WATER_TAP)
from coil_design import Wire, WIRES, Coil, core_loss, rho_cu, skin_depth_cu
import cell as CELL


# ============================================================================
# CORE GEOMETRY WITH POLE SHOES
# ============================================================================
@dataclass
class CoreGeom:
    pole_w: float = CELL.POLE_W       # 0.240 m
    pole_h: float = CELL.POLE_H       # 0.240 m
    shoe_t: float = 0.030             # m, pole-shoe thickness
    leg_a: float = 0.120              # m, square leg side
    leg_len: float = 0.150            # m, coil window length
    gap: float = CELL.MAG_GAP         # 0.030 m

    @property
    def pole_area(self): return self.pole_w * self.pole_h

    @property
    def leg_area(self): return self.leg_a ** 2

    @property
    def yoke_len(self): return self.gap + 2 * self.shoe_t + 2 * self.leg_len

    @property
    def vol_shoe(self): return 2 * self.pole_area * self.shoe_t

    @property
    def vol_leg(self): return 2 * self.leg_area * self.leg_len

    @property
    def vol_yoke(self): return self.leg_area * self.yoke_len

    @property
    def volume(self): return self.vol_shoe + self.vol_leg + self.vol_yoke

    @property
    def path_len(self):
        return 2 * self.shoe_t + 2 * self.leg_len + self.yoke_len

    def mass(self, mat: CoreMaterial):
        return self.volume * mat.rho_mass * mat.stacking

    def mean_turn_length(self):
        """Mean length of turn around a square leg with the winding build."""
        build = 0.5 * CELL.WINDOW_H
        return 4 * (self.leg_a + 2 * build)


# ============================================================================
# CELL SOLUTION AT ONE OPERATING POINT
# ============================================================================
@dataclass
class CellSolution:
    f: float
    b_ecv: float
    b_pole: float
    b_leg: float
    cv_b: float
    mmf: float
    flux: float
    reluctance: float
    N_loop: int
    L: float
    i_rms: float
    i_peak: float
    j_cu: float
    fr_ac: float
    r_ac: float
    p_cu: float
    p_core: float
    p_water: float
    e_water: float
    v_r: float
    v_x: float
    v_uncomp: float
    q_var: float
    c_series: Optional[float]
    v_cap: float
    v_drive: float
    va_drive: float
    efficiency: float
    wire: str
    turns_per_coil: int
    fits: bool
    fill: float
    limits: List[str] = field(default_factory=list)


@dataclass
class DriverLimits:
    """Phase-3 driver specification TARGETS (evidence level T)."""
    v_max: float = 600.0        # V rms per channel
    i_max: float = 200.0        # A rms per channel
    s_max: float = 60.0e3       # VA per channel
    p_max: float = 8.0e3        # W real per channel
    f_min: float = 0.1
    f_max: float = 10.0e3
    j_max: float = 4.0          # A/mm^2 continuous
    p_cell_thermal: float = 3.0e3   # W removable per cell by the cooling loop
    compensate_above: float = 80.0  # Hz
    v_cap_max: float = 2500.0   # V rms across the compensation capacitor
    q_max: float = 40.0         # max loaded Q of the compensated loop


def solve_cell(f: float, b_ecv: float, core: CoreGeom, mat: CoreMaterial,
               wire: Wire, turns_per_coil: int, gain: float, cv: float,
               temp_coil_c: float = 80.0, lim: DriverLimits = None,
               sigma_water: float = None) -> CellSolution:
    lim = lim or DriverLimits()
    sigma_water = SIGMA_ELECTROLYTE_MAX.value if sigma_water is None else sigma_water

    b_pole = b_ecv / gain
    flux = b_pole * core.pole_area
    b_leg = flux / core.leg_area

    # --- MMF: gap (rigorous line integral, scaled) + core (reluctance) ------
    f_gap_unit, _, _ = _gap_mmf_unit(core)
    f_gap = f_gap_unit * b_pole
    mu_r = mat.mu_r_init
    f_core = b_leg * core.path_len / (MU0 * mu_r) if mu_r > 1 else 0.0
    mmf = f_gap + f_core
    reluct = mmf / flux if flux > 0 else float("inf")

    # --- winding -----------------------------------------------------------
    N_loop = 2 * turns_per_coil          # two coils in series in the loop
    coil = Coil(turns=turns_per_coil, wire=wire,
                mean_turn_length=core.mean_turn_length(),
                window_w=core.leg_len, window_h=CELL.WINDOW_H, n_coils_series=2)
    i_rms = mmf / N_loop
    L = N_loop ** 2 / reluct if reluct > 0 else 0.0
    r_ac = coil.r_ac(f, temp_coil_c) * 2
    fr = coil.r_ac(f, temp_coil_c) / coil.r_dc(temp_coil_c)

    # --- losses ------------------------------------------------------------
    p_cu = i_rms ** 2 * r_ac
    p_core = (core_loss(mat, f, b_pole * math.sqrt(2), core.vol_shoe) +
              core_loss(mat, f, b_leg * math.sqrt(2), core.vol_leg + core.vol_yoke))
    # induced E in the water and its ohmic dissipation over the gap volume
    r_eff = 0.5 * math.sqrt(core.pole_w * core.pole_h / PI)   # equivalent loop radius
    e_water = PI * f * b_ecv * r_eff
    v_water_field = core.pole_area * CELL.WATER_GAP
    p_water = sigma_water * e_water ** 2 * v_water_field

    # --- drive point -------------------------------------------------------
    w = 2 * PI * f
    x = w * L
    v_r = i_rms * r_ac
    v_x = i_rms * x
    v_unc = math.hypot(v_r, v_x)
    q = i_rms ** 2 * x
    if f >= lim.compensate_above and x > 0:
        # SWITCHED series-capacitor bank: one fixed C per octave band, tuned
        # at the band's geometric centre.  Inside a band the residual
        # reactance is NOT zero, which is deliberate: exact tuning would give
        # a loaded Q of ~10^3 and an uncontrollable, hyper-sensitive loop.
        c_ser = band_capacitor(f, L)
        x_c = 1.0 / (w * c_ser)
        x_res = x - x_c
        v_cap = i_rms * x_c
        v_drive = i_rms * math.hypot(r_ac, x_res)
    else:
        c_ser, v_cap, v_drive = None, 0.0, v_unc

    p_in = p_cu + p_core
    eta = (p_core + p_water) / p_in if p_in > 0 else 0.0   # "useful" fraction is ~0

    sol = CellSolution(
        f=f, b_ecv=b_ecv, b_pole=b_pole, b_leg=b_leg, cv_b=cv, mmf=mmf,
        flux=flux, reluctance=reluct, N_loop=N_loop, L=L, i_rms=i_rms,
        i_peak=i_rms * math.sqrt(2), j_cu=coil.current_density(i_rms), fr_ac=fr,
        r_ac=r_ac, p_cu=p_cu, p_core=p_core, p_water=p_water, e_water=e_water,
        v_r=v_r, v_x=v_x, v_uncomp=v_unc, q_var=q, c_series=c_ser, v_cap=v_cap,
        v_drive=v_drive, va_drive=i_rms * v_drive, efficiency=eta,
        wire=wire.label, turns_per_coil=turns_per_coil, fits=coil.fits,
        fill=coil.fill_factor)

    # --- limit checks (Failure Surfaces FS1-FS4) ---------------------------
    if sol.i_rms > lim.i_max: sol.limits.append("FS3 I>Imax")
    if sol.v_drive > lim.v_max: sol.limits.append("FS3 V>Vmax")
    if sol.va_drive > lim.s_max: sol.limits.append("FS3 S>Smax")
    if (sol.p_cu + sol.p_core) > lim.p_max: sol.limits.append("FS4 P>Pmax")
    if (sol.p_cu + sol.p_core) > lim.p_cell_thermal: sol.limits.append("FS4 cooling")
    if sol.j_cu > lim.j_max: sol.limits.append("FS4 J>Jmax")
    if sol.b_leg * math.sqrt(2) > 0.8 * mat.b_sat: sol.limits.append("FS1 core sat")
    if not sol.fits: sol.limits.append("FS1 window overflow")
    if f > lim.f_max: sol.limits.append("FS3 bandwidth")
    return sol


# ----------------------------------------------------------------------------
# SWITCHED COMPENSATION BANK
# ----------------------------------------------------------------------------
COMP_BANDS = [(80.0, 160.0), (160.0, 320.0), (320.0, 640.0),
              (640.0, 1280.0), (1280.0, 2200.0), (2200.0, 3300.0)]


def band_capacitor(f: float, L: float) -> float:
    """Fixed capacitance of the bank section covering f, tuned at band centre."""
    for lo, hi in COMP_BANDS:
        if lo <= f < hi:
            fc = math.sqrt(lo * hi)
            return 1.0 / ((2 * PI * fc) ** 2 * L)
    lo, hi = COMP_BANDS[-1]
    fc = math.sqrt(lo * hi)
    return 1.0 / ((2 * PI * fc) ** 2 * L)


def loaded_Q(f: float, L: float, r: float) -> float:
    return 2 * PI * f * L / r if r > 0 else float("inf")


_GAP_CACHE = {}


def _gap_mmf_unit(core: CoreGeom):
    """
    Ampere-turns across ONE gap per tesla of pole-face flux density,
    from the charge-sheet line integral.  Cached (linear model).
    """
    key = (core.pole_w, core.pole_h, core.gap)
    if key in _GAP_CACHE:
        return _GAP_CACHE[key]
    from magnetics import ForkGeometry, B_at
    from architectures import BUILDERS
    fk = ForkGeometry(n_prong=1, prong_w=core.pole_w, prong_h=core.pole_h,
                      prong_len=core.leg_len, gap=core.gap)
    sheets = BUILDERS["R3"](fk, 1.0)
    n = 800
    z0, z1 = 1e-4, core.gap - 1e-4
    acc = 0.0
    for i in range(n + 1):
        z = z0 + (z1 - z0) * i / n
        wt = 0.5 if i in (0, n) else 1.0
        acc += wt * abs(B_at((0.0, 0.0, z), sheets)[2])
    val = acc * (z1 - z0) / n / MU0
    # path-spread model-error estimate
    spread = []
    for dx, dy in ((core.pole_w * 0.3, 0.0), (0.0, core.pole_h * 0.3)):
        a = 0.0
        for i in range(n + 1):
            z = z0 + (z1 - z0) * i / n
            wt = 0.5 if i in (0, n) else 1.0
            a += wt * abs(B_at((dx, dy, z), sheets)[2])
        spread.append(a * (z1 - z0) / n / MU0)
    err = (max(spread + [val]) - min(spread + [val])) / val
    _GAP_CACHE[key] = (val, err, spread)
    return _GAP_CACHE[key]


# ============================================================================
# WINDING SELECTION
# ============================================================================
def choose_winding(core: CoreGeom, f_max_band: float, mmf_max: float,
                   lim: DriverLimits = None):
    """
    Pick (wire, turns) that (a) fits the window, (b) keeps J <= J_max at the
    worst-case MMF, (c) keeps R_ac/R_dc low at the top of the band, and
    (d) keeps the driver current within I_max.
    """
    lim = lim or DriverLimits()
    best = None
    for wire in WIRES:
        for n in range(4, 121, 2):
            i = mmf_max / (2 * n)
            if i > lim.i_max:
                continue
            j = i / (wire.a_cu * 1e6)
            if j > lim.j_max:
                continue
            coil = Coil(turns=n, wire=wire, mean_turn_length=core.mean_turn_length(),
                        window_w=core.leg_len, window_h=CELL.WINDOW_H, n_coils_series=2)
            if not coil.fits:
                continue
            fr = coil.r_ac(f_max_band, 80.0) / coil.r_dc(80.0)
            r = coil.r_ac(f_max_band, 80.0) * 2
            p = i * i * r
            # capacitor voltage at the top of the band scales linearly with N
            gv, _, _ = _gap_mmf_unit(core)
            reluct = gv / core.pole_area          # A/Wb per tesla -> 1/(Wb/A-t)
            L = (2 * n) ** 2 / reluct
            v_x = i * 2 * PI * f_max_band * L
            if v_x > lim.v_cap_max:
                continue
            if i * 2 * PI * f_max_band * L / r > lim.q_max * 1.0e9:
                continue
            score = p * fr
            if best is None or score < best[0]:
                best = (score, wire, n, fr, p, j, v_x, L)
    return best
