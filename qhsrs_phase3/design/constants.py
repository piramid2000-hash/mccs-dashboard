"""
Q-HSRS Phase 3 — Physical constants and material property library.

EVIDENCE LEVELS (see report Section 02):
  E1 = measured on this build          (NONE of the values in this file are E1)
  E2 = supplier datasheet value        (must be replaced before design freeze)
  P0 = public literature / physics prior
  T  = development target
  H  = unverified hypothesis (never used as a design variable)

Every constant below carries an explicit `.evidence` tag. Nothing in this
module may be reported as E1.
"""
from dataclasses import dataclass, field

MU0 = 4.0e-7 * 3.14159265358979323846  # H/m, exact by definition of A (P0)
PI = 3.14159265358979323846


@dataclass(frozen=True)
class Q:
    """A quantity with units and an evidence tag."""
    value: float
    unit: str
    evidence: str          # 'E1' | 'E2' | 'P0' | 'T' | 'H'
    note: str = ""

    def __float__(self):
        return float(self.value)


# ----------------------------------------------------------------------------
# CONDUCTORS
# ----------------------------------------------------------------------------
RHO_CU_20C = Q(1.724e-8, "ohm*m", "P0", "annealed copper @20 C, IEC 60028")
ALPHA_CU = Q(3.93e-3, "1/K", "P0", "copper temperature coefficient @20 C")
K_CU = Q(401.0, "W/m/K", "P0", "copper thermal conductivity")
CP_CU = Q(385.0, "J/kg/K", "P0")
RHO_M_CU = Q(8960.0, "kg/m3", "P0")

# ----------------------------------------------------------------------------
# SUS316L  (the tank) — the single most consequential material in this design
# ----------------------------------------------------------------------------
# 316L is austenitic: essentially non-ferromagnetic in the annealed condition,
# but COLD WORK (rolling, forming, welding HAZ) induces alpha'-martensite and
# mu_r can rise to 1.5-2.0 locally.  This is a real, measurable risk item.
SIGMA_SUS316L = Q(1.35e6, "S/m", "P0", "rho ~ 7.4e-7 ohm.m @20 C, ASM data")
MU_R_SUS316L_ANNEALED = Q(1.005, "-", "P0", "annealed, non-magnetic")
MU_R_SUS316L_COLDWORK = Q(1.8, "-", "P0", "worst-case cold-worked / weld HAZ")
K_SUS316L = Q(14.6, "W/m/K", "P0")
RHO_M_SUS = Q(8000.0, "kg/m3", "P0")
CP_SUS = Q(500.0, "J/kg/K", "P0")

# ----------------------------------------------------------------------------
# WATER  (process medium)
# ----------------------------------------------------------------------------
SIGMA_WATER_DI = Q(5.5e-6, "S/m", "P0", "ultrapure water @25 C")
SIGMA_WATER_TAP = Q(4.0e-2, "S/m", "P0", "~400 uS/cm municipal tap")
SIGMA_WATER_GW = Q(9.0e-2, "S/m", "P0", "~900 uS/cm groundwater")
SIGMA_ELECTROLYTE_MAX = Q(0.5, "S/m", "P0", "5000 uS/cm controlled electrolyte")
MU_R_WATER = Q(0.999991, "-", "P0", "diamagnetic; treated as 1.0 in the circuit")
K_WATER = Q(0.60, "W/m/K", "P0")
CP_WATER = Q(4182.0, "J/kg/K", "P0")
RHO_M_WATER = Q(998.0, "kg/m3", "P0")
NU_WATER_20C = Q(1.004e-6, "m2/s", "P0", "kinematic viscosity @20 C")

