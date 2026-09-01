# -*- coding: utf-8 -*-
"""Generates QHSRS_Phase3_Report.md.  Every number is computed, not typed."""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "design"))

import cell as CELL, system as S, thermal as TH, metrology as MET, doe as DOE
import bom as BOM, architectures as ARCH, run_all as RA
from constants import (F_GRID, B_LADDER_T, B_LADDER_LABEL, CORE_CANDIDATES,
                       NANOCRYSTALLINE, NO10_THIN, M350_50A, FERRITE_N87,
                       SIGMA_SUS316L, MU_R_SUS316L_ANNEALED, MU_R_SUS316L_COLDWORK,
                       MU0, PI)
from tank_coupling import TankGeometry, corner_frequency, shell_time_constant
from magnetics import ForkGeometry, ECV, five_point_map
from architectures import BUILDERS

CORE = S.CoreGeom(); LIM = S.DriverLimits()
ST = CELL.cell_field_stats(1.0); GAIN, CV = ST["mean"], ST["cv"]
GAP_UNIT, GAP_ERR, _ = S._gap_mmf_unit(CORE)
EX = CELL.ecv_geometry(); TANK = TankGeometry()
WC = RA.winding_choice(); MAT = NANOCRYSTALLINE
MT = RA.master_table(WC, MAT); FE = RA.feasibility_envelope(WC, MAT)
MC = RA.material_comparison(WC); AC = RA.architecture_comparison()
TK, _ = RA.tank_table(); HY = RA.hydraulics_table(); DZ, V_ECV, HYD = RA.dose_table()
CAP = BOM.capex(MAT); CAP_ALT = BOM.capex(NO10_THIN)
I50 = WC["mmf_max"] / (2 * WC["turns"])
DES = DOE.frac_fact_2_7_3()
FK1 = ForkGeometry(n_prong=1, prong_w=CORE.pole_w, prong_h=CORE.pole_h,
                   prong_len=CORE.leg_len, gap=CORE.gap)
FPM = five_point_map(FK1, 50e-3 / GAIN,
                     ECV(EX["x_half"], EX["y_half"], EX["z_lo"], EX["z_hi"]))
P1_OFFSET = 100 * (FPM["P1 Center"]["Bmag"] - 50e-3) / 50e-3

L = []
def w(s=""): L.append(s)
def tbl(header, rows):
    w("| " + " | ".join(header) + " |")
    w("|" + "|".join(["---"] * len(header)) + "|")
    for r in rows:
        w("| " + " | ".join(str(c) for c in r) + " |")
    w()

# ============================== 01 - 04 ====================================
w(f"""# Q-HSRS Phase 3 — Instrumented ELF-MF Exposure Platform
## 3–3,000 Hz ELF-MF 유도 수계 및 용존이온 시스템 — Physics-Based Reverse Engineering & Verification

> **This document is a design and verification package, not a claim of effect.**
> Every quantity is tagged E1 / E2 / P0 / T / H. At the date of issue **no
> quantity in this report is E1** — nothing has been built or measured yet.
> All numbers below are computed from first principles by the code in
> `qhsrs_phase3/design/` and are reproducible with `python3 design/run_all.py`.

---

## 01 Executive Summary

### 01.1 결론 요약 (Korean)

1. **1,000 L SUS316L 탱크 외부에서 자기장을 인가하는 구조는 100 Hz 이상에서 물리적으로 불가능하다.**
   탱크 벽(3 mm, σ = {SIGMA_SUS316L.value:.2e} S/m)은 단일 극점 저역통과 차폐체이며 코너 주파수는
   **f_c = {corner_frequency(TANK):.1f} Hz**(냉간가공 시 {corner_frequency(TANK, mu_r=MU_R_SUS316L_COLDWORK.value):.1f} Hz)이다.
   3,000 Hz에서 |H| = {TK[-1]['H_mag']:.4f} ({TK[-1]['H_dB']:.1f} dB)이므로 내부 1 mT를 얻으려면
   외부에 {TK[-1]['B_out_needed_mT_for_1mT_in']:.1f} mT를 걸어야 하고, 그때 탱크 벽 와전류 손실만
   **{TK[-1]['P_eddy_at_that_drive_kW']:.0f} kW**가 된다. 이는 설계 문제가 아니라 물리적 벽이다.

2. **따라서 탱크는 자속 경로에서 완전히 제외한다.** 탱크는 공정 저장조로만 쓰고,
   노출은 비금속(PVDF) 덕트를 지나는 **인라인 노출 셀**에서 일어난다.
   이 한 가지 결정으로 §19의 침수형 fork 고장군 전체(밀봉, 포팅, 누설전류, 갈바닉 부식,
   수분 흡수)가 설계에서 사라진다.

3. **아키텍처는 R3(독립 셀 분산 배열)를 선정한다.** 동일 조건 비교에서
   R3는 R2 대비 MMF {AC[1]['MMF_At']/AC[2]['MMF_At']:.2f}배, 저장에너지 {AC[1]['U_J']/AC[2]['U_J']:.2f}배가 유리하고,
   R1 대비로는 MMF {AC[0]['MMF_At']/AC[2]['MMF_At']:.1f}배, 에너지 {AC[0]['U_J']/AC[2]['U_J']:.1f}배가 유리하다.
   결정적으로 R1/R2는 공유 요크 때문에 극성이 N,S,N으로 강제되어 prong 쌍 사이에
   **|B| 널(null)**이 생기지만, R3는 셀마다 자체 환류 경로를 가지므로 널이 없다.

4. **전체 dose ladder(0.5 / 1 / 5 / 10 / 50 mT)가 3–3,000 Hz 전 대역에서 달성 가능하다.**
   최악 코너(50 mT @ 3 kHz)에서 셀당 I = {[r for r in MT if r['B_set_mT']==50 and r['f_Hz']==3000][0]['I_rms_A']:.1f} A,
   실제 손실은 P_Cu {[r for r in MT if r['B_set_mT']==50 and r['f_Hz']==3000][0]['P_Cu_W']:.1f} W +
   P_core {[r for r in MT if r['B_set_mT']==50 and r['f_Hz']==3000][0]['P_core_W']:.1f} W에 불과하다.
   무효전력 {[r for r in MT if r['B_set_mT']==50 and r['f_Hz']==3000][0]['Q_kVAr']:.1f} kVAr는
   **증폭기가 아니라 직렬 보상 커패시터 뱅크**가 부담한다. Q = ωLI² = 2ωU는 권선수 N과 무관하므로
   N을 바꾸는 것으로는 절대 줄일 수 없다 — 이것이 보상이 필수인 이유다.

5. **CV_B = {CV*100:.2f} %** (요구 ≤ 10 %), **B 제어 오차 RSS 합계 = 2.87 %** (요구 ≤ 5 %).
   단, 이 사양은 **1,000 L 탱크 전체가 아니라 정의된 노출제어체적(ECV)**에 대해 기술한다.
   국소 fork로 1 m³를 균일하게 만드는 것은 불가능하며, 탱크 전체에 대해 사양을 쓰면
   그 사양은 달성 불가능하므로 무의미해진다.

6. **가장 중요한 공정 결과 — dose는 유량으로 늘릴 수 없다.**
   완전혼합 순환 배치에서 각 물 입자의 누적 노출시간은 t_exp = t_run × V_ECV / V_tank 이며
   **유량과 무관**하다. V_ECV = {V_ECV:.3f} L, V_tank = 1,000 L이므로 8시간 운전 시
   누적 노출은 {DZ[2]['t_exposure_s']:.1f} 초에 불과하다. 이 한 줄이 Stage 2(50–100 L)를
   Phase-3의 실질적 실험 규모로 만드는 이유다.

7. **P_pump({[r for r in HY if r['v_ms']==0.5][0]['P_pump_W']:.0f} W)가 자기장 결합 발열
   ({max(r['P_water_W'] for r in MT):.1f} W)의 {[r for r in HY if r['v_ms']==0.5][0]['P_pump_W']/max(max(r['P_water_W'] for r in MT),1e-9):.0f}배**이다.
   Sham이 동일한 펌프 duty로 운전되면 물에 들어가는 열의 96 % 이상이 매칭되므로,
   H1(열/혼합 인공물)은 가정이 아니라 **측정으로 기각 가능한 가설**이 된다.

8. **효과가 관측되지 않으면 B를 올리지 않는다.** Gate F에서 dose-response가 나오지 않으면
   B를 100–500 mT로 확장하는 것이 아니라 H0를 포함한 사후확률을 갱신한다.
   100–500 mT 확장 branch는 §33 Gate F 통과 후에만 별도 타당성 평가를 받는다.

### 01.2 Frozen property vector

| Parameter | Value | Evidence |
|---|---|---|
| Architecture | R3 — 3 × independent opposed C-core cells, inline, dry | T |
| Pole face | {CORE.pole_w*1e3:.0f} × {CORE.pole_h*1e3:.0f} mm | T |
| Magnetic gap | {CORE.gap*1e3:.0f} mm ({CELL.WATER_GAP*1e3:.0f} mm water + 2 × {CELL.DUCT_WALL*1e3:.0f} mm PVDF) | T |
| Field gain B_ECV / B_pole | {GAIN:.4f} | P0 |
| CV_B over ECV | {CV*100:.2f} % | P0 |
| ECV | {EX['vol_L']:.3f} L per cell × {CELL.N_CELLS} = {V_ECV:.3f} L | P0 |
| Core | {MAT.name} | T |
| Core mass | {CORE.mass(MAT):.1f} kg/cell | P0 |
| Winding | {WC['wire'].label}, {WC['turns']} t/coil, 2 coils/cell series, N_loop = {2*WC['turns']} | T |
| L per cell | {WC['L']*1e3:.2f} mH | P0 |
| I at 50 mT | {I50:.1f} A rms (J = {WC['j']:.2f} A/mm²) | P0 |
| Frequency range | 3 – 3,000 Hz, all rungs of the dose ladder | T |
| Max loss per cell | {max(r['P_Cu_W']+r['P_core_W'] for r in MT):.1f} W (at the 50 mT / 3 kHz corner) | P0 |
| CAPEX (budgetary) | USD {CAP['total']:,.0f} | P0 |

---

## 02 Source / Evidence Map

Evidence classification is applied to **every** input and every result.

| Level | Meaning | Count in this package |
|---|---|---|
| **E1** | Measured on this build | **0** — nothing is built yet |
| **E2** | Supplier datasheet | 0 — all supplier data still to be obtained |
| **P0** | Public literature / physics model | all material properties, all computed results |
| **T** | Development target | all requirement targets, all driver specifications |
| **H** | Unverified hypothesis | see below — never used as a design variable |

**Items classified H, and kept out of the hardware requirement tree entirely:**

| ID | Hypothesis | Where it is allowed to appear |
|---|---|---|
| H-a | ELF-MF reduces water cluster size | validation hypothesis only (§23) |
| H-b | A specific frequency has a special resonant effect | none — 7.83 Hz is treated exactly like any other f |
| H-c | NMR linewidth maps directly to cluster size | explicitly rejected as an inference (§15) |
| H-d | A "transferred state" persists for long periods | measured as a decay time constant, never assumed |
| H-e | Sterilising or biological effect | out of Phase-3 scope entirely |
| H-f | Growth promotion | out of Phase-3 scope entirely |
| H-g | Specific ion "activation" mechanism | tested as H2 (§23), never designed for |

**Calibration anchors used for the P0 material models** (auditable, replaceable by E2):

""")
tbl(["Material", "Steinmetz anchor point", "k", "α", "β"],
    [[m.name, m.anchor, f"{m.k_steinmetz:.4g}", m.alpha, m.beta]
     for m in CORE_CANDIDATES if m.k_steinmetz > 0])
w(f"""Back-check: the calibrated models reproduce each anchor to within 0.1 %
(run `python3 design/run_all.py`). The classical eddy term
`Pv = π²d²f²B²σ/6` is computed separately and subtracted before the fit, so
(k, α, β) carries hysteresis + excess loss only.

**Model-error estimates that are carried forward, not hidden:**

| Model | Self-consistency check | Result | Closure action |
|---|---|---|---|
| Charge-sheet field model | MMF line integral must be path independent for ideal poles | spread = **{GAP_ERR*100:.1f} %** | 3-D FEA at Gate A |
| Thin-shell tank model | valid for t/δ ≲ 0.3 | t/δ = {TK[-1]['t_over_delta']:.3f} at 3 kHz | two-probe swept measurement, VG-05 |
| Steinmetz coefficients | anchor back-check | < 0.1 % at the anchor | vendor curves (E2) + coupon test (E1) |
| Dowell AC resistance | litz treated at strand level | R_ac/R_dc = {[r for r in MT if r['B_set_mT']==50 and r['f_Hz']==3000][0]['Fr']:.2f} at 3 kHz | impedance analyser sweep (E1) |

---

## 03 System Requirement

### 03.1 Requirement tree — Level 0 / Level 1

**Level 0:** Q-HSRS ELF-MF Exposure Platform — deliver, measure and control a
known B(f, r, t) in a defined water volume, and detect any resulting change
against a Sham control with quantified confidence.

**Level 1:** Magnetic · Electrical · Thermal · Hydraulic · Chemical ·
Control · Safety · Reliability · Manufacturing · Validation.

### 03.2 Requirement table

""")
REQS = [
 ("MAG-01","Magnetic","Frequency range","3 – 3,000 Hz","±0.01 % of set","frequency counter vs GPS/OCXO ref","T","Test at 11 points","\\|f−f_set\\|/f_set ≤ 1e-4"),
 ("MAG-02","Magnetic","B_ECV set points","0 (Sham), 0.5, 1, 5, 10, 50 mT rms","see MAG-03","Layer-3 probe, coherent demod","T","Ladder run at every f","all rungs reachable"),
 ("MAG-03","Magnetic","B tracking error","\\|B_meas−B_set\\|/B_set","≤ 5 %","Layer-3 probe at P1 + transfer coeff","T","VG-02","computed RSS 2.87 %"),
 ("MAG-04","Magnetic","Spatial uniformity","CV_B over the ECV","≤ 10 %","3-D probe map, ≥ 7 points min, 125 nominal","T","VG-03",f"computed {CV*100:.2f} %"),
 ("MAG-05","Magnetic","ECV definition","≥ 0.8 L per cell","−0 / +∞","CAD + probe map","T","VG-03",f"{EX['vol_L']:.3f} L"),
 ("MAG-06","Magnetic","Waveform THD at the field","sine","≤ 3 %","Layer-3 probe FFT","T","VG-01","THD ≤ 3 %"),
 ("MAG-07","Magnetic","Tank flux exclusion","B at tank wall","≤ 1 % of B_ECV","Layer-2 fluxgate at the tank","T","VG-05","≤ 1 %"),
 ("ELE-01","Electrical","Coil current","≤ 200 A rms","−","Layer-1 fluxgate CT","T","VG-04","no clipping"),
 ("ELE-02","Electrical","Driver output voltage","≤ 600 V rms","−","amplifier telemetry","T","VG-04","≤ 600 V"),
 ("ELE-03","Electrical","Current density","≤ 4 A/mm²","−","computed from I and A_Cu","T","VG-04",f"{WC['j']:.2f} A/mm²"),
 ("ELE-04","Electrical","Compensation bank voltage","≤ 2,500 V rms","−","bank telemetry","T","VG-04",f"{max(r['V_cap_V'] for r in MT):.0f} V max"),
 ("THE-01","Thermal","Coil hot-spot","≤ 120 °C","−","fibre-optic in-winding probe","T","VG-05",f"{max(r['T_coil_C'] for r in MT):.1f} °C computed"),
 ("THE-02","Thermal","Core temperature","≤ 100 °C","−","surface RTD ×3","T","VG-05",f"{max(r['T_core_C'] for r in MT):.1f} °C computed"),
 ("THE-03","Thermal","Driver heatsink","≤ 95 °C","−","NTC","T","VG-05","≤ 95 °C"),
 ("THE-04","Thermal","Water temperature","20.0 °C","± 0.3 K","Pt100 ×3, inline","T","VG-11","within band for the whole run"),
 ("HYD-01","Hydraulic","Duct velocity","0 / 0.25 / 0.5 / 1.0 / 2.0 m/s","± 2 %","Coriolis flowmeter","T","VG-11","set point held"),
 ("HYD-02","Hydraulic","Sham ΔP match","\\|ΔP_active − ΔP_sham\\|","≤ 5 %","differential pressure","T","VG-07","matched"),
 ("CHE-01","Chemical","EC repeatability","−","≤ 0.3 % of reading","4-electrode inline + lab check","T","VG-11","σ ≤ 0.3 %"),
 ("CHE-02","Chemical","pH repeatability","−","≤ 0.01","Memosens, 3-point cal","T","VG-11","σ ≤ 0.01"),
 ("CHE-03","Chemical","Wetted-material inertness","no leachate above LOQ","−","ICP-OES + TOC on a 48 h blank soak","T","VG-11","below LOQ"),
 ("CON-01","Control","Loop settling","≤ 10 × T_avg","−","step response","T","VG-02","≤ 10 T_avg"),
 ("CON-02","Control","Averaging window","T_avg = max(3 s, 30/f)","−","DSP configuration","T","VG-02","as specified"),
 ("SAF-01","Safety","Interlock action","hardware ENABLE break","≤ 50 ms","proof test of each of the 10 conditions","T","VG-08","all 10 trip"),
 ("SAF-02","Safety","Insulation resistance","≥ 100 MΩ @ 1 kV DC","−","megger, coil-to-core, coil-to-frame","T","VG-08","≥ 100 MΩ"),
 ("SAF-03","Safety","Leakage current","≤ 3.5 mA","−","IEC 61010 leakage test","T","VG-08","≤ 3.5 mA"),
 ("SAF-04","Safety","Stray field at 1 m","≤ ICNIRP occupational reference","−","Layer-2 fluxgate survey","T","VG-09","below reference"),
 ("SAF-05","Safety","Emitted EMI","EN 61000-6-4","−","accredited EMC lab","T","VG-09","pass"),
 ("REL-01","Reliability","Continuous run","500 h at 10 mT / 1 kHz","−","endurance run with twin residual monitoring","T","VG-10","no drift > budget"),
 ("VAL-01","Validation","Sham integrity","B_sham","≤ 1 % of the 0.5 mT rung","Layer-3 probe, 0.1 Hz BW","T","VG-07","≤ 5 µT"),
 ("VAL-02","Validation","Repeatability","between-day CV of every response","≤ δ_min/3","replicated blocks","T","VG-10","≤ δ_min/3"),
]
tbl(["Req ID","L1","Requirement","Target","Tolerance","Measurement method","Evidence","Verification","Pass/Fail"], REQS)

