"""seion_expdata 검증 — 파라미터를 알고 만든 합성 데이터에서 값을 되찾는지 본다."""
import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import seion_expdata as e  # noqa: E402


def _pv(x, c, fwhm, h, eta=0.5):
    s = fwhm / 2
    lor = 1 / (1 + ((x - c) / s) ** 2)
    gau = np.exp(-np.log(2) * ((x - c) / s) ** 2)
    return h * (eta * lor + (1 - eta) * gau)


def test_peaks_recover_positions_widths_on_curved_baseline(tmp_path):
    rng = np.random.default_rng(0)
    x = np.linspace(10, 60, 2501)
    y = 200 + 2 * x + 0.03 * (x - 35) ** 2                      # 휘어진 기준선
    truth = [(20.0, 0.30, 1000), (26.6, 0.20, 2500), (45.3, 0.45, 600)]
    for c, w, h in truth:
        y += _pv(x, c, w, h)
    y += rng.normal(0, 5, x.size)
    f = tmp_path / "xrd.csv"
    np.savetxt(f, np.c_[x, y], delimiter=",", header="2theta,I")
    r = e.cmd_peaks(str(f), wavelength=1.5406)
    assert len(r["peaks"]) == 3 and r["fit_R2"] > 0.99
    for (c, w, h), p in zip(truth, r["peaks"]):
        assert p["center"] == pytest.approx(c, abs=0.01)
        assert p["fwhm"] == pytest.approx(w, rel=0.08)
    # Scherrer: 26.6°, FWHM 0.20° → K λ /(β cosθ) ≈ 40.8 nm
    assert r["peaks"][1]["scherrer_size_nm"] == pytest.approx(40.8, rel=0.1)


def test_xrdmatch_ranks_right_phase(tmp_path):
    from pymatgen.core import Lattice, Structure
    nacl = Structure.from_spacegroup("Fm-3m", Lattice.cubic(5.64), ["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]])
    si = Structure.from_spacegroup("Fd-3m", Lattice.cubic(5.43), ["Si"], [[0, 0, 0]])
    fn, fs = tmp_path / "NaCl.cif", tmp_path / "Si.cif"
    nacl.to(filename=str(fn)); si.to(filename=str(fs))
    _, sx, sy = e.simulate_xrd(str(fn), two_theta=(10, 80))
    x = np.linspace(10, 80, 7001)
    y = 50 + sum(_pv(x, c, 0.15, h * 10) for c, h in zip(sx, sy))
    f = tmp_path / "exp.csv"
    np.savetxt(f, np.c_[x, y], delimiter=",")
    r = e.cmd_xrdmatch(str(f), [str(fs), str(fn)])
    assert r["candidates"][0]["formula"] == "NaCl"
    assert r["candidates"][0]["weighted_match"] > 0.9 > r["candidates"][1]["weighted_match"]


def test_eis_recovers_bulk_resistance_and_conductivity(tmp_path):
    from impedance.models.circuits import CustomCircuit
    true = [50.0, 2000.0, 1e-9, 0.9, 1e-6, 0.8]
    cc = CustomCircuit("R0-p(R1,CPE1)-CPE2", initial_guess=true)
    f = np.logspace(-1, 6, 60)
    Z = cc.predict(f)
    Z = Z * (1 + np.random.default_rng(1).normal(0, 0.003, f.size))
    path = tmp_path / "eis.csv"
    np.savetxt(path, np.c_[f, Z.real, -Z.imag], delimiter=",")     # 장비식 -Z'' 저장
    r = e.cmd_eis(str(path), "R0-p(R1,CPE1)-CPE2", thickness_cm=0.1, area_cm2=0.785)
    assert r["parameters"]["R1"] == pytest.approx(2000, rel=0.03)
    assert r["parameters"]["CPE1_1"] == pytest.approx(0.9, abs=0.02)
    assert r["conductivity_S_cm"] == pytest.approx(0.1 / (2000 * 0.785), rel=0.03)
    assert r["rms_relative_error"] < 0.02


def test_arrhenius_recovers_activation_energy(tmp_path):
    T = np.array([300, 325, 350, 375, 400, 450])
    Ea, A = 0.30, 1e4
    sigma = A * np.exp(-Ea / (e.KB_EV * T)) / T
    path = tmp_path / "s.csv"
    np.savetxt(path, np.c_[T, sigma], delimiter=",")
    r = e.cmd_arrhenius(str(path), "sigmaT", at=298.15)
    assert r["Ea_eV"] == pytest.approx(0.30, abs=1e-6)
    assert r["R2"] == pytest.approx(1.0)
    assert r["extrapolated"]["value"] == pytest.approx(A * np.exp(-Ea / (e.KB_EV * 298.15)) / 298.15, rel=1e-6)
    assert r["extrapolated"]["outside_measured_range"]