# ----------------------------------------------------------------------------
# CORE MATERIAL CANDIDATES
# Steinmetz  Pv = kh*f^a*B^b  [W/m3], B in T, f in Hz.
# The Steinmetz triplets are LITERATURE-TYPICAL (P0).  They MUST be replaced
# with vendor loss curves (E2) and then coupon-measured (E1) before Gate A.
# ----------------------------------------------------------------------------
# Steinmetz coefficients below are CALIBRATED against a published anchor
# point for each grade (stated in `anchor`), with the classical eddy term
# subtracted first so that (k, alpha, beta) carries hysteresis + excess only.
# This makes them auditable.  They remain P0 and MUST be replaced by vendor
# loss curves (E2) and then by coupon measurement (E1) before Gate A.
@dataclass(frozen=True)
class CoreMaterial:
    name: str
    mu_r_init: float          # initial relative permeability (low field, low f)
    b_sat: float              # T
    rho_mass: float           # kg/m3
    sigma: float              # S/m (bulk, for classical eddy term)
    lam_t: float              # m, lamination / ribbon thickness
    k_steinmetz: float        # W/m3 with f[Hz], B[T]
    alpha: float
    beta: float
    stacking: float           # lamination stacking factor
    cost_kg: float            # USD/kg  -- BUDGETARY ESTIMATE, not a quote
    machinability: str
    anchor: str = ""          # the published point the Steinmetz k was fitted to
    evidence: str = "P0"


M350_50A = CoreMaterial(
    name="NO electrical steel M350-50A (0.50 mm)",
    mu_r_init=4000.0, b_sat=2.03, rho_mass=7650.0, sigma=2.13e6,
    lam_t=0.50e-3, k_steinmetz=15.6, alpha=1.65, beta=1.95,
    stacking=0.96, cost_kg=3.0, machinability="excellent (EDM/stamped)",
    anchor="P(1.5 T, 50 Hz) = 3.50 W/kg (grade designation), rho=7650",
)

NO10_THIN = CoreMaterial(
    name="Thin-gauge NO silicon steel 0.10 mm (10JNEX-class)",
    mu_r_init=3500.0, b_sat=1.80, rho_mass=7500.0, sigma=1.20e6,
    lam_t=0.10e-3, k_steinmetz=3.92, alpha=1.62, beta=1.92,
    stacking=0.90, cost_kg=22.0, machinability="good, fragile handling",
    anchor="P(1.0 T, 400 Hz) = 9.0 W/kg (thin-gauge 6.5%Si class), rho=7490",
)

NANOCRYSTALLINE = CoreMaterial(
    name="Nanocrystalline FeCuNbSiB ribbon 18 um (FINEMET-class)",
    mu_r_init=30000.0, b_sat=1.23, rho_mass=7300.0, sigma=0.83e6,
    lam_t=18e-6, k_steinmetz=2.18e-3, alpha=1.75, beta=2.00,
    stacking=0.75, cost_kg=95.0, machinability="poor: wound cores only, brittle",
    anchor="P(0.2 T, 20 kHz) ~ 10 kW/m3 (FeCuNbSiB ribbon class)",
)

FERRITE_N87 = CoreMaterial(
    name="MnZn power ferrite (N87-class)",
    mu_r_init=2200.0, b_sat=0.39, rho_mass=4850.0, sigma=0.5,
    lam_t=1.0, k_steinmetz=0.466, alpha=1.55, beta=2.60,
    stacking=1.00, cost_kg=32.0, machinability="brittle, ground cores only",
    anchor="P(0.2 T, 100 kHz, 25 C) ~ 400 kW/m3 (MnZn power ferrite class)",
)

AIR_CORE = CoreMaterial(
    name="Air core (no ferromagnetic circuit)",
    mu_r_init=1.0, b_sat=1e9, rho_mass=0.0, sigma=0.0,
    lam_t=1.0, k_steinmetz=0.0, alpha=1.0, beta=1.0,
    stacking=1.0, cost_kg=0.0, machinability="n/a",
    anchor="lossless by construction",
)

CORE_CANDIDATES = [M350_50A, NO10_THIN, NANOCRYSTALLINE, FERRITE_N87, AIR_CORE]

# ----------------------------------------------------------------------------
# STANDARD FREQUENCY GRID (Section 09 of the master prompt)
# 7.83 Hz is included because it is REQUESTED, not because a Schumann
# resonance effect is assumed.  It is treated exactly like any other f.
# ----------------------------------------------------------------------------
F_GRID = [3.0, 7.83, 10.0, 30.0, 50.0, 100.0, 300.0, 500.0, 1000.0, 2000.0, 3000.0]

# Dose ladder (Section 05).  Values are TARGETS (T), not achieved fields.
B_LADDER_T = [0.0, 0.5e-3, 1.0e-3, 5.0e-3, 10.0e-3, 50.0e-3]
B_LADDER_LABEL = ["Sham", "0.5 mT", "1 mT", "5 mT", "10 mT", "50 mT"]
