"""
Sections 11, 12, 13, 20, 32 — sensing, the constant-B loop, the measurement
uncertainty budget, and Sham verification.

The Phase-3 requirement |B_meas - B_set|/B_set <= 5 % is a CONTROL error.
It is meaningless unless the MEASUREMENT uncertainty is smaller than it, so
the uncertainty budget is computed first and the control target is checked
against it -- not the other way round.
"""
import math
from dataclasses import dataclass
from typing import List

from constants import PI, MU0


# ============================================================================
# SENSOR CANDIDATES  (all specifications are TARGETS/typical-class, P0/T,
# to be replaced by datasheet values E2 then calibration E1)
# ============================================================================
@dataclass
class Sensor:
    name: str
    kind: str
    f_lo: float            # Hz, -3 dB low corner (0 = DC coupled)
    f_hi: float            # Hz, -3 dB high corner
    range_mT: float
    noise_nT_rtHz: float   # nT/sqrt(Hz) at 1 Hz
    lin_pct: float         # % of reading
    tempco_ppm_K: float
    phase_err_deg: float   # over 3-3000 Hz
    notes: str


SENSORS = [
    Sensor("3-axis Hall probe (InSb/GaAs)", "Hall", 0.0, 20e3, 2000.0,
           300.0, 1.0, 400.0, 2.0,
           "DC-capable, wide range, poor low-field resolution, strong tempco"),
    Sensor("Fluxgate magnetometer", "Fluxgate", 0.0, 3e3, 1.0,
           0.01, 0.1, 30.0, 1.0,
           "best resolution; SATURATES far below the dose ladder - reference/Sham only"),
    Sensor("Air-cored search coil (induction)", "SearchCoil", 1.0, 100e3, 1e6,
           1.0, 0.05, 20.0, 0.5,
           "output ~ dB/dt: excellent at HF, degrades as 1/f at LF; inherently AC"),
    Sensor("Rogowski coil (coil current)", "Rogowski", 0.1, 1e6, 1e9,
           5.0, 0.2, 50.0, 0.5, "measures I, not B; Layer-1 observer"),
    Sensor("Precision shunt + isolated ADC", "Shunt", 0.0, 100e3, 1e9,
           1.0, 0.05, 15.0, 0.2, "measures I, not B; Layer-1 observer"),
]


def search_coil_sensitivity(n_turns: int, area_m2: float, f: float) -> float:
    """V per tesla for an air-cored search coil: V = N*A*2*pi*f*B."""
    return n_turns * area_m2 * 2 * PI * f


def search_coil_output(n_turns, area_m2, f, b_rms):
    return search_coil_sensitivity(n_turns, area_m2, f) * b_rms


# ============================================================================
# MEASUREMENT UNCERTAINTY BUDGET  (GUM-style, combined in quadrature)
# ============================================================================
@dataclass
class UncertaintyTerm:
    label: str
    rel_pct: float          # standard uncertainty as % of reading
    kind: str               # 'A' (statistical) or 'B' (systematic)
    source: str


def combined_uncertainty(terms: List[UncertaintyTerm], k: float = 2.0):
    u = math.sqrt(sum(t.rel_pct ** 2 for t in terms))
    return dict(u_c_pct=u, U_expanded_pct=k * u, k=k, n_terms=len(terms))


def budget_internal_probe(f: float, b_rms: float, probe_n=200, probe_a=1e-4,
                          bw_hz=1.0):
    """
    Layer-3 internal water-side probe: an air-cored search coil in a sealed
    PVDF finger.  Its uncertainty is frequency dependent because the induced
    voltage falls as f falls.
    """
    v = search_coil_output(probe_n, probe_a, f, b_rms)
    # amplifier input noise 4 nV/rtHz over bw, plus 1/f corner at 10 Hz
    e_n = 4e-9 * math.sqrt(bw_hz) * math.sqrt(1 + 10.0 / max(f, 1e-3))
    snr_pct = 100.0 * e_n / v if v > 0 else 1e9
    terms = [
        UncertaintyTerm("coil area x turns (dimensional)", 0.30, "B", "CMM, E1 at cal"),
        UncertaintyTerm("Helmholtz calibration transfer", 0.50, "B", "accredited cal, E2"),
        UncertaintyTerm("integrator gain & phase", 0.40, "B", "swept cal"),
        UncertaintyTerm("ADC gain + INL", 0.15, "B", "24-bit sigma-delta"),
        UncertaintyTerm("probe position within ECV", 1.20, "B",
                        "from the computed dB/dx over +/-2 mm placement"),
        UncertaintyTerm("temperature drift 20 ppm/K x 15 K", 0.03, "B", "P0"),
        UncertaintyTerm("electronic noise / SNR", min(snr_pct, 50.0), "A", "computed"),
        UncertaintyTerm("repeatability (type A, n=10)", 0.30, "A", "to be measured E1"),
    ]
    return terms, combined_uncertainty(terms), v, snr_pct


