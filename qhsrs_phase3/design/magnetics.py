"""
SS-02 / SS-03 — Fork geometry, magnetic circuit and 3-D field synthesis.

TWO COUPLED MODELS
------------------
(1) LUMPED RELUCTANCE CIRCUIT  -> ampere-turns, inductance, flux, saturation.
(2) MAGNETIC SURFACE-CHARGE SHEET MODEL -> the actual 3-D field B(r) in the
    water, hence B_mean / B_min / B_max / CV_B and the 5-point map.

Model (2) replaces every pole face by a uniformly magnetically-charged
rectangle of density sigma_m = B_pole [T].  For a rectangle in the plane
z = z0 spanning x in [a1,a2], y in [b1,b2] the closed-form field is the
classical solid-angle / log result (Engel-Herbert & Hesjedal form).  In the
water mu_r = 1, so B = mu0*H and superposition is exact.

VALIDITY: this is a linear, magnetostatic, quasi-static model.  It is correct
for the water region as long as (a) the core is unsaturated, (b) the water's
own eddy currents are negligible, and (c) frequency is low enough that the
field pattern is quasi-static.  All three are checked numerically in
feasibility.py.  Evidence level P0 throughout; 3-D FEA and E1 probe mapping
are required at Gate B before any dimension is frozen.
"""
import math
from dataclasses import dataclass, field
from typing import List, Tuple

from constants import MU0, PI, MU_R_WATER, SIGMA_ELECTROLYTE_MAX


# ============================================================================
# 1. CHARGE-SHEET FIELD PRIMITIVE
# ============================================================================
def _rect_sheet_B(px, py, pz, sigma_m, x1, x2, y1, y2, z0):
    """
    B [T] at (px,py,pz) from a rectangle at z=z0, x in [x1,x2], y in [y1,y2]
    carrying uniform magnetic surface charge sigma_m [T].
    """
    z = pz - z0
    az = abs(z)
    sz = 1.0 if z >= 0.0 else -1.0
    bx = by = bz = 0.0
    for i, xa in enumerate((x1, x2)):
        X = px - xa
        for j, ya in enumerate((y1, y2)):
            Y = py - ya
            s = 1.0 if (i + j) % 2 == 0 else -1.0
            R = math.sqrt(X * X + Y * Y + z * z)
            # guard against the logarithmic singularity on the sheet edge
            bx += s * math.log(max(Y + R, 1e-12))
            by += s * math.log(max(X + R, 1e-12))
            # solid-angle term: written with |z| and an explicit sign so that
            # Bn is ODD in z (a charge sheet reverses its normal field across
            # itself).  atan2(.., z*R) alone is NOT odd in z and gives a
            # spurious pi-branch offset for z < 0.
            bz += s * math.atan2(X * Y, az * R if az * R > 1e-18 else 1e-18)
    k = sigma_m / (4.0 * PI)
    return (k * bx, k * by, sz * k * bz)


# ============================================================================
# 2. FORK GEOMETRY
# ============================================================================
@dataclass
class ForkGeometry:
    """
    A 3-prong fork.  Prongs are rectangular blades projecting from a yoke
    (spine).  The pole FACES are the prong end faces that look across the
    working gap.

    Coordinate convention used everywhere in this package:
        x = along the fork spine (prong-to-prong direction) = FLOW direction
        y = prong height direction (vertical when the fork is upright)
        z = across the working gap (fork A at z=0, fork B at z=+g)
    """
    n_prong: int = 3
    prong_w: float = 0.120        # m, pole-face width  (x)
    prong_h: float = 0.300        # m, pole-face height (y)
    prong_len: float = 0.250      # m, prong length (z), sets coil window
    prong_pitch: float = 0.200    # m, prong centre-to-centre (x)
    yoke_w: float = 0.120         # m
    yoke_h: float = 0.300         # m
    gap: float = 0.060            # m, working gap between opposed pole faces
    name: str = "R2 opposed dual 3-prong fork"

    @property
    def pole_area(self) -> float:
        return self.prong_w * self.prong_h

    @property
    def core_area(self) -> float:
        return self.prong_w * self.prong_h

    @property
    def span(self) -> float:
        return (self.n_prong - 1) * self.prong_pitch + self.prong_w

    def pole_centres(self) -> List[float]:
        x0 = -(self.n_prong - 1) * self.prong_pitch / 2.0
        return [x0 + i * self.prong_pitch for i in range(self.n_prong)]

    def core_path_length(self) -> float:
        """Mean ferromagnetic path length of ONE closed flux loop [m].

        Loop: A_i -> gap -> B_i -> B yoke -> B_(i+1) -> gap -> A_(i+1) -> A yoke.
        = 4 prong lengths + 2 yoke runs of one pitch.
        """
        return 4.0 * self.prong_len + 2.0 * self.prong_pitch

    def core_volume(self) -> float:
        """Total ferromagnetic volume of BOTH forks [m3]."""
        prongs = 2 * self.n_prong * self.prong_w * self.prong_h * self.prong_len
        yokes = 2 * self.span * self.yoke_w * self.yoke_h
        return prongs + yokes


