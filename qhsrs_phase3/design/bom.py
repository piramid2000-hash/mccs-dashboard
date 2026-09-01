"""
Sections 28, 29 — Pilot hardware BOM and CAPEX.

ALL prices are BUDGETARY ESTIMATES (evidence level P0/T).  None is a quotation.
No line may be presented as a verified purchase price until a supplier
quotation (E2) is attached and the `evidence` field is changed.
"""
from dataclasses import dataclass, field
from typing import List

import cell as CELL
import system as S
from constants import NANOCRYSTALLINE, NO10_THIN, M350_50A

CORE = S.CoreGeom()


@dataclass
class BomLine:
    subsystem: str
    part: str
    spec: str
    qty: float
    unit: str
    material: str
    mfr_candidate: str
    model_candidate: str
    unit_cost_usd: float
    lead_weeks: int
    criticality: str        # A = single point of failure, B, C
    alternative: str
    evidence: str = "P0 budgetary estimate"

    @property
    def total(self):
        return self.qty * self.unit_cost_usd


def build_bom(core_mat=NANOCRYSTALLINE) -> List[BomLine]:
    core_mass = CORE.mass(core_mat)
    core_cost = core_mass * core_mat.cost_kg
    L = []
    A = L.append

    # --- SS-01 Water process ------------------------------------------------
    A(BomLine("SS-01 Water", "Process tank", "1,000 L vertical SUS316L, 2B, "
              "dished bottom, DN50 ports, level probe port, CIP spray ball",
              1, "ea", "SUS316L", "local pressure-vessel fabricator", "custom",
              6500, 10, "A", "SUS304 tank (NOT equivalent: different sigma)"))
    A(BomLine("SS-01 Water", "Exposure duct", "PVDF rectangular duct 240x24 mm "
              "ID, 3 mm wall, 1,200 mm long, flanged, DN50 transitions",
              1, "ea", "PVDF (virgin)", "GF Piping / Agru", "custom fabrication",
              4200, 8, "A", "PP-H duct (lower temp rating, cheaper)"))
    A(BomLine("SS-01 Water", "Circulation pump", "Magnetic-drive centrifugal, "
              "PP/PVDF wetted, 25 m3/h @ 2 bar, VFD driven",
              1, "ea", "PVDF/PP", "Iwaki / March", "MX-serie class",
              3100, 6, "A", "Peripheral pump (higher shear - confounder risk)"))
    A(BomLine("SS-01 Water", "VFD for pump", "2.2 kW, sensorless vector, "
              "Modbus RTU, EMC filter C2", 1, "ea", "-", "Danfoss / ABB",
              "FC-51 class", 650, 4, "B", "soft-start + fixed speed"))
    A(BomLine("SS-01 Water", "Chiller / heat exchanger", "3 kW cooling, "
              "titanium plate HX + glycol chiller, +/-0.2 K control",
              1, "ea", "Ti/SUS316L", "Lauda / Julabo", "process chiller class",
              7800, 8, "A", "tap-water HX (no set-point control - NOT acceptable)"))
    A(BomLine("SS-01 Water", "Sham bypass loop", "Identical duct, identical "
              "length, no core; matched dP orifice", 1, "set", "PVDF",
              "same fabricator", "custom", 2800, 8, "A", "none - required for VG-07"))

    # --- SS-02/03 Magnetics -------------------------------------------------
    A(BomLine("SS-02 Fork/Coil", "C-core set", f"{core_mat.name}; "
              f"{CORE.pole_w*1e3:.0f}x{CORE.pole_h*1e3:.0f} mm pole face, "
              f"{CORE.leg_a*1e3:.0f} mm leg, {CORE.gap*1e3:.0f} mm gap; "
              f"{core_mass:.0f} kg/cell",
              CELL.N_CELLS, "set", core_mat.name.split("(")[0].strip(),
              "Hitachi Metals / VAC / JFE", "cut-core, bonded, gapped",
              core_cost, 16, "A",
              "0.10 mm thin-gauge silicon steel: -70% cost, +2.1 kW loss at "
              "the 50 mT/3 kHz corner (see S08)"))
    A(BomLine("SS-02 Fork/Coil", "Litz coil", "Litz 2000 x 0.20 mm, 16 turns "
              "per coil, 2 coils per cell, class-H polyimide, vacuum "
              "epoxy potted with alumina filler",
              2 * CELL.N_CELLS, "ea", "Cu / epoxy", "Rudolf Pack / New England Wire",
              "custom wound", 1150, 10, "A", "AWG-6 solid (Fr=6.4 at 3 kHz - rejected)"))
    A(BomLine("SS-03 Mag circuit", "Cold plate + clamp frame", "6061-T6 "
              "water-cooled cold plate, non-magnetic clamping, 316L hardware",
              CELL.N_CELLS, "set", "Al 6061 / SUS316L", "Boyd / Wakefield",
              "liquid cold plate", 890, 6, "B", "forced-air heatsink (marginal)"))
    A(BomLine("SS-03 Mag circuit", "Non-magnetic structural frame", "SUS316L "
              "30x30 profile, >200 mm clearance from any pole face",
              1, "set", "SUS316L", "item / Bosch Rexroth", "profile system",
              2400, 4, "C", "painted mild steel (REJECTED - flux distortion)"))

    # --- SS-04/05 Power electronics ----------------------------------------
    A(BomLine("SS-04 Amplifier", "4-quadrant current-mode power amplifier",
              "DC-10 kHz, 600 V rms / 200 A rms, 60 kVA, THD<0.5% at rated, "
              "external current command, differential B feedback input",
              CELL.N_CELLS, "ea", "-", "AE Techron / Kepco / Puissance+",
              "7796HF class", 28000, 20, "A",
              "Class-D H-bridge with LC output filter: -60% cost, "
              "worse THD and EMI (see S10)"))
    A(BomLine("SS-04 Amplifier", "Series compensation bank", "6-band switched "
              "AC film capacitor bank, 1.25-710 uF, 2.5 kV rms, 60 A rms, "
              "self-healing MKP, vacuum contactor switching",
              CELL.N_CELLS, "set", "MKP film", "Vishay / KEMET / Electronicon",
              "PhMKP class", 9400, 14, "A", "none - required above 300 Hz"))
    A(BomLine("SS-04 Amplifier", "Isolation transformer + line filter",
              "30 kVA, screened, EMC filter to EN 61000-6-4",
              1, "ea", "-", "Schaffner / Block", "screened isolation",
              4300, 10, "B", "none"))
    A(BomLine("SS-05 Waveform", "DSP arbitrary waveform / control platform",
              "2 MSPS, 6 x 18-bit DAC, 12 x 24-bit ADC, deterministic "
              "EtherCAT, coherent demodulation, <1 ppm frequency reference",
              1, "ea", "-", "Speedgoat / dSPACE / NI", "real-time target",
              21000, 12, "A", "STM32H7 + external ADC (loses traceable timebase)"))

    # --- SS-06 Magnetic instrumentation ------------------------------------
    A(BomLine("SS-06 B sensing", "Layer-3 internal water-side B probe",
              "3-axis air-cored search coil, N=200, A=1 cm2 per axis, sealed "
              "PVDF finger, PTFE cable, calibrated 1 Hz-10 kHz",
              5, "ea", "PVDF / Cu", "custom + accredited cal lab",
              "custom", 2600, 12, "A",
              "commercial ELF probe (usually not immersible)"))
    A(BomLine("SS-06 B sensing", "Layer-2 external reference B probe",
              "3-axis fluxgate, 100 uT range, 0.01 nT/rtHz, DC-3 kHz",
              1, "ea", "-", "Bartington / Stefan Mayer", "Mag-13 class",
              5400, 10, "A", "3-axis Hall (75x worse noise floor)"))
    A(BomLine("SS-06 B sensing", "Layer-1 coil current sensor",
              "Closed-loop fluxgate current transducer, 300 A, 0.1% linearity, "
              "DC-100 kHz, plus precision shunt cross-check",
              2 * CELL.N_CELLS, "ea", "-", "LEM / Danisense",
              "IT-series class", 780, 8, "A", "Rogowski (no DC, worse drift)"))
    A(BomLine("SS-06 B sensing", "3-D probe mapping gantry", "3-axis "
              "non-magnetic (PEEK/Al) traverse, +/-0.1 mm, 400x400x300 mm",
              1, "ea", "PEEK / Al", "Igus / custom", "custom", 8900, 12, "B",
              "manual 5-point jig (loses VG-03 map density)"))
    A(BomLine("SS-06 B sensing", "Helmholtz calibration coil", "1 m, "
              "accredited calibration to 3 kHz, uniformity <0.1% in 100 mm",
              1, "ea", "-", "Serviciencia / custom", "custom", 6200, 14, "A",
              "none - required for VG-06 traceability"))

    # --- SS-07 Water chemistry ---------------------------------------------
    A(BomLine("SS-07 Water inst", "Inline EC / temperature", "4-electrode, "
              "0.1-20 mS/cm, +/-0.3% of reading, Pt1000, sanitary fitting",
              2, "ea", "PEEK/Ti", "Endress+Hauser / Mettler", "Condumax class",
              2200, 6, "A", "2-electrode (polarisation error at high EC)"))
    A(BomLine("SS-07 Water inst", "Inline pH + ORP", "glass/Pt combination, "
              "auto 3-point cal, +/-0.01 pH", 2, "set", "glass/Pt",
              "Endress+Hauser / Mettler", "Memosens class", 1900, 6, "A",
              "ISFET (drift)"))
    A(BomLine("SS-07 Water inst", "Optical dissolved oxygen", "luminescent, "
              "0-20 mg/L, +/-0.05 mg/L", 2, "ea", "-", "Hamilton / Hach",
              "VisiFerm class", 2400, 6, "B", "Clark cell (consumable)"))
    A(BomLine("SS-07 Water inst", "Coriolis flowmeter", "DN50, +/-0.1% of "
              "rate, integral density and temperature", 1, "ea", "SUS316L",
              "Endress+Hauser / Micro Motion", "Promass class", 9800, 10, "A",
              "electromagnetic flowmeter (REJECTED: it is itself an EM device "
              "in the ELF band and couples to the exposure field)"))
    A(BomLine("SS-07 Water inst", "Benchtop: surface tension", "pendant drop / "
              "du Nouy, +/-0.15 mN/m", 1, "ea", "-", "KRUSS / Biolin",
              "force tensiometer", 21000, 10, "B", "capillary rise (worse sigma)"))
    A(BomLine("SS-07 Water inst", "Benchtop: zeta potential", "electrophoretic "
              "light scattering", 1, "ea", "-", "Malvern / Anton Paar",
              "Zetasizer class", 48000, 12, "C",
              "outsourced analysis per sample (recommended for Phase 3)"))
    A(BomLine("SS-07 Water inst", "Autosampler + sample archive", "chilled "
              "4 C, 200 x 50 mL amber, barcoded, blinded labels",
              1, "set", "-", "generic", "-", 5600, 6, "A",
              "manual sampling (breaks operator blinding)"))

    # --- SS-08/09/10 --------------------------------------------------------
    A(BomLine("SS-08 Thermal", "RTD sensor set", "Pt100 class A, 4-wire: "
              "T_coil x6, T_core x3, T_driver x3, T_tank x2, T_water x3",
              17, "ea", "-", "generic", "Pt100 1/3 DIN", 85, 4, "A",
              "thermocouples (worse accuracy, EMI pickup)"))
    A(BomLine("SS-08 Thermal", "Fibre-optic hot-spot probe", "in-winding, "
              "immune to the ELF field, 2 channels",
              2, "ea", "-", "Opsens / Rugged Monitoring", "GaAs probe",
              3400, 12, "A",
              "none - an RTD lead inside the winding is itself a pickup loop"))
    A(BomLine("SS-09 Control", "PLC + safety CPU", "SIL2 safety controller, "
              "16 DI / 16 DO safety, EtherCAT master", 1, "set", "-",
              "Beckhoff / Siemens", "TwinSAFE / F-CPU class", 7200, 8, "A",
              "standard PLC (REJECTED: S18 forbids software-only interlocks)"))
    A(BomLine("SS-09 Control", "Analog I/O", "8 x AO 16-bit isolated, "
              "16 x AI 24-bit isolated", 1, "set", "-", "Beckhoff", "EL3thth/EL4thth",
              3100, 6, "B", "-"))
    A(BomLine("SS-10 Safety", "Hardwired interlock chain", "safety relays, "
              "E-stop x3, door switches, amplifier ENABLE contactor, "
              "insulation monitor, leak detection tape",
              1, "set", "-", "Pilz / Bender", "PNOZ + IRDH class", 5900, 8, "A",
              "none - required by S18"))
    A(BomLine("SS-10 Safety", "RCD / insulation monitoring device",
              "IMD for the IT-earthed exposure sub-net, 30 mA RCD upstream",
              1, "set", "-", "Bender", "isometer class", 2100, 6, "A", "none"))
    A(BomLine("SS-10 Safety", "EMC enclosure + shielding", "screened cabinet, "
              "shielded power cabling, ferrite suppression, bonded ground grid",
              1, "set", "-", "Rittal", "TS-8 + EMC kit", 6800, 8, "B",
              "open rack (will fail EN 61000-6-4)"))

    # --- SS-11/12 -----------------------------------------------------------
    A(BomLine("SS-11 Twin", "Data historian + digital twin server",
              "workstation, 10 Gb, 20 TB, time-series DB, model runtime",
              1, "ea", "-", "generic", "-", 7400, 4, "B", "cloud instance"))
    A(BomLine("SS-12 Pilot", "Assembly, wiring, commissioning labour",
              "mechanical + electrical build, FAT support",
              320, "h", "-", "in-house / integrator", "-", 95, 0, "A", "-"))
    A(BomLine("SS-12 Pilot", "Calibration and accreditation",
              "B probes, EC/pH/DO, flow, temperature; ISO 17025 certificates",
              1, "set", "-", "accredited lab", "-", 9500, 8, "A",
              "none - required for E1 status of every measurement"))
    A(BomLine("SS-12 Pilot", "Contingency", "15% of hardware subtotal",
              1, "set", "-", "-", "-", 0, 0, "A", "-"))
    return L


def capex(core_mat=NANOCRYSTALLINE):
    lines = build_bom(core_mat)
    sub = sum(l.total for l in lines if l.part != "Contingency")
    for l in lines:
        if l.part == "Contingency":
            l.unit_cost_usd = round(sub * 0.15, 0)
    total = sum(l.total for l in lines)
    by_ss = {}
    for l in lines:
        by_ss[l.subsystem] = by_ss.get(l.subsystem, 0.0) + l.total
    crit = {}
    for l in lines:
        crit[l.criticality] = crit.get(l.criticality, 0.0) + l.total
    lead = max(l.lead_weeks for l in lines)
    return dict(lines=lines, subtotal=sub, total=total, by_subsystem=by_ss,
                by_criticality=crit, longest_lead_weeks=lead)
