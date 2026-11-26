#!/usr/bin/env python3
"""세이온 소재 계산 도구 (seion-materials-check 스킬용).

암산 대신 이 스크립트를 실행해 수치를 얻고, 출력(JSON)을 그대로 보관한다.
모든 결과는 계산값(P0)이며 실측(E1)이 아니다.

하위 명령
  formula  화학식 → 분자량, 원소별 질량%·몰분율, 산화물 기준 질량%
  convert  배합 조성 질량% ↔ 몰%  (성분은 화학식으로)
  cif      CIF/POSCAR → 격자, 부피, Z, 이론 밀도, 공간군(symprec 3단계), 읽기 경고
  mix      혼합칙 상·하한(Voigt/Reuss) — 질량분율이면 밀도로 부피분율 환산
  hull     Materials Project 안정선 위 에너지 (MP_API_KEY 와 mp-api 필요)

예
  python seion_matcalc.py formula "K0.65Al2.65Si3.35O10(OH)2"
  python seion_matcalc.py convert --basis wt --to mol "SiO2=60,Al2O3=25,K2O=15"
  python seion_matcalc.py cif sample.cif
  python seion_matcalc.py mix --basis wt "A:frac=0.7,rho=2.65,prop=1.4" "B:frac=0.3,rho=1.2,prop=0.2"
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from importlib.metadata import PackageNotFoundError, version

# 흔한 세라믹·광물 산화물 기준 (원소 → 산화물). 필요한 경우 --oxide 로 덮어쓴다.
DEFAULT_OXIDES = {
    "Si": "SiO2", "Al": "Al2O3", "Fe": "Fe2O3", "Mg": "MgO", "Ca": "CaO",
    "Na": "Na2O", "K": "K2O", "Ti": "TiO2", "Li": "Li2O", "P": "P2O5",
    "Mn": "MnO", "Zr": "ZrO2", "B": "B2O3", "Ba": "BaO", "Sr": "SrO",
    "Zn": "ZnO", "H": "H2O",
}


def _versions() -> dict:
    out = {"python": sys.version.split()[0]}
    for pkg in ("pymatgen", "pycalphad", "mp-api"):
        try:
            out[pkg] = version(pkg)
        except PackageNotFoundError:
            pass
    return out


def _r(x, n=6):
    return None if x is None else round(float(x), n)


# ---------------------------------------------------------------- formula
def cmd_formula(formula: str, oxide_overrides: dict | None = None) -> dict:
    from pymatgen.core import Composition

    comp = Composition(formula)
    mw = comp.weight
    elements = {}
    for el, amt in comp.items():
        elements[str(el)] = {
            "atoms_per_formula": _r(amt),
            "mol_fraction": _r(comp.get_atomic_fraction(el)),
            "wt_percent": _r(100 * comp.get_wt_fraction(el), 4),
        }

    oxides = dict(DEFAULT_OXIDES, **(oxide_overrides or {}))
    oxide_wt, missing, o_needed = {}, [], 0.0
    for el, amt in comp.items():
        sym = str(el)
        if sym == "O":
            continue
        if sym not in oxides:
            missing.append(sym)
            continue
        ox = Composition(oxides[sym])
        n_cat = ox[sym]
        ox_moles = amt / n_cat
        oxide_wt[oxides[sym]] = ox_moles * ox.weight
        o_needed += ox_moles * ox["O"]
    total = sum(oxide_wt.values())
    oxide_basis = None
    if oxide_wt and not missing:
        oxide_basis = {
            "wt_percent": {k: _r(100 * v / total, 4) for k, v in oxide_wt.items()},
            "oxygen_in_formula": _r(comp["O"]),
            "oxygen_implied_by_oxides": _r(o_needed),
            "note": "산화물 합은 100%로 정규화. 화학식 O 와 산화물 O 가 다르면 산화수 가정이 다르다는 뜻 — 보고서에 그대로 적을 것.",
        }
    return {
        "input": formula,
        "reduced_formula": comp.reduced_formula,
        "molar_mass_g_per_mol": _r(mw, 4),
        "elements": elements,
        "oxide_basis": oxide_basis,
        "oxide_missing_elements": missing,
        "grade": "P0 (계산)",
    }


# ---------------------------------------------------------------- convert
def _parse_pairs(text: str) -> dict:
    out = {}
    for part in text.split(","):
        if not part.strip():
            continue
        k, v = part.split("=")
        out[k.strip()] = float(v)
    return out


def cmd_convert(spec: str, basis: str, to: str) -> dict:
    from pymatgen.core import Composition

    amounts = _parse_pairs(spec)
    s = sum(amounts.values())
    warn = []
    if abs(s - 100) > 1e-6 and abs(s - 1) > 1e-6:
        warn.append(f"입력 합이 {s:g} — 100(또는 1)이 아님. 비율로만 환산했으며 원 입력을 확인할 것.")
    mw = {k: Composition(k).weight for k in amounts}
    if basis == to:
        raise SystemExit("basis 와 to 가 같습니다.")
    if basis == "wt":
        moles = {k: amounts[k] / mw[k] for k in amounts}
        t = sum(moles.values())
        result = {k: _r(100 * moles[k] / t, 4) for k in amounts}
    else:
        mass = {k: amounts[k] * mw[k] for k in amounts}
        t = sum(mass.values())
        result = {k: _r(100 * mass[k] / t, 4) for k in amounts}
    return {
        "input": amounts, "input_basis": basis, "output_basis": to,
        "molar_masses": {k: _r(v, 4) for k, v in mw.items()},
        "result_percent": result,
        "formula_used": "mol%_i = (wt_i/M_i)/Σ(wt_j/M_j)·100 ; wt%_i = (x_i·M_i)/Σ(x_j·M_j)·100",
        "warnings": warn, "grade": "P0 (계산)",
    }


# ---------------------------------------------------------------- cif
def cmd_cif(path: str, symprecs=(0.001, 0.01, 0.1)) -> dict:
    from pymatgen.core import Structure
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        st = Structure.from_file(path)
    read_warnings = sorted({str(w.message) for w in caught})

    partial = [i for i, site in enumerate(st) if not site.is_ordered]
    sg = []
    for sp in symprecs:
        try:
            a = SpacegroupAnalyzer(st, symprec=sp)
            sg.append({"symprec": sp, "symbol": a.get_space_group_symbol(),
                       "number": a.get_space_group_number()})
        except Exception as e:  # noqa: BLE001
            sg.append({"symprec": sp, "error": str(e)})
    numbers = {x.get("number") for x in sg if "number" in x}

    comp = st.composition
    z = None
    try:
        z = _r(comp.get_reduced_composition_and_factor()[1], 4)
    except Exception:  # noqa: BLE001
        pass
    lat = st.lattice
    return {
        "file": path,
        "formula_cell": comp.formula,
        "reduced_formula": comp.reduced_formula,
        "Z_formula_units": z,
        "lattice": {"a": _r(lat.a), "b": _r(lat.b), "c": _r(lat.c),
                    "alpha": _r(lat.alpha), "beta": _r(lat.beta), "gamma": _r(lat.gamma),
                    "volume_A3": _r(lat.volume, 4)},
        "theoretical_density_g_cm3": _r(st.density, 5),
        "n_sites": len(st),
        "partial_occupancy_sites": partial,
        "space_group_by_symprec": sg,
        "space_group_consistent": len(numbers) == 1,
        "read_warnings": read_warnings,
        "grade": "P0 (계산 — 결정학적 이론 밀도, 기공·불순물 미반영)",
    }


# ---------------------------------------------------------------- mix
def _parse_phase(text: str) -> dict:
    name, _, rest = text.partition(":")
    d = {"name": name.strip()}
    for kv in rest.split(","):
        k, v = kv.split("=")
        d[k.strip()] = float(v)
    return d


def cmd_mix(phase_specs: list, basis: str) -> dict:
    phases = [_parse_phase(p) for p in phase_specs]
    fsum = sum(p["frac"] for p in phases)
    warn = []
    if abs(fsum - 1) > 1e-6:
        warn.append(f"분율 합 {fsum:g} ≠ 1 — 정규화하지 않고 중단")
        return {"phases": phases, "warnings": warn}
    if basis == "wt":
        if not all("rho" in p for p in phases):
            raise SystemExit("질량분율 입력에는 각 상의 rho(밀도) 가 필요합니다.")
        vol = [p["frac"] / p["rho"] for p in phases]
        tv = sum(vol)
        vf = [v / tv for v in vol]
    else:
        vf = [p["frac"] for p in phases]
    out = {"phases": phases, "input_basis": basis,
           "volume_fractions": {p["name"]: _r(v) for p, v in zip(phases, vf)}}
    if all("rho" in p for p in phases):
        out["density_dense_g_cm3"] = _r(sum(v * p["rho"] for p, v in zip(phases, vf)), 5)
    if all("prop" in p for p in phases):
        voigt = sum(v * p["prop"] for p, v in zip(phases, vf))
        reuss = 1 / sum(v / p["prop"] for p, v in zip(phases, vf))
        out["property_bounds"] = {"upper_voigt": _r(voigt), "lower_reuss": _r(reuss),
                                  "note": "실제 값은 미세조직에 따라 두 한계 사이. 단일 값으로 단정 금지."}
    out["warnings"] = warn
    out["grade"] = "P0 (혼합칙 추정, 기공 0 가정)"
    return out


# ---------------------------------------------------------------- hull
def cmd_hull(chemsys: str) -> dict:
    import os
    if not os.environ.get("MP_API_KEY"):
        return {"error": "MP_API_KEY 미설정 — 키 없이 추정값을 내지 말 것. 공개 웹 값은 출처와 함께 따로 기록."}
    try:
        from mp_api.client import MPRester
    except ImportError:
        return {"error": "mp-api 미설치: pip install mp-api"}
    with MPRester() as mpr:
        docs = mpr.materials.summary.search(
            chemsys=chemsys,
            fields=["material_id", "formula_pretty", "energy_above_hull",
                    "formation_energy_per_atom", "is_stable", "symmetry"])
    rows = sorted(({"id": str(d.material_id), "formula": d.formula_pretty,
                    "e_above_hull_eV_atom": _r(d.energy_above_hull),
                    "formation_energy_eV_atom": _r(d.formation_energy_per_atom),
                    "stable": d.is_stable,
                    "space_group": d.symmetry.symbol if d.symmetry else None} for d in docs),
                  key=lambda r: (r["e_above_hull_eV_atom"] is None, r["e_above_hull_eV_atom"]))
    return {"chemsys": chemsys, "n": len(rows), "entries": rows,
            "grade": "P0 (DFT 계산 DB, 0 K)", "source": "Materials Project"}


# ---------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("formula"); p.add_argument("formula")
    p.add_argument("--oxide", default="", help="원소=산화물 덮어쓰기, 예 Fe=FeO")
    p = sub.add_parser("convert"); p.add_argument("spec")
    p.add_argument("--basis", choices=["wt", "mol"], required=True)
    p.add_argument("--to", choices=["wt", "mol"], required=True)
    p = sub.add_parser("cif"); p.add_argument("path")
    p = sub.add_parser("mix"); p.add_argument("phases", nargs="+")
    p.add_argument("--basis", choices=["wt", "vol"], required=True)
    p = sub.add_parser("hull"); p.add_argument("chemsys", help="예 Li-P-S-Cl")
    a = ap.parse_args(argv)

    if a.cmd == "formula":
        ov = {k: v for k, v in (x.split("=") for x in a.oxide.split(",") if x)}
        res = cmd_formula(a.formula, ov)
    elif a.cmd == "convert":
        res = cmd_convert(a.spec, a.basis, a.to)
    elif a.cmd == "cif":
        res = cmd_cif(a.path)
    elif a.cmd == "mix":
        res = cmd_mix(a.phases, a.basis)
    else:
        res = cmd_hull(a.chemsys)
    res["versions"] = _versions()
    res["command"] = " ".join(["seion_matcalc.py"] + (argv if argv is not None else sys.argv[1:]))
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
