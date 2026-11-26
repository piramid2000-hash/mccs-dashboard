#!/usr/bin/env python3
"""세이온 이론 계산 도구 — 병진(기체분자운동·통계열역학) · 열역학 · 오비탈 · 양자화학.

모든 결과는 계산값(P0)이며 실측(E1)이 아니다. 출력 JSON 을 재현 자료로 보관한다.

하위 명령
  trans   병진운동: 병진 분배함수, Sackur–Tetrode 엔트로피, 평균·rms·최빈 속도, 평균자유행로
  mo      분자 오비탈(PySCF HF/DFT): 오비탈 에너지, HOMO·LUMO·갭, Mulliken 전하, 쌍극자
  thermo  양자화학 열역학: 구조 최적화 → 진동수 → 병진·회전·진동 분해 S, H, G (이상기체·조화진동자)
  equil   기체 화학평형(Cantera): T·P 고정 평형 조성 또는 단열 화염온도

분자 입력: ASE G2 이름(H2O, CO2, CH4, NH3, C6H6 …) 또는 .xyz 파일 경로

예
  python seion_theory.py trans N2 --T 298.15 --P 101325 --diameter 3.7
  python seion_theory.py mo H2O --method b3lyp --basis def2-svp
  python seion_theory.py thermo H2O --method hf --basis 6-31g* --T 298.15
  python seion_theory.py equil --X "CH4:1,O2:2,N2:7.52" --mode HP --T 300 --P 101325
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from importlib.metadata import PackageNotFoundError, version

import scipy.constants as C

HARTREE_EV = C.physical_constants["Hartree energy in eV"][0]
HARTREE_J_MOL = C.physical_constants["Hartree energy"][0] * C.N_A


def _versions():
    out = {"python": sys.version.split()[0]}
    for p in ("numpy", "scipy", "ase", "pyscf", "geometric", "cantera"):
        try:
            out[p] = version(p)
        except PackageNotFoundError:
            pass
    return out


def _r(x, n=6):
    return None if x is None else round(float(x), n)


def _molar_mass_kg(formula: str) -> float:
    from ase.formula import Formula
    from ase.data import atomic_masses, atomic_numbers
    return sum(atomic_masses[atomic_numbers[s]] * n for s, n in Formula(formula).count().items()) / 1000.0


# ---------------------------------------------------------------- trans
def cmd_trans(formula: str, T: float, P: float, diameter_A: float | None = None) -> dict:
    M = _molar_mass_kg(formula)
    m = M / C.N_A
    k, h, R = C.k, C.h, C.R
    lam = h / math.sqrt(2 * math.pi * m * k * T)          # 열적 드브로이 파장
    V_per = k * T / P                                     # 분자 1개당 부피 (이상기체)
    q_trans = V_per / lam ** 3
    S_trans = R * (math.log(q_trans) + 2.5)              # Sackur–Tetrode
    out = {
        "species": formula, "T_K": T, "P_Pa": P,
        "molar_mass_g_mol": _r(M * 1000, 5),
        "thermal_de_broglie_wavelength_m": lam,
        "translational_partition_function_per_molecule": q_trans,
        "S_trans_J_molK": _r(S_trans, 4),
        "Cv_trans_J_molK": _r(1.5 * R, 4),
        "U_trans_J_mol": _r(1.5 * R * T, 2),
        "speed_mean_m_s": _r(math.sqrt(8 * k * T / (math.pi * m)), 3),
        "speed_rms_m_s": _r(math.sqrt(3 * k * T / m), 3),
        "speed_most_probable_m_s": _r(math.sqrt(2 * k * T / m), 3),
        "number_density_m3": P / (k * T),
        "assumptions": "이상기체, 병진 자유도만(회전·진동·전자 제외). 원자 기체는 S_trans 가 전체 S 와 거의 같다.",
    }
    if diameter_A:
        d = diameter_A * 1e-10
        mfp = k * T / (math.sqrt(2) * math.pi * d ** 2 * P)
        out["collision_diameter_A"] = diameter_A
        out["mean_free_path_m"] = mfp
        out["collision_frequency_s-1"] = out["speed_mean_m_s"] / mfp
    out["grade"] = "P0 (통계역학 해석식)"
    return out


# ---------------------------------------------------------------- 분자 준비
def _atoms(spec: str):
    from ase.build import molecule
    from ase.io import read
    if os.path.isfile(spec):
        return read(spec)
    return molecule(spec)


def _mol(atoms, basis, charge=0, spin=0):
    from pyscf import gto
    return gto.M(atom=[(s, tuple(p)) for s, p in zip(atoms.get_chemical_symbols(), atoms.positions)],
                 basis=basis, charge=charge, spin=spin, unit="Angstrom", verbose=0)


def _mf(mol, method):
    from pyscf import dft, scf
    if method.lower() == "hf":
        mf = scf.RHF(mol) if mol.spin == 0 else scf.UHF(mol)
    else:
        mf = dft.RKS(mol) if mol.spin == 0 else dft.UKS(mol)
        mf.xc = method
    return mf


# ---------------------------------------------------------------- mo
def cmd_mo(spec: str, method="b3lyp", basis="def2-svp", charge=0, spin=0, n_show=5) -> dict:
    import numpy as np
    atoms = _atoms(spec)
    mol = _mol(atoms, basis, charge, spin)
    mf = _mf(mol, method)
    e = mf.kernel()
    if not mf.converged:
        return {"error": "SCF 미수렴 — 결과를 쓰지 말 것", "molecule": spec}
    if spin != 0:
        return {"molecule": spec, "E_total_Hartree": _r(e, 8),
                "note": "개각(spin≠0) 계는 α/β 오비탈이 분리됨 — 현재 요약은 폐각만 지원"}
    occ, mo_e = mf.mo_occ, mf.mo_energy
    homo = int(np.where(occ > 0)[0][-1])
    lumo = homo + 1
    lo, hi = max(0, homo - n_show + 1), min(len(mo_e), lumo + n_show)
    orbitals = [{"index": i, "label": ("HOMO" if i == homo else "LUMO" if i == lumo else
                                        f"HOMO-{homo - i}" if i < homo else f"LUMO+{i - lumo}"),
                 "occ": _r(occ[i], 3), "energy_eV": _r(mo_e[i] * HARTREE_EV, 4)} for i in range(lo, hi)]
    pop, chg = mf.mulliken_pop(verbose=0)
    dip = mf.dip_moment(unit="Debye", verbose=0)
    return {
        "molecule": spec, "formula": atoms.get_chemical_formula(), "method": method, "basis": basis,
        "charge": charge, "spin_2S": spin, "n_electrons": mol.nelectron,
        "E_total_Hartree": _r(e, 8),
        "HOMO_eV": _r(mo_e[homo] * HARTREE_EV, 4),
        "LUMO_eV": _r(mo_e[lumo] * HARTREE_EV, 4) if lumo < len(mo_e) else None,
        "gap_eV": _r((mo_e[lumo] - mo_e[homo]) * HARTREE_EV, 4) if lumo < len(mo_e) else None,
        "orbitals_near_frontier": orbitals,
        "mulliken_charges": {f"{s}{i}": _r(q, 4) for i, (s, q) in enumerate(zip(atoms.get_chemical_symbols(), chg))},
        "dipole_Debye": [_r(x, 4) for x in dip], "dipole_total_Debye": _r(float(np.linalg.norm(dip)), 4),
        "geometry": "입력 구조 그대로(최적화 안 함)",
        "caveats": "HF 갭은 과대, DFT(B3LYP 등) 갭은 과소 경향 — 광학 밴드갭 실측과 직접 같다고 쓰지 말 것. Mulliken 전하는 기저 의존.",
        "grade": "P0 (양자화학 계산)",
    }


# ---------------------------------------------------------------- thermo
def cmd_thermo(spec: str, method="hf", basis="6-31g*", T=298.15, P=101325.0, charge=0, spin=0, optimize=True) -> dict:
    from pyscf.hessian import thermo
    atoms = _atoms(spec)
    mol = _mol(atoms, basis, charge, spin)
    mf = _mf(mol, method)
    mf.kernel()
    if optimize:
        import contextlib
        import logging
        import tempfile
        from pyscf.geomopt.geometric_solver import optimize as geo_opt
        # geomeTRIC 은 배너·로그를 stdout 으로 내보낸다 → JSON 출력과 섞이지 않게 stderr 로 돌리고 로그는 임시 폴더에
        logging.getLogger("geometric").setLevel(logging.WARNING)
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(sys.stderr):
            mol = geo_opt(mf, maxsteps=100, prefix=os.path.join(tmp, "opt"))
        mf = _mf(mol, method)
        mf.kernel()
    if not mf.converged:
        return {"error": "SCF 미수렴", "molecule": spec}
    hess = mf.Hessian().kernel()
    freq = thermo.harmonic_analysis(mol, hess)
    res = thermo.thermo(mf, freq["freq_au"], T, P)
    wn = [float(x) for x in freq["freq_wavenumber"]]
    imag = [x for x in wn if isinstance(x, complex) or x < 0]
    get = lambda key: res[key][0] if key in res else None  # noqa: E731
    out = {
        "molecule": spec, "formula": atoms.get_chemical_formula(), "method": method, "basis": basis,
        "optimized": optimize, "T_K": T, "P_Pa": P,
        "frequencies_cm-1": [_r(x, 2) for x in wn],
        "imaginary_modes": len(imag),
        "ZPE_kJ_mol": _r(get("ZPE") * HARTREE_J_MOL / 1000, 4),
        "S_J_molK": {
            "translational": _r(get("S_trans") * HARTREE_J_MOL, 4),
            "rotational": _r(get("S_rot") * HARTREE_J_MOL, 4),
            "vibrational": _r(get("S_vib") * HARTREE_J_MOL, 4),
            "electronic": _r(get("S_elec") * HARTREE_J_MOL, 4),
            "total": _r(get("S_tot") * HARTREE_J_MOL, 4),
        },
        "Cv_J_molK_total": _r(get("Cv_tot") * HARTREE_J_MOL, 4),
        "H_tot_Hartree": _r(get("H_tot"), 8), "G_tot_Hartree": _r(get("G_tot"), 8),
        "rotational_symmetry_number": res.get("sym_number", (None,))[0],
        "model": "이상기체·강체회전자·조화진동자(RRHO). 진동수 보정계수 미적용.",
        "grade": "P0 (양자화학 + 통계열역학)",
    }
    if imag:
        out["warning"] = f"허수 진동수 {len(imag)}개 — 극소점 아님. 열역학 값 사용 금지, 구조 재확인."
    return out


# ---------------------------------------------------------------- equil
def cmd_equil(X: str, T: float, P: float, mode="TP", mech="gri30.yaml", top=10) -> dict:
    import cantera as ct
    g = ct.Solution(mech)
    g.TPX = T, P, X
    h0 = g.enthalpy_mass
    g.equilibrate(mode)
    pairs = sorted(zip(g.species_names, g.X), key=lambda t: -t[1])[:top]
    return {
        "mechanism": mech, "mode": mode, "initial": {"T_K": T, "P_Pa": P, "X": X},
        "final_T_K": _r(g.T, 3), "final_P_Pa": _r(g.P, 2),
        "mole_fractions_top": {s: _r(x, 6) for s, x in pairs},
        "enthalpy_conserved": mode == "HP" and abs(g.enthalpy_mass - h0) < 1e-3 * max(1, abs(h0)),
        "note": "기체상 이상기체 평형. 고체상·응축상은 mechanism 에 없으면 미포함 — 소성·세라믹 상평형은 pycalphad 로.",
        "grade": "P0 (열역학 평형 계산)",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("trans"); p.add_argument("formula")
    p.add_argument("--T", type=float, default=298.15); p.add_argument("--P", type=float, default=101325.0)
    p.add_argument("--diameter", type=float, help="충돌 지름 Å (평균자유행로 계산용)")
    for name in ("mo", "thermo"):
        p = sub.add_parser(name); p.add_argument("molecule")
        p.add_argument("--method", default="b3lyp" if name == "mo" else "hf")
        p.add_argument("--basis", default="def2-svp" if name == "mo" else "6-31g*")
        p.add_argument("--charge", type=int, default=0); p.add_argument("--spin", type=int, default=0)
        if name == "thermo":
            p.add_argument("--T", type=float, default=298.15); p.add_argument("--P", type=float, default=101325.0)
            p.add_argument("--no-opt", action="store_true")
    p = sub.add_parser("equil"); p.add_argument("--X", required=True)
    p.add_argument("--T", type=float, required=True); p.add_argument("--P", type=float, default=101325.0)
    p.add_argument("--mode", default="TP", choices=["TP", "HP"]); p.add_argument("--mech", default="gri30.yaml")
    a = ap.parse_args(argv)

    if a.cmd == "trans":
        res = cmd_trans(a.formula, a.T, a.P, a.diameter)
    elif a.cmd == "mo":
        res = cmd_mo(a.molecule, a.method, a.basis, a.charge, a.spin)
    elif a.cmd == "thermo":
        res = cmd_thermo(a.molecule, a.method, a.basis, a.T, a.P, a.charge, a.spin, not a.no_opt)
    else:
        res = cmd_equil(a.X, a.T, a.P, a.mode, a.mech)
    res["versions"] = _versions()
    res["command"] = " ".join(["seion_theory.py"] + (argv if argv is not None else sys.argv[1:]))
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