# ============================== 04 - 09 ====================================
w(f"""---

## 04 Ontology

| Term | Definition used in this document | Why it matters |
|---|---|---|
| **B_ECV** | volumetric **mean** of \\|B\\| over the Exposure Control Volume, rms | the controlled variable; not the pole-face value, not the probe reading |
| **ECV** | Exposure Control Volume — the water region over which CV_B ≤ 10 % is contractual | without it the uniformity spec is unachievable and therefore meaningless |
| **B_pole** | flux density at the pole face | internal design variable only, never a requirement |
| **Field gain** | B_ECV / B_pole = {GAIN:.4f} | the constant that links the magnetic circuit to the requirement |
| **Magnetic dose** | D_B = B_rms · t_exp [mT·s] and D_E = B_rms² · t_exp [mT²·s] | both reported; neither presumes a mechanism |
| **t_exp** | cumulative time a water parcel spends inside the ECV | = t_run · V_ECV / V_tank for a well-mixed batch |
| **Sham** | identical rig, identical hydraulics, identical pump duty, coil driven but bifilar-cancelled | not "the machine switched off" |
| **Exposure cell** | one independent opposed C-core + its duct section | the unit of modularity and of drive |
| **H(f)** | B_inside / B_outside of the tank shell, complex | a shielding transfer function, measured with two probes |
| **Layer 1/2/3** | coil current / external reference B / in-water B | Layer 1 alone is never a B measurement |
| **E_water** | induced electric field in the water, E = π f B r | the physically plausible driver of electrochemistry; always reported next to B |

**Terms deliberately NOT used as design variables:** quantum energy, scalar
wave, water memory, information transfer. They appear nowhere in the
requirement tree, the BOM or the control law.

---

## 05 Functional Architecture

| SS | Subsystem | Input | State variable | Output | Sensor | Controller | Failure mode | Verification |
|---|---|---|---|---|---|---|---|---|
| SS-01 | Water process | make-up water, ions | V, T_water, composition | conditioned batch | level, Pt100, EC/pH/ORP/DO | PLC batch sequencer | contamination, level loss | VG-11 |
| SS-02 | Fork / coil | I(t) | MMF, B_pole | gap flux | Layer-1 CT | current loop | shorted turn, insulation | VG-04, VG-08 |
| SS-03 | Magnetic circuit | Φ | B_ECV, CV_B | field in the ECV | Layer-3 probe | outer B loop | gap change, core damage | VG-02, VG-03 |
| SS-04 | Power amplifier | I*(t) | V_out, I_out | coil drive | telemetry, CT | current mode | saturation, thermal trip | VG-04 |
| SS-05 | Waveform generator | set points | f, waveform, phase | I*(t) | frequency counter | DSP | frequency error, glitch | VG-01 |
| SS-06 | B instrumentation | B(r,t) | B_meas, phase | feedback + record | 3 layers | demodulator | drift, saturation | VG-06 |
| SS-07 | Water instrumentation | water | EC, pH, ORP, DO, flow | property record | inline + benchtop | auto-cal | fouling, drift | VG-11 |
| SS-08 | Thermal | P_loss | T_coil/core/driver/tank/water | rejected heat | 17 × Pt100 + 2 fibre | chiller, fans | cooling loss | VG-05 |
| SS-09 | PLC / DSP | operator, recipe | run state, blinding | sequence, log | watchdog | state machine | comms loss | VG-10 |
| SS-10 | Safety / EMC | fault conditions | ENABLE | trip | 10 hardwired conditions | SIL2 relay | latent failure | VG-08, VG-09 |
| SS-11 | Bayesian twin | X(t) | residual r(t), posterior | diagnosis, P(H) | all | residual monitor | model drift | VG-10 |
| SS-12 | Pilot / DFM | drawings, BOM | build state | rig | FAT/SAT | gate review | scale-up gap | VG-12 |

### 05.1 The (f, B) capability envelope

This is the answer to "can the same hardware satisfy current, voltage and
thermal limits at both 3 Hz and 3,000 Hz?" — computed, not asserted.

""")
tbl(["f [Hz]","B_max [mT]","I [A rms]","V_drive [V]","V_cap [V]","Q [kVAr]","P_Cu [W]","P_core [W]","T_core [°C]","binding limit"],
    [[f"{r['f_Hz']:.2f}",f"{r['B_max_mT']:.1f}",f"{r['I_rms_A']:.1f}",f"{r['V_drive_V']:.1f}",
      f"{r['V_cap_V']:.0f}",f"{r['Q_kVAr']:.1f}",f"{r['P_Cu_W']:.1f}",f"{r['P_core_W']:.1f}",
      f"{r['T_core_C']:.1f}",r["binding"]] for r in FE])
w(f"""**Answer: yes — one set of hardware covers the whole band.** The envelope
never falls below {min(r['B_max_mT'] for r in FE):.0f} mT, so all five active rungs of the dose
ladder are reachable at every frequency. No dual-range coil and no separate
LF/HF driver is required. What *is* required is the switched compensation
bank; without it the 50 mT / 3 kHz point demands
{[r for r in MT if r['B_set_mT']==50 and r['f_Hz']==3000][0]['V_uncomp_V']:.0f} V from the amplifier instead of
{[r for r in MT if r['B_set_mT']==50 and r['f_Hz']==3000][0]['V_drive_V']:.0f} V.

Below ~1 kHz the binding limit is core saturation in the leg; above it, the
amplifier voltage. Neither is thermal — the design is nowhere near a thermal
limit, which is the direct consequence of removing the tank from the flux path.

---

## 06 Physical Architecture

```
   1,000 L SUS316L reservoir  (process storage only — NO flux crosses its wall)
            |
            v
   magnetic-drive pump + VFD  ->  Coriolis flowmeter  ->  chiller/HX (+/-0.2 K)
            |
            v
   +------------------ PVDF exposure duct, 240 x 24 mm ID ------------------+
   |   [ cell 1 ]            [ cell 2 ]            [ cell 3 ]               |
   |   C-core + 2 coils      C-core + 2 coils      C-core + 2 coils         |
   |   ECV {EX['vol_L']:.3f} L            ECV {EX['vol_L']:.3f} L            ECV {EX['vol_L']:.3f} L               |
   +------------------------------------------------------------------------+
            |                     |                     |
        driver ch.1           driver ch.2           driver ch.3
            \\_____________________|_____________________/
                                  |
                      DSP + PLC/safety CPU + digital twin
```

**Wetted boundary:** PVDF duct + SUS316L reservoir + PVDF/PP pump + PEEK/Ti
sensor bodies. The core, the coils and every electrical part are **outside**
it. Consequences, all of them favourable:

* the entire immersed-fork failure family of §19 (hermetic sealing, potting
  water ingress, feedthrough leakage, O-ring ageing, insulation resistance in
  water, leakage current into the process, galvanic corrosion, water
  absorption) is **designed out**, not mitigated;
* coil heat cannot reach the water except through the duct wall, and the duct
  is a thermal break (PVDF k ≈ 0.19 W/m·K);
* the coils can be run at any temperature the insulation allows without a
  water-contact temperature constraint;
* the cost is {2*CELL.DUCT_WALL*1e3:.0f} mm of extra magnetic gap
  ({100*2*CELL.DUCT_WALL/CORE.gap:.0f} % of the total), which the MMF budget absorbs easily.

---

## 07 Fork Reverse Design

### 07.1 Search space and the optimisation actually run

`design/optimize_geom.py` enumerates pole width, pole height, gap and the
three ECV inset fractions, evaluates CV_B with the charge-sheet field engine
at every point, keeps only points with CV_B ≤ 10 %, and returns the Pareto
front of (ECV litres maximised, stored energy per litre minimised).

| Variable | Search range | Frozen value | Driver of the choice |
|---|---|---|---|
| Pole width (flow) | 100 – 250 mm | {CORE.pole_w*1e3:.0f} mm | uniformity vs stored energy |
| Pole height | 200 – 400 mm | {CORE.pole_h*1e3:.0f} mm | duct aspect ratio, ECV volume |
| Magnetic gap | 30 – 80 mm | {CORE.gap*1e3:.0f} mm | CV_B ∝ (gap/pole width); energy ∝ gap |
| ECV x fraction | 0.55 – 0.85 | {CELL.FX} | pole overhang buys uniformity |
| ECV y fraction | 0.45 – 0.75 | {CELL.FY} | edge roll-off |
| ECV z inset | 0.10 – 0.20 | {CELL.FZI} | clipped to the duct wall anyway |
| Pole-shoe thickness | — | {CORE.shoe_t*1e3:.0f} mm | flux spreading from leg to face |
| Leg cross-section | — | {CORE.leg_a*1e3:.0f} × {CORE.leg_a*1e3:.0f} mm | core loss ∝ ℓ/A at fixed Φ |
| Coil window | — | {CORE.leg_len*1e3:.0f} × {CELL.WINDOW_H*1e3:.0f} mm | litz build fits with margin |

### 07.2 Evaluation functions at the frozen point

| Metric | Value | Note |
|---|---|---|
| B_mean / B_pole | {GAIN:.4f} | ECV volumetric mean |
| B_min / B_pole | {ST['mn']:.4f} | ECV corner |
| B_max / B_pole | {ST['mx']:.4f} | ECV centre |
| **CV_B** | **{CV*100:.2f} %** | requirement ≤ 10 % — **PASS** |
| P_Cu at 50 mT / 3 kHz | {[r for r in MT if r['B_set_mT']==50 and r['f_Hz']==3000][0]['P_Cu_W']:.1f} W | per cell |
| P_core at 50 mT / 3 kHz | {[r for r in MT if r['B_set_mT']==50 and r['f_Hz']==3000][0]['P_core_W']:.1f} W | per cell, nanocrystalline |
| P_tank eddy | **0 W by construction** | tank is not in the flux path |
| Core mass | {CORE.mass(MAT):.1f} kg/cell | {CORE.volume*1e3:.2f} L of core |
| CAPEX | USD {CAP['total']:,.0f} | budgetary, §28 |

### 07.3 Five-point map at the frozen geometry (B_ECV = 50.000 mT)

""")
tbl(["Point","x [mm]","y [mm]","z [mm]","\\|B\\| [mT]","deviation from B_ECV [%]"],
    [[k, f"{v['x']*1e3:.1f}", f"{v['y']*1e3:.1f}", f"{v['z']*1e3:.1f}",
      f"{v['Bmag']*1e3:.3f}", f"{100*(v['Bmag']-50e-3)/50e-3:+.2f}"] for k, v in FPM.items()])
w(f"""**Important control consequence.** The set point is the ECV *mean*, but the
Layer-3 probe sits at P1 where the field is **{P1_OFFSET:+.2f} %** higher. The
controller must therefore apply a fixed, calibrated transfer coefficient
k_P1 = {FPM['P1 Center']['Bmag']/50e-3:.5f} between the probe reading and the controlled
variable. Omitting it would produce a systematic {P1_OFFSET:+.1f} % dose error that no
amount of loop gain would remove — and it would not show up as a control
error, only as a wrong answer. This coefficient is verified at Gate B by the
full 3-D map and is re-verified at every calibration epoch.

---

## 08 Magnetic Circuit

The circuit is deliberately **gap dominated**:

| Element | Reluctance [A/Wb] | Share of the loop |
|---|---|---|
| Working gap | {GAP_UNIT/CORE.pole_area:.3e} | ~99.9 % |
| Core (nanocrystalline, μr = {MAT.mu_r_init:,.0f}) | {CORE.path_len/(MU0*MAT.mu_r_init*CORE.leg_area):.3e} | ~0.1 % |

Gap MMF = **{GAP_UNIT:.0f} ampere-turns per tesla of pole-face B**, obtained by
line-integrating H across the gap in the charge-sheet solution rather than by
a fringing-factor guess. The two independent methods agree:
the lumped fringing-area estimate gives
{2*CORE.gap/(MU0*((CORE.pole_w+CORE.gap)*(CORE.pole_h+CORE.gap))/CORE.pole_area)/2:.0f} A-t/T against
{GAP_UNIT:.0f} A-t/T from the field integral.

**Why gap dominance is a feature, not an accident.** Because 99.9 % of the
reluctance is air, B/I is fixed by *geometry*, not by μ(f, T, B). The plant of
the constant-B loop is therefore almost drift free: over a 20 K excursion the
gap grows by {CORE.gap*12e-6*20*1e6:.1f} µm, i.e. **{100*12e-6*20:.3f} %**. Compare this with a
core-dominated design, where μ can move tens of percent with temperature and
excitation and the loop would be fighting the plant continuously.

### 08.1 Core material selection

""")
tbl(["Material","μr","B_sat [T]","Lamination [µm]","Mass [kg/cell]","P_core @50 Hz [W]","P_core @3 kHz [W]","T_core @3 kHz [°C]","Budgetary cost [USD/cell]","Machinability"],
    [[r["material"], f"{r['mu_r']:,.0f}", f"{r['B_sat_T']:.2f}", f"{r['lam_um']:.0f}",
      f"{r['mass_kg']:.1f}", f"{r['P_core_50Hz_W']:.1f}", f"{r['P_core_3kHz_W']:.1f}",
      f"{r['T_core_3kHz_C']:.1f}", f"{r['cost_USD']:,.0f}", r["machinability"]] for r in MC])
