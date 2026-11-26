"""seion_crystal 검증 — 실측 참고값과 비교(MLIP 오차를 감안한 허용폭).

허용폭은 '모델이 이 정도는 맞춘다'는 기록이다. 넓은 이유는 PBE 학습 MLIP 의 알려진 오차 때문이며,
값이 이 범위를 벗어나면 라이브러리·모델 버전이 바뀌어 거동이 달라진 것이므로 재검증한다.
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import seion_crystal as c  # noqa: E402


def _cif(tmp_path, name, sg, a, species, coords):
    from pymatgen.core import Lattice, Structure
    f = tmp_path / f"{name}.cif"
    Structure.from_spacegroup(sg, Lattice.cubic(a), species, coords).to(filename=str(f))
    return str(f)


@pytest.fixture(scope="module")
def cifs(tmp_path_factory):
    d = tmp_path_factory.mktemp("cif")
    return {
        "Si": _cif(d, "Si", "Fd-3m", 5.43, ["Si"], [[0, 0, 0]]),
        "Al": _cif(d, "Al", "Fm-3m", 4.05, ["Al"], [[0, 0, 0]]),
        "MgO": _cif(d, "MgO", "Fm-3m", 4.21, ["Mg", "O"], [[0, 0, 0], [0.5, 0.5, 0.5]]),
    }


def test_relax_si_lattice(cifs):
    r = c.cmd_relax(cifs["Si"])
    assert r["converged"]
    assert 5.43 <= r["cellpar_after"][0] <= 5.50          # 실측 5.431, PBE ~5.47


def test_phonon_si_stable_and_cv(cifs):
    r = c.cmd_phonon(cifs["Si"], temps=[300.0])
    assert r["dynamically_stable"]
    assert r["thermal"][0]["Cv_J_molK_per_mol_atoms"] == pytest.approx(19.8, rel=0.15)  # 실측 Cp≈20.0


def test_qha_aluminium_300K(cifs):
    r = c.cmd_qha(cifs["Al"], temps=[300.0])
    row = r["results"][0]
    assert row["alpha_linear_per_K"] == pytest.approx(23.1e-6, rel=0.2)   # 실측 23.1e-6 /K
    assert 60 <= row["bulk_modulus_GPa"] <= 85                            # 실측 76 GPa
    assert r["warning"] is None


def test_qha_mgo_300K(cifs):
    r = c.cmd_qha(cifs["MgO"], temps=[300.0])
    row = r["results"][0]
    assert row["alpha_linear_per_K"] == pytest.approx(10.5e-6, rel=0.25)  # 실측 ~10.5e-6 /K
    assert 140 <= row["bulk_modulus_GPa"] <= 180                          # 실측 ~160 GPa


def test_chgnet_blocked_for_phonons(cifs):
    with pytest.raises(SystemExit):
        c.cmd_phonon(cifs["Si"], model="chgnet")


def test_md_smoke(cifs):
    r = c.cmd_md(cifs["Al"], "Al", T=300, steps=40, equil=10)
    assert r["n_species"] == 4 and r["D_cm2_s"] >= 0
    assert not r["diffusive"]                                             # 상온 고체 Al 은 확산하지 않음
