"""
SS-03 / Section 13 — SUS316L tank electromagnetic coupling model.

Defines the complex transfer function

        H(f) = B_inside(f) / B_outside(f) = |H(f)| * exp(j*phi(f))

for a thin conducting (essentially non-magnetic) cylindrical shell.

PHYSICS
-------
An axial AC field threading a closed conducting shell drives an azimuthal
eddy current that opposes the field.  For a shell of radius a, wall thickness
t, conductivity sigma, with t << delta (skin depth), the classic thin-shell
(Kaden) result is a single-pole low-pass:

        H(f) = 1 / (1 + j*omega*tau_s)      tau_s = mu0*mu_r*sigma*t*a/2

For the transverse orientation the shell time constant is the same to within
a factor of order unity; the standard result carries the same tau_s, so both
are computed and the axial case is used as the design-driving (worst) case.

When t is no longer small versus the skin depth the thin-shell form
under-predicts attenuation; the exact plane-wall correction

        H_wall = 1 / cosh(k*t),   k = (1+j)/delta

is computed alongside and the two are combined multiplicatively, which is the
conventional engineering composition of the "loop" (shape) term and the
"diffusion" (thickness) term.  Validity is flagged whenever t/delta > 0.3.

EVIDENCE: this entire module is P0 (physics prior).  Its output is a
PREDICTION.  VG-05 / Section 13 requires E1 replacement by a two-probe
(inside/outside) swept-frequency measurement on the real tank.
"""
import cmath
import math
from dataclasses import dataclass

from constants import MU0, PI, SIGMA_SUS316L, MU_R_SUS316L_ANNEALED, MU_R_SUS316L_COLDWORK


@dataclass
class TankGeometry:
    """1,000 L class SUS316L vertical cylindrical tank."""
    inner_diameter: float = 1.00      # m
    straight_height: float = 1.30     # m
    wall_thickness: float = 3.0e-3    # m   (2B finish, typical for 1 m3)
    name: str = "1000 L SUS316L vertical cylinder"

    @property
    def radius(self) -> float:
        return self.inner_diameter / 2.0

    @property
    def volume_m3(self) -> float:
        return PI * self.radius ** 2 * self.straight_height

    @property
    def wall_mass(self) -> float:
        from constants import RHO_M_SUS
        area = 2 * PI * self.radius * self.straight_height + 2 * PI * self.radius ** 2
        return area * self.wall_thickness * RHO_M_SUS.value


def skin_depth(f: float, sigma: float, mu_r: float = 1.0) -> float:
    """Classical skin depth [m].  f in Hz."""
    if f <= 0:
        return float("inf")
    return math.sqrt(2.0 / (2 * PI * f * MU0 * mu_r * sigma))


def shell_time_constant(tank: TankGeometry, sigma: float, mu_r: float) -> float:
    """tau_s = mu0*mu_r*sigma*t*a/2  [s]"""
    return MU0 * mu_r * sigma * tank.wall_thickness * tank.radius / 2.0


def H_tank(f: float, tank: TankGeometry, sigma: float = None,
           mu_r: float = None, include_thickness: bool = True) -> complex:
    """Complex transfer function B_inside/B_outside at frequency f."""
    sigma = SIGMA_SUS316L.value if sigma is None else sigma
    mu_r = MU_R_SUS316L_ANNEALED.value if mu_r is None else mu_r
    tau = shell_time_constant(tank, sigma, mu_r)
    w = 2 * PI * f
    H_loop = 1.0 / (1.0 + 1j * w * tau)
    if not include_thickness or f <= 0:
        return H_loop
    d = skin_depth(f, sigma, mu_r)
    k = (1 + 1j) / d
    H_wall = 1.0 / cmath.cosh(k * tank.wall_thickness)
    return H_loop * H_wall


def corner_frequency(tank: TankGeometry, sigma: float = None, mu_r: float = None) -> float:
    """-3 dB frequency of the shell low-pass [Hz]."""
    sigma = SIGMA_SUS316L.value if sigma is None else sigma
    mu_r = MU_R_SUS316L_ANNEALED.value if mu_r is None else mu_r
    return 1.0 / (2 * PI * shell_time_constant(tank, sigma, mu_r))


def eddy_loss_shell(f: float, b_outside_rms: float, tank: TankGeometry,
                    sigma: float = None) -> float:
    """
    Eddy-current power dissipated in the tank wall [W] for an axial field.

    Thin-ring model integrated over the shell height:
        EMF_rms(ring) = omega * B_in_rms * pi * a^2
        R(ring of height dh) = 2*pi*a / (sigma * t * dh)
        dP = EMF^2 / R
      => P = (1/2)... -> closed form below.
    The INTERNAL (shielded) field is used as the driving flux, which is the
    self-consistent thin-shell result.
    """
    sigma = SIGMA_SUS316L.value if sigma is None else sigma
    if f <= 0:
        return 0.0
    w = 2 * PI * f
    b_in = abs(H_tank(f, tank, sigma)) * b_outside_rms
    a = tank.radius
    h = tank.straight_height
    # P = (w*B*pi*a^2)^2 * sigma*t*h / (2*pi*a)
    return (w * b_in * PI * a ** 2) ** 2 * sigma * tank.wall_thickness * h / (2 * PI * a)


def wall_temp_rise_rate(p_loss: float, tank: TankGeometry) -> float:
    """Adiabatic wall dT/dt [K/s] — an upper bound with no heat removal."""
    from constants import CP_SUS
    return p_loss / (tank.wall_mass * CP_SUS.value)


def sweep(tank: TankGeometry, freqs, b_outside_rms: float = 1.0e-3,
          mu_r: float = None):
    """Return a list of dicts, one per frequency."""
    mu_r = MU_R_SUS316L_ANNEALED.value if mu_r is None else mu_r
    sigma = SIGMA_SUS316L.value
    rows = []
    for f in freqs:
        H = H_tank(f, tank, sigma, mu_r)
        d = skin_depth(f, sigma, mu_r)
        p = eddy_loss_shell(f, b_outside_rms, tank, sigma)
        rows.append(dict(
            f_Hz=f,
            H_mag=abs(H),
            H_dB=20 * math.log10(abs(H)) if abs(H) > 0 else -999.0,
            phase_deg=math.degrees(cmath.phase(H)),
            skin_depth_mm=d * 1e3,
            t_over_delta=tank.wall_thickness / d,
            B_in_mT=abs(H) * b_outside_rms * 1e3,
            P_eddy_W=p,
            dTdt_K_per_s=wall_temp_rise_rate(p, tank),
            model_valid=("thin-shell OK" if tank.wall_thickness / d <= 0.3
                         else "t/delta>0.3: diffusion term dominates"),
        ))
    return rows
