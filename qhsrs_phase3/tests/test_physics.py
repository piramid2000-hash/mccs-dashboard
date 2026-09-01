"""
Self-verification of the physics engines.

These are not unit tests of code style; they are ANALYTIC LIMIT CHECKS. Each
one compares a model against a case whose answer is known in closed form.
Run:  python3 tests/test_physics.py
"""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "design"))

import magnetics as M
import tank_coupling as TC
import coil_design as CD
import doe as DOE
import system as S
import cell as CELL
from constants import (MU0, PI, M350_50A, NO10_THIN, NANOCRYSTALLINE, FERRITE_N87,
                       SIGMA_SUS316L)
import numpy as np

FAILS = []
def check(name, got, want, tol, unit=""):
    ok = abs(got - want) <= tol * max(abs(want), 1e-30)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got:.6g}{unit}, expect {want:.6g}{unit} (tol {tol*100:g} %)")
    if not ok:
        FAILS.append(name)


print("1. Charge-sheet field primitive vs analytic limits")
Lg = 500.0
check("infinite sheet, Bn just above", M._rect_sheet_B(0, 0, 1e-3, 1.0, -Lg, Lg, -Lg, Lg, 0)[2], 0.5, 1e-4)
check("infinite sheet, Bn just below", M._rect_sheet_B(0, 0, -1e-3, 1.0, -Lg, Lg, -Lg, Lg, 0)[2], -0.5, 1e-4)
b1 = M._rect_sheet_B(0, 0, 0.5, 1.0, -Lg, Lg, -Lg, Lg, 0)[2]
b2 = M._rect_sheet_B(0, 0, 0.5, -1.0, -Lg, Lg, -Lg, Lg, 1.0)[2]
check("infinite opposed pair, midplane Bn", b1 + b2, 1.0, 1e-3)
b3 = M._rect_sheet_B(0, 0, 1.5, 1.0, -Lg, Lg, -Lg, Lg, 0)[2]
b4 = M._rect_sheet_B(0, 0, 1.5, -1.0, -Lg, Lg, -Lg, Lg, 1.0)[2]
# absolute check: outside an opposed pair the normal field must vanish.
# The residual is finite-sheet truncation of the 500 m test sheet, not model error.
_out = abs(b3 + b4)
print(f"  [{'PASS' if _out < 1e-3 else 'FAIL'}] outside the pair |Bn| = {_out:.2e} (< 1e-3, truncation only)")
if _out >= 1e-3:
    FAILS.append("outside pair")

print("\n2. Gap MMF: field integral vs Ampere's law for a near-parallel-plate gap")
core = S.CoreGeom()
gv, err, _ = S._gap_mmf_unit(core)
ideal = core.gap / MU0          # A-t per tesla for an ideal (no fringing) gap
print(f"  charge-sheet integral {gv:.0f} A-t/T vs ideal parallel plate {ideal:.0f} A-t/T "
      f"-> fringing reduction {100*(1-gv/ideal):.1f} % (expected: positive and < 40 %)")
if not (0.0 < 1 - gv / ideal < 0.40):
    FAILS.append("gap MMF fringing out of physical range")
print(f"  [{'PASS' if 0.0 < 1-gv/ideal < 0.40 else 'FAIL'}] fringing within physical range")
print(f"  [{'PASS' if err < 0.10 else 'FAIL'}] model path spread {err*100:.1f} % (< 10 % for a plate-like gap)")
if err >= 0.10: FAILS.append("path spread")

print("\n3. Tank shell: corner frequency from two independent routes")
t = TC.TankGeometry()
tau = TC.shell_time_constant(t, SIGMA_SUS316L.value, 1.005)
check("f_c from tau", TC.corner_frequency(t), 1 / (2 * PI * tau), 1e-9, " Hz")
H = TC.H_tank(TC.corner_frequency(t), t, include_thickness=False)
check("|H| at f_c (loop term only)", abs(H), 1 / math.sqrt(2), 1e-6)
check("phase at f_c", math.degrees(math.atan2(H.imag, H.real)), -45.0, 1e-6, " deg")
check("skin depth in 316L at 3 kHz", TC.skin_depth(3000, SIGMA_SUS316L.value) * 1e3, 7.906, 1e-3, " mm")

