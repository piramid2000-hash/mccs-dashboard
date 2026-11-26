#!/usr/bin/env python3
"""세이온 결정 시뮬레이션 — 범용 머신러닝 원자간 퍼텐셜(MLIP) + phonopy.

기본 모델: MACE-MP-0 medium (Materials Project PBE 데이터 학습, float64).
선택 모델: CHGNet (--model chgnet) — 구조 이완·MD 는 쓸 만하나, 2026-11 점검에서 Si 의
퍼텐셜면이 부피 변화에 매끄럽지 않아(±0.5 % 변형에 힘상수 9.3→11.9→5.9) 포논·준조화
계산에는 쓰지 않는다(도구가 막는다).

결과는 P0(계산)이다. PBE 학습 모델이므로 격자상수 약 1 % 과대, 포논 진동수 다소 과소 경향.

하위 명령
  relax   CIF → 구조 이완(격자 포함/제외), 에너지, 밀도, 이완 CIF 저장
  phonon  포논: Γ점 진동수, 동역학 안정성, 온도별 Cv·S·F (조화근사)
  qha     준조화 근사: 부피별 포논 → 선열팽창계수 α(T), 부피(T), 체적탄성률
  md      분자동역학(NVT, Langevin): 지정 원소의 평균제곱변위 → 확산계수, Nernst–Einstein 전도도

예
  python seion_crystal.py relax Si.cif --out Si_relaxed.cif
  python seion_crystal.py phonon Si.cif --supercell 2 --T 300
  python seion_crystal.py qha Si.cif --supercell 2 --T 100 300 600
  python seion_crystal.py md Li3PS4.cif --species Li --T 800 --steps 2000
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import warnings
from importlib.metadata import PackageNotFoundError, version

import numpy as np

warnings.filterwarnings("ignore")
_CALC = {}


def _versions():
    out = {"python": sys.version.split()[0]}
    for p in ("numpy", "torch", "mace-torch", "chgnet", "phonopy", "pymatgen", "ase"):
        try:
            out[p] = version(p)
        except PackageNotFoundError:
            pass
    return out


def _r(x, n=6):
    return None if x is None else round(float(x), n)


def _calc(model="mace"):
    if model not in _CALC:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            if model in ("mace", "mace32"):
                from mace.calculators import mace_mp
                _CALC[model] = mace_mp(model="medium", device="cpu",
                                       default_dtype="float64" if model == "mace" else "float32")
            elif model == "chgnet":
                from chgnet.model.dynamics import CHGNetCalculator
                _CALC[model] = CHGNetCalculator()
            else:
                raise SystemExit(f"알 수 없는 모델: {model}")
    return _CALC[model]


MODEL_NOTE = {
    "mace": "MACE-MP-0 medium (PBE 학습)",
    "mace32": "MACE-MP-0 medium (PBE 학습, float32 — MD 용)",
    "chgnet": "CHGNet 0.3 (PBE 학습) — 포논·QHA 비권장",
}


def _atoms(path):
    from ase.io import read
    return read(path)


def _relax(atoms, model, relax_cell=True, fmax=0.005, steps=500):
    from ase.filters import FrechetCellFilter
    from ase.optimize import BFGS
    a = atoms.copy()
    a.calc = _calc(model)
    obj = FrechetCellFilter(a) if relax_cell else a
    with contextlib.redirect_stdout(io.StringIO()):
        opt = BFGS(obj, logfile=None)
        converged = opt.run(fmax=fmax, steps=steps)
    return a, float(a.get_potential_energy()), bool(converged)


# ---------------------------------------------------------------- relax
def cmd_relax(path, model="mace", relax_cell=True, out=None, fmax=0.005):
    a0 = _atoms(path)
    a, e, conv = _relax(a0, model, relax_cell, fmax)
    if out:
        a.write(out)
    c0, c1 = a0.cell.cellpar(), a.cell.cellpar()
    mass = a.get_masses().sum() * 1.66053906660e-24
    return {
        "input": path, "model": MODEL_NOTE[model], "formula": a.get_chemical_formula(mode="reduce"),
        "n_atoms": len(a), "relax_cell": relax_cell, "fmax_eV_A": fmax, "converged": conv,
        "energy_eV": _r(e), "energy_eV_per_atom": _r(e / len(a)),
        "cellpar_before": [_r(x, 5) for x in c0], "cellpar_after": [_r(x, 5) for x in c1],
        "volume_change_percent": _r(100 * (a.get_volume() / a0.get_volume() - 1), 3),
        "density_g_cm3": _r(mass / (a.get_volume() * 1e-24), 5), "relaxed_file": out,
        "grade": "P0 (MLIP, PBE 근사 — 격자 약 1% 과대 경향)",
    }


# ---------------------------------------------------------------- phonon core
def _phonopy(atoms, model, supercell, distance=0.01):
    from phonopy import Phonopy
    from phonopy.structure.atoms import PhonopyAtoms
    from ase import Atoms
    unit = PhonopyAtoms(symbols=atoms.get_chemical_symbols(), cell=atoms.cell[:],
                        scaled_positions=atoms.get_scaled_positions())
    ph = Phonopy(unit, supercell_matrix=np.diag([supercell] * 3))
    ph.generate_displacements(distance=distance)
    calc = _calc(model)
    forces = []
    for sc in ph.supercells_with_displacements:
        s = Atoms(sc.symbols, cell=sc.cell, scaled_positions=sc.scaled_positions, pbc=True)
        s.calc = calc
        f = s.get_forces()
        forces.append(f - f.mean(axis=0))
    ph.forces = forces
    ph.produce_force_constants()
    ph.symmetrize_force_constants()
    return ph


def _thermal(ph, temps, mesh=20):
    """phonopy 열물성은 원시 단위포 1 mol 기준 → 입력 단위포 기준으로 환산."""
    ph.run_mesh([mesh] * 3)
    ph.run_thermal_properties(temperatures=temps)
    d = dict(ph.get_thermal_properties_dict())
    k = len(ph.unitcell) / len(ph.primitive)
    for key in ("free_energy", "entropy", "heat_capacity"):
        d[key] = np.asarray(d[key]) * k
    return d


def _guard(model):
    if model == "chgnet":
        raise SystemExit("CHGNet 은 포논·QHA 에 쓰지 않습니다(퍼텐셜면 불연속 확인). --model mace 사용.")


# ---------------------------------------------------------------- phonon
def cmd_phonon(path, model="mace", supercell=2, temps=(300.0,), mesh=20, relax_first=True):
    _guard(model)
    a = _atoms(path)
    if relax_first:
        a, _, _ = _relax(a, model, True)
    ph = _phonopy(a, model, supercell)
    gamma = ph.get_frequencies([0, 0, 0])
    tp = _thermal(ph, list(temps), mesh)
    all_f = ph.get_mesh_dict()["frequencies"].ravel()
    n = len(a)
    rows = [{"T_K": _r(T, 2),
             "Cv_J_molK_per_mol_atoms": _r(tp["heat_capacity"][i] / n, 4),
             "S_J_molK_per_mol_atoms": _r(tp["entropy"][i] / n, 4),
             "F_kJ_mol_per_mol_atoms": _r(tp["free_energy"][i] / n, 5)}
            for i, T in enumerate(tp["temperatures"])]
    return {
        "input": path, "model": MODEL_NOTE[model], "formula": a.get_chemical_formula(mode="reduce"),
        "atoms_in_cell": n, "supercell": supercell, "q_mesh": mesh, "relaxed_first": relax_first,
        "gamma_frequencies_THz": [_r(f, 4) for f in gamma],
        "min_frequency_THz_on_mesh": _r(all_f.min(), 4),
        "dynamically_stable": bool(all_f.min() > -0.05),
        "thermal": rows,
        "note": "조화근사. Γ 음향모드 ~0 은 정상. 메쉬 최소 진동수 < -0.05 THz 면 동역학 불안정 의심. PBE 학습 MLIP 는 진동수를 다소 낮게 예측 — 정량 값은 라만·중성자 실측 또는 DFT 로 확인.",
        "grade": "P0 (MLIP + phonopy)",
    }


# ---------------------------------------------------------------- qha
def cmd_qha(path, model="mace", supercell=2, temps=(300.0,),
            strains=(-0.015, -0.01, -0.005, 0.0, 0.005, 0.01, 0.015, 0.02), mesh=20):
    _guard(model)
    from phonopy import PhonopyQHA
    a0, _, _ = _relax(_atoms(path), model, True)
    tgrid = np.arange(0, max(temps) * 1.3 + 201, 10.0)
    vols, energies, fe, cv, ent = [], [], [], [], []
    for s in strains:
        a = a0.copy()
        a.set_cell(a0.cell[:] * (1 + s), scale_atoms=True)
        a, e, _ = _relax(a, model, relax_cell=False)
        ph = _phonopy(a, model, supercell)
        tp = _thermal(ph, tgrid, mesh)
        vols.append(a.get_volume()); energies.append(e)
        fe.append(tp["free_energy"]); cv.append(tp["heat_capacity"]); ent.append(tp["entropy"])
    with contextlib.redirect_stdout(io.StringIO()):
        q = PhonopyQHA(volumes=vols, electronic_energies=energies, temperatures=tgrid,
                       free_energy=np.array(fe).T, cv=np.array(cv).T, entropy=np.array(ent).T,
                       eos="vinet", t_max=float(max(temps) + 100))
    beta = np.array(q.thermal_expansion)
    vT = np.array(q.volume_temperature)
    B = np.array(q.bulk_modulus_temperature)
    qt = tgrid[: len(beta)]
    rows = []
    for T in temps:
        i = int(np.argmin(abs(qt - T)))
        rows.append({"T_K": _r(qt[i], 1), "volume_A3": _r(vT[i], 4),
                     "alpha_linear_per_K": _r(beta[i] / 3, 10), "beta_volumetric_per_K": _r(beta[i], 10),
                     "bulk_modulus_GPa": _r(B[i], 3)})
    edge = vT.max() > max(vols) or vT.min() < min(vols)
    # 물리 점검: 온도가 오르면 체적탄성률은 줄어야 한다. 늘면 MLIP 의 고온 Grüneisen 거동 오차.
    unphysical = [r["T_K"] for prev, r in zip(rows, rows[1:]) if r["bulk_modulus_GPa"] > prev["bulk_modulus_GPa"] + 0.5]
    return {
        "input": path, "model": MODEL_NOTE[model], "formula": a0.get_chemical_formula(mode="reduce"),
        "strains_linear": list(strains), "volumes_A3": [_r(v, 4) for v in vols],
        "energies_eV": [_r(e, 6) for e in energies],
        "results": rows,
        "warning": "평형 부피가 계산한 부피 범위를 벗어남 — strains 범위를 넓혀 재계산" if edge else None,
        "unphysical_trend_at_T": unphysical or None,
        "reliability": "검증: 300 K 에서 Al α 21.6e-6(실측 23.1e-6), MgO α 12.2e-6(실측 ~10.5e-6)·B 163 GPa(실측 160). Si 는 α 4배 과대(포논 과소 예측) — 공유결합 반도체·음의 열팽창 물질은 신뢰 낮음. 고온(대략 600 K 이상)에서 체적탄성률이 증가하는 비물리적 경향이 나타날 수 있음 — unphysical_trend_at_T 가 있으면 그 온도 결과는 쓰지 말 것.",
        "note": "준조화 근사·등방 팽창 가정(비입방 결정은 축별 팽창 다를 수 있음). Debye 온도 이상·용융 근처에서 비조화 오차 증가.",
        "grade": "P0 (MLIP + 준조화 포논)",
    }


# ---------------------------------------------------------------- md
def cmd_md(path, species, model="mace32", T=800.0, steps=2000, dt_fs=2.0, supercell=1, equil=200, seed=0):
    from ase import units
    from ase.md.langevin import Langevin
    from ase.md.velocitydistribution import MaxwellBoltzmannDistribution
    atoms = _atoms(path)
    if supercell > 1:
        atoms = atoms.repeat(supercell)
    atoms.calc = _calc(model)
    idx = [i for i, s in enumerate(atoms.get_chemical_symbols()) if s == species]
    if not idx:
        return {"error": f"{species} 원자가 구조에 없음"}
    MaxwellBoltzmannDistribution(atoms, temperature_K=T, rng=np.random.default_rng(seed))
    dyn = Langevin(atoms, dt_fs * units.fs, temperature_K=T, friction=0.02, rng=np.random.default_rng(seed + 1))
    dyn.run(equil)
    pos, temps_seen = [], []
    for _ in range(max(steps // 10, 4)):
        dyn.run(10)
        pos.append(atoms.get_positions(wrap=False)[idx].copy())
        temps_seen.append(atoms.get_temperature())
    pos = np.array(pos)
    msd = ((pos - pos[0]) ** 2).sum(axis=2).mean(axis=1)       # Å²
    t_ps = np.arange(len(msd)) * 10 * dt_fs / 1000
    half = len(t_ps) // 2
    slope = np.polyfit(t_ps[half:], msd[half:], 1)[0]          # Å²/ps
    D = max(slope, 0.0) / 6 * 1e-4                             # cm²/s
    n_m3 = len(idx) / (atoms.get_volume() * 1e-30)
    q, kB = 1.602176634e-19, 1.380649e-23
    sigma = n_m3 * q ** 2 * (D * 1e-4) / (kB * T)               # S/m, 1가 이온
    return {
        "input": path, "model": MODEL_NOTE[model], "species": species, "n_species": len(idx),
        "n_atoms": len(atoms), "T_target_K": T, "T_mean_K": _r(np.mean(temps_seen), 1),
        "steps": steps, "dt_fs": dt_fs, "simulated_ps": _r(t_ps[-1], 3),
        "final_msd_A2": _r(msd[-1], 4), "D_cm2_s": D, "sigma_NernstEinstein_S_cm": sigma / 100,
        "diffusive": bool(msd[-1] > 3.0),
        "note": "짧은 MD 는 통계 오차가 크다. MSD 가 수 Å² 이상이어야 확산으로 본다. 여러 온도에서 D 를 구해 seion_expdata.py arrhenius 로 상온 외삽. Nernst–Einstein 은 이온 상관 무시(Haven 비 1)·1가 이온 가정.",
        "grade": "P0 (MLIP-MD)",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", choices=["mace", "chgnet"], default="mace")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("relax"); p.add_argument("cif"); p.add_argument("--out")
    p.add_argument("--fixed-cell", action="store_true"); p.add_argument("--fmax", type=float, default=0.005)
    p = sub.add_parser("phonon"); p.add_argument("cif"); p.add_argument("--supercell", type=int, default=2)
    p.add_argument("--T", type=float, nargs="+", default=[300.0]); p.add_argument("--mesh", type=int, default=20)
    p.add_argument("--no-relax", action="store_true")
    p = sub.add_parser("qha"); p.add_argument("cif"); p.add_argument("--supercell", type=int, default=2)
    p.add_argument("--T", type=float, nargs="+", default=[300.0]); p.add_argument("--mesh", type=int, default=20)
    p = sub.add_parser("md"); p.add_argument("cif"); p.add_argument("--species", required=True)
    p.add_argument("--T", type=float, default=800.0); p.add_argument("--steps", type=int, default=2000)
    p.add_argument("--dt", type=float, default=2.0); p.add_argument("--supercell", type=int, default=1)
    a = ap.parse_args(argv)
    if a.cmd == "relax":
        res = cmd_relax(a.cif, a.model, not a.fixed_cell, a.out, a.fmax)
    elif a.cmd == "phonon":
        res = cmd_phonon(a.cif, a.model, a.supercell, a.T, a.mesh, not a.no_relax)
    elif a.cmd == "qha":
        res = cmd_qha(a.cif, a.model, a.supercell, a.T, mesh=a.mesh)
    else:
        res = cmd_md(a.cif, a.species, "mace32" if a.model == "mace" else a.model, a.T, a.steps, a.dt, a.supercell)
    res["versions"] = _versions()
    res["command"] = " ".join(["seion_crystal.py"] + (argv if argv is not None else sys.argv[1:]))
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