# ============================================================================
# 3. LUMPED RELUCTANCE CIRCUIT
# ============================================================================
def fringing_area(fk: ForkGeometry) -> float:
    """Effective gap area with first-order fringing (McLyman/Rosenberg)."""
    return (fk.prong_w + fk.gap) * (fk.prong_h + fk.gap)


def reluctances(fk: ForkGeometry, mu_r_core: float):
    """Return (R_gap_single, R_core_loop, R_loop_total) [A/Wb]."""
    a_eff = fringing_area(fk)
    r_gap = fk.gap / (MU0 * a_eff)
    r_core = fk.core_path_length() / (MU0 * mu_r_core * fk.core_area)
    return r_gap, r_core, 2 * r_gap + r_core


def ampere_turns_for_gap_B(b_gap: float, fk: ForkGeometry, mu_r_core: float):
    """
    Total ampere-turns linking ONE flux loop to establish pole-face flux
    density b_gap [T].  Returns (F_loop [A-turns], flux [Wb], B_core [T]).
    """
    _, _, r_loop = reluctances(fk, mu_r_core)
    flux = b_gap * fk.pole_area
    return flux * r_loop, flux, flux / fk.core_area


def inductance(fk: ForkGeometry, mu_r_core: float, n_total_per_loop: int):
    """
    Loop inductance seen by the driver [H]:  L = N_loop^2 / R_loop,
    where N_loop is the total turns linking one flux loop.
    """
    _, _, r_loop = reluctances(fk, mu_r_core)
    return n_total_per_loop ** 2 / r_loop


# ============================================================================
# 4. 3-D FIELD SYNTHESIS FROM POLE FACES
# ============================================================================
def build_pole_sheets(fk: ForkGeometry, b_pole: float):
    """
    Return the list of charged rectangles representing all 2*n_prong pole
    faces.  Polarity alternates along the fork (N,S,N ...) on fork A and is
    mirrored on fork B so that flux crosses the gap and returns through the
    neighbouring prong pair.
    """
    sheets = []
    for i, xc in enumerate(fk.pole_centres()):
        sgn = 1.0 if i % 2 == 0 else -1.0
        x1, x2 = xc - fk.prong_w / 2, xc + fk.prong_w / 2
        y1, y2 = -fk.prong_h / 2, fk.prong_h / 2
        # fork A pole face at z = 0, outward normal +z
        sheets.append((sgn * b_pole, x1, x2, y1, y2, 0.0))
        # fork B pole face at z = gap, opposite sign
        sheets.append((-sgn * b_pole, x1, x2, y1, y2, fk.gap))
    return sheets


def B_at(point, sheets):
    """Superposed B vector [T] at point=(x,y,z)."""
    bx = by = bz = 0.0
    for (sm, x1, x2, y1, y2, z0) in sheets:
        b = _rect_sheet_B(point[0], point[1], point[2], sm, x1, x2, y1, y2, z0)
        bx += b[0]; by += b[1]; bz += b[2]
    return (bx, by, bz)


def Bmag(point, sheets):
    b = B_at(point, sheets)
    return math.sqrt(b[0] ** 2 + b[1] ** 2 + b[2] ** 2)


