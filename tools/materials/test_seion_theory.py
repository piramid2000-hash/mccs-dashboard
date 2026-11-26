"""seion_theory 검증 — 표준 참고값(NIST 등)과 비교한다."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import seion_theory as t  # noqa: E402


# ---- 병진 (Sackur–Tetrode, 기체분자운동론)
def test_trans_argon_entropy_matches_nist():
    # NIST: Ar S°(298.15 K, 1 bar) = 154.846 J/mol/K (원자 기체 → 병진 성분이 전체)
    r = t.cmd_trans("Ar", 298.15, 1e5)
    assert r["S_trans_J_molK"] == pytest.approx(154.846, abs=0.05)
    assert r["Cv_trans_J_molK"] == pytest.approx(12.472, abs=0.01)


def test_trans_speeds_ordering_and_n2_values():
    r = t.cmd_trans("N2", 298.15, 101325, diameter_A=3.7)
    assert r["speed_most_probable_m_s"] < r["speed_mean_m_s"] < r["speed_rms_m_s"]
    assert r["speed_mean_m_s"] == pytest.approx(474.7, abs=0.5)      # √(8kT/πm)
    assert r["mean_free_path_m"] == pytest.approx(6.68e-8, rel=0.01)  # 상온·1기압 ~67 nm


# ---- 오비탈 (PySCF)
def test_mo_water_b3lyp():
    r = t.cmd_mo("H2O", "b3lyp", "def2-svp")
    assert "error" not in r
    assert r["HOMO_eV"] < 0 < r["gap_eV"]
    assert 1.7 < r["dipole_total_Debye"] < 2.2                      # 실측 1.85 D
    assert sum(r["mulliken_charges"].values()) == pytest.approx(0, abs=1e-3)
    assert r["mulliken_charges"]["O0"] < 0


# ---- 양자화학 열역학 (최적화 → 진동수 → RRHO)
def test_thermo_water_entropy_matches_nist():
    r = t.cmd_thermo("H2O", "hf", "6-31g*", 298.15, 1e5)
    assert r["imaginary_modes"] == 0
    assert len(r["frequencies_cm-1"]) == 3
    assert r["rotational_symmetry_number"] == 2
    assert r["S_J_molK"]["total"] == pytest.approx(188.84, abs=1.5)   # NIST 188.84
    # 병진 성분은 trans 명령(Sackur–Tetrode)과 일치해야 함
    st = t.cmd_trans("H2O", 298.15, 1e5)["S_trans_J_molK"]
    assert r["S_J_molK"]["translational"] == pytest.approx(st, abs=0.05)


# ---- 화학평형 (Cantera)
def test_equil_methane_air_adiabatic_flame():
    r = t.cmd_equil("CH4:1,O2:2,N2:7.52", 300, 101325, "HP")
    assert r["final_T_K"] == pytest.approx(2225, abs=15)              # 문헌 ~2220–2230 K
    assert r["enthalpy_conserved"]


def test_equil_tp_keeps_temperature():
    r = t.cmd_equil("H2:2,O2:1", 1500, 101325, "TP")
    assert r["final_T_K"] == pytest.approx(1500)
    assert max(r["mole_fractions_top"], key=r["mole_fractions_top"].get) == "H2O"
