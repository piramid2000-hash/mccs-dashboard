"""
Sections 21, 22, 23 — design of experiments, the hierarchical Bayesian model
and the H0-H3 discrimination plan.

The experiment is NOT designed to prove H3.  It is designed so that the
posterior can separate H0/H1/H2/H3.  That drives three structural choices:

  * every run has a Sham twin with identical hydraulics and identical pump
    heat, so H1 (thermal/mixing artifact) is a MEASURED contrast, not an
    assumption;
  * ion composition is a designed factor, not a nuisance, so H2 is estimable;
  * B enters at >= 4 levels so H3 (dose dependence) is separable from a
    binary on/off effect.
"""
import itertools
import math
from dataclasses import dataclass
from typing import List, Dict

import numpy as np


# ============================================================================
# FACTORS
# ============================================================================
@dataclass
class Factor:
    code: str
    name: str
    unit: str
    levels: list
    kind: str          # 'design' | 'held' | 'blocked' | 'nuisance'
    rationale: str


SCREENING_FACTORS = [
    Factor("A", "Magnetic flux density B_ECV", "mT", [0.0, 10.0], "design",
           "primary dose variable; Sham vs mid-ladder for screening"),
    Factor("B", "Frequency", "Hz", [7.83, 1000.0], "design",
           "two decades apart; no resonance assumed"),
    Factor("C", "Waveform", "-", ["sine", "square"], "design",
           "harmonic content changes dB/dt at equal B_rms"),
    Factor("D", "Ca2+ concentration", "mg/L", [10.0, 100.0], "design",
           "hardness cation, scaling-relevant"),
    Factor("E", "HCO3- concentration", "mg/L", [30.0, 250.0], "design",
           "carbonate buffer, controls pH stability"),
    Factor("F", "Conductivity (NaCl trim)", "uS/cm", [200.0, 2000.0], "design",
           "sets induced-current density at fixed B"),
    Factor("G", "Flow velocity", "m/s", [0.25, 1.0], "design",
           "residence time and mixing; confounder for H1"),
]

HELD_CONSTANT = [
    Factor("h1", "Water temperature", "degC", [20.0], "held", "20.0 +/- 0.3 K, chiller controlled"),
    Factor("h2", "Total batch volume", "L", [1000.0], "held", "level probe +/- 5 L"),
    Factor("h3", "Run duration", "h", [8.0], "held", "fixes cumulative dose per B level"),
    Factor("h4", "Dissolved O2 at t0", "mg/L", [8.5], "held", "sparged to a set point"),
    Factor("h5", "Tank / duct material lot", "-", ["lot-1"], "held", "removes surface chemistry drift"),
]

BLOCKS = ["day", "operator", "water_batch", "instrument_calibration_epoch"]

RESPONSES = [
    # (name, unit, instrument repeatability 1-sigma, delta_min of interest)
    ("Electrical conductivity", "uS/cm", 0.30, 1.0),       # sigma in % of reading
    ("pH", "-", 0.010, 0.05),
    ("ORP", "mV", 2.0, 10.0),
    ("Dissolved oxygen", "mg/L", 0.05, 0.20),
    ("Surface tension", "mN/m", 0.15, 0.50),
    ("Dynamic viscosity", "%", 0.25, 1.00),
    ("Zeta potential", "mV", 1.5, 4.0),
    ("Ca2+ (ICP-OES)", "%", 1.0, 3.0),
]

EXPLORATORY = [
    ("1H NMR linewidth (T2*)", "Hz",
     "EXPLORATORY ONLY. A linewidth change is NOT evidence of cluster size. "
     "Reported with temperature, shim quality and susceptibility controls."),
    ("Raman OH-stretch band decomposition", "cm-1",
     "EXPLORATORY. Band-shape changes are temperature sensitive at the same "
     "order as any expected effect."),
    ("FTIR-ATR", "a.u.", "EXPLORATORY. Surface film artifacts dominate."),
    ("DLS apparent size", "nm",
     "EXPLORATORY. In clean water DLS measures particulate contamination, "
     "not water structure."),
]


# ============================================================================
# FRACTIONAL FACTORIAL
# ============================================================================
def frac_fact_2_7_3():
    """
    2^(7-3) resolution IV design, 16 runs.
    Base factors A,B,C,D; generators  E = ABC,  F = BCD,  G = ACD.
    Defining relation  I = ABCE = BCDF = ACDG (shortest word length 4
    => main effects are clear of 2-factor interactions).
    """
    out = []
    for a, b, c, d in itertools.product((-1, 1), repeat=4):
        out.append(dict(A=a, B=b, C=c, D=d,
                        E=a * b * c, F=b * c * d, G=a * c * d))
    return out