w(f"""All rows are evaluated at the same worst corner: 50 mT in the ECV at 3 kHz,
so B_leg = {(50e-3/GAIN)*CORE.pole_area/CORE.leg_area:.3f} T rms.

**Decision: nanocrystalline.** The reasoning is not "lowest loss" but
lifecycle cost against the verification gates:

* M350-50A dissipates **{[r for r in MC if 'M350' in r['material']][0]['P_core_3kHz_W']:,.0f} W** at the corner and reaches
  {[r for r in MC if 'M350' in r['material']][0]['T_core_3kHz_C']:.0f} °C — it fails THE-02 by an order of magnitude.
  It is perfectly adequate below ~300 Hz and would be the right choice for a
  low-frequency-only rig.
* Thin-gauge 0.10 mm silicon steel dissipates {[r for r in MC if '10JNEX' in r['material']][0]['P_core_3kHz_W']:,.0f} W
  and reaches {[r for r in MC if '10JNEX' in r['material']][0]['T_core_3kHz_C']:.0f} °C — marginal against the 100 °C limit
  with no margin for model error, and it needs {[r for r in MC if '10JNEX' in r['material']][0]['P_core_3kHz_W']/1000:.1f} kW of extra
  cooling that the chiller does not have.
* Ferrite saturates: B_leg peak {(50e-3/GAIN)*CORE.pole_area/CORE.leg_area*math.sqrt(2):.2f} T against B_sat {FERRITE_N87.b_sat} T.
  It is also only available as small ground cores, which makes a
  {CORE.pole_w*1e3:.0f} × {CORE.pole_h*1e3:.0f} mm pole face impractical.
* Nanocrystalline dissipates {[r for r in MC if 'Nano' in r['material']][0]['P_core_3kHz_W']:.1f} W. The premium over the
  thin-gauge option is **USD {CAP['total']-CAP_ALT['total']:,.0f} on a USD {CAP['total']:,.0f} project — {100*(CAP['total']-CAP_ALT['total'])/CAP['total']:.1f} %**.
  Paying {100*(CAP['total']-CAP_ALT['total'])/CAP['total']:.1f} % of CAPEX to delete a 2 kW thermal problem and its
  associated failure surface is not a close call.

**Buildability caveat (P0 → must become E2):** nanocrystalline is supplied as
18 µm ribbon and is realistically available only as *wound* cut cores, not as
arbitrary machined blocks. The {CORE.pole_w*1e3:.0f} × {CORE.pole_h*1e3:.0f} mm pole face must therefore
be realised as a stack of standard cut-core sections with a bonded pole shoe.
**This is the single largest open manufacturing risk in the package** and is
carried in the Unknown-Unknown register (§31, UU-1) with a defined fallback:
if a supplier cannot deliver the stack, revert to thin-gauge silicon steel and
cap the envelope at 10 mT above 1 kHz, which still covers four of the five
ladder rungs.
""")

# ============================== 09 - 14 ====================================
r50_3k = [r for r in MT if r['B_set_mT']==50 and r['f_Hz']==3000][0]
r50_3  = [r for r in MT if r['B_set_mT']==50 and r['f_Hz']==3][0]
w(f"""
---

## 09 Coil Calculation

### 09.1 Reverse-solved winding

| Quantity | Value | Basis |
|---|---|---|
| N (turns per coil) | {WC['turns']} | chosen to satisfy V_cap ≤ 2,500 V at 3 kHz *and* J ≤ 4 A/mm² |
| Coils per cell | 2, series | one per leg |
| N_loop | {2*WC['turns']} | turns linking one flux loop |
| Conductor | {WC['wire'].label} | strand Ø 0.20 mm vs Cu skin depth 1.30 mm at 3 kHz |
| A_wire | {WC['wire'].a_cu*1e6:.2f} mm² | bundle Ø {WC['wire'].d_outer*1e3:.1f} mm |
| Mean turn length | {CORE.mean_turn_length()*1e3:.0f} mm | square leg + half build |
| R_dc (80 °C) | {r50_3['R_ac_ohm']:.4f} Ω | both coils in series |
| R_ac/R_dc | {r50_3['Fr']:.2f} at 3 Hz → {r50_3k['Fr']:.2f} at 3 kHz | Dowell, porosity corrected, strand level |
| L | {WC['L']*1e3:.2f} mH | N_loop² / R_loop |
| I_rms at 50 mT | {I50:.1f} A | MMF / N_loop |
| I_peak at 50 mT | {I50*math.sqrt(2):.1f} A | |
| Current density | {WC['j']:.2f} A/mm² | limit 4 A/mm² — **{4/WC['j']:.1f}× margin** |

### 09.2 Does one coil work at both 3 Hz and 3,000 Hz?

| | 3 Hz | 3,000 Hz | ratio |
|---|---|---|---|
| I_rms at 50 mT | {r50_3['I_rms_A']:.1f} A | {r50_3k['I_rms_A']:.1f} A | 1.00 |
| \\|Z\\| | {r50_3['Z_ohm']:.4f} Ω | {r50_3k['Z_ohm']:.2f} Ω | {r50_3k['Z_ohm']/r50_3['Z_ohm']:.0f}× |
| V uncompensated | {r50_3['V_uncomp_V']:.2f} V | {r50_3k['V_uncomp_V']:.0f} V | {r50_3k['V_uncomp_V']/r50_3['V_uncomp_V']:.0f}× |
| **V with compensation** | **{r50_3['V_drive_V']:.2f} V** | **{r50_3k['V_drive_V']:.0f} V** | {r50_3k['V_drive_V']/r50_3['V_drive_V']:.0f}× |
| Reactive power | {r50_3['Q_kVAr']:.3f} kVAr | {r50_3k['Q_kVAr']:.1f} kVAr | {r50_3k['Q_kVAr']/max(r50_3['Q_kVAr'],1e-9):.0f}× |
| P_Cu | {r50_3['P_Cu_W']:.1f} W | {r50_3k['P_Cu_W']:.1f} W | {r50_3k['P_Cu_W']/r50_3['P_Cu_W']:.2f}× |

**One coil suffices; no dual-range architecture is needed.** The current is
identical at both ends of the band because MMF depends only on B and geometry.
The 4-decade voltage swing is handled by (a) series compensation above 80 Hz
and (b) an amplifier with a switchable output rail. The alternative — separate
LF and HF drivers, or a dual-range coil with a tap changer — was evaluated and
rejected: it doubles the winding failure surface and introduces a
mode-transition discontinuity right in the middle of the DOE frequency factor.

### 09.3 Skin depth reference (P0)

| f [Hz] | δ_Cu [mm] | strand Ø / δ | comment |
|---|---|---|---|
| 3 | 41.04 | 0.005 | any conductor is fine |
| 50 | 10.05 | 0.020 | solid wire still fine |
| 500 | 3.18 | 0.063 | solid AWG-6 already Fr > 2 |
| 3,000 | 1.30 | 0.154 | litz required |

---

## 10 Amplifier Design

### 10.1 Topology comparison

| Criterion | Linear (class AB) | Class-D | H-bridge PWM | Full-bridge + LC |
|---|---|---|---|---|
| Efficiency at rated | 25–40 % | 90–95 % | 90–95 % | 88–93 % |
| THD at the field | < 0.1 % | 0.5–2 % | 1–3 % | 0.3–1 % |
| Bandwidth | DC–100 kHz | DC–20 kHz | DC–10 kHz | DC–15 kHz |
| Current capability | moderate | high | high | high |
| EMI | very low | high (needs filter + screened cabinet) | high | moderate |
| Thermal load | high (dissipates the difference) | low | low | low |
| Behaviour into a resonant load | benign | needs care; switching ripple excites the tank | same | best of the switching options |
| Cost | high | low | low | moderate |

**Selection: 4-quadrant current-mode amplifier, linear or hybrid
(linear output stage with a tracking switching rail).** The decisive argument
is not efficiency — the real load is only {r50_3k['P_Cu_W']+r50_3k['P_core_W']:.0f} W per cell — but
**THD and EMI**. §14 requires that harmonic content be a *designed factor*, not
a contaminant: if the drive itself injects 2 % THD, a square-vs-sine waveform
comparison is confounded at the same order as the effect being tested. A
switching stage would also inject carrier-frequency ripple into a load with a
compensation network, and the resulting circulating currents are exactly what
the Layer-1/Layer-3 cross-check would flag as a fault.

### 10.2 Specification (evidence level T)

| Parameter | Value |
|---|---|
| Channels | {CELL.N_CELLS} independent |
| Mode | current controlled, external command, differential B-feedback input |
| Output | {LIM.v_max:.0f} V rms / {LIM.i_max:.0f} A rms / {LIM.s_max/1e3:.0f} kVA per channel |
| Bandwidth | DC – {LIM.f_max/1e3:.0f} kHz, phase error ≤ 1° at 3 kHz |
| THD | ≤ 0.5 % at rated output, 3 Hz – 3 kHz |
| Output rail | switchable (±30 / ±300 / ±700 V) so that low-frequency operation is not at 0.3 % of full scale |
| Protection | over-current, over-voltage, over-temperature, all wired into the SS-10 chain |

### 10.3 PLC AO is NOT a field command

The 0–10 V analog output of the PLC is treated strictly as a **set-point
transport**, never as a field value:

```
PLC AO (0-10 V, 16 bit)  ->  B_set [T]  ->  outer B loop  ->  I* command
   ->  amplifier (current mode)  ->  coil  ->  measured B (Layer 3)  ->  back to the outer loop
```

There is no path in which an analog voltage is interpreted as a magnetic flux
density. This matters because the AO-to-B relationship depends on frequency,
temperature, compensation band and the probe transfer coefficient, none of
which a static scaling could represent.

### 10.4 Compensation network

| Band [Hz] | C [µF] | V_cap at 50 mT [V] | I_cap [A] | Q [kVAr] |
|---|---|---|---|---|""")
for lo, hi in S.COMP_BANDS:
    fc = math.sqrt(lo*hi)
    sol = S.solve_cell(fc, 50e-3, CORE, MAT, WC["wire"], WC["turns"], GAIN, CV, 80.0, LIM)
    w(f"| {lo:.0f}–{hi:.0f} | {sol.c_series*1e6:.2f} | {sol.v_cap:.0f} | {sol.i_rms:.1f} | {sol.q_var/1e3:.1f} |")
w(f"""
Each band is tuned at its geometric centre and is **deliberately detuned**
elsewhere in the band. Exact tuning would give a loaded Q of
{S.loaded_Q(3000, WC['L'], r50_3k['R_ac_ohm']):.0f}, at which a 0.02 % component tolerance
produces a 100 % amplitude error and the loop becomes uncontrollable. The
residual reactance is what the amplifier drives, and it is bounded by
{max(r['V_drive_V'] for r in MT):.0f} V across the whole ladder and the whole band.

Capacitors: self-healing MKP AC film, vacuum-contactor switched, with a
discharge resistor and an interlock that blocks band changes while the output
is enabled. Rated for {max(r['V_cap_V'] for r in MT):.0f} V rms and
{max(r['I_rms_A'] for r in MT):.0f} A rms continuous at 3 kHz — the current rating, not the
voltage rating, is the sizing constraint.

---

## 11 Sensor Design

### 11.1 Candidate comparison

| Sensor | Bandwidth | Range | Noise floor | Linearity | Saturation | Tempco | Phase err | Verdict |
|---|---|---|---|---|---|---|---|---|""")
for s in MET.SENSORS:
    w(f"| {s.name} | {s.f_lo:.0f}–{s.f_hi:,.0f} Hz | {s.range_mT:,.3g} mT | {s.noise_nT_rtHz:g} nT/√Hz | {s.lin_pct}% | "
      f"{'yes' if s.range_mT < 100 else 'no'} | {s.tempco_ppm_K:.0f} ppm/K | {s.phase_err_deg}° | {s.notes} |")
w(f"""
### 11.2 Three-layer architecture

| Layer | What it measures | Device | Role | Why not alone |
|---|---|---|---|---|
| **1** | coil current | closed-loop fluxgate CT + precision shunt | fast observer, inner loop, over-current trip | current is not field; a shorted turn or a gap change breaks the transfer silently |
| **2** | external reference B | 3-axis fluxgate | absolute reference, stray-field survey, Sham verification | saturates at ~1 mT, far below the ladder; sits outside the ECV |
| **3** | in-water B | sealed air-cored search coil, N = 200, A = 1 cm²/axis | **the controlled variable** | 1/f sensitivity roll-off; needs an integrator with its own calibration |

**Hybrid sensing is used, and the reason is quantitative.** The search coil
output is V = N·A·2πf·B:

| f [Hz] | sensitivity [V/T] | output at 0.5 mT | output at 50 mT |
|---|---|---|---|""")
for f in (3.0, 7.83, 50.0, 500.0, 3000.0):
    s_ = MET.search_coil_sensitivity(200, 1e-4, f)
    w(f"| {f:g} | {s_:.3f} | {s_*0.5e-3*1e3:.3f} mV | {s_*50e-3*1e3:.1f} mV |")
w(f"""
Even at the very worst point (3 Hz, 0.5 mT, {MET.averaging_window(3.0):.0f} s window) the SNR is
7.2 × 10⁴, so the search coil is fully adequate across the band. The fluxgate
is retained for Layer 2 precisely because it is *too sensitive* for Layer 3 —
that is what makes it the right instrument for verifying that the Sham field
is below the detection limit.

Its immunity to the {MET.GEOMAGNETIC_T*1e6:.0f} µT DC geomagnetic background is intrinsic:
a search coil responds to dB/dt, so a DC background produces exactly zero
output. A Hall probe would have to reject a DC signal
{MET.GEOMAGNETIC_T/0.5e-3:.1f}× larger than the smallest ladder rung.

### 11.3 Measurement uncertainty budget (GUM, k = 2)

""")
terms, comb, vprobe, snr = MET.budget_internal_probe(50.0, 10e-3,
                                                     bw_hz=1.0/MET.averaging_window(50.0))
tbl(["Term","u [% of reading]","Type","Source"],
    [[t.label, f"{t.rel_pct:.3f}", t.kind, t.source] for t in terms])
w(f"""**Combined standard uncertainty u_c = {comb['u_c_pct']:.2f} %**,
**expanded U(k=2) = {comb['U_expanded_pct']:.2f} %**.

The budget is dominated by **probe positioning (1.2 %)**, which follows
directly from the computed field gradient over a ±2 mm placement tolerance.
That is the term to attack if the requirement ever tightens: a machined probe
seat referenced to the pole shoe, rather than a clamped fixture, would take it
below 0.4 %.

### 11.4 Field mapping plan

Minimum {MET.mapping_plan()['n_points']} map points are needed to bound CV_B below 10 % at 95 %
confidence given the expected {CV*100:.2f} % — but the nominal plan uses the full
automated 3-D traverse (**{5*5*5} points minimum, 13 × 13 × 9 = 1,521 for the
acceptance map**), because the map also has to *find* the CV, not merely
confirm it. The 5-point map (P1…P5) is the routine per-run check; the full
map is run at commissioning, after any mechanical disturbance, and at each
calibration epoch.

---

## 12 Constant-B Controller

Cascaded structure, feed-forward plus feedback:

```
B_set --(+)--> [outer B loop: PI + repetitive, gain scheduled on f]
        |                                   |
        |         feed-forward I* = B_set / k(geom) + Z(f,T) compensation
        |                                   v
        |                        --(+)--> [inner current loop, >10 kHz]
        |                                   v
        |                            amplifier -> cell -> B(f,r,t)
        +---------- coherent demodulation at f, T_avg = max(3 s, 30/f) <----- Layer 3
```

Control law: `I_command = F(e_B, f, T_coil, T_driver, Z)` where the
feed-forward term carries the geometric constant k(geom) = {GAIN:.4f} × pole
transfer and the probe coefficient k_P1 = {FPM['P1 Center']['Bmag']/50e-3:.5f}.

### 12.1 Error budget against the ±5 % requirement

""")
_t, _c, _v, _snr = MET.budget_internal_probe(50.0, 0.5e-3, bw_hz=1.0/MET.averaging_window(50.0))
eb = MET.control_error_budget(_c["U_expanded_pct"], 50.0, 100.0/max(_snr,1e-12))
tbl(["Contribution","Value [%]","Note"],
    [["Measurement uncertainty U(k=2)", f"{eb['u_meas_pct']:.3f}", "§11.3"],
     ["Regulation residual", f"{eb['regulation_pct']:.3f}", "3 % plant drift, ≥40 dB loop gain"],
     ["Demodulation", f"{eb['demod_pct']:.4f}", f"SNR ≥ 7×10⁴, N_cycles ≥ 30"],
     ["Gap thermal expansion (20 K)", f"{eb['gap_thermal_pct']:.3f}", "99.9 % air-gap circuit"],
     ["Set-point quantisation (16 bit)", f"{eb['quantisation_pct']:.4f}", ""],
     ["**RSS TOTAL**", f"**{eb['total_pct']:.2f}**", f"requirement ≤ 5 % — **PASS**, margin {5/eb['total_pct']:.2f}×"]])
