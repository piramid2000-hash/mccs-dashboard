"""Master runner: computes every table in the Phase-3 report."""
import csv
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from constants import (F_GRID, B_LADDER_T, B_LADDER_LABEL, CORE_CANDIDATES,
                       M350_50A, NO10_THIN, NANOCRYSTALLINE, FERRITE_N87,
                       SIGMA_ELECTROLYTE_MAX, SIGMA_WATER_TAP, MU0, PI,
                       MU_R_SUS316L_COLDWORK)
import cell as CELL
import system as S
import thermal as TH
import architectures as ARCH
from magnetics import ForkGeometry
from tank_coupling import TankGeometry, sweep as tank_sweep, corner_frequency, shell_time_constant
from coil_design import WIRES, Coil, core_loss

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")
os.makedirs(OUT, exist_ok=True)

CORE = S.CoreGeom()
LIM = S.DriverLimits()
STATS = CELL.cell_field_stats(1.0)
GAIN, CV = STATS["mean"], STATS["cv"]
GAP_UNIT, GAP_ERR, _ = S._gap_mmf_unit(CORE)
BASE_MAT = NANOCRYSTALLINE


def write_csv(name, rows, header=None):
    if not rows:
        return
    header = header or list(rows[0].keys())
    with open(os.path.join(OUT, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})