def alias_structure(design):
    """Empirically detect confounded effect columns up to 2-factor interactions."""
    cols = "ABCDEFG"
    vecs = {}
    for c in cols:
        vecs[c] = np.array([r[c] for r in design])
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            vecs[cols[i] + cols[j]] = vecs[cols[i]] * vecs[cols[j]]
    keys = list(vecs)
    groups = {}
    for k in keys:
        sig = tuple(vecs[k])
        sig = min(sig, tuple(-x for x in sig))
        groups.setdefault(sig, []).append(k)
    return [g for g in groups.values() if len(g) > 1]


def d_optimality(design, cols="ABCDEFG"):
    X = np.column_stack([np.ones(len(design))] +
                        [np.array([r[c] for r in design], float) for c in cols])
    XtX = X.T @ X
    p = XtX.shape[0]
    return float(np.linalg.det(XtX) ** (1.0 / p) / len(design))


# ============================================================================
# BAYESIAN SAMPLE SIZE  (Section 22)
# ============================================================================
def posterior_power(delta_true, delta_min, sigma_within, sigma_batch,
                    n_per_arm, n_batches, n_sim=20000, cred=0.95, seed=7):
    """
    Hierarchical normal model:
        y_ijk = mu + tau*x_i + b_j + e_ijk
        b_j ~ N(0, sigma_batch^2),  e ~ N(0, sigma_within^2)

    Returns the probability that the posterior mass P(effect > delta_min|data)
    exceeds `cred`, i.e. the Bayesian analogue of power.
    """
    rng = np.random.default_rng(seed)
    se = math.sqrt(2 * sigma_within ** 2 / n_per_arm +
                   2 * sigma_batch ** 2 / max(n_batches, 1))
    # flat prior on the effect => posterior N(effect_hat, se^2)
    hats = rng.normal(delta_true, se, n_sim)
    from math import erf, sqrt
    z = (hats - delta_min) / se
    post = 0.5 * (1 + np.vectorize(lambda t: erf(t / sqrt(2)))(z))
    return dict(se=se, power=float(np.mean(post > cred)),
                mean_post=float(np.mean(post)))


def required_n(delta_true, delta_min, sigma_within, sigma_batch,
               n_batches=4, target_power=0.90, n_max=400):
    for n in range(2, n_max + 1):
        r = posterior_power(delta_true, delta_min, sigma_within, sigma_batch,
                            n, n_batches, n_sim=4000)
        if r["power"] >= target_power:
            return n, r
    return None, None


# ============================================================================
# H0-H3 DISCRIMINATION
# ============================================================================
HYPOTHESES = {
    "H0": dict(
        statement="ELF-MF produces no measurable change in water properties.",
        signature="No credible B main effect at any level; Sham and Active "
                  "posteriors overlap within delta_min.",
        discriminator="Requires that the Sham arm be instrumented identically. "
                      "Evidence FOR H0 is a narrow posterior around zero, not "
                      "a non-significant p-value."),
    "H1": dict(
        statement="An effect exists but is a thermal or mixing artifact.",
        signature="Effect tracks P_pump and delta-T, not B; disappears when "
                  "the Sham arm is run with matched pump duty.",
        discriminator="Pump heat (computed ~524 W at 0.5 m/s) is ~25x the "
                      "field-coupled water heating (~20 W at the 50 mT/3 kHz "
                      "corner), so the Sham MUST run the pump identically. "
                      "Flow is a designed factor (G) so this is estimable."),
    "H2": dict(
        statement="An effect exists and is ion-specific.",
        signature="Credible B x D, B x E or B x F interactions with a null "
                  "or much smaller B main effect in low-conductivity water.",
        discriminator="Conductivity is factor F precisely because the induced "
                      "electric field E = pi*f*B*r drives a current density "
                      "J = sigma*E. If the effect scales with sigma it is "
                      "electrochemical, not 'magnetic'."),
    "H3": dict(
        statement="An effect exists and depends on magnetic dose.",
        signature="Monotone, credible dose-response across >=4 B levels at "
                  "fixed f, chemistry, flow and temperature.",
        discriminator="Requires the dose ladder, not a single B level. "
                      "Distinguishing H3 from H2 requires B and sigma to be "
                      "varied independently, which the design does."),
}