# ============================================================================
# 5. EXPOSURE CONTROL VOLUME (ECV) AND UNIFORMITY
# ============================================================================
@dataclass
class ECV:
    """
    Exposure Control Volume — the region over which the uniformity
    requirement CV_B <= 10 % is CONTRACTUAL.  Defining this is mandatory:
    the requirement cannot be written against 'the whole 1,000 L tank',
    which is physically unachievable with any local fork (see report S.13).
    """
    x_half: float
    y_half: float
    z_lo: float
    z_hi: float
    label: str = "ECV"

    @property
    def volume_L(self) -> float:
        return (2 * self.x_half) * (2 * self.y_half) * (self.z_hi - self.z_lo) * 1000.0


def field_statistics(fk: ForkGeometry, b_pole: float, ecv: ECV, n=(9, 9, 7)):
    """Grid-sample |B| over the ECV and return uniformity statistics."""
    sheets = build_pole_sheets(fk, b_pole)
    vals = []
    nx, ny, nz = n
    for ix in range(nx):
        x = -ecv.x_half + 2 * ecv.x_half * ix / (nx - 1) if nx > 1 else 0.0
        for iy in range(ny):
            y = -ecv.y_half + 2 * ecv.y_half * iy / (ny - 1) if ny > 1 else 0.0
            for iz in range(nz):
                z = ecv.z_lo + (ecv.z_hi - ecv.z_lo) * iz / (nz - 1) if nz > 1 else ecv.z_lo
                vals.append(Bmag((x, y, z), sheets))
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    sd = math.sqrt(var)
    return dict(B_mean_T=mean, B_std_T=sd, B_min_T=min(vals), B_max_T=max(vals),
                CV_B=sd / mean if mean > 0 else float("inf"), n_samples=len(vals),
                ECV_L=ecv.volume_L, label=ecv.label)


def five_point_map(fk: ForkGeometry, b_pole: float, ecv: ECV):
    """P1..P5 of Section 13 of the master prompt."""
    sheets = build_pole_sheets(fk, b_pole)
    zc = 0.5 * (ecv.z_lo + ecv.z_hi)
    pts = {
        "P1 Center":        (0.0, 0.0, zc),
        "P2 Fork-near":     (0.0, 0.0, ecv.z_lo),
        "P3 Fork-opposite": (0.0, 0.0, ecv.z_hi),
        "P4 Upper":         (0.0, ecv.y_half, zc),
        "P5 Lower":         (0.0, -ecv.y_half, zc),
    }
    out = {}
    for k, p in pts.items():
        b = B_at(p, sheets)
        out[k] = dict(x=p[0], y=p[1], z=p[2], Bx=b[0], By=b[1], Bz=b[2],
                      Bmag=math.sqrt(sum(c * c for c in b)))
    return out


def pole_B_for_target_centre_B(fk: ForkGeometry, b_target_centre: float,
                               ecv: ECV) -> float:
    """
    Invert the sheet model: what pole-face flux density is needed so that the
    ECV MEAN |B| equals the target?  Linear model => single evaluation scales.
    """
    probe = 0.1  # T at the pole face
    st = field_statistics(fk, probe, ecv, n=(7, 7, 5))
    return probe * b_target_centre / st["B_mean_T"]


# ============================================================================
# 6. WATER EDDY-CURRENT / INDUCED-E CHECK  (safety + confounder)
# ============================================================================
def induced_E_water(f: float, b_rms: float, r_loop: float) -> float:
    """
    Induced electric field magnitude at radius r in the water [V/m].
    E = pi*f*B*r  (Faraday, circular path).  This is the quantity that
    ICNIRP limits and it is ALSO the physically plausible driver of any
    electrochemical effect -- so it must be reported next to B, never
    hidden behind it.
    """
    return PI * f * b_rms * r_loop


def water_eddy_loss_density(f: float, b_rms: float, r_loop: float,
                            sigma_w: float = None) -> float:
    """Ohmic dissipation density in the water [W/m3] = sigma*E^2."""
    sigma_w = SIGMA_ELECTROLYTE_MAX.value if sigma_w is None else sigma_w
    return sigma_w * induced_E_water(f, b_rms, r_loop) ** 2