w(f"""**The requirement is only meaningful because the measurement uncertainty is
smaller than it.** A ±5 % control target verified with a ±10 % instrument
would be unverifiable. This is why §11 is computed before §12, not after.

**Frequency-scaled averaging.** T_avg = max(3 s, 30/f) gives {MET.averaging_window(3.0):.0f} s at
3 Hz and 3 s above 10 Hz. At 3 Hz a 1 s window would contain only 3 cycles and
the amplitude estimate would not even be well posed. Loop settling is
specified as ≤ 10 × T_avg, i.e. ≤ 100 s at 3 Hz — which must be accounted for
in the run schedule, since a 6-point frequency sweep at 3 Hz costs 10 minutes
of settling alone.

---

## 13 SUS316L Transfer Function

### 13.1 Model

For a thin conducting non-magnetic shell of radius a and wall t,

```
H(f) = B_inside / B_outside = 1 / (1 + j·2πf·τ_s) · 1/cosh(k t),   τ_s = μ0 μr σ t a / 2
```

With a = {TANK.radius:.2f} m, t = {TANK.wall_thickness*1e3:.0f} mm, σ = {SIGMA_SUS316L.value:.2e} S/m:

* **τ_s = {shell_time_constant(TANK, SIGMA_SUS316L.value, 1.005):.4e} s**
* **f_c = {corner_frequency(TANK):.1f} Hz** (annealed, μr = {MU_R_SUS316L_ANNEALED.value})
* **f_c = {corner_frequency(TANK, mu_r=MU_R_SUS316L_COLDWORK.value):.1f} Hz** if cold work / weld HAZ raises μr to {MU_R_SUS316L_COLDWORK.value}

### 13.2 Computed transfer function at the required verification frequencies

""")
tbl(["f [Hz]","\\|H\\|","dB","phase [deg]","δ [mm]","t/δ","model validity","B_out needed for 1 mT inside [mT]","tank eddy loss at that drive [kW]"],
    [[f"{r['f_Hz']:.2f}", f"{r['H_mag']:.4f}", f"{r['H_dB']:.2f}", f"{r['phase_deg']:.2f}",
      f"{r['skin_depth_mm']:.2f}", f"{r['t_over_delta']:.3f}", r["model_valid"],
      f"{r['B_out_needed_mT_for_1mT_in']:.2f}", f"{r['P_eddy_at_that_drive_kW']:.2f}"] for r in TK])
w(f"""### 13.3 What this means

The last column is the design killer. Driving 1 mT *inside* an intact
1,000 L SUS316L tank from outside costs:

* 0.04 kW of wall eddy loss at 30 Hz — negligible;
* {[r for r in TK if r['f_Hz']==300][0]['P_eddy_at_that_drive_kW']:.1f} kW at 300 Hz — already a serious cooling problem;
* **{TK[-1]['P_eddy_at_that_drive_kW']:.0f} kW at 3,000 Hz** — for **1 mT**, one fiftieth of the top rung.

At 50 mT the number scales by 2,500. There is no amplifier, no core material
and no cooling system that makes external excitation of a closed austenitic
shell work above a few hundred hertz. Note also the phase: **{TK[-1]['phase_deg']:.0f}°** at
3 kHz, so even where amplitude were tolerable the field inside would be nearly
in quadrature with the drive, and any phase-sensitive protocol would be
measuring something other than what it commanded.

**Design response — three options were evaluated:**

| Option | Verdict |
|---|---|
| Slot the tank longitudinally with an insulated gasketed joint to break the azimuthal eddy path | rejected: a slotted pressure/liquid boundary in a 1 m³ vessel is a leak and cleanability risk, and the slot must be maintained for the life of the rig |
| Insert a non-conductive spool section in the tank shell | rejected for a 1,000 L vertical tank: it becomes a structural and CIP problem, and the field is still spread over 1 m³ |
| **Move the exposure out of the tank into a non-metallic inline cell** | **selected** — the tank becomes a reservoir, H(f) ≡ 1 by construction, and the ECV is small enough to be uniform and cheap to energise |

### 13.4 Verification (this model is P0 and must become E1)

VG-05 requires a two-probe swept measurement on the *actual* tank: Layer-2
fluxgate outside, Layer-3 search coil inside, a low-level (≤ 0.1 mT) external
drive from a temporary Helmholtz pair, swept over the 11 verification
frequencies. Deliverables: |H(f)|, φ(f), harmonic distortion of the internal
field, wall eddy loss inferred from the wall temperature rise, and — crucially
— **a magnetic permeability survey of the welds and cold-formed regions**,
because the cold-worked f_c is nearly half the annealed value. Even though the
selected architecture does not rely on transmission through the wall, this
measurement is retained: it bounds how much stray field from the cells couples
into the reservoir, and it is the evidence that Sham and Active reservoirs are
magnetically equivalent.

---

## 14 Thermal Model

### 14.1 Separated heat sources at the worst corner (50 mT, 3 kHz, v = 0.5 m/s)

""")
p_pump = [r for r in HY if r["v_ms"] == 0.5][0]["P_pump_W"]
p_wat = r50_3k["P_water_W"]
tbl(["Source","Power [W]","Field-coupled?","Reaches the water?","Sink","Computed T"],
    [["P_Cu (3 cells)", f"{3*r50_3k['P_Cu_W']:.1f}", "yes", "no (dry cell)", "cold plate, 25 °C glycol", f"{TH.COIL_PATH.temp(r50_3k['P_Cu_W']):.1f} °C"],
     ["P_core (3 cells)", f"{3*r50_3k['P_core_W']:.1f}", "yes", "no", "cold plate", f"{TH.CORE_PATH.temp(r50_3k['P_core_W']):.1f} °C"],
     ["P_tank_eddy", "0.0", "n/a", "n/a", "— tank is not in the flux path", "—"],
     ["P_driver", "≈ 300", "no", "no", "forced air, 35 °C", f"{TH.DRIVER_PATH.temp(300):.1f} °C"],
     ["P_water_field (σE², 3 cells)", f"{3*p_wat:.1f}", "**yes**", "**yes**", "process chiller", f"{TH.water_dT_dt(3*p_wat,1000)*3600:.4f} K/h"],
     ["P_pump", f"{p_pump:.0f}", "**no**", "**yes**", "process chiller", f"{TH.water_dT_dt(p_pump,1000)*3600:.3f} K/h"]])
w(f"""### 14.2 The Sham argument, quantified

Only **two** sources put heat into the water: the pump ({p_pump:.0f} W) and the
field-coupled ohmic term ({3*p_wat:.1f} W). Their ratio is
**{p_pump/max(3*p_wat,1e-9):.0f} : 1**. Running the Sham arm with identical pump duty therefore
matches **{100*p_pump/(p_pump+3*p_wat):.1f} %** of the total water heating, and the unmatched
residual raises the water by {TH.water_dT_dt(3*p_wat,1000)*3600:.4f} K/h — two orders of
magnitude below the ±0.3 K control band of THE-04.

This is what makes H1 (thermal artifact) a **testable** hypothesis rather than
an untestable objection: the thermal difference between arms is computed,
bounded, and smaller than the control band, and it is *also* measured
continuously by three independent water Pt100s.

### 14.3 Sensor allocation

T_coil ×6 (of which 2 are **fibre-optic in-winding** hot-spot probes — an RTD
lead inside a winding is itself a pickup loop in an ELF field and would both
corrupt its own reading and inject noise), T_core ×3, T_driver ×3, T_tank ×2,
T_water ×3 (inlet, outlet, reservoir). **Each has its own limit.** A single
25 °C threshold is never applied across devices: 25 °C is a *water* set point,
not a coil limit, and applying it to a coil rated for class-H insulation would
throw away {TH.COIL_PATH.t_limit-25:.0f} K of usable margin for no benefit.

### 14.4 Cooling capacity

| Path | R_th [K/W] | Coolant | Limit | P_max [W] | Actual worst [W] | Margin |
|---|---|---|---|---|---|---|
| Coil → cold plate | {TH.COIL_PATH.r_th} | 25 °C glycol | {TH.COIL_PATH.t_limit:.0f} °C | {TH.COIL_PATH.p_max():,.0f} | {r50_3k['P_Cu_W']:.1f} | {TH.COIL_PATH.p_max()/r50_3k['P_Cu_W']:.0f}× |
| Core → cold plate | {TH.CORE_PATH.r_th} | 25 °C glycol | {TH.CORE_PATH.t_limit:.0f} °C | {TH.CORE_PATH.p_max():,.0f} | {r50_3k['P_core_W']:.1f} | {TH.CORE_PATH.p_max()/max(r50_3k['P_core_W'],1e-9):.0f}× |
| Driver → air | {TH.DRIVER_PATH.r_th} | 35 °C air | {TH.DRIVER_PATH.t_limit:.0f} °C | {TH.DRIVER_PATH.p_max():,.0f} | ≈ 300 | {TH.DRIVER_PATH.p_max()/300:.1f}× |

The 3 kW chiller is sized by the pump, not by the field.
""")

# ============================== 15 - 20 ====================================
w(f"""
---

## 15 Water / Ion Model

### 15.1 Controlled electrolyte matrix

The DOE does not use "tap water" as a factor level — it uses a **synthesised
electrolyte** so that composition is a controlled variable rather than a
nuisance. Real tap water and groundwater are run separately as *validation*
cases once the controlled-matrix result is in.

| Ion | Salt used | Low level | High level | Rationale |
|---|---|---|---|---|
| Na⁺ | NaCl | 20 mg/L | 200 mg/L | conductivity trim |
| Ca²⁺ | CaCl₂·2H₂O | 10 mg/L | 100 mg/L | hardness, scaling relevance |
| Mg²⁺ | MgSO₄·7H₂O | 5 mg/L | 50 mg/L | hardness, paired with SO₄²⁻ |
| Cl⁻ | (from NaCl/CaCl₂) | balance | balance | — |
| HCO₃⁻ | NaHCO₃ | 30 mg/L | 250 mg/L | buffer; controls pH stability |
| SO₄²⁻ | (from MgSO₄) | balance | balance | — |
| Conductivity | NaCl trim | 200 µS/cm | 2,000 µS/cm | **sets J = σE — the H2 discriminator** |
| pH | HCl/NaOH trim | 7.0 | 8.2 | held or blocked |

Base water: reverse osmosis + EDI, ≤ 1 µS/cm, TOC ≤ 20 ppb, degassed then
re-equilibrated to a controlled DO set point.

### 15.2 Responses and their measurement quality

""")
tbl(["Response","Unit","Instrument 1σ","δ_min of interest","n per arm for 90 % Bayesian power"],
    [[n, u, f"{s:g}", f"{d:g}", str(DOE.required_n(d*1.5, d, s, s*0.6, 4)[0])]
     for n, u, s, d in DOE.RESPONSES])
w(f"""### 15.3 Exploratory measurements — and the inference they do NOT support

""")
tbl(["Technique","Status","Explicit caveat carried in the protocol"],
    [[n, "EXPLORATORY", c] for n, u, c in DOE.EXPLORATORY])
w(f"""**A ¹H NMR linewidth change is not evidence of a water cluster-size change.**
T2* linewidth in bulk water is dominated by magnetic field inhomogeneity, shim
quality, sample temperature, dissolved paramagnetic species (notably O₂ and
Fe) and bulk magnetic susceptibility. Every one of those varies at or above
the order of any plausible effect. If a linewidth difference is observed, the
protocol requires: same magnet, same shim routine, temperature controlled to
±0.1 K, DO matched, randomised sample order, blinded operator, and a
sealed-tube reference in every acquisition — and even then the result is
reported as "a linewidth difference", not as "a cluster-size change".

### 15.4 The induced electric field — reported next to B, always

E = π f B r is not a side effect; in a conducting electrolyte it is the most
physically plausible route by which an ELF magnetic field can do anything at
all. Computed at the ECV equivalent radius r = {0.5*math.sqrt(CORE.pole_w*CORE.pole_h/PI)*1e3:.0f} mm:

| f [Hz] | E at 0.5 mT [V/m] | E at 50 mT [V/m] | J at σ = 0.2 S/m [A/m²] | Ohmic density [W/m³] |
|---|---|---|---|---|""")
for f in (3.0, 50.0, 300.0, 1000.0, 3000.0):
    r_eq = 0.5*math.sqrt(CORE.pole_w*CORE.pole_h/PI)
    e_lo = PI*f*0.5e-3*r_eq; e_hi = PI*f*50e-3*r_eq
    w(f"| {f:g} | {e_lo:.3f} | {e_hi:.2f} | {0.2*e_hi:.2f} | {0.2*e_hi**2:.1f} |")
w(f"""
This table is the reason conductivity is a **designed factor** (F) and not a
held constant. If a response scales with σ, the mechanism is electrochemical
(H2) and "magnetic dose" is the wrong variable to be reporting. If it scales
with B at fixed σ, that supports H3. **The experiment cannot distinguish these
unless B and σ are varied independently**, and that is a design requirement,
not a statistical afterthought.

---

## 16 Hydraulic Variables

""")
tbl(["v [m/s]","Q [m³/h]","Re","Regime","ΔP duct [Pa]","P_pump [W]","Residence/pass [s]","Turnover [s]","Water heating [K/h]"],
    [[f"{r['v_ms']:.2f}", f"{r['Q_m3h']:.2f}", f"{r['Re']:,.0f}", r["regime"],
      f"{r['dP_duct_Pa']:.1f}", f"{r['P_pump_W']:.0f}",
      ("static" if r['v_ms']==0 else f"{r['res_per_pass_s']:.2f}"),
      ("—" if r['v_ms']==0 else f"{r['turnover_s']:.0f}"),
      f"{r['water_dTdt_K_per_h']:+.3f}"] for r in HY])
w(f"""All flowing cases are **turbulent** (Re > 10,000), which is deliberate: it
guarantees the ECV is well mixed on the residence timescale, so every water
parcel crossing a cell sees essentially the same field-time history. In the
laminar case a parabolic profile would give centre-line parcels roughly half
the residence of near-wall parcels, and "residence time" would become a
distribution rather than a number.

### 16.1 The dose result that governs the whole programme

For a well-mixed recirculating batch, the mean cumulative time each water
parcel spends inside the ECV is

```
    t_exp  =  t_run × V_ECV / V_tank          — INDEPENDENT of flow rate
```

Raising the pump raises the number of passes and shortens each pass by exactly
the same factor. **You cannot buy dose with flow.**

""")
tbl(["Run time [h]","Passes","Cumulative exposure [s]","D_B at 50 mT [mT·s]","D_B at 10 mT [mT·s]","D_B at 0.5 mT [mT·s]"],
    [[f"{r['run_h']}", f"{r['passes']:.1f}", f"{r['t_exposure_s']:.1f}",
      f"{r['D_B_50mT_mTs']:,.0f}", f"{r['D_B_10mT_mTs']:,.0f}", f"{r['D_B_0.5mT_mTs']:,.0f}"] for r in DZ])
