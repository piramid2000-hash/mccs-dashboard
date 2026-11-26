"""seion_matcalc 검증 — 손으로 확인 가능한 기준값과 비교한다."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import seion_matcalc as m  # noqa: E402


def test_formula_alumina():
    r = m.cmd_formula("Al2O3")
    assert r["molar_mass_g_per_mol"] == pytest.approx(101.961, abs=0.01)
    assert r["elements"]["Al"]["wt_percent"] == pytest.approx(52.925, abs=0.01)
    assert r["oxide_basis"]["wt_percent"]["Al2O3"] == pytest.approx(100.0)


def test_formula_kaolinite_oxides():
    # 카올리나이트 Al2Si2O5(OH)4 표준 산화물 조성: SiO2 46.5, Al2O3 39.5, H2O 14.0 wt%
    r = m.cmd_formula("Al2Si2O5(OH)4")
    ox = r["oxide_basis"]["wt_percent"]
    assert ox["SiO2"] == pytest.approx(46.55, abs=0.05)
    assert ox["Al2O3"] == pytest.approx(39.50, abs=0.05)
    assert ox["H2O"] == pytest.approx(13.96, abs=0.05)
    assert r["oxide_basis"]["oxygen_in_formula"] == pytest.approx(9)
    assert r["oxide_basis"]["oxygen_implied_by_oxides"] == pytest.approx(9)


def test_convert_roundtrip():
    wt = "SiO2=60,Al2O3=25,K2O=15"
    mol = m.cmd_convert(wt, "wt", "mol")["result_percent"]
    assert sum(mol.values()) == pytest.approx(100, abs=1e-3)
    back = m.cmd_convert(",".join(f"{k}={v}" for k, v in mol.items()), "mol", "wt")["result_percent"]
    assert back["SiO2"] == pytest.approx(60, abs=1e-3)
    assert back["K2O"] == pytest.approx(15, abs=1e-3)


def test_convert_warns_on_bad_sum():
    r = m.cmd_convert("SiO2=60,Al2O3=30", "wt", "mol")
    assert r["warnings"]


def test_cif_nacl(tmp_path):
    from pymatgen.core import Lattice, Structure
    st = Structure.from_spacegroup("Fm-3m", Lattice.cubic(5.64), ["Na", "Cl"],
                                   [[0, 0, 0], [0.5, 0.5, 0.5]])
    f = tmp_path / "nacl.cif"
    st.to(filename=str(f))
    r = m.cmd_cif(str(f))
    assert r["theoretical_density_g_cm3"] == pytest.approx(2.165, abs=0.01)  # 문헌 2.16–2.17
    assert r["space_group_consistent"]
    assert all(x["number"] == 225 for x in r["space_group_by_symprec"])
    assert r["Z_formula_units"] == pytest.approx(4)


def test_mix_bounds_and_density():
    r = m.cmd_mix(["A:frac=0.5,rho=2.0,prop=10", "B:frac=0.5,rho=1.0,prop=1"], "vol")
    assert r["density_dense_g_cm3"] == pytest.approx(1.5)
    b = r["property_bounds"]
    assert b["upper_voigt"] == pytest.approx(5.5)
    assert b["lower_reuss"] == pytest.approx(1 / (0.5 / 10 + 0.5 / 1))
    assert b["upper_voigt"] >= b["lower_reuss"]


def test_mix_wt_to_vol():
    r = m.cmd_mix(["A:frac=0.5,rho=2.0", "B:frac=0.5,rho=1.0"], "wt")
    assert r["volume_fractions"]["A"] == pytest.approx(1 / 3)


def test_mix_rejects_bad_sum():
    r = m.cmd_mix(["A:frac=0.5,rho=2.0", "B:frac=0.6,rho=1.0"], "vol")
    assert "density_dense_g_cm3" not in r and r["warnings"]


def test_hull_without_key(monkeypatch):
    monkeypatch.delenv("MP_API_KEY", raising=False)
    assert "error" in m.cmd_hull("Li-P-S")