def md_table(rows, cols, headers=None, fmt=None):
    headers = headers or cols
    fmt = fmt or {}
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(cols)) + "|"]
    for r in rows:
        cells = []
        for c in cols:
            v = r.get(c, "")
            f = fmt.get(c)
            cells.append(f % v if (f and isinstance(v, (int, float))) else str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


# ---------------------------------------------------------------------------
def winding_choice():
    mmf_max = GAP_UNIT * (max(B_LADDER_T) / GAIN)
    b = S.choose_winding(CORE, 3000.0, mmf_max, LIM)
    return dict(wire=b[1], turns=b[2], fr=b[3], p_cu=b[4], j=b[5],
                v_cap=b[6], L=b[7], mmf_max=mmf_max)


def master_table(wc, mat=None):
    mat = mat or BASE_MAT
    rows = []
    for b_t, lab in zip(B_LADDER_T, B_LADDER_LABEL):
        if b_t == 0.0:
            continue
        for f in F_GRID:
            sol = S.solve_cell(f, b_t, CORE, mat, wc["wire"], wc["turns"],
                               GAIN, CV, 80.0, LIM)
            t_coil = TH.COIL_PATH.temp(sol.p_cu)
            t_core = TH.CORE_PATH.temp(sol.p_core)
            lims = list(sol.limits)
            if t_coil > TH.COIL_PATH.t_limit: lims.append("FS4 T_coil")
            if t_core > TH.CORE_PATH.t_limit: lims.append("FS4 T_core")
            rows.append(dict(
                B_set_mT=b_t * 1e3, label=lab, f_Hz=f, B_pole_T=sol.b_pole,
                B_leg_T=sol.b_leg, CV_B=sol.cv_b, N_loop=sol.N_loop,
                wire=sol.wire, L_mH=sol.L * 1e3, R_ac_ohm=sol.r_ac,
                Fr=sol.fr_ac, Z_ohm=math.hypot(sol.r_ac, 2 * PI * f * sol.L),
                I_rms_A=sol.i_rms, I_pk_A=sol.i_peak, J_A_mm2=sol.j_cu,
                V_uncomp_V=sol.v_uncomp, V_drive_V=sol.v_drive,
                V_cap_V=sol.v_cap, C_ser_uF=(sol.c_series * 1e6 if sol.c_series else 0.0),
                Q_kVAr=sol.q_var / 1e3, S_drive_kVA=sol.va_drive / 1e3,
                P_Cu_W=sol.p_cu, P_core_W=sol.p_core, P_water_W=sol.p_water,
                E_water_Vpm=sol.e_water, T_coil_C=t_coil, T_core_C=t_core,
                status=("OK" if not lims else ";".join(sorted(set(lims))))))
    return rows


def feasibility_envelope(wc, mat, n=60):
    """Max achievable B_ECV at each frequency under all limits."""
    rows = []
    for f in F_GRID:
        lo, hi = 1e-5, 0.5
        for _ in range(n):
            mid = math.sqrt(lo * hi)
            sol = S.solve_cell(f, mid, CORE, mat, wc["wire"], wc["turns"],
                               GAIN, CV, 80.0, LIM)
            bad = bool(sol.limits) or TH.COIL_PATH.temp(sol.p_cu) > TH.COIL_PATH.t_limit \
                  or TH.CORE_PATH.temp(sol.p_core) > TH.CORE_PATH.t_limit
            if bad: hi = mid
            else:   lo = mid
        sol = S.solve_cell(f, lo, CORE, mat, wc["wire"], wc["turns"], GAIN, CV, 80.0, LIM)
        rows.append(dict(f_Hz=f, B_max_mT=lo * 1e3, I_rms_A=sol.i_rms,
                         V_drive_V=sol.v_drive, V_cap_V=sol.v_cap,
                         Q_kVAr=sol.q_var / 1e3, P_Cu_W=sol.p_cu,
                         P_core_W=sol.p_core, T_core_C=TH.CORE_PATH.temp(sol.p_core),
                         binding=_binding(f, lo, mat, wc)))
    return rows


def _binding(f, b, mat, wc):
    """Which limit binds just above the envelope."""
    sol = S.solve_cell(f, b * 1.15, CORE, mat, wc["wire"], wc["turns"],
                       GAIN, CV, 80.0, LIM)
    l = list(sol.limits)
    if TH.COIL_PATH.temp(sol.p_cu) > TH.COIL_PATH.t_limit: l.append("FS4 T_coil")
    if TH.CORE_PATH.temp(sol.p_core) > TH.CORE_PATH.t_limit: l.append("FS4 T_core")
    return ";".join(sorted(set(l))) if l else "none (>0.5 T search cap)"


def material_comparison(wc):
    rows = []
    for mat in CORE_CANDIDATES:
        if mat.name.startswith("Air"):
            continue
        b_pole = 50e-3 / GAIN
        b_leg = b_pole * CORE.pole_area / CORE.leg_area
        p3k = (core_loss(mat, 3000, b_pole * math.sqrt(2), CORE.vol_shoe) +
               core_loss(mat, 3000, b_leg * math.sqrt(2), CORE.vol_leg + CORE.vol_yoke))
        p50 = (core_loss(mat, 50, b_pole * math.sqrt(2), CORE.vol_shoe) +
               core_loss(mat, 50, b_leg * math.sqrt(2), CORE.vol_leg + CORE.vol_yoke))
        m = CORE.mass(mat)
        rows.append(dict(material=mat.name, mu_r=mat.mu_r_init, B_sat_T=mat.b_sat,
                         lam_um=mat.lam_t * 1e6, mass_kg=m,
                         P_core_50Hz_W=p50, P_core_3kHz_W=p3k,
                         T_core_3kHz_C=TH.CORE_PATH.temp(p3k),
                         cost_USD=m * mat.cost_kg, machinability=mat.machinability,
                         B_leg_margin=("OK" if b_leg * math.sqrt(2) < 0.8 * mat.b_sat else "SAT"),
                         anchor=mat.anchor))
    return rows


def architecture_comparison():
    """R1/R2/R3 on a common basis: same water gap, same target B, same f."""
    rows = []
    fk3 = ForkGeometry(n_prong=3, prong_w=0.240, prong_h=0.240, prong_len=0.15,
                       prong_pitch=0.375, gap=0.030)
    for arch in ("R1", "R2", "R3"):
        per, uni = ARCH.stats_channels(arch, fk3, 1.0)
        mmf, mmf_gap, mmf_core = ARCH.loop_mmf(arch, fk3, 50e-3 / uni["mean"], 30000.0)
        u, n_loops = ARCH.field_energy(arch, fk3, 50e-3 / uni["mean"], mmf)
        rows.append(dict(arch=arch, gain=uni["mean"], CV_B=uni["cv"],
                         B_min_rel=uni["mn"], B_max_rel=uni["mx"],
                         n_drive_loops=n_loops, MMF_At=mmf,
                         U_J=u, Q_3kHz_kVAr=2 * 2 * PI * 3000 * u / 1e3,
                         ECV_L=ARCH.ecv_volume_L(fk3),
                         nulls=("YES - polarity nulls between prong pairs"
                                if arch in ("R1", "R2") else "no")))
    return rows


def tank_table():
    t = TankGeometry()
    rows = tank_sweep(t, F_GRID, 1.0e-3)
    for r in rows:
        r["B_out_needed_mT_for_1mT_in"] = 1.0 / r["H_mag"] if r["H_mag"] > 0 else float("inf")
        r["P_eddy_at_that_drive_kW"] = (r["P_eddy_W"] * (1.0 / r["H_mag"]) ** 2) / 1e3
    return rows, t


def hydraulics_table():
    rows = []
    for v in (0.0, 0.25, 0.5, 1.0, 2.0):
        h = CELL.Hydraulics(velocity=max(v, 1e-9))
        dp = TH.duct_pressure_drop(max(v, 1e-9), h.hydraulic_diameter,
                                   CELL.N_CELLS * CELL.POLE_W * 1.6)
        pp = TH.pump_heat(dp + 1.0e5, h.flow_m3s) if v > 0 else 0.0
        rows.append(dict(v_ms=v, Q_m3h=h.flow_m3h if v > 0 else 0.0,
                         Re=h.reynolds if v > 0 else 0.0,
                         regime=h.regime if v > 0 else "static",
                         dP_duct_Pa=dp if v > 0 else 0.0,
                         P_pump_W=pp,
                         res_per_pass_s=h.residence_per_pass() if v > 0 else float("inf"),
                         turnover_s=h.turnover_time() if v > 0 else float("inf"),
                         water_dTdt_K_per_h=TH.water_dT_dt(pp, 1000.0) * 3600))
    return rows


def dose_table():
    h = CELL.Hydraulics(velocity=0.5)
    v_ecv = CELL.ecv_geometry()["vol_L"] * CELL.N_CELLS
    rows = []
    for hrs in (1, 4, 8, 24, 48):
        t_exp = h.cumulative_exposure(hrs * 3600)
        r = dict(run_h=hrs, t_exposure_s=t_exp, passes=hrs * 3600 / h.turnover_time())
        for b, lab in zip(B_LADDER_T, B_LADDER_LABEL):
            if b == 0: continue
            r[f"D_B_{lab.replace(' ','')}_mTs"] = b * 1e3 * t_exp
        rows.append(r)
    return rows, v_ecv, h


if __name__ == "__main__":
    wc = winding_choice()
    print("=" * 78)
    print("FROZEN CELL")
    print("=" * 78)
    print(f"  pole face      : {CORE.pole_w*1e3:.0f} x {CORE.pole_h*1e3:.0f} mm")
    print(f"  magnetic gap   : {CORE.gap*1e3:.0f} mm  (water {CELL.WATER_GAP*1e3:.0f} mm + 2 x {CELL.DUCT_WALL*1e3:.0f} mm duct)")
    print(f"  field gain     : B_ECV/B_pole = {GAIN:.4f}")
    print(f"  CV_B over ECV  : {CV*100:.2f} %   (requirement <= 10 %)")
    print(f"  ECV per cell   : {CELL.ecv_geometry()['vol_L']:.3f} L   x{CELL.N_CELLS} = {CELL.ecv_geometry()['vol_L']*CELL.N_CELLS:.3f} L")
    print(f"  gap MMF        : {GAP_UNIT:.0f} A-t per tesla of pole B (model path spread {GAP_ERR*100:.1f} %)")
    print(f"  core volume    : {CORE.volume*1e3:.2f} L   path {CORE.path_len:.3f} m")
    print(f"  winding        : {wc['wire'].label}, N={wc['turns']}/coil, N_loop={2*wc['turns']}, L={wc['L']*1e3:.2f} mH")
    print(f"  I at 50 mT     : {wc['mmf_max']/(2*wc['turns']):.1f} A rms,  J={wc['j']:.2f} A/mm2")

    mt = master_table(wc)
    write_csv("S35_master_calculation_table.csv", mt)
    fe = feasibility_envelope(wc, BASE_MAT)
    write_csv("S05_feasibility_envelope.csv", fe)
    mc = material_comparison(wc)
    write_csv("S08_core_material_comparison.csv", mc)
    ac = architecture_comparison()
    write_csv("S21_architecture_comparison.csv", ac)
    tk, tank = tank_table()
    write_csv("S13_sus316L_transfer_function.csv", tk)
    hy = hydraulics_table()
    write_csv("S16_hydraulics.csv", hy)
    dz, v_ecv, hyd = dose_table()
    write_csv("S16_dose.csv", dz)

    print("\n--- feasibility envelope (nanocrystalline core) ---")
    for r in fe:
        print("  f=%7.2f Hz  B_max=%8.2f mT  I=%6.1f A  V=%7.1f V  Vcap=%7.0f V  Q=%7.1f kVAr  binds: %s"
              % (r["f_Hz"], r["B_max_mT"], r["I_rms_A"], r["V_drive_V"], r["V_cap_V"], r["Q_kVAr"], r["binding"]))

    print("\n--- 50 mT row of the master table ---")
    for r in mt:
        if abs(r["B_set_mT"] - 50.0) < 1e-9:
            print("  f=%7.2f  I=%6.1f A  V=%7.1f V  Vcap=%7.0f V  C=%8.3f uF  Q=%7.1f kVAr  Pcu=%6.1f W  Pcore=%8.1f W  Tcore=%6.1f C  E_w=%5.1f V/m  %s"
                  % (r["f_Hz"], r["I_rms_A"], r["V_drive_V"], r["V_cap_V"], r["C_ser_uF"],
                     r["Q_kVAr"], r["P_Cu_W"], r["P_core_W"], r["T_core_C"], r["E_water_Vpm"], r["status"]))

    print("\n--- core materials at 50 mT / 3 kHz ---")
    for r in mc:
        print("  %-50s mass %6.1f kg  P50Hz %8.1f W  P3kHz %10.1f W  Tcore %8.1f C  ~USD %7.0f  %s"
              % (r["material"][:50], r["mass_kg"], r["P_core_50Hz_W"], r["P_core_3kHz_W"],
                 r["T_core_3kHz_C"], r["cost_USD"], r["B_leg_margin"]))

    print("\n--- architecture comparison (same gap, same 50 mT target) ---")
    for r in ac:
        print("  %s gain=%.3f CV_B=%.3f MMF=%8.0f A-t U=%7.3f J Q@3kHz=%8.1f kVAr loops=%d  %s"
              % (r["arch"], r["gain"], r["CV_B"], r["MMF_At"], r["U_J"],
                 r["Q_3kHz_kVAr"], r["n_drive_loops"], r["nulls"]))

    print("\n--- SUS316L tank ---")
    print("  tau_s=%.4e s  f_c=%.1f Hz (annealed)  %.1f Hz (cold-worked mu_r=1.8)"
          % (shell_time_constant(tank, 1.35e6, 1.005), corner_frequency(tank),
             corner_frequency(tank, mu_r=MU_R_SUS316L_COLDWORK.value)))
    for r in tk:
        print("  f=%7.2f |H|=%.4f (%7.2f dB) phase=%7.2f deg  B_out needed for 1 mT inside = %8.1f mT -> tank eddy %9.1f kW"
              % (r["f_Hz"], r["H_mag"], r["H_dB"], r["phase_deg"],
                 r["B_out_needed_mT_for_1mT_in"], r["P_eddy_at_that_drive_kW"]))

    print("\n--- hydraulics ---")
    for r in hy:
        print("  v=%.2f m/s Q=%6.2f m3/h Re=%7.0f %-12s dP=%8.1f Pa Ppump=%7.1f W  pass=%6.2f s turnover=%7.1f s  water %+.3f K/h"
              % (r["v_ms"], r["Q_m3h"], r["Re"], r["regime"], r["dP_duct_Pa"],
                 r["P_pump_W"], r["res_per_pass_s"], r["turnover_s"], r["water_dTdt_K_per_h"]))

    print("\n--- dose bookkeeping (V_ECV=%.2f L into %.0f L, v=0.5 m/s) ---" % (v_ecv, 1000))
    for r in dz:
        print("  run %3d h -> %6.1f passes, cumulative exposure %7.1f s,  D_B(50mT)=%9.0f mT.s"
              % (r["run_h"], r["passes"], r["t_exposure_s"], r["D_B_50mT_mTs"]))
    print("\nCSV written to", os.path.abspath(OUT))
