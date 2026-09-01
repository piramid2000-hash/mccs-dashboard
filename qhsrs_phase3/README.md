# Q-HSRS Phase 3 — Instrumented ELF-MF Exposure Platform

Physics-based reverse engineering and verification package for a
3–3,000 Hz ELF-MF water-exposure system.

**This is a design and verification package, not a claim of effect.** Every
quantity carries an evidence tag (E1 / E2 / P0 / T / H). At the date of issue
**nothing is E1** — nothing has been built or measured. Every number in the
report is computed from first principles by the code in `design/` and is
reproducible.

## Headline results

| | |
|---|---|
| **Tank is unusable as a flux path above ~125 Hz** | SUS316L shell is a single-pole low-pass with f_c = 124.5 Hz; at 3 kHz \|H\| = −27.7 dB, and driving 1 mT *inside* would cost 367 kW of wall eddy loss |
| **Selected architecture** | R3 — 3 independent opposed C-core cells, dry, on a non-metallic PVDF duct; the 1,000 L tank is a reservoir outside the flux path |
| **Uniformity** | CV_B = 6.25 % over a 0.881 L Exposure Control Volume per cell (requirement ≤ 10 %) |
| **Control** | B tracking error 2.87 % RSS (requirement ≤ 5 %), dominated by probe positioning |
| **Envelope** | the entire dose ladder (0.5 / 1 / 5 / 10 / 50 mT) is reachable at every frequency 3–3,000 Hz with one set of hardware |
| **Power** | 20.7 W of real loss per cell at the worst corner; the 83.9 kVAr of circulating power is carried by a switched compensation bank, not the amplifier |
| **Dose** | t_exp = t_run · V_ECV / V_tank — **independent of flow rate**. This is why the dose campaign belongs at Stage 2 (50–100 L), not at 1,000 L |
| **CAPEX** | USD 473k budgetary; 29 % magnetics, 29 % instrumentation |

## Layout

```
design/           the physics engines — everything the report cites
  constants.py      materials, evidence tags, calibrated Steinmetz anchors
  magnetics.py      charge-sheet 3-D field engine + reluctance circuit
  tank_coupling.py  SUS316L shell transfer function H(f)
  coil_design.py    wire table, Dowell AC resistance, core loss
  architectures.py  R1 / R2 / R3 on a common basis
  optimize_geom.py  multi-objective geometry search (Pareto front)
  cell.py           the frozen exposure cell + hydraulics + dose
  system.py         electro-magneto-thermal solver + compensation bank
  thermal.py        separated heat sources and cooling paths
  metrology.py      sensors, GUM uncertainty budget, Sham detection limit
  doe.py            2^(7-3) resolution IV design, Bayesian sample size, H0-H3
  bom.py            pilot BOM and CAPEX
  run_all.py        master runner -> outputs/*.csv
figures/          16-figure patent-style package (SVG + PNG)
outputs/          computed CSV tables
report/           QHSRS_Phase3_Report.md (32 sections + Appendix A)
tests/            analytic-limit self-verification
```

## Reproduce

```bash
pip install numpy scipy matplotlib pandas
python3 tests/test_physics.py        # analytic limit checks — all must pass
python3 design/run_all.py            # regenerates outputs/*.csv
python3 figures/make_figures.py      # regenerates FIG01..FIG16
python3 report/make_report.py        # regenerates the report from live numbers
```

`tests/test_physics.py` validates the field primitive against the
infinite-sheet limit, the tank model against its own pole, all four core-loss
models against their published anchors, the reactive-power identity
Q = ωLI² = ωΦF and its invariance to turns count, the orthogonality and
resolution of the DOE, and the flow-independence of the dose identity.

## What this package deliberately does not do

It does not treat "quantum energy", "scalar waves" or "water memory" as design
variables; it does not assume a special effect at 7.83 Hz; it does not read a
¹H NMR linewidth change as a cluster-size change; and it does not respond to a
null result by raising the flux density. Those claims are carried as
hypotheses H-a…H-g and are tested, not designed for.
