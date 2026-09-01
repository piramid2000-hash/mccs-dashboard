"""
Section 17 — Thermal model.  Heat sources are kept SEPARATE, because the
whole Sham design (Section 20) depends on knowing which of them are
field-coupled and which are not.

    P_loss = P_Cu + P_core + P_tank_eddy + P_driver + P_pump + P_water_field
             \_______________________/   \______/   \____/   \___________/
                  field-coupled, but      not in    NOT      field-coupled
                  OUTSIDE the wetted      water     field-   and INSIDE the
                  boundary (dry cell)               coupled  water

Only P_water_field enters the water because of the field.  Everything else
is either outside the wetted boundary or is reproduced identically in the
Sham arm.  That is the quantitative basis for rejecting H1 (thermal artifact).
"""
import math
from dataclasses import dataclass

from constants import CP_WATER, RHO_M_WATER


@dataclass
class CoolingPath:
    label: str
    r_th: float          # K/W, source -> coolant
    t_coolant: float     # degC
    t_limit: float       # degC

    def temp(self, p_w: float) -> float:
        return self.t_coolant + p_w * self.r_th

    def ok(self, p_w: float) -> bool:
        return self.temp(p_w) <= self.t_limit

    def p_max(self) -> float:
        return (self.t_limit - self.t_coolant) / self.r_th


# Baseline Phase-3 cooling design (evidence level T; to be verified at FAT)
COIL_PATH = CoolingPath("coil -> potting -> cold plate -> 25 C glycol loop",
                        r_th=0.055, t_coolant=25.0, t_limit=120.0)
CORE_PATH = CoolingPath("core -> clamp -> cold plate -> 25 C glycol loop",
                        r_th=0.030, t_coolant=25.0, t_limit=100.0)
DRIVER_PATH = CoolingPath("power stage -> heatsink -> forced air 35 C",
                          r_th=0.045, t_coolant=35.0, t_limit=95.0)


def pump_heat(delta_p_pa: float, q_m3s: float, eta_pump: float = 0.55) -> float:
    """All pump shaft power ultimately appears as heat in the loop [W]."""
    return delta_p_pa * q_m3s / eta_pump


def duct_pressure_drop(v: float, d_h: float, length: float,
                       rho: float = None, nu: float = 1.004e-6) -> float:
    """Darcy-Weisbach for the exposure duct [Pa]."""
    rho = RHO_M_WATER.value if rho is None else rho
    re = v * d_h / nu
    if re < 2300:
        fd = 64.0 / max(re, 1e-6)
    else:
        fd = 0.316 * re ** -0.25          # Blasius
    return fd * (length / d_h) * 0.5 * rho * v * v


def water_dT_dt(p_w: float, volume_L: float) -> float:
    """K/s for a well-mixed batch with no heat rejection."""
    return p_w / (volume_L * RHO_M_WATER.value / 1000.0 * CP_WATER.value)


def chiller_duty(p_w: float, margin: float = 1.5) -> float:
    return p_w * margin
