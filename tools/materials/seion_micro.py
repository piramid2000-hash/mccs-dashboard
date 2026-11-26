#!/usr/bin/env python3
"""세이온 미세조직 정량 + 실험설계(베이지안 최적화, ask–tell).

하위 명령
  pores    SEM(2D) 또는 CT 단층 묶음(3D) 이미지 → 기공률, 기공 크기 분포(d10/d50/d90),
           비표면적, 관통 연결성, (3D) 굴곡도
  doe      실험 기록(CSV) + 인자 공간(JSON) → 다음 실험 조건 제안 (Optuna, 적은 실험용)
           suggest: 다음 N 개 조건 / status: 지금까지 최선·파레토

이미지: .png/.tif/.jpg(2D 흑백), .npy(2D/3D 배열), 여러 장 .tif(3D 단층 묶음).
이미 이진화된 영상(0/1)은 1 = 기공 으로 읽는다(--pores-dark 무시).
pores 결과는 E1(실측 영상 해석)이지만 이진화 임계값·화소 크기에 민감 — 둘 다 출력에 남긴다.

예
  python seion_micro.py pores sem.png --pixel-um 0.5 --pores-dark
  python seion_micro.py pores ct.tif --pixel-um 2.0 --pores-dark --tortuosity
  python seion_micro.py doe suggest --space doe_space_paste.json --log doe_log.csv --n 3
  python seion_micro.py doe status --space doe_space_paste.json --log doe_log.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import warnings
from importlib.metadata import PackageNotFoundError, version

import numpy as np

warnings.filterwarnings("ignore")


def _versions():
    out = {"python": sys.version.split()[0]}
    for p in ("numpy", "scipy", "scikit-image", "porespy", "optuna", "torch"):
        try:
            out[p] = version(p)
        except PackageNotFoundError:
            pass
    return out


def _g(x, n=5):
    return None if x is None else float(f"{float(x):.{n}g}")


# ================================================================ pores
def load_image(path):
    if path.endswith(".npy"):
        return np.load(path).astype(float)
    from skimage import io
    im = io.imread(path)
    if im.ndim == 3 and im.shape[-1] in (3, 4) and not path.lower().endswith((".tif", ".tiff")):
        from skimage.color import rgb2gray
        im = rgb2gray(im[..., :3])
    return np.asarray(im, float)


def segment(im, threshold=None, pores_dark=True):
    from skimage.filters import threshold_otsu
    th = threshold_otsu(im) if threshold is None else threshold
    pores = (im < th) if pores_dark else (im > th)
    return pores, float(th)


def cmd_pores(path, pixel_um, threshold=None, pores_dark=True, tortuosity=False, min_pore_px=2):
    import porespy as ps
    from scipy import ndimage
    from skimage import morphology
    im = load_image(path)
    if im.dtype == bool or set(np.unique(im)) <= {0.0, 1.0}:
        pores, th = im.astype(bool), None        # 이미 이진화된 입력: 1(True) = 기공 으로 약속
    else:
        pores, th = segment(im, threshold, pores_dark)
    if min_pore_px > 1:
        pores = morphology.remove_small_objects(pores, min_size=min_pore_px)
    dim = pores.ndim
    phi = float(pores.mean())
    lt = 2 * ps.filters.local_thickness(pores, method="dt")[pores] * pixel_um   # 지름 µm
    d10, d50, d90 = (np.percentile(lt, q) if lt.size else None for q in (10, 50, 90))
    # 비표면적: 2D 는 경계 길이/면적, 3D 는 메쉬 면적/부피
    if dim == 2:
        from skimage.measure import perimeter
        sv = perimeter(pores) * pixel_um / (pores.size * pixel_um ** 2)
        sv_unit = "µm⁻¹ (경계 길이/면적)"
    else:
        try:
            sv = ps.metrics.mesh_surface_area(im=pores) * pixel_um ** 2 / (pores.size * pixel_um ** 3)
        except Exception:  # noqa: BLE001
            sv = None
        sv_unit = "µm⁻¹ (면적/부피)"
    lab, n = ndimage.label(pores)
    perc = {}
    for ax in range(dim):
        a = np.take(lab, 0, axis=ax); b = np.take(lab, -1, axis=ax)
        common = (set(np.unique(a)) & set(np.unique(b))) - {0}
        perc["xyz"[ax]] = bool(common)
    out = {
        "input": path, "shape": list(pores.shape), "dimension": dim, "pixel_um": pixel_um,
        "segmentation": {"method": "Otsu" if threshold is None and th is not None else ("manual" if th is not None else "pre-binarized"),
                         "threshold": th, "pores_dark": pores_dark},
        "porosity": phi,
        "pore_diameter_um": {"d10": _g(d10), "d50": _g(d50), "d90": _g(d90), "mean": _g(lt.mean() if lt.size else None)},
        "pore_count_connected_regions": int(n),
        "specific_surface": {"value": _g(sv) if sv is not None else None, "unit": sv_unit},
        "percolating_axes": perc,
    }
    if tortuosity and dim == 3:
        # 굴곡도 τ = ε / (D_eff/D0) — 기공상만 전도하는 복셀 FEM(seion_voxelfem)으로 축별 계산
        from seion_voxelfem import effective_conductivity
        tau = {}
        for ax in range(3):
            if perc["xyz"[ax]]:
                sub = np.moveaxis(pores, ax, 2)              # 계산 축을 z 로
                k_rel, _ = effective_conductivity(sub)
                tau["xyz"[ax]] = _g(phi / k_rel) if k_rel > 0 else None
            else:
                tau["xyz"[ax]] = "관통 안 됨"
        out["tortuosity"] = tau
        out["tortuosity_definition"] = "τ = ε·D0/D_eff (기공률 / 상대 유효 확산·전도도). 직선 관통 채널 = 1."
    out["notes"] = ("2D 단면의 기공률은 3D 기공률의 추정(등방·무작위 단면 가정). 2D 기공 크기는 단면 지름 — 3D 구 지름보다 작게 나온다. "
                    "이진화 임계값에 민감 — 임계값 ±5 % 로 다시 돌려 민감도를 함께 보고할 것.") if dim == 2 else \
                   "CT 해상도(화소 크기)보다 작은 기공은 보이지 않는다 — 수은압입·BET 와 병행."
    out["grade"] = "E1 (실측 영상 해석) — 이진화·화소 크기 의존"
    return out


# ================================================================ doe
def load_space(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_log(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if any(v.strip() for v in r.values() if v)]


def _distributions(space):
    import optuna
    d = {}
    for name, spec in space["factors"].items():
        if spec["type"] == "float":
            d[name] = optuna.distributions.FloatDistribution(spec["low"], spec["high"])
        elif spec["type"] == "int":
            d[name] = optuna.distributions.IntDistribution(spec["low"], spec["high"])
        else:
            d[name] = optuna.distributions.CategoricalDistribution(spec["choices"])
    return d


def derived(space, params):
    """'balance' 인자(예: 물 = 100 - 나머지 합) 계산과 범위 위반량."""
    out, viol = {}, []
    for name, spec in space.get("derived", {}).items():
        if spec["type"] == "balance":
            val = spec["total"] - sum(float(params[k]) for k in spec["of"])
            out[name] = val
            viol.append(max(spec["low"] - val, val - spec["high"]))   # ≤ 0 이면 범위 안
    return out, viol


def _study(space, rows, seed):
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    objs = space["objectives"]
    cons_cols = space.get("constraints", [])
    dists = _distributions(space)

    def cons_func(tr):
        return tr.user_attrs.get("c", [0.0])

    if len(objs) == 1:
        sampler = optuna.samplers.GPSampler(seed=seed, n_startup_trials=space.get("n_startup", 6),
                                            constraints_func=cons_func, deterministic_objective=False)
    else:
        sampler = optuna.samplers.TPESampler(seed=seed, n_startup_trials=space.get("n_startup", 6),
                                             constraints_func=cons_func, multivariate=True)
    study = optuna.create_study(directions=[o["direction"] for o in objs], sampler=sampler)
    used = 0
    for r in rows:
        try:
            params = {}
            for k, dist in dists.items():
                v = r[k]
                params[k] = float(v) if isinstance(dist, optuna.distributions.FloatDistribution) else \
                    int(float(v)) if isinstance(dist, optuna.distributions.IntDistribution) else v
            vals = [float(r[o["name"]]) for o in objs]
        except (KeyError, ValueError):
            continue                                            # 결과가 아직 없는 행(진행 중 실험)
        _, dviol = derived(space, params)
        c = [float(r[c_]) for c_ in cons_cols if r.get(c_, "") != ""] + dviol
        study.add_trial(optuna.trial.create_trial(params=params, distributions=dists, values=vals,
                                                  user_attrs={"c": c or [0.0]}))
        used += 1
    return study, used


def cmd_doe_suggest(space_path, log_path, n=1, seed=0, max_tries=200):
    space = load_space(space_path)
    rows = read_log(log_path)
    study, used = _study(space, rows, seed)
    out = []
    tries = 0
    while len(out) < n and tries < max_tries:
        tries += 1
        tr = study.ask(_distributions(space))
        p = {k: tr.params[k] for k in space["factors"]}
        d, viol = derived(space, p)
        if any(v > 0 for v in viol):                            # 파생값(예: 물) 범위 밖이면 버리고 다시
            study.tell(tr, state=__import__("optuna").trial.TrialState.FAIL)
            continue
        for k, spec in space["factors"].items():
            if spec["type"] == "float" and "round" in spec:
                p[k] = round(p[k], spec["round"])
        out.append({**p, **{k: round(v, 3) for k, v in d.items()}})
        study.tell(tr, state=__import__("optuna").trial.TrialState.FAIL)   # 결과는 실험 후 log 에 기록
    phase = "탐색(무작위 초기 실험)" if used < space.get("n_startup", 6) else "베이지안 최적화"
    return {"space": space_path, "log": log_path, "completed_experiments": used, "phase": phase,
            "suggestions": out,
            "next_step": f"제안 조건으로 실험 → {log_path} 에 인자·결과(" + ", ".join(o["name"] for o in space["objectives"]) +
                         (", " + ", ".join(space.get("constraints", [])) if space.get("constraints") else "") + ") 행 추가 → 다시 suggest",
            "note": "제안은 지금까지의 실험에만 근거한다. 초기 몇 회는 공간을 넓게 탐색한다. 같은 조건 반복 실험으로 재현성(오차)도 함께 기록할 것."}


def cmd_doe_status(space_path, log_path):
    space = load_space(space_path)
    rows = read_log(log_path)
    study, used = _study(space, rows, 0)
    trials = [t for t in study.trials if t.values]
    feas = [t for t in trials if all(c <= 0 for c in t.user_attrs.get("c", [0]))]
    objs = space["objectives"]
    res = {"completed_experiments": used, "feasible": len(feas)}
    if not feas:
        res["note"] = "제약을 만족한 실험이 아직 없음"
        return res
    if len(objs) == 1:
        sign = 1 if objs[0]["direction"] == "minimize" else -1
        best = min(feas, key=lambda t: sign * t.values[0])
        res["best"] = {"params": best.params, objs[0]["name"]: best.values[0]}
    else:
        sign = np.array([1 if o["direction"] == "minimize" else -1 for o in objs])
        V = np.array([t.values for t in feas]) * sign
        front = [i for i in range(len(feas)) if not any(np.all(V[j] <= V[i]) and np.any(V[j] < V[i]) for j in range(len(feas)))]
        res["pareto"] = [{"params": feas[i].params, **{o["name"]: feas[i].values[k] for k, o in enumerate(objs)}} for i in front]
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pores"); p.add_argument("image"); p.add_argument("--pixel-um", type=float, required=True)
    p.add_argument("--threshold", type=float); p.add_argument("--pores-dark", action="store_true")
    p.add_argument("--tortuosity", action="store_true"); p.add_argument("--min-pore-px", type=int, default=2)
    p = sub.add_parser("doe"); p.add_argument("action", choices=["suggest", "status"])
    p.add_argument("--space", required=True); p.add_argument("--log", required=True)
    p.add_argument("--n", type=int, default=1); p.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    if a.cmd == "pores":
        res = cmd_pores(a.image, a.pixel_um, a.threshold, a.pores_dark, a.tortuosity, a.min_pore_px)
    elif a.action == "suggest":
        res = cmd_doe_suggest(a.space, a.log, a.n, a.seed)
    else:
        res = cmd_doe_status(a.space, a.log)
    res["versions"] = _versions()
    res["command"] = " ".join(["seion_micro.py"] + (argv if argv is not None else sys.argv[1:]))
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