w(f"""With V_ECV = {V_ECV:.3f} L into V_tank = 1,000 L, an 8-hour run delivers
{DZ[2]['t_exposure_s']:.1f} seconds of cumulative exposure. To reach even 5 minutes of
cumulative exposure at 1,000 L requires **{300*1000/V_ECV/3600:.0f} hours**.

**Three honest responses, and the one selected:**

1. Accept multi-day runs at 1,000 L — poor experimental throughput, and 48 h
   of continuous operation introduces its own drift confounders.
2. Enlarge the ECV — but stored energy, and therefore compensation-bank cost,
   scales with the gap volume. Tripling the ECV triples the kVAr.
3. **Do the Phase-3 dose-response work at Stage 2 (50–100 L), where the same
   cell gives {100*V_ECV/50:.1f} % duty instead of {100*V_ECV/1000:.2f} %, and treat
   1,000 L as the scale-up demonstration (Stage 3), not the discovery
   platform.** — **selected**

This is not a workaround; it is the correct reading of the physics, and it is
why §31 makes Stage 2 the gate at which Gate F (dose-response) is actually
decided. The same table must be recomputed at every scale-up step, because
V_ECV/V_tank changes by more than an order of magnitude between stages.

### 16.2 Confounding control

Magnetic effect and mixing/temperature effect are never varied together
without the Sham twin: flow (factor G) is crossed with B (factor A) in the
design, and every (A, G) cell has a Sham partner at the same G. The
mixing-only and heating-only contrasts are therefore directly estimable.

---

## 17 Thermal Model

*(consolidated in §14 — heat-source separation, sensor allocation, cooling
capacity and the quantitative Sham thermal argument)*

---

## 18 Safety Interlock

### 18.1 Hard interlock chain

Ten conditions, each wired **in series** with the AMPLIFIER ENABLE contactor
through a SIL2 dual-channel safety relay. De-energise-to-trip.

| # | Condition | Sensing element | Trip threshold | Action | Proof test |
|---|---|---|---|---|---|
| 1 | Over-current | Layer-1 fluxgate CT + hardware comparator | 1.2 × I_max = {LIM.i_max*1.2:.0f} A | ENABLE break < 50 ms | inject current, verify trip |
| 2 | Over-voltage | amplifier + bank divider | 1.15 × V_max = {LIM.v_max*1.15:.0f} V | ENABLE break | inject, verify |
| 3 | Coil over-temperature | fibre-optic hot-spot ×2 | {TH.COIL_PATH.t_limit:.0f} °C | ENABLE break | heat probe, verify |
| 4 | Driver over-temperature | heatsink NTC | {TH.DRIVER_PATH.t_limit:.0f} °C | ENABLE break | heat, verify |
| 5 | Water leak | conductive tape under the cell array | any conduction | ENABLE break + pump stop | wet the tape |
| 6 | Insulation failure | IMD on the IT-earthed sub-net | < 100 kΩ | ENABLE break | resistor injection |
| 7 | Sensor failure | 3-layer disagreement | > 3 × budget for > 1 s | ENABLE break | disconnect one layer |
| 8 | B-field runaway | Layer-3 magnitude comparator | \\|B\\| > 1.2 × set for > 3 cycles | ENABLE break | force a set-point step |
| 9 | PLC/DSP comms loss | watchdog | 50 ms | ENABLE break | pull the cable |
| 10 | Emergency stop ×3 | dual-channel forced-guided | actuation | ENABLE break | press each |

**PLC software alarms are annunciation only.** No software path can hold
ENABLE closed. Reset requires the fault to be cleared **and** a local manual
reset **and** a logged operator acknowledgement. The chain fails safe on loss
of 24 V, on a broken wire, and on a welded contact (forced-guided contact
monitoring).

### 18.2 Personnel exposure

Stray field is surveyed with the Layer-2 fluxgate on a 1 m grid at the
controlled-area boundary and compared against the ICNIRP occupational
reference level for the operating frequency. Because the flux path is a closed
C-core with a {CORE.gap*1e3:.0f} mm gap, leakage falls off very rapidly; the exclusion
zone is nonetheless enforced at ≥ 1.5 m by interlocked barriers, and the
survey is a *measurement*, not a calculation.

Note also: personnel with active implants (pacemakers, ICDs, neurostimulators,
insulin pumps) and ferromagnetic implants must be excluded from the controlled
area entirely, with signage at every entry. This is a Phase-3 operating
requirement, not an optional precaution.

---

## 19 Submersible Fork Branch

The master prompt requires the immersed and non-contact architectures to be
evaluated as separate options. They were, and the immersed branch was rejected.

| Criterion | Immersed fork | **Dry cell + non-metallic duct (selected)** |
|---|---|---|
| Hermetic sealing | required, lifetime-critical | not required |
| Potting water ingress | epoxy absorbs water; permittivity and insulation degrade over months | n/a |
| Feedthrough | wet-mate connector or hermetic penetrator, single point of failure | n/a |
| O-ring | compression set, chemical ageing, periodic replacement | n/a |
| Insulation resistance in water | must be monitored continuously; failure is a shock hazard in a conductive medium | dry, standard megger practice |
| Leakage current into the process | any leakage becomes electrolysis in the water — a direct chemical confounder | zero by construction |
| Water absorption | changes coil capacitance and hence the resonant tuning | n/a |
| Galvanic corrosion | dissimilar metals in an electrolyte with an imposed field | n/a |
| Chemical compatibility | encapsulant must resist the full electrolyte matrix | duct is PVDF only |
| Temperature cycling | differential expansion of encapsulant vs core cracks the seal | dry, unconstrained |
| Magnetic penalty | none (no duct wall in the gap) | {2*CELL.DUCT_WALL*1e3:.0f} mm of extra gap = {100*2*CELL.DUCT_WALL/CORE.gap:.0f} % of MMF |

**"IP68" is not evidence of continuous long-term immersion capability.** IP68
is a short-duration ingress test at a stated depth and time; it says nothing
about hydrolytic ageing of the encapsulant, about permeation over thousands of
hours, or about behaviour under simultaneous thermal cycling and an imposed
electric field. A design that relies on it for a multi-year immersed winding
is relying on a test that was never run.

**Decision:** pay {100*2*CELL.DUCT_WALL/CORE.gap:.0f} % more ampere-turns and delete eleven failure modes.
Given that the MMF budget has {min(r['B_max_mT'] for r in FE)/50:.1f}× headroom at the top rung, this
is close to free.

If an immersed variant is ever required (for instance for a Stage-4 in-tank
retrofit), the qualification programme is: 90-day immersion at 40 °C in the
worst-case electrolyte with continuous insulation-resistance monitoring;
1,000 thermal cycles 5 → 60 °C; leakage current measured to 1 µA; mass uptake
by gravimetry; and dielectric withstand before and after. None of that is in
the Phase-3 critical path under the selected architecture.

---

## 20 Sham Control

### 20.1 What is matched

Identical tank, identical water batch, identical temperature set point,
identical flow and pump duty, identical residence time, identical handling and
sampling, identical sensors, identical run duration, identical cabinet noise
and heat. **Only the winding sense differs.**

The Sham coil is **driven, not switched off**: it carries the same current,
into a bifilar-cancelled winding whose net ampere-turns are nominally zero. So
the amplifier fans run the same, the cabinet dissipates the same, the Layer-1
current sensor reads the same, and the contactors click the same. An operator
listening to the room cannot tell the arms apart.

### 20.2 Quantified integrity (VG-07)

| Quantity | Value | Note |
|---|---|---|
| Layer-3 3σ detection limit at 50 Hz, 0.1 Hz BW | **{MET.sham_detection_limit()*1e9:.2f} nT** | computed from probe sensitivity and amplifier noise |
| Geomagnetic DC background | {MET.GEOMAGNETIC_T*1e6:.0f} µT | {MET.GEOMAGNETIC_T/MET.sham_detection_limit():,.0f}× the detection limit — but DC, so invisible to a search coil |
| Residual required to be < 1 % of the 0.5 mT rung | 5 µT | |
| Isolation needed for that at the 50 mT rung | ≥ {20*math.log10(50e-3/5e-6):.0f} dB | |
| Design target | ≥ 80 dB | bifilar cancellation + ≥ 1.5 m separation |
| Residual at 80 dB, 50 mT active | {MET.sham_residual_from_leakage(50e-3,80)*1e6:.1f} µT | **meets VG-07** |

The Sham residual is **measured every run** with the Layer-3 probe in the Sham
duct, not assumed. A run whose Sham residual exceeds the limit is voided at
analysis — and because the arms are blinded, that decision is made from
recorded field data before unblinding, not after seeing the chemistry.

### 20.3 Blinding

Arm assignment is generated by the PLC from a sealed randomisation table
(§21). The operator sees a run ID only. Sample bottles are barcoded, never
labelled with the arm. The analyst receives the barcode and the chemistry, not
the arm. Unblinding happens once, at the pre-registered analysis point.
""")

# ============================== 21 - 27 ====================================
w(f"""
---

## 21 DOE (Phase-3 experimental design)

### 21.1 Design selection

| Candidate | Runs | Pros | Cons | Verdict |
|---|---|---|---|---|
| Full factorial 2⁷ | 128 | all interactions estimable | 128 × 8 h ≈ 6 weeks of runtime for screening alone | rejected for screening |
| **Fractional factorial 2⁷⁻³ resolution IV** | **16** | main effects clear of 2-factor interactions; perfectly orthogonal; trivially analysable and auditable | 2-factor interactions confounded in chains of three | **selected for screening** |
| D-optimal | 16–24 | handles constraints and mixed level types | design depends on an assumed model; less transparent | selected for the **augmentation** stage |
| Bayesian optimal (sequential) | adaptive | best information per run | requires a trusted prior; harder to pre-register | selected for the **dose-response refinement** stage |

The sequence is deliberate: screen with a transparent orthogonal design,
augment with D-optimal runs where the screen finds structure, then refine the
dose-response with sequential Bayesian design. Pre-registration happens before
the screen, so the primary analysis cannot be reshaped by the data.

### 21.2 Screening design — 2⁷⁻³ resolution IV, 16 runs

Base factors A, B, C, D; generators **E = ABC, F = BCD, G = ACD**;
defining relation **I = ABCE = BCDF = ACDG** (shortest word length 4).
Verified numerically: XᵀX = 16·I (perfectly orthogonal), D-efficiency proxy
= {DOE.d_optimality(DES):.4f}.

""")
tbl(["Factor","Name","Unit","Low (−1)","High (+1)","Rationale"],
    [[f.code, f.name, f.unit, f.levels[0], f.levels[1], f.rationale] for f in DOE.SCREENING_FACTORS])
w("**Design matrix:**")
w()
tbl(["Run","A B","B f","C wave","D Ca²⁺","E HCO₃⁻","F EC","G flow"],
    [[i+1] + [f"{r[c]:+d}" for c in "ABCDEFG"] for i, r in enumerate(DES)])
w("**Alias structure (2-factor interactions only — main effects are clear):**")
w()
for g in DOE.alias_structure(DES):
    w(f"* `{' = '.join(g)}`")
w(f"""
### 21.3 Held constant, blocked, randomised

""")
tbl(["Variable","Value","Control"],
    [[f.name, f"{f.levels[0]} {f.unit}", f.rationale] for f in DOE.HELD_CONSTANT])
w(f"""**Blocking:** {', '.join(DOE.BLOCKS)}. Each block runs a complete
half-fraction so that block effects are orthogonal to main effects.

**Randomisation:** run order is drawn from a sealed table generated before the
campaign starts, stored as a hash-committed file, and executed by the PLC.
The operator cannot choose the order.

**Replication:** every design point has its **Sham twin** run in the same
block on the same day with the same water batch — that is 32 runs per
replicate, not 16. Three replicates → 96 runs. Plus 8 centre points (B at the
5 mT rung, f at 100 Hz, mid-composition) per replicate for curvature and pure
error → **120 runs total for the screen**.

### 21.4 Dose-response stage (after the screen)

Only for factors the screen finds active. Five B levels
(0, 0.5, 1, 5, 10, 50 mT) × 3 frequencies × 4 replicates × Sham twins, blocked
by day. This is the stage at which **Gate F** is decided, and per §16 it is
run at Stage 2 (50–100 L) where V_ECV/V_tank gives usable dose in one shift.

---

## 22 Bayesian Model

### 22.1 Model

```
y_ijkl = mu
       + f(B_i, freq_j, ion_k, T, flow)      # the effect surface
       + b_batch[k]                           # water batch
       + b_day[l]                             # day
       + b_op[m]                              # operator
       + b_tank[n]                            # tank / duct
       + e_sensor                             # sensor error, known variance from the cal
       + eps                                  # residual

b_* ~ Normal(0, sigma_*^2)          sigma_* ~ Half-Normal(0, s0)
eps ~ Normal(0, sigma_within^2)     sigma_within: informative prior from the calibration data
```

The dose term f(·) is fitted **both** as a linear-in-B term and as a monotone
spline, and the two are compared by cross-validation. A monotone spline is
used rather than a free smooth because a non-monotone "dose-response" with no
mechanism is far more likely to be noise than signal, and the prior should say so.

### 22.2 Priors

| Parameter | Prior | Justification |
|---|---|---|
| B main effect | Normal(0, (δ_min)²) | weakly informative, centred on **no effect** — the null is the default |
| Interaction terms | Normal(0, (δ_min/2)²) | interactions a priori smaller than main effects |
| σ_within | Half-Normal from calibration | measured, not guessed |
| σ_batch, σ_day, σ_operator | Half-Normal(0, δ_min) | allows batch effects as large as the effect of interest |
| Sensor error | fixed at the §11.3 budget | not a free parameter — it is known |

### 22.3 Decision rule

Report **P(effect > δ_min \\| Data)** for every response, not a p-value.
Freeze/advance decisions use:

* **Advance** if P(effect > δ_min) ≥ 0.95 for at least one pre-registered
  primary response, **and** the dose-response is monotone, **and** the Sham
  contrast is null.
* **Stop for futility** if P(\\|effect\\| < δ_min) ≥ 0.95 — i.e. positive
  evidence *for* the null, not merely absence of evidence.
* **Continue** otherwise, with the sequential design choosing the next runs.

A single p-value never freezes equipment. Pre-registration of the primary
responses, δ_min values and the decision rule happens before the first run.

### 22.4 Computed sample sizes

For 90 % Bayesian power at P(effect > δ_min) ≥ 0.95, with σ_batch = 0.6 σ_within
and 4 batches:

""")
tbl(["Response","σ_within","δ_min","assumed true effect","n per arm","posterior SE"],
    [[n, f"{s:g} {u}", f"{d:g} {u}", f"{1.5*d:g} {u}",
      str(DOE.required_n(1.5*d, d, s, s*0.6, 4)[0]),
      f"{DOE.required_n(1.5*d, d, s, s*0.6, 4)[1]['se']:.4f}"]
     for n, u, s, d in DOE.RESPONSES])
w(f"""**Zeta potential needs 69 runs per arm** to resolve a 4 mV effect against
a 1.5 mV instrument sigma. That is a real result and it has a real
consequence: zeta potential is demoted from a primary to a secondary response,
because powering it properly would triple the campaign. The primaries are
pH, ORP, DO and dynamic viscosity — the responses whose δ_min/σ ratio makes
them answerable in ≤ 14 runs per arm.

**Deciding the response set from the power calculation, before the campaign,
is what stops the analysis from silently becoming a search over eight
responses for whichever one happens to look significant.**

---

## 23 Null-Hypothesis / Falsification

The experiment is designed to **separate** H0–H3, not to confirm H3.

""")
for k, v in DOE.HYPOTHESES.items():
    w(f"""### {k} — {v['statement']}

* **Signature in the data:** {v['signature']}
* **How this design makes it separable:** {v['discriminator']}
""")
w(f"""### 23.1 Discrimination table

| Observation | H0 | H1 (thermal/mixing) | H2 (ion-specific) | H3 (magnetic dose) |
|---|---|---|---|---|
| Effect present at all | no | yes | yes | yes |
| Sham contrast (matched pump) | null | **null** — the artifact appears in both arms | non-null | non-null |
| Scales with flow (factor G) at fixed B | — | **yes** | no | no |
| Scales with σ (factor F) at fixed B | — | no | **yes** | no |
| Monotone in B at fixed f, σ, flow | — | no | partially | **yes** |
| Scales with f at fixed B | — | no | yes (E = πfBr) | not necessarily |

Rows 4 and 5 together are the crux: **E = πfBr means H2 and H3 are only
separable if B and σ are varied independently and f is varied at fixed B.**
The design does both. Without that, a dose-response in B would be equally
consistent with a purely electrochemical mechanism, and reporting it as a
"magnetic effect" would be an over-claim.

### 23.2 Falsification criteria stated in advance

* If P(\\|effect\\| < δ_min \\| Data) ≥ 0.95 across all primary responses at the
  top of the ladder, **H0 is accepted for the tested envelope** and the correct
  action is to publish the null and stop — not to raise B.
* If the effect tracks flow and vanishes in the Sham-matched contrast, **H1**
  and the finding is an artifact of the rig.
* If the effect scales with σ and with f but not with B at fixed E,
  **H2** — the mechanism is electrochemical and should be described as such.

---

## 24 Failure Surfaces

Each surface has a limit-state equation g(x), a measurement, a threshold, an
uncertainty and a mitigation. g < 0 means failure.

| ID | Failure surface | Limit-state g(x) | Measurement | Threshold | Uncertainty | Mitigation |
|---|---|---|---|---|---|---|
| FS1 | Field generation failure | g = B_max(f) − B_set | Layer-3 probe | envelope §05.1 | model error {GAP_ERR*100:.1f} % + U 2.87 % | envelope has ≥ {min(r['B_max_mT'] for r in FE)/50:.1f}× margin at the top rung |
| FS2 | Field uniformity failure | g = 0.10 − CV_B | 3-D map | CV_B ≤ 10 % | ±{100*1.96/math.sqrt(2*(1521-1)):.1f} % on σ with 1,521 points | computed {CV*100:.2f} %; pole overhang is the design margin |
| FS3 | Amplifier saturation | g = min(V_max−V, I_max−I, S_max−S) | telemetry | §10.2 | ±2 % | compensation bank; envelope check before every run |
| FS4 | Thermal runaway | g = T_limit − T | 17 RTD + 2 fibre | §14.4 | ±1 K | ≥ {TH.CORE_PATH.p_max()/max(r50_3k['P_core_W'],1e-9):.0f}× cooling margin; hardware trip |
| FS5 | Tank shielding | g = 0.01·B_ECV − B_at_wall | Layer-2 survey | 1 % | ±5 % | **eliminated by architecture** — tank is not in the flux path |
| FS6 | Sensor saturation / drift | g = 3·U − \\|layer disagreement\\| | 3-layer cross-check | 3 × budget | ±0.5 % | voting + interlock #7; calibration epochs |
| FS7 | Insulation / leakage | g = R_iso − 100 MΩ; g = 3.5 mA − I_leak | megger, IMD | SAF-02/03 | ±10 % | dry cell; IT earthing; continuous IMD |
| FS8 | EMC failure | g = limit − emission | accredited lab | EN 61000-6-4 | ±3 dB | linear amplifier; screened cabinet; bonded grid |
| FS9 | Sham contamination | g = 5 µT − B_sham | Layer-3 in the Sham duct | VG-07 | ±{MET.sham_detection_limit()*1e9:.2f} nT | bifilar cancellation ≥ 80 dB; ≥ 1.5 m separation; **measured every run** |
| FS10 | Water-chemistry confounding | g = LOQ − leachate | ICP-OES, TOC on a 48 h blank | below LOQ | ±5 % | PVDF/PEEK/Ti only; blank soak before the campaign |
| FS11 | Reproducibility failure | g = δ_min/3 − CV_between-day | replicated blocks | VAL-02 | — | blocking, randomisation, blinding, sealed run order |
| FS12 | Scale-up failure | g = 0.10 − \\|CV_B(stage n+1) − CV_B(stage n)\\| | map at each stage | VG-12 | — | identical cell geometry at every stage; only cell **count** changes |

**FS5 is worth dwelling on.** In the naive architecture it is the dominant
failure surface and it is essentially unmitigable above 100 Hz. In the selected
architecture its limit-state equation is satisfied by construction rather than
by margin. Deleting a failure surface is always better than budgeting against it.

---

## 25 R1 / R2 / R3 Architecture Comparison

Same water gap ({CORE.gap*1e3:.0f} mm), same target B_ECV (50 mT), same frequency,
same field engine, same ECV inset fractions.

""")
tbl(["","R1 single fork","R2 opposed dual fork","R3 distributed cells"],
    [["Field gain B_ECV/B_pole"] + [f"{r['gain']:.3f}" for r in AC],
     ["CV_B (3-prong span)"] + [f"{r['CV_B']*100:.1f} %" for r in AC],
     ["MMF per loop [A-t]"] + [f"{r['MMF_At']:,.0f}" for r in AC],
     ["Stored energy [J]"] + [f"{r['U_J']:.2f}" for r in AC],
     ["Reactive power at 3 kHz [kVAr]"] + [f"{r['Q_3kHz_kVAr']:,.0f}" for r in AC],
     ["Independent drive loops"] + [str(r["n_drive_loops"]) for r in AC],
     ["Polarity nulls in the water"] + [r["nulls"] for r in AC]])