print("\n4. Copper skin depth")
check("delta_Cu at 50 Hz, 20 C", CD.skin_depth_cu(50, 20) * 1e3, 9.35, 0.02, " mm")
check("delta_Cu scaling 50->3000 Hz", CD.skin_depth_cu(3000, 20) / CD.skin_depth_cu(50, 20),
      math.sqrt(50 / 3000), 1e-9)

print("\n5. Core-loss models reproduce their published anchors")
for mat, f, b, want_wkg in ((M350_50A, 50, 1.5, 3.50), (NO10_THIN, 400, 1.0, 9.00),
                            (NANOCRYSTALLINE, 20000, 0.2, 1.37), (FERRITE_N87, 100000, 0.2, 82.3)):
    got = CD.core_loss(mat, f, b, 1.0) / mat.stacking / mat.rho_mass
    check(f"{mat.name[:34]} anchor", got, want_wkg, 0.01, " W/kg")

print("\n6. Reactive power identity  Q = omega*L*I^2 = 2*omega*U")
sol = S.solve_cell(3000.0, 50e-3, core, NANOCRYSTALLINE, CD.WIRES[5], 16,
                   CELL.cell_field_stats(1.0)["mean"], 0.0625)
U = 0.5 * sol.L * sol.i_rms ** 2 * 2      # time-average stored energy = L*I_rms^2 ... /2 *2
check("Q vs 2*omega*U_avg", sol.q_var, 2 * PI * 3000 * sol.L * sol.i_rms ** 2, 1e-9, " VAr")
q_from_flux = 2 * PI * 3000 * sol.flux * sol.mmf
check("Q vs omega*Phi*F", sol.q_var, q_from_flux, 1e-6, " VAr")

print("\n7. Q is independent of turns count (the central claim of S09/S10)")
qs = []
for n in (8, 16, 32, 64):
    sn = S.solve_cell(3000.0, 50e-3, core, NANOCRYSTALLINE, CD.WIRES[5], n,
                      CELL.cell_field_stats(1.0)["mean"], 0.0625)
    qs.append(sn.q_var)
spread = (max(qs) - min(qs)) / min(qs)
print(f"  Q for N/coil = 8,16,32,64: {['%.0f' % q for q in qs]} VAr -> spread {spread:.2e}")
print(f"  [{'PASS' if spread < 1e-9 else 'FAIL'}] Q invariant to N")
if spread >= 1e-9: FAILS.append("Q not invariant to N")

print("\n8. DOE design is a genuine resolution-IV orthogonal fraction")
des = DOE.frac_fact_2_7_3()
X = np.column_stack([np.ones(16)] + [np.array([r[c] for r in des], float) for c in "ABCDEFG"])
orth = np.allclose(X.T @ X, 16 * np.eye(8))
print(f"  [{'PASS' if orth else 'FAIL'}] X^T X = 16 I (perfect orthogonality)")
if not orth: FAILS.append("DOE orthogonality")
groups = DOE.alias_structure(des)
main = set("ABCDEFG")
clear = all(not (len(set(g) & main) > 1) for g in groups)
print(f"  [{'PASS' if clear else 'FAIL'}] no two MAIN effects are aliased (resolution >= IV)")
if not clear: FAILS.append("DOE resolution")

print("\n9. Dose identity: t_exp independent of flow rate")
te = []
for v in (0.25, 0.5, 1.0, 2.0):
    te.append(CELL.Hydraulics(velocity=v).cumulative_exposure(8 * 3600))
sp = (max(te) - min(te)) / min(te)
print(f"  t_exp at v = 0.25/0.5/1/2 m/s: {['%.2f' % x for x in te]} s -> spread {sp:.2e}")
print(f"  [{'PASS' if sp < 1e-12 else 'FAIL'}] dose does not depend on flow")
if sp >= 1e-12: FAILS.append("dose/flow independence")

print("\n10. Uniformity requirement is met at the frozen geometry")
st = CELL.cell_field_stats(1.0)
print(f"  [{'PASS' if st['cv'] <= 0.10 else 'FAIL'}] CV_B = {st['cv']*100:.2f} % (requirement <= 10 %)")
if st["cv"] > 0.10: FAILS.append("CV_B")

print("\n" + "=" * 60)
if FAILS:
    print("FAILURES:", ", ".join(FAILS)); sys.exit(1)
print("ALL CHECKS PASSED")