def averaging_window(f: float, min_cycles: float = 30.0, min_s: float = 3.0) -> float:
    """
    Coherent averaging window for the B amplitude estimate.  At 3 Hz a 1 s
    window holds only 3 cycles, so the window must be frequency scaled or the
    +/-5 % requirement is not even well posed.
    """
    return max(min_s, min_cycles / max(f, 1e-6))


def control_error_budget(u_meas_pct: float, f: float, snr_linear: float,
                         plant_drift_pct: float = 3.0,
                         loop_gain_db: float = 40.0,
                         dac_bits: int = 16):
    """
    Total |B_meas - B_set|/B_set budget.

    Terms:
      * measurement uncertainty  U(k=2) from budget_internal_probe()
      * regulation residual = plant gain drift suppressed by the closed loop
      * demodulation error   = 1/(SNR*sqrt(2*N_cycles))
      * setpoint quantisation

    The dominant plant drifts (coil resistance with temperature, core
    permeability) are BOTH rejected: the inner loop is current controlled, and
    the magnetic circuit is 99.9 % air gap, so B/I is set by geometry.  Gap
    growth from thermal expansion over 20 K is ~0.02 %.
    """
    t_avg = averaging_window(f)
    n_cycles = f * t_avg
    reg = plant_drift_pct / (10 ** (loop_gain_db / 20.0))
    demod = 100.0 / (max(snr_linear, 1e-9) * math.sqrt(2 * max(n_cycles, 1.0)))
    quant = 100.0 / (2 ** dac_bits)
    gap_thermal = 0.024
    total = math.sqrt(u_meas_pct ** 2 + reg ** 2 + demod ** 2 + quant ** 2
                      + gap_thermal ** 2)
    return dict(u_meas_pct=u_meas_pct, regulation_pct=reg,
                demod_pct=demod, quantisation_pct=quant,
                gap_thermal_pct=gap_thermal, t_avg_s=t_avg,
                n_cycles=n_cycles, total_pct=total, meets_5pct=total <= 5.0)


# ============================================================================
# SHAM INTEGRITY  (Section 20)
# ============================================================================
def sham_detection_limit(probe_n=200, probe_a=1e-4, f=50.0, bw_hz=0.1,
                         e_n_v_rthz=4e-9):
    """
    Smallest B the Layer-3 probe can resolve at 3-sigma in the given
    bandwidth.  The Sham arm's residual field must be BELOW this AND below
    the geomagnetic reference, and both must be recorded.
    """
    s = search_coil_sensitivity(probe_n, probe_a, f)
    e_n = e_n_v_rthz * math.sqrt(bw_hz) * math.sqrt(1 + 10.0 / max(f, 1e-3))
    return 3.0 * e_n / s if s > 0 else float("inf")


def sham_residual_from_leakage(b_active: float, isolation_db: float) -> float:
    return b_active * 10 ** (-isolation_db / 20.0)


GEOMAGNETIC_T = 50e-6      # ~50 uT, P0 -- the natural DC background


# ============================================================================
# FIELD-MAP SAMPLING PLAN  (Section 13)
# ============================================================================
def mapping_plan(cv_target=0.10, cv_expected=0.0625, conf=0.95):
    """
    Number of map points needed to bound CV_B with the required confidence.
    Chi-square based interval on a standard deviation.
    """
    from math import sqrt
    # normal approximation to the chi-square CI half width on sigma: 1/sqrt(2(n-1))
    z = 1.96 if conf == 0.95 else 2.576
    n = 2
    while True:
        half = z / sqrt(2 * (n - 1))
        if cv_expected * (1 + half) <= cv_target or n > 5000:
            break
        n += 1
    return dict(n_points=n, cv_expected=cv_expected, cv_upper=cv_expected * (1 + z / sqrt(2 * (n - 1))),
                cv_target=cv_target, confidence=conf)