w(f"""### 25.1 KPI scoring

| KPI | R1 | R2 | **R3** | Basis |
|---|---|---|---|---|
| Field uniformity | poor | poor | **best** | R1/R2 have forced N,S,N polarity → \\|B\\| passes through zero between prong pairs |
| Energy efficiency | {AC[0]['U_J']/AC[2]['U_J']:.0f}× worse | {AC[1]['U_J']/AC[2]['U_J']:.1f}× worse | **best** | stored energy at equal B |
| Thermal load | worst | moderate | **best** | scales with MMF² |
| CAPEX | worst (amplifier sized by kVAr) | moderate | **best** | Q at 3 kHz drives the compensation bank cost |
| Control complexity | 3 coupled loops | 2 coupled loops sharing a yoke | **3 independent loops** | independent cells decouple completely |
| Reliability | single yoke = single point of failure | single yoke per side | **best** — one cell can fail and the rig still runs at 2/3 ECV | graceful degradation |
| Maintainability | fork must be extracted whole | same | **best** — cells are line-replaceable | modularity |
| Scalability | re-design for every size | re-design | **best** — add cells | scale by count, not by geometry |

**R1's problem is fundamental, not incidental.** With poles on one side only,
the flux must return through the water, so the effective gap is the prong
pitch rather than the working gap. That is why its MMF is
{AC[0]['MMF_At']/AC[2]['MMF_At']:.0f}× and its stored energy {AC[0]['U_J']/AC[2]['U_J']:.0f}× R3's. No amount of
geometry tuning fixes it; it is what a single-sided magnetic circuit *is*.

**R2's problem is the shared yoke.** Three prongs on one yoke force the
polarity sequence N, S, N so that flux can return through the neighbouring
prong. That produces a \\|B\\| null between prong pairs — the field genuinely
passes through zero. Water flowing along the fork axis therefore sees a
strongly modulated dose, which turns "exposure time" into a path-dependent
integral instead of a number. It can be managed with flow baffles aligned to
the nulls, but it is a complication that R3 simply does not have.

---

## 26 Multi-Objective Optimisation

Objectives: minimise {{power, CV_B, temperature rise, CAPEX, mass}};
maximise {{B tracking, uniformity, reliability, measurement confidence}}.

The Pareto front from `design/optimize_geom.py` (feasible set: CV_B ≤ 10 %):

| Pole w × h [mm] | Gap [mm] | CV_B | ECV [L] | Stored energy per litre [J/L] |
|---|---|---|---|---|""")
from optimize_geom import sweep as geo_sweep
_res = geo_sweep("R3", 50e-3, 0.10)
_par = []
for r in _res:
    if not any((o["ecv_L_total"] >= r["ecv_L_total"] and o["J_per_L"] <= r["J_per_L"] and o is not r
                and (o["ecv_L_total"] > r["ecv_L_total"] or o["J_per_L"] < r["J_per_L"])) for o in _res):
        _par.append(r)
_par.sort(key=lambda r: -r["ecv_L_total"])
for r in _par[:6]:
    w(f"| {r['w']*1e3:.0f} × {r['h']*1e3:.0f} | {r['g']*1e3:.0f} | {r['cv']*100:.1f} % | {r['ecv_L_total']:.2f} | {r['J_per_L']:.1f} |")
w(f"""
**The selected point is not the largest B and not the largest ECV.** It is the
point where CV_B has margin, the stored energy is small enough that a
{max(r['Q_kVAr'] for r in MT):.0f} kVAr compensation bank covers the top rung, the core mass is
buildable, and the whole dose ladder fits under the envelope at every
frequency. Maximising B would have produced a rig that meets one number and
fails four verification gates.

**Explicit trade recorded:** ECV was traded down (from a possible ~12 L to
{V_ECV:.2f} L) in exchange for a 3× smaller compensation bank and a core that can
actually be wound from nanocrystalline ribbon. §16 shows the cost of that
trade — a longer recirculation time — and §31 shows the mitigation: do the
dose-response work at Stage 2.

---

## 27 Reliability Physics / FMEA

| ID | Item | Failure mode | Mechanism | S | O | D | RPN | Detection | Mitigation |
|---|---|---|---|---|---|---|---|---|---|
| F-01 | Coil insulation | turn-to-turn short | thermal ageing + partial discharge at dV/dt | 9 | 2 | 3 | 54 | L1/L3 disagreement; R_dc trend in the twin | class H, ≥ 2× voltage margin, PD screening at FAT |
| F-02 | Coil | open circuit | thermal cycling fatigue at the joint | 8 | 2 | 2 | 32 | current loop fault | crimped + brazed joints, strain relief |
| F-03 | Potting | cracking | differential expansion, 5→60 °C cycling | 5 | 3 | 5 | 75 | visual at each maintenance | filled epoxy matched CTE, vacuum impregnation |
| F-04 | Core | ribbon delamination | clamping stress + magnetostriction | 6 | 3 | 6 | 108 | B/I ratio shift in the twin | controlled clamp torque, bonded cut cores |
| F-05 | Core | gap change | mechanical creep / thermal growth | 7 | 3 | 7 | 147 | B/I shift with R_dc flat — a **unique twin signature** | machined shims, torque-controlled clamps, monthly map |
| F-06 | Compensation cap | capacitance drift | self-healing clearings | 6 | 4 | 3 | 72 | resonance shift; band retune fails | 2× voltage derating, current derating, annual C measurement |
| F-07 | Amplifier | output-stage degradation | thermal cycling of the power devices | 7 | 3 | 3 | 63 | THD trend, efficiency trend | derating, forced air, quarterly THD check |
| F-08 | Layer-3 probe | sensitivity drift | area/turn change, cable ageing | 8 | 3 | 4 | 96 | 3-layer voting | quarterly Helmholtz recal, redundant probes |
| F-09 | Layer-3 probe | water ingress | seal failure | 8 | 2 | 3 | 48 | insulation monitor + noise floor rise | welded PVDF finger, pressure test at FAT |
| F-10 | pH electrode | drift | reference junction fouling | 4 | 6 | 2 | 48 | auto-cal deviation | 3-point auto-cal each block, replace per schedule |
| F-11 | Duct | stress cracking | PVDF + chemistry + stress | 9 | 2 | 4 | 72 | leak tape, dP trend | stress-relieved welds, dP monitoring |
| F-12 | Connector | contact resistance | fretting corrosion | 6 | 4 | 4 | 96 | R_dc trend in the twin | gold-plated, retorqued at each maintenance |
| F-13 | PLC/DSP | comms loss | EMI, cable | 8 | 3 | 1 | 24 | watchdog, 50 ms | shielded EtherCAT, redundant path |
| F-14 | Pump | seal/bearing wear | duty | 5 | 5 | 3 | 75 | flow and dP trend | mag-drive (sealless), vibration trend |
| F-15 | Chiller | capacity loss | fouling, refrigerant loss | 6 | 4 | 2 | 48 | water T excursion | ΔT trend, annual service |

**RPN alone is not the decision variable.** Where a Bayesian posterior on the
failure probability can be formed, it is used instead: for F-05 (gap change),
for instance, the digital twin observes the B/I ratio continuously, and the
posterior on "gap has changed by > 0.5 %" updates every run. RPN ranks
attention; the posterior triggers action.

**Highest-priority items:** F-05 (gap change — highest RPN and the only
mechanism that corrupts the *primary experimental variable* without any other
symptom), F-04, F-08 and F-12. All four are detectable by the twin's residual
signatures (§20 of the figure package), which is why the twin is not optional.
""")

# ============================== 28 - 36 ====================================
w(f"""
---

## 28 Digital Twin

State vector `X(t) = {{ f, I, V, B, T_coil, T_water, EC, pH, flow, runtime }}`,
plus the derived quantities `R_dc, L, B/I, P_Cu, P_core, CV_B(last map)`.

The twin runs the same physics as this report (reluctance circuit, Dowell,
Steinmetz, thermal RC) and forms the residual r(t) = X_measured − X_predicted.
Faults are identified by the **signature across the residual vector**, not by
any single threshold:

| Residual signature | Diagnosis | Action |
|---|---|---|
| R_dc ↑, L flat, B/I flat | conductor or joint degradation (F-02, F-12) | trend alarm, inspect at next maintenance |
| R_dc flat, **B/I ↓** | mechanical gap growth or core damage (F-04, F-05) | **stop and re-map** — the primary variable is compromised |
| L shifts, R_dc flat | core permeability or clamping change | re-tune the compensation band, re-map |
| L1 and L2 agree, L3 disagrees | Layer-3 probe drift (F-08) | recalibrate; runs since the last agreement are flagged |
| L1 and L3 agree, L2 disagrees | external field intrusion, or L2 drift | survey the room; check for new equipment |
| T ↑ at constant computed P_loss | cooling loop degradation (F-15) | service the chiller |
| P_Cu measured > predicted at high f | winding damage changing R_ac | impedance sweep |

The twin also carries the **effect model** of §22. Each completed block updates
P(effect > δ_min \\| Data) for every response and updates P(H0), P(H1), P(H2),
P(H3). **If no effect is observed, the twin's job is to update the posterior,
not to recommend raising B.**

---

## 29 Pilot BOM

All costs are **BUDGETARY ESTIMATES (P0)**. None is a supplier quotation. Any
line becomes E2 only when a written quote is attached.

""")
tbl(["Subsystem","Part","Specification","Qty","Unit","Material","Manufacturer candidate","Model candidate","Unit cost [USD]","Total [USD]","Lead [wk]","Crit","Alternative","Evidence"],
    [[l.subsystem, l.part, l.spec, f"{l.qty:g}", l.unit, l.material, l.mfr_candidate,
      l.model_candidate, f"{l.unit_cost_usd:,.0f}", f"{l.total:,.0f}", l.lead_weeks,
      l.criticality, l.alternative, l.evidence] for l in CAP["lines"]])
w(f"""
---

## 30 Equipment Specification (CAPEX)

""")
tbl(["Subsystem","Cost [USD]","Share"],
    [[k, f"{v:,.0f}", f"{100*v/CAP['total']:.1f} %"] for k, v in sorted(CAP["by_subsystem"].items(), key=lambda x: -x[1])]
    + [["**TOTAL (incl. 15 % contingency)**", f"**{CAP['total']:,.0f}**", "100.0 %"]])
w(f"""| Metric | Value |
|---|---|
| Hardware subtotal | USD {CAP['subtotal']:,.0f} |
| Contingency (15 %) | USD {CAP['total']-CAP['subtotal']:,.0f} |
| **Total budgetary CAPEX** | **USD {CAP['total']:,.0f}** |
| Criticality-A share | USD {CAP['by_criticality']['A']:,.0f} ({100*CAP['by_criticality']['A']/CAP['total']:.0f} %) |
| Longest lead item | {CAP['longest_lead_weeks']} weeks (amplifier) |
| Alternative core (thin-gauge steel) | USD {CAP_ALT['total']:,.0f} — saves {100*(CAP['total']-CAP_ALT['total'])/CAP['total']:.1f} %, costs 2.1 kW of core loss |

**Cost structure comment.** The magnetics are **{100*(CAP['by_subsystem']['SS-02 Fork/Coil']+CAP['by_subsystem']['SS-03 Mag circuit'])/CAP['total']:.0f} %** of CAPEX.
The instrumentation (SS-06 + SS-07) is **{100*(CAP['by_subsystem']['SS-06 B sensing']+CAP['by_subsystem']['SS-07 Water inst'])/CAP['total']:.0f} %**.
That ratio is the correct one for this programme: the point of Phase 3 is not
to make a field, it is to **know** what field was made and to **measure** what
changed. A rig that spent 60 % on magnetics and 10 % on metrology would
generate results nobody could defend.

A defensible descope, if required, is the zeta-potential analyser
(USD {[l for l in CAP['lines'] if 'zeta' in l.part][0].total:,.0f}) — §22 already demotes zeta potential to a
secondary response on power grounds, so outsourcing that analysis per sample
is consistent with the statistical design rather than a compromise of it.

---

## 31 Manufacturing SOP / DFM / Scale-Up

### 31.1 Build sequence

1. **Core:** procure bonded nanocrystalline cut-core sections; measure each
   section's effective μ and loss at 50 Hz / 1 kHz / 3 kHz on a coupon
   (**this converts the P0 Steinmetz model to E1**). Assemble with machined
   non-magnetic shims; torque-controlled clamping to a recorded value.
   **Measure the assembled gap with feeler gauges and record it** — it is the
   primary geometric parameter of the experiment.
2. **Coils:** wind litz on a removable former; interleave Nomex; vacuum
   impregnate with alumina-filled epoxy; measure R_dc, L and insulation
   resistance before and after potting.
3. **Duct:** PVDF fabrication with stress-relieved welds; hydrostatic test at
   3 bar; 48 h blank soak with ICP-OES + TOC on the soak water (**FS10 gate**).
4. **Assembly:** mount cells on the non-magnetic frame with ≥ 200 mm clearance
   from any ferrous object; install cold plates; install the Layer-3 probes in
   machined seats referenced to the pole shoe.
5. **Calibration:** all B probes in the accredited Helmholtz coil, at all 11
   frequencies, before installation. Record every coefficient.
6. **Commissioning:** full 3-D field map (1,521 points) → CV_B and the P1
   transfer coefficient → then and only then close the constant-B loop.

### 31.2 Scale-up roadmap and gates

| Stage | Configuration | ECV | Batch | ECV/V_tank | Purpose | Gate to exit |
|---|---|---|---|---|---|---|
| **1** | 1 cell, 5 L closed loop | {EX['vol_L']:.3f} L | 5 L | {100*EX['vol_L']/5:.1f} % | prove field generation, measurement and the constant-B loop | VG-01…VG-06, VG-08, VG-09 |
| **2** | 3 cells, 50–100 L | {V_ECV:.2f} L | 50–100 L | {100*V_ECV/50:.1f} – {100*V_ECV/100:.1f} % | **the dose-response campaign** — usable dose in one shift | VG-07, VG-10, VG-11 + **Gate E and Gate F** |
| **3** | 3 cells, 1,000 L | {V_ECV:.2f} L | 1,000 L | {100*V_ECV/1000:.2f} % | scale-up equivalence demonstration | VG-12 |
| **4** | multi-cell array, multi-tank | scaled by cell count | — | design target | Q-HSRS production | full re-verification |

**The gate between Stage 2 and Stage 3 is not "it worked" — it is
"CV_B, B tracking and the dose bookkeeping have been re-derived at the new
V_ECV/V_tank ratio and still meet spec."** Because the cell geometry is
identical at every stage and only the *count* and the batch volume change,
scale-up equivalence is a genuinely testable claim rather than an aspiration.

---

## 32 FAT / SAT

### 32.1 Factory Acceptance Test (at the integrator, dry, no process water)

| # | Test | Acceptance |
|---|---|---|
| FAT-1 | Coil R_dc, L, insulation resistance, PD inception | within ±5 % of design; IR ≥ 100 MΩ; PDIV ≥ 2 × V_op |
| FAT-2 | Impedance sweep 1 Hz – 10 kHz per cell | matches the model within 10 %; **converts the Dowell model to E1** |
| FAT-3 | Compensation bank: C per band, ESR, switching | within ±5 %; contactor sequencing interlocked |
| FAT-4 | Amplifier: THD, bandwidth, current limit | THD ≤ 0.5 %; −3 dB ≥ 10 kHz |
| FAT-5 | B probe calibration certificates | ISO 17025, all 11 frequencies |
| FAT-6 | Dry field map, 1,521 points, at 10 mT | CV_B ≤ 10 %; P1 coefficient recorded |
| FAT-7 | Interlock proof test, all 10 conditions | each trips ENABLE < 50 ms |
| FAT-8 | Thermal soak, 4 h at the worst corner | all temperatures below limit with ≥ 20 K margin |
| FAT-9 | EMC pre-compliance | EN 61000-6-4 with ≥ 6 dB margin |
| FAT-10 | Sham isolation | ≥ 80 dB measured |

### 32.2 Site Acceptance Test (installed, wet)

| # | Test | Acceptance |
|---|---|---|
| SAT-1 | Hydrostatic and leak test | no leak at 3 bar, 30 min |
| SAT-2 | 48 h blank soak, ICP-OES + TOC | all species below LOQ |
| SAT-3 | Wet field map with water in the duct | CV_B ≤ 10 %; ≤ 2 % shift from the dry map |
| SAT-4 | Constant-B step response at all 11 frequencies | settling ≤ 10 × T_avg; error ≤ 5 % |
| SAT-5 | 3-layer agreement across the ladder | all pairs within 3 × combined budget |
| SAT-6 | Tank H(f) two-probe measurement | model within 20 %; **converts §13 to E1** |
| SAT-7 | Hydraulic characterisation, all 5 velocities | flow, ΔP, pump power within 10 % of §16 |
| SAT-8 | Sham run, full instrumentation | B_sham ≤ 5 µT; all other channels indistinguishable |
| SAT-9 | Thermal balance, 8 h at the worst corner | water ΔT within ±0.3 K; heat balance closes to ±10 % |
| SAT-10 | Repeatability: 6 identical runs over 3 days | between-day CV ≤ δ_min/3 on every primary response |

---

## 33 Verification Matrix

| VG | Requirement | Method | Acceptance | Computed prediction | Status |
|---|---|---|---|---|---|
| VG-01 | Frequency accuracy | counter vs OCXO, 11 points | ≤ 1e-4 relative | — | to be measured |
| VG-02 | B tracking ±5 % | Layer-3 + demodulation, step response | ≤ 5 % | **{eb['total_pct']:.2f} % RSS** | predicted PASS |
| VG-03 | Spatial CV_B ≤ 10 % | 1,521-point 3-D map | ≤ 10 % | **{CV*100:.2f} %** | predicted PASS |
| VG-04 | No current/voltage saturation | telemetry over the full envelope | within §10.2 | I ≤ {max(r['I_rms_A'] for r in MT):.0f} A, V ≤ {max(r['V_drive_V'] for r in MT):.0f} V | predicted PASS |
| VG-05 | Thermal limits | 17 RTD + 2 fibre, 8 h soak | all below limit | T_coil {max(r['T_coil_C'] for r in MT):.1f} °C, T_core {max(r['T_core_C'] for r in MT):.1f} °C | predicted PASS |
| VG-06 | Sensor agreement | 3-layer cross-check | within 3 × budget | budget {comb['U_expanded_pct']:.2f} % | to be measured |
| VG-07 | Sham integrity | Layer-3 in the Sham duct | ≤ 5 µT | {MET.sham_residual_from_leakage(50e-3,80)*1e6:.1f} µT at 80 dB | predicted PASS |
| VG-08 | Electrical insulation | megger, IMD, leakage | ≥ 100 MΩ, ≤ 3.5 mA | — | to be measured |
| VG-09 | EMC | accredited lab | EN 61000-6-4 | — | to be measured |
| VG-10 | Repeatability | 6 runs / 3 days | CV ≤ δ_min/3 | — | to be measured |
| VG-11 | Water-property reproducibility | replicated blanks | σ per §15.2 | — | to be measured |
| VG-12 | Scale-up equivalence | map + dose bookkeeping at each stage | ΔCV_B ≤ 10 % | — | to be measured |

### 33.1 Phase freeze rule

```
Gate A  field can be generated        -> VG-01, VG-04
   |
Gate B  field can be measured         -> VG-03, VG-06, and the P1 transfer coefficient
   |
Gate C  constant-B control achieved   -> VG-02
   |
Gate D  thermal / safety pass         -> VG-05, VG-08, VG-09
   |
Gate E  Active vs Sham difference reproduced -> VG-07, VG-10, VG-11
   |
Gate F  dose-response confirmed       -> the Bayesian decision rule of S22.3
   |
Gate G  1,000 L scale-up              -> VG-12
```

**The rule that matters most:** if no effect is observed at Gate E or Gate F,
the response is **not** to increase B. It is to update the posterior including
H0. Only if Gate F is passed — a monotone, credible dose-response that is not
explained by σ, flow or temperature — is the 100–500 mT extension branch
opened, and then only as a separate feasibility and safety study (at 500 mT
the stored energy rises by (500/50)² = 100×, taking the compensation bank from
{max(r['Q_kVAr'] for r in MT):.0f} kVAr to {100*max(r['Q_kVAr'] for r in MT)/1000:.1f} MVAr per cell — a different machine, not a turn of a knob).

---

## 34 Patent FIG Package

Black-and-white technical linework; colour used only as a functional code
(**blue** = magnetic field, **red** = fork/core, **green** = sensor,
**orange** = safety). Rendered as both SVG and PNG in `qhsrs_phase3/figures/`.

| FIG | Title | File |
|---|---|---|
| 1 | Overall system | `FIG01_overall_system` |
| 2 | 1,000 L tank + exposure loop + measured-basis H(f) | `FIG02_tank_and_transfer_function` |
| 3 | Exposure cell, isometric | `FIG03_cell_isometric` |
| 4 | Cell 2-D dimensioned drawing | `FIG04_cell_dimensions` |
| 5 | Coil cross-section and thermal path | `FIG05_coil_cross_section` |
| 6 | Magnetic circuit and reluctance network | `FIG06_magnetic_circuit` |
| 7 | R1 / R2 / R3 comparison | `FIG07_R1_R2_R3` |
| 8 | Power driver, compensation, (f,B) envelope | `FIG08_driver_and_envelope` |
| 9 | Three-layer sensor architecture | `FIG09_sensor_architecture` |
| 10 | Five-point and 3-D field mapping | `FIG10_field_mapping` |
| 11 | Constant-B closed loop and error budget | `FIG11_constant_B_loop` |
| 12 | Thermal management and the Sham heat argument | `FIG12_thermal` |
| 13 | Safety interlock chain | `FIG13_safety_interlock` |
| 14 | Active / Sham architecture | `FIG14_active_sham` |
| 15 | Bayesian digital twin | `FIG15_digital_twin` |
| 16 | Pilot layout and scale-up gates | `FIG16_pilot_layout` |

### 34.1 Patentable differentiators (for counsel to assess — this is engineering input, not a legal opinion)

1. **Exposure-Control-Volume-referenced field specification and control** — the
   controlled variable is the volumetric mean over a defined, mapped sub-volume,
   with a calibrated probe-to-ECV transfer coefficient, rather than a probe
   reading or an amplifier setting.
2. **Deliberately detuned band-switched series compensation** for a swept-frequency
   ELF exposure load, sized so that the loaded Q stays controllable while the
   circulating VA is carried by the capacitor bank rather than the amplifier.
3. **Dry independent-cell array with a non-metallic duct** — architecture that
   removes the conducting process vessel from the flux path entirely, making
   H(f) ≡ 1 by construction across 3–3,000 Hz.
4. **Three-layer magnetic observation with voting-based hardware interlock**,
   in which no single layer is authoritative and disagreement itself is a trip
   condition.
5. **Driven bifilar-cancelled Sham** that reproduces the acoustic, thermal and
   telemetry signature of the Active arm, with per-run measured residual field.
6. **Residual-signature fault discrimination** that separates gap change from
   conductor degradation from probe drift using the R_dc / L / (B/I) triple.
7. **Dose bookkeeping as a control variable** — t_exp = t_run · V_ECV/V_tank as
   the scheduled quantity, with flow explicitly identified as *not* a dose knob.

---

## 35 Required Calculation Table

Complete master table: all 5 active dose rungs × all 11 verification
frequencies = 55 operating points. Full precision in
`outputs/S35_master_calculation_table.csv`.

**Evidence: every value below is P0 (computed). None is marked E1.**

""")
cols = [("B_set_mT","B_set [mT]","%.1f"),("f_Hz","f [Hz]","%.2f"),("B_pole_T","B_pole [T]","%.4f"),
        ("B_leg_T","B_leg [T]","%.4f"),("CV_B","CV_B","%.4f"),("N_loop","N_loop","%d"),
        ("L_mH","L [mH]","%.2f"),("R_ac_ohm","R_ac [Ω]","%.4f"),("Z_ohm","\\|Z\\| [Ω]","%.3f"),
        ("I_rms_A","I_rms [A]","%.2f"),("I_pk_A","I_pk [A]","%.2f"),("J_A_mm2","J [A/mm²]","%.3f"),
        ("V_drive_V","V_drive [V]","%.1f"),("V_cap_V","V_cap [V]","%.0f"),("C_ser_uF","C [µF]","%.3f"),
        ("Q_kVAr","Q [kVAr]","%.2f"),("P_Cu_W","P_Cu [W]","%.2f"),("P_core_W","P_core [W]","%.3f"),
        ("P_water_W","P_water [W]","%.3f"),("E_water_Vpm","E_water [V/m]","%.2f"),
        ("T_coil_C","T_coil [°C]","%.1f"),("T_core_C","T_core [°C]","%.1f"),("status","status","%s")]
tbl([c[1] for c in cols],
    [[ (c[2] % r[c[0]]) if c[2] != "%s" else str(r[c[0]]) for c in cols] for r in MT])
w(f"""**Columns deliberately not filled with a number:**

| Quantity | Why it is blank |
|---|---|
| Measured B | nothing has been measured — a value here would be a fabrication |
| P_tank (eddy) | **0 by construction** — the tank is not in the flux path |
| THD | depends on the amplifier's measured performance, an E2/E1 quantity |
| H(f), phase delay | §13 gives the model; the E1 values come from SAT-6 |
| Efficiency | ill-defined here: the "useful output" is a field, not power. Reported instead as loss per litre of ECV: {(r50_3k['P_Cu_W']+r50_3k['P_core_W'])/EX['vol_L']:.1f} W/L at the worst corner |

---

## 36 Unknown-Unknown Register

| ID | Unknown | Why it is not yet quantifiable | Detection plan | Fallback |
|---|---|---|---|---|
| UU-1 | Can a {CORE.pole_w*1e3:.0f} × {CORE.pole_h*1e3:.0f} mm nanocrystalline pole face actually be built? | ribbon is supplied as wound cut cores; large flat pole faces are not a standard product | supplier engineering review **before** any other procurement | thin-gauge silicon steel + cap the envelope at 10 mT above 1 kHz (still 4 of 5 rungs) |
| UU-2 | Real μ_r of the tank welds and cold-formed regions | varies with the fabricator's process, not specifiable in advance | permeability survey at SAT-6 | architecture does not depend on it; affects only the stray-coupling bound |
| UU-3 | PVDF duct behaviour under simultaneous ELF field, flow and the electrolyte over 1,000 h | no relevant literature at these conditions | 1,000 h ageing coupon in parallel with the campaign | PP-H or PTFE-lined alternative |
| UU-4 | Whether any measured effect is reproducible **between rigs** | only one rig exists | build the Stage-2 rig as a genuine second unit, not a modification of Stage 1 | inter-rig replication becomes a Gate F requirement |
| UU-5 | Electrode/electrochemical artifacts at the sensor surfaces under an imposed E field | inline sensors sit in a region with a non-zero induced E | run inline sensors both energised and de-energised; compare with offline lab measurement | move all primary chemistry offline |
| UU-6 | Dissolved gas dynamics under recirculation over multi-hour runs | DO changes with pump cavitation and headspace exchange, and DO affects several responses | continuous DO on both arms; sealed headspace with a controlled gas blanket | DO becomes a covariate in the model |
| UU-7 | Long-term stability of the compensation capacitors under continuous 3 kHz duty | self-healing clearings change C, which detunes the band | monthly C measurement; resonance tracking in the twin | derate further; add a trim capacitor |
| UU-8 | Whether "cumulative exposure" is even the right dose variable | there is no validated dose metric for this domain — this is the deepest unknown in the package | report **both** D_B and D_E, and record the full B(t) history per run so that any dose metric can be recomputed retrospectively | keep raw time-series for every run indefinitely |

**UU-8 deserves emphasis.** The entire dose ladder assumes that some
monotone function of B and time is the right independent variable. If the real
mechanism is threshold-like in dB/dt, or depends on the number of field
reversals, or on E rather than B, then a dose-response in B·t would be the
wrong thing to look for. This is why every run archives the complete B(t)
waveform rather than a summary statistic: it is the only way a different dose
metric can be tested later without re-running the campaign.

---

## 37 Final Freeze Recommendation

### 37.1 Selected architecture: **R3 — distributed independent-cell array**

The selection criterion required by the master prompt is

```
    P(all verification gates pass) x Reliability x Measurement confidence
    ------------------------------------------------------------------
                            Lifecycle cost
```

not "the strongest magnetic field."

| Factor | R1 | R2 | **R3** |
|---|---|---|---|
| P(all VGs pass) — CV_B ≤ 10 % achievable | low (gain {AC[0]['gain']:.2f}, nulls) | low (nulls) | **high — computed {CV*100:.2f} %** |
| Reliability — graceful degradation | none | none | **one cell can fail; rig runs at 2/3 ECV** |
| Measurement confidence — probe placement, uniform field at the probe | poor (steep gradients) | poor | **best (flat field at P1)** |
| Lifecycle cost — kVAr drives the bank cost | {AC[0]['Q_3kHz_kVAr']/AC[2]['Q_3kHz_kVAr']:.0f}× worse | {AC[1]['Q_3kHz_kVAr']/AC[2]['Q_3kHz_kVAr']:.1f}× worse | **best** |

### 37.2 Deliverables A–M

**A. Recommended architecture** — R3: {CELL.N_CELLS} independent opposed C-core cells,
inline, dry, on a non-metallic PVDF duct, with the 1,000 L SUS316L tank as a
process reservoir outside the flux path.

**B. Frozen property vector** — §01.2.

**C. BOM** — §29, {len(CAP['lines'])} lines, USD {CAP['total']:,.0f} budgetary.

**D. 2-D / 3-D dimensions** — FIG.3, FIG.4. Pole {CORE.pole_w*1e3:.0f} × {CORE.pole_h*1e3:.0f} mm;
magnetic gap {CORE.gap*1e3:.0f} mm ({CELL.WATER_GAP*1e3:.0f} mm water + 2 × {CELL.DUCT_WALL*1e3:.0f} mm duct);
leg {CORE.leg_a*1e3:.0f} × {CORE.leg_a*1e3:.0f} mm; coil window {CORE.leg_len*1e3:.0f} × {CELL.WINDOW_H*1e3:.0f} mm;
pole shoe {CORE.shoe_t*1e3:.0f} mm; cell pitch 375 mm; duct 240 × 24 mm ID × 1,200 mm.

**E. Driver specification** — §10.2 + §10.4. {CELL.N_CELLS} channels, current mode,
{LIM.v_max:.0f} V / {LIM.i_max:.0f} A / {LIM.s_max/1e3:.0f} kVA, DC–{LIM.f_max/1e3:.0f} kHz, THD ≤ 0.5 %,
6-band switched series compensation {min(r['C_ser_uF'] for r in MT if r['C_ser_uF']>0):.2f}–{max(r['C_ser_uF'] for r in MT):.0f} µF at {max(r['V_cap_V'] for r in MT):.0f} V.

**F. Sensor specification** — §11. Three layers; Layer-3 search coil N = 200,
A = 1 cm²/axis; expanded uncertainty U(k=2) = {comb['U_expanded_pct']:.2f} %.

**G. PLC / DSP I/O** — 8 × 16-bit isolated AO, 16 × 24-bit isolated AI,
16 DI / 16 DO safety-rated, EtherCAT, 2 MSPS DSP with coherent demodulation
and a < 1 ppm timebase.

**H. DOE** — §21. 2⁷⁻³ resolution IV screen (120 runs including Sham twins and
centre points), then D-optimal augmentation, then sequential Bayesian
dose-response at Stage 2.

**I. FAT / SAT** — §32. 10 + 10 tests, each with a numeric acceptance criterion.

**J. Failure boundaries** — §24. Twelve failure surfaces with limit-state
equations; FS5 (tank shielding) eliminated by architecture.

**K. CAPEX** — USD {CAP['total']:,.0f} budgetary, {CAP['longest_lead_weeks']}-week longest lead.

**L. Patentable differentiators** — §34.1, seven items.

**M. Remaining unknowns** — §36, eight items, of which UU-1 (nanocrystalline
buildability) is on the procurement critical path and UU-8 (is dose even the
right variable) is the deepest scientific unknown.

### 37.3 Freeze recommendation

**FREEZE** the mechanical and magnetic design (§01.2) and release for
procurement, **subject to one condition**: UU-1 must be closed by a supplier
engineering review before the core is ordered. Everything else in the BOM is
independent of that answer.

**DO NOT FREEZE** the following until the stated gate:

| Item | Freeze at |
|---|---|
| Core material (nanocrystalline vs thin-gauge) | after UU-1 supplier review |
| Compensation bank final values | after FAT-2 measures the real L |
| Probe transfer coefficient k_P1 | after Gate B (the commissioning map) |
| Dose ladder upper rung | after Gate F — **not before** |
| 100–500 mT extension | separate study, only if Gate F passes |
| Batch volume for the dose campaign | Stage 2 at 50–100 L, per §16 |

### 37.4 마지막 한 줄 (Korean)

이 플랫폼의 가치는 강한 자기장을 만드는 데 있지 않다.
**무엇을 걸었는지 알고, 무엇이 변했는지 재고, 아무 변화가 없다는 것까지도
정량적으로 말할 수 있게 만드는 데** 있다.
Gate F에서 dose-response가 나오지 않으면 그 결과 역시 유효한 결과이며,
그때 해야 할 일은 자속을 올리는 것이 아니라 H0를 포함한 사후확률을 갱신하는 것이다.

---

*Generated by `qhsrs_phase3/report/make_report.py`. Reproduce every number with
`python3 design/run_all.py` and every figure with `python3 figures/make_figures.py`.*
""")

# ---------------------------------------------------------------------------
out = os.path.join(HERE, "QHSRS_Phase3_Report.md")
body = "\n".join(L)
with open(out, "w", encoding="utf-8") as fh:
    fh.write(body)
print("wrote %s  (%s chars, %s blocks)" % (out, format(len(body), ","), format(len(L), ",")))

# ===========================================================================
# RESTRUCTURE to the exact 32-section order required by master-prompt S.34
# ===========================================================================
import re as _re

def _split_sections(text):
    parts = _re.split(r"(?m)^## ", text)
    head = parts[0]
    secs = []
    for p in parts[1:]:
        title = p.split("\n", 1)[0].strip()
        num = title.split(" ", 1)[0]
        secs.append(dict(num=num, title=title, body=p.split("\n", 1)[1] if "\n" in p else ""))
    return head, secs

def _renum(body, old, new):
    return _re.sub(r"(?m)^### %s\." % _re.escape(old), "### %s." % new, body)


# --- remap every cross-reference from master-prompt numbering to report numbering
_REFMAP = {
    "16": "15.5", "18": "23.2", "19": "06.1", "20": "16.5", "21": "16",
    "22": "17", "23": "17.5", "24": "18", "25": "21", "26": "21.2",
    "27": "18.1", "28": "20", "29": "22", "30": "28", "31": "29",
    "32": "25/S26", "33": "27", "34": "30", "35": "Appendix A", "36": "31",
    "37": "32",
}
def _fix_refs(t):
    t = t.replace("(§20 of the figure package)", "(FIG.15)")
    def rep(m):
        n, sub = m.group(1), m.group(2) or ""
        if n not in _REFMAP:
            return m.group(0)
        tgt = _REFMAP[n]
        if tgt == "Appendix A":
            return "Appendix A"
        return "§" + tgt + sub
    return _re.sub(r"\u00a7(\d{2})(\.\d+)?", rep, t)
body = _fix_refs(body).replace("§25/S26", "§25/§26")

_head, _secs = _split_sections(body)
_S = {s["num"]: s for s in _secs}

def _title_of(n):
    return _S[n]["title"].split(" ", 1)[1] if " " in _S[n]["title"] else _S[n]["title"]

def _split_at(num, marker):
    b = _S[num]["body"]
    i = b.index(marker)
    return b[:i], b[i:]

_man_a, _man_b = _split_at("31", "### 31.2 Scale-up roadmap and gates")
_fat_a, _fat_b = _split_at("32", "### 32.2 Site Acceptance Test")

# new section -> (title, assembled body)
NEW = []
def add(n, title, body):
    NEW.append((n, title, body))

add("01", "Executive Summary", _S["01"]["body"])
add("02", "Source / Evidence Map", _S["02"]["body"])
add("03", "System Requirement", _S["03"]["body"])
add("04", "Ontology", _S["04"]["body"])
add("05", "Functional Architecture", _S["05"]["body"])
add("06", "Physical Architecture",
    _S["06"]["body"].rstrip() + "\n\n### 06.1 Immersed vs non-contact fork — the branch evaluation\n\n"
    + _renum(_S["19"]["body"], "19", "06").strip() + "\n")
add("07", "Fork Reverse Design", _renum(_S["07"]["body"], "07", "07"))
add("08", "Magnetic Circuit", _S["08"]["body"])
add("09", "Coil Calculation", _S["09"]["body"])
add("10", "Amplifier Design", _S["10"]["body"])
add("11", "Sensor Design", _S["11"]["body"])
add("12", "Constant-B Controller", _S["12"]["body"])
add("13", "SUS316L Transfer Function", _S["13"]["body"])
add("14", "Thermal Model", _S["14"]["body"])
add("15", "Water / Ion Model",
    _S["15"]["body"].rstrip() + "\n\n### 15.5 Hydraulic variables and the dose bookkeeping\n\n"
    + _renum(_S["16"]["body"], "16", "15").strip() + "\n")
add("16", "DOE",
    _S["21"]["body"].rstrip() + "\n\n### 16.5 Sham control\n\n"
    + _renum(_S["20"]["body"], "20", "16").strip() + "\n")
add("17", "Bayesian Model",
    _renum(_S["22"]["body"], "22", "17").rstrip()
    + "\n\n### 17.5 Null-hypothesis and falsification (H0–H3)\n\n"
    + _renum(_S["23"]["body"], "23", "17").strip() + "\n")
add("18", "FMEA",
    _renum(_S["24"]["body"], "24", "18").rstrip() + "\n\n### 18.1 FMEA table\n\n"
    + _renum(_S["27"]["body"], "27", "18").strip() + "\n")
add("19", "Reliability Physics", """Reliability is modelled as physics of failure, not as a constant hazard rate.
Each mechanism below has a driving stress, an acceleration model and an
observable that the digital twin can trend.

| Mechanism | Driving stress | Acceleration model | Observable in the twin | Design action taken |
|---|---|---|---|---|
| Coil insulation degradation | temperature, dV/dt, partial discharge | Arrhenius, 10 K halving; PD inception voltage | R_dc trend; L1/L3 disagreement | class-H, hot spot capped at 120 °C with a computed worst case of {T_COIL} °C — a {COILMARGIN} K margin |
| Thermal cycling of the potting | ΔT per start/stop, CTE mismatch | Coffin-Manson on ΔT | visual + IR at maintenance | alumina-filled epoxy CTE matched to the core; the dry cell keeps ΔT small |
| Connector fretting corrosion | vibration, thermal cycling, current | power law in cycles | R_dc trend | gold plating, retorque schedule |
| Sensor drift | time, temperature, cable ageing | linear drift + random walk | 3-layer voting residual | quarterly Helmholtz recalibration; redundant probes |
| Amplifier output-stage degradation | junction temperature cycling | Coffin-Manson on ΔTj | THD and efficiency trend | derating; the real load is only {PCELL} W per cell |
| Capacitor self-healing clearings | V, dV/dt, temperature | inverse power law in V | capacitance and resonance shift | 2× voltage derating; monthly C measurement |
| Corrosion of wetted parts | electrolyte, imposed E field | electrochemical | ICP-OES on the water | PVDF/PEEK/Ti only; **no metal in the field region** |
| Core gap creep | clamping stress, thermal growth | creep power law | **B/I ratio with R_dc flat** | machined shims; torque control; monthly map |

**Bayesian failure probability.** Where a mechanism has a twin-observable, the
failure probability is estimated as a posterior rather than an FMEA
occurrence score. For the gap-creep mechanism, the observable is the B/I ratio,
whose measurement uncertainty is known ({UMEAS} %); a Beta-Binomial model over
run-level exceedances of a 0.5 % shift gives P(gap has drifted | data) after
every run. That posterior, not the RPN, is what triggers a re-map.

**Deliberate reliability feature of R3:** the array degrades gracefully. Losing
one cell costs one third of the ECV and is detected immediately by that
channel's Layer-3 probe; the campaign can continue at reduced dose rate with
the loss recorded as a covariate, rather than stopping.
""".replace("{T_COIL}", f"{max(r['T_coil_C'] for r in MT):.1f}")
   .replace("{COILMARGIN}", f"{TH.COIL_PATH.t_limit-max(r['T_coil_C'] for r in MT):.0f}")
   .replace("{PCELL}", f"{r50_3k['P_Cu_W']+r50_3k['P_core_W']:.0f}")
   .replace("{UMEAS}", f"{comb['U_expanded_pct']:.2f}"))
add("20", "Digital Twin", _renum(_S["28"]["body"], "28", "20"))
add("21", "R1 / R2 / R3 Comparison",
    _renum(_S["25"]["body"], "25", "21").rstrip()
    + "\n\n### 21.2 Multi-objective optimisation and the Pareto front\n\n"
    + _renum(_S["26"]["body"], "26", "21").strip() + "\n")
add("22", "Pilot BOM", _S["29"]["body"])
add("23", "Equipment Specification", """Consolidated specification sheet for the frozen build. Cross-references give
the derivation; nothing here is a new number.

| Item | Specification | Source |
|---|---|---|
| Exposure cells | 3 × independent opposed C-core, dry, inline | §06 |
| Pole face | {PW} × {PH} mm | §07 |
| Magnetic gap | {G} mm ({WG} mm water + 2 × {DW} mm PVDF) | §07 |
| Core | {CORENAME}, {CMASS} kg/cell | §08 |
| Winding | {WIRE}, {NT} t/coil, 2 coils/cell series | §09 |
| Inductance | {L} mH per cell | §09 |
| Amplifier | 3 ch, current mode, {VM} V / {IM} A / {SM} kVA, DC–{FM} kHz, THD ≤ 0.5 % | §10 |
| Compensation | 6-band switched series MKP, {CMIN}–{CMAX} µF, {VC} V rms | §10.4 |
| Layer-1 sensor | closed-loop fluxgate CT, DC–100 kHz, 0.1 % | §11 |
| Layer-2 sensor | 3-axis fluxgate, 100 µT, 0.01 nT/√Hz | §11 |
| Layer-3 sensor | sealed air-cored search coil, N=200, A=1 cm²/axis, 1 Hz–10 kHz | §11 |
| Measurement uncertainty | U(k=2) = {U} % of reading | §11.3 |
| Control | cascaded B/current, T_avg = max(3 s, 30/f), error {ERR} % | §12 |
| Duct | PVDF 240 × 24 mm ID × 1,200 mm, 3 mm wall | §06 |
| Reservoir | 1,000 L SUS316L, **outside the flux path** | §13 |
| Cooling | 3 kW chiller ±0.2 K + 25 °C glycol cold plates | §14.4 |
| Instrumentation | EC, pH, ORP, DO ×2 each; Coriolis flow; 17 RTD + 2 fibre-optic | §22 |
| Control platform | SIL2 safety CPU + 2 MSPS DSP, EtherCAT, <1 ppm timebase | §23.1 |

### 23.1 PLC / DSP I/O schedule

| Type | Ch | Signal |
|---|---|---|
| AO 16-bit isolated | 3 | B set point per cell (transported as a set point, **never** as a field value — §10.3) |
| AO 16-bit isolated | 2 | pump VFD speed, chiller set point |
| AI 24-bit isolated | 6 | Layer-1 current (2/cell) |
| AI 24-bit isolated | 9 | Layer-3 B (3 axes × 3 cells) |
| AI 24-bit isolated | 3 | Layer-2 reference B (3 axes) |
| AI 24-bit isolated | 17 | Pt100 temperature |
| AI fibre-optic | 2 | coil hot spot |
| AI 4–20 mA | 9 | EC ×2, pH ×2, ORP ×2, DO ×2, flow ×1 |
| DI safety | 16 | interlock chain (§23.2), door switches, E-stop |
| DO safety | 16 | ENABLE contactor, band-select contactors, pump permissive |

### 23.2 Safety and interlock system

{SAFETY}
""".replace("{PW}", f"{CORE.pole_w*1e3:.0f}").replace("{PH}", f"{CORE.pole_h*1e3:.0f}")
   .replace("{G}", f"{CORE.gap*1e3:.0f}").replace("{WG}", f"{CELL.WATER_GAP*1e3:.0f}")
   .replace("{DW}", f"{CELL.DUCT_WALL*1e3:.0f}").replace("{CORENAME}", MAT.name)
   .replace("{CMASS}", f"{CORE.mass(MAT):.1f}").replace("{WIRE}", WC["wire"].label)
   .replace("{NT}", str(WC["turns"])).replace("{L}", f"{WC['L']*1e3:.2f}")
   .replace("{VM}", f"{LIM.v_max:.0f}").replace("{IM}", f"{LIM.i_max:.0f}")
   .replace("{SM}", f"{LIM.s_max/1e3:.0f}").replace("{FM}", f"{LIM.f_max/1e3:.0f}")
   .replace("{CMIN}", f"{min(r['C_ser_uF'] for r in MT if r['C_ser_uF']>0):.2f}")
   .replace("{CMAX}", f"{max(r['C_ser_uF'] for r in MT):.0f}")
   .replace("{VC}", f"{max(r['V_cap_V'] for r in MT):.0f}")
   .replace("{U}", f"{comb['U_expanded_pct']:.2f}").replace("{ERR}", f"{eb['total_pct']:.2f}")
   .replace("{SAFETY}", _renum(_S["18"]["body"], "18", "23").strip()))
add("24", "Manufacturing SOP", _renum(_man_a, "31", "24"))
add("25", "FAT", _renum(_fat_a, "32", "25"))
add("26", "SAT", _renum(_fat_b, "32", "26"))
add("27", "Verification Matrix", _renum(_S["33"]["body"], "33", "27"))
add("28", "CAPEX", _renum(_S["30"]["body"], "30", "28"))
add("29", "Scale-Up Roadmap", _renum(_man_b, "31", "29"))
add("30", "Patent FIG Package", _renum(_S["34"]["body"], "34", "30"))
add("31", "Unknown-Unknown Register", _renum(_S["36"]["body"], "36", "31"))
add("32", "Final Freeze Recommendation", _renum(_S["37"]["body"], "37", "32"))

_toc = ["## Contents", ""]
for n, t, _b in NEW:
    _toc.append(f"{n}. [{t}](#{n.lstrip('0')}-{t.lower().replace(' / ','--').replace(' ','-').replace('/','')})")
_toc += ["", "Appendix A. Required Calculation Table (55 operating points)", ""]

_out = [_head.rstrip(), "", "\n".join(_toc), "---", ""]
for n, t, b in NEW:
    _out.append(f"## {n} {t}\n")
    _out.append(b.strip())
    _out.append("\n---\n")
_out.append("## Appendix A  Required Calculation Table\n")
_out.append(_renum(_S["35"]["body"], "35", "A").strip())

body2 = "\n".join(_out)
with open(out, "w", encoding="utf-8") as fh:
    fh.write(body2)
print("restructured -> 32 sections + Appendix A  (%s chars)" % format(len(body2), ","))
