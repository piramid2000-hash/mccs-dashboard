#!/usr/bin/env python3
"""세이온 자이로이드 메타물질 — 페이스트 압출(DIW) 3D 프린팅 설계·최적화.

대상: 팽창 일라이트 + 알지네이트 + C38H78O(장쇄 지방알코올) + 물 페이스트로 출력하는
자이로이드(TPMS) 다공 격자. 설정은 gyroid_seion_config.json — '가정' 값은 실측으로 교체.

모델 연결
  형상    레벨셋 f = sin x cos y + sin y cos z + sin z cos x
          network(골격형): f ≤ t   /   sheet(막형): |f| ≤ t
          → 상대밀도 φ, 벽두께·기공 크기 분포(국소두께), 연결성, 하향 오버행 각 분포
  물성    복셀 FEM(seion_voxelfem) → E_rel, k_rel → Gibson–Ashby 지수 맞춤
  공정    Herschel–Bulkley 관유동 → 노즐 압출압력 / 항복응력 → 적층 가능 높이
          층마다 벽이 옆으로 밀리는 거리 h·tanα ≤ 0.5·필라멘트폭 이어야 받쳐짐
  후처리  건조·소성 선수축 → 출력 치수 보정 배율, 유기물 연소 → 벽 기공률
  최적화  Optuna NSGA-II 다목적 + 제약 → 파레토 해, 추천안

하위 명령
  calibrate  형상·물성 보정표 생성(1회, 수 분) → data/gyroid_calibration.json
  rheo       유변 측정(전단속도, 전단응력) CSV → Herschel–Bulkley τ0·K·n
  paste      배합 → 페이스트 밀도, 부피분율, 건조·소성 후 벽 기공률
  evaluate   설계 1개 평가 (--kind --t --cell --nozzle --layer-ratio --speed)
  optimize   다목적 최적화 → 파레토 해와 추천안 (--trials)
  stl        설계 → 수축 보정된 출력용 STL + 검사(닫힘·부피)

모든 결과는 P0(모델 계산). 설정에 '가정'이 남아 있으면 출력에 그대로 표시한다.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import warnings
from importlib.metadata import PackageNotFoundError, version

import numpy as np

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
CAL_PATH = os.path.join(HERE, "data", "gyroid_calibration.json")
CFG_PATH = os.path.join(HERE, "gyroid_seion_config.json")
G = 9.80665
UNSUPPORTED_SHIFT = 0.5          # 층간 옆밀림 허용: 필라멘트 폭의 절반


def _versions():
    out = {"python": sys.version.split()[0]}
    for p in ("numpy", "scipy", "porespy", "pyamg", "optuna", "trimesh", "scikit-image", "lmfit"):
        try:
            out[p] = version(p)
        except PackageNotFoundError:
            pass
    return out


def _r(x, n=5):
    return None if x is None else round(float(x), n)


def load_cfg(path=None):
    with open(path or CFG_PATH, encoding="utf-8") as f:
        return json.load(f)


def assumptions(cfg):
    """설정에서 '가정'·'요측정'으로 남은 항목 목록."""
    out = []

    def walk(d, key=""):
        if isinstance(d, dict):
            g = str(d.get("grade", d.get("_grade", "")))
            if g.startswith("가정") or g.startswith("요측정"):
                out.append(f"{key} ({g.split(' ')[0]})")
            for k, v in d.items():
                if not k.startswith("_"):
                    walk(v, f"{key}.{k}" if key else k)
    walk(cfg)
    return out


# ================================================================ 형상
def gyroid(X, Y, Z):
    return np.sin(X) * np.cos(Y) + np.sin(Y) * np.cos(Z) + np.sin(Z) * np.cos(X)


def gyroid_grad(X, Y, Z):
    fx = np.cos(X) * np.cos(Y) - np.sin(Z) * np.sin(X)
    fy = -np.sin(X) * np.sin(Y) + np.cos(Y) * np.cos(Z)
    fz = -np.sin(Y) * np.sin(Z) + np.cos(Z) * np.cos(X)
    return fx, fy, fz


def grid(n_per_cell, cells):
    g = (np.arange(n_per_cell * cells) + 0.5) * (2 * np.pi / n_per_cell)
    return np.meshgrid(g, g, g, indexing="ij")


def solid_of(f, kind, t):
    return (f <= t) if kind == "network" else (np.abs(f) <= t)


T_RANGE = {"network": (-1.0, 1.0), "sheet": (0.25, 1.1)}


def geometry_metrics(kind, t, n=24, cells=3):
    """단위포 L=1 기준 무차원 형상 지표. 가장자리 영향을 피하려 3×3×3 중 가운데 단위포만 통계."""
    import porespy as ps
    from scipy import ndimage
    X, Y, Z = grid(n, cells)
    f = gyroid(X, Y, Z)
    s = solid_of(f, kind, t)
    c = slice(n, 2 * n)
    phi = float(s[c, c, c].mean())
    lab, nlab = ndimage.label(s)
    conn = float(np.bincount(lab.ravel())[1:].max() / s.sum()) if nlab else 0.0
    wall = 2 * ps.filters.local_thickness(s, method="dt")[c, c, c][s[c, c, c]] / n
    pore = 2 * ps.filters.local_thickness(~s, method="dt")[c, c, c][~s[c, c, c]] / n
    # 하향 오버행 각 분포 (면적 가중): α=0 수직벽, 90 수평 천장
    m = 4 * n
    g = (np.arange(m) + 0.5) * (2 * np.pi / m)
    X, Y, Z = np.meshgrid(g, g, g, indexing="ij")
    f = gyroid(X, Y, Z); fx, fy, fz = gyroid_grad(X, Y, Z)
    gm = np.sqrt(fx ** 2 + fy ** 2 + fz ** 2) + 1e-12
    eps = 2 * np.pi / m
    surfaces = [(np.abs(f - t) < eps, 1.0)] if kind == "network" else [(np.abs(f - t) < eps, 1.0), (np.abs(f + t) < eps, -1.0)]
    hist = np.zeros(90); total = 0.0
    for band, sign in surfaces:
        w = gm[band]                                   # 띠 안 점의 |∇f| 가 면적 가중
        nz = sign * fz[band] / gm[band]                # 바깥 법선 z 성분
        alpha = np.degrees(np.arctan2(np.abs(fz[band]), np.sqrt(fx[band] ** 2 + fy[band] ** 2)))
        total += w.sum()
        down = nz < 0
        hist += np.histogram(alpha[down], bins=90, range=(0, 90), weights=w[down])[0]
    hist = hist / total if total else hist
    return {
        "kind": kind, "t": t, "phi": phi, "connectivity": conn,
        "wall_p10": float(np.percentile(wall, 10)), "wall_p50": float(np.percentile(wall, 50)),
        "pore_p10": float(np.percentile(pore, 10)), "pore_p50": float(np.percentile(pore, 50)),
        "downfacing_alpha_hist": [float(x) for x in hist],
    }


def fem_metrics(kind, t, n=14, cells=2, nu=0.25):
    from seion_voxelfem import effective_conductivity, effective_modulus
    X, Y, Z = grid(n, cells)
    s = solid_of(gyroid(X, Y, Z), kind, t)
    E, _ = effective_modulus(s, nu)
    k, _ = effective_conductivity(s)
    return {"E_rel": E, "k_rel": k}


def cmd_calibrate(n_geo=24, n_fem=18, points=9, out=CAL_PATH):
    rows = []
    for kind in ("network", "sheet"):
        for t in np.linspace(*T_RANGE[kind], points):
            g = geometry_metrics(kind, float(t), n_geo)
            g.update(fem_metrics(kind, float(t), n_fem))
            rows.append(g)
            print(f"  {kind:8s} t={t:+.3f} φ={g['phi']:.3f} E={g['E_rel']:.4f} k={g['k_rel']:.4f}", file=sys.stderr)
    fits = {}
    for kind in ("network", "sheet"):
        r = [x for x in rows if x["kind"] == kind and x["E_rel"] > 0 and x["phi"] < 0.95]
        ph = np.log([x["phi"] for x in r])
        for key in ("E_rel", "k_rel"):
            nexp, lnC = np.polyfit(ph, np.log([x[key] for x in r]), 1)
            fits[f"{kind}_{key}"] = {"C": float(np.exp(lnC)), "n": float(nexp)}
    data = {"resolution": {"geometry_vox_per_cell": n_geo, "fem_vox_per_cell": n_fem, "fem_cells": 2},
            "rows": rows, "gibson_ashby": fits, "versions": _versions()}
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return {"written": out, "n_rows": len(rows), "gibson_ashby": fits,
            "note": "Gibson–Ashby: 물성/고체물성 = C·φ^n. 골격형 굽힘지배면 E 지수 ≈2, 막형은 더 낮음(신장 성분)."}


def load_cal(path=CAL_PATH):
    if not os.path.exists(path):
        raise SystemExit(f"보정표 없음: {path} — 먼저 'calibrate' 실행")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def interp_geo(cal, kind, t):
    rows = sorted([r for r in cal["rows"] if r["kind"] == kind], key=lambda r: r["t"])
    ts = np.array([r["t"] for r in rows])
    if not (ts[0] <= t <= ts[-1]):
        raise ValueError(f"t={t} 가 보정 범위 {ts[0]}~{ts[-1]} 밖")
    out = {"kind": kind, "t": t}
    for key in ("phi", "connectivity", "wall_p10", "wall_p50", "pore_p10", "pore_p50", "E_rel", "k_rel"):
        out[key] = float(np.interp(t, ts, [r[key] for r in rows]))
    H = np.array([r["downfacing_alpha_hist"] for r in rows])
    out["hist"] = np.array([np.interp(t, ts, H[:, i]) for i in range(H.shape[1])])
    return out


# ================================================================ 페이스트·공정
def paste_props(cfg):
    wt = {k: v for k, v in cfg["formulation_wt_percent"].items() if not k.startswith("_")}
    rho = {k: v["value"] for k, v in cfg["component_density_g_cm3"].items()}
    tot = sum(wt.values())
    vol = {k: (wt[k] / tot) / rho[k] for k in wt}            # cm³ per g paste
    V = sum(vol.values())
    rho_paste = 1.0 / V
    vf = {k: vol[k] / V for k in vol}
    sd = cfg["shrinkage_linear"]["drying"]["value"]
    sf = cfg["shrinkage_linear"]["firing"]["value"] if cfg["shrinkage_linear"].get("fired") else 0.0
    burn = cfg["particles_after_firing"]["organics_burn_out"]
    p_int = cfg["particles_after_firing"]["illite_particle_internal_porosity"]["value"]
    V_green = (1 - sd) ** 3                                    # 페이스트 부피 1 기준
    solids_green = 1 - vf.get("water", 0)
    warn = []
    por_green = 1 - solids_green / V_green
    if por_green < 0:
        warn.append("건조 수축이 물 부피보다 큼 — 수축률·배합 재확인(기공률 음수)")
    V_fired = V_green * (1 - sf) ** 3
    solids_fired = sum(v for k, v in vf.items() if k not in burn and k != "water") / (1 - p_int)
    por_fired = 1 - solids_fired / V_fired if cfg["shrinkage_linear"].get("fired") else None
    if por_fired is not None and por_fired < 0:
        warn.append("소성 후 기공률 음수 — 수축률 재확인")
    return {
        "paste_density_g_cm3": rho_paste, "volume_fraction_in_paste": vf,
        "solids_volume_fraction_in_paste": solids_green,
        "wall_porosity_green": por_green, "wall_porosity_fired": por_fired,
        "linear_shrinkage": {"drying": sd, "firing": sf},
        "print_scale_factor": 1 / ((1 - sd) * (1 - sf)), "warnings": warn,
    }


def hb_wall_stress(Q_m3s, R_m, tau0, K, n):
    """Herschel–Bulkley 원관 유동: 유량 Q 를 내는 벽 전단응력 τw (Pa)."""
    from scipy.integrate import quad
    from scipy.optimize import brentq

    def Q_of(tw):
        if tw <= tau0:
            return 0.0
        val, _ = quad(lambda s: s ** 2 * ((s - tau0) / K) ** (1 / n), tau0, tw, limit=200)
        return math.pi * R_m ** 3 / tw ** 3 * val

    hi = max(tau0 * 2, 10.0)
    while Q_of(hi) < Q_m3s:
        hi *= 2
        if hi > 1e9:
            return float("inf")
    return brentq(lambda tw: Q_of(tw) - Q_m3s, tau0 * (1 + 1e-9) + 1e-9, hi, xtol=1e-6)


def process_metrics(cfg, paste, d_mm, h_mm, v_mm_s, part_height_mm):
    rh = cfg["rheology_herschel_bulkley"]
    pr = cfg["printer"]
    w = d_mm * pr["filament_width_to_nozzle_ratio"]
    Q = v_mm_s * w * h_mm * 1e-9
    R = d_mm / 2 * 1e-3
    tw = hb_wall_stress(Q, R, rh["tau0_Pa"], rh["K_Pa_s_n"], rh["n"])
    dP = 2 * pr["nozzle_equivalent_length_mm"] * 1e-3 * tw / R
    rho = paste["paste_density_g_cm3"] * 1000
    tau_eff = rh["tau0_Pa"] * rh["crosslink_yield_multiplier"]["value"]
    sf = cfg["part"]["safety_factor_buildability"]
    H_max = math.sqrt(3) * tau_eff / (rho * G * sf) * 1000
    return {"filament_width_mm": w, "flow_mm3_s": Q * 1e9, "wall_shear_stress_Pa": tw,
            "extrusion_pressure_kPa": dP / 1000, "buildable_height_mm": H_max,
            "part_height_printed_mm": part_height_mm}


def unsupported_fraction(hist, w, h, alpha_material=0.0):
    """하향 면 중 허용각보다 가파른 면적 비율. 허용각 = max(층간 밀림 기하 기준, 재료가 버티는 오버행 각)."""
    a_crit = max(math.degrees(math.atan(UNSUPPORTED_SHIFT * w / h)), alpha_material)
    i = int(min(max(a_crit, 0), 89.999))
    frac = float(np.sum(hist[i + 1:]) + hist[i] * (1 - (a_crit - i)))
    return frac, a_crit


# ================================================================ 평가
def evaluate(cfg, cal, kind, t, cell_mm, d_mm, layer_ratio, v_mm_s):
    paste = paste_props(cfg)
    geo = interp_geo(cal, kind, t)
    tg = cfg["design_targets"]
    size = cfg["part"]["size_mm"]
    scale = paste["print_scale_factor"]
    printed_size = [s * scale for s in size]
    h = d_mm * layer_ratio
    pm = process_metrics(cfg, paste, d_mm, h, v_mm_s, printed_size[2])
    w = pm["filament_width_mm"]
    unsup, a_crit = unsupported_fraction(geo["hist"], w, h, cfg["printer"]["overhang_capability_deg"]["value"])
    rh = cfg["rheology_herschel_bulkley"]
    tau_req = (paste["paste_density_g_cm3"] * 1000 * G * printed_size[2] * 1e-3
               * cfg["part"]["safety_factor_buildability"] / math.sqrt(3))
    pm["required_tau0_Pa_for_part_height"] = tau_req / rh["crosslink_yield_multiplier"]["value"]
    wall10 = geo["wall_p10"] * cell_mm; pore10 = geo["pore_p10"] * cell_mm
    path_len = geo["phi"] * np.prod(printed_size) / (w * h)
    time_min = path_len / v_mm_s / 60
    wm = cfg["wall_material"]
    out = {
        "design": {"kind": kind, "t": t, "unit_cell_printed_mm": cell_mm,
                   "unit_cell_final_mm": cell_mm / scale, "nozzle_mm": d_mm,
                   "layer_height_mm": h, "speed_mm_s": v_mm_s},
        "geometry": {"relative_density": geo["phi"], "connectivity": geo["connectivity"],
                     "wall_thickness_p10_mm": wall10, "wall_thickness_median_mm": geo["wall_p50"] * cell_mm,
                     "pore_size_p10_mm": pore10, "pore_size_median_mm": geo["pore_p50"] * cell_mm,
                     "unsupported_downfacing_area_fraction": unsup, "critical_overhang_deg": a_crit,
                     "overhang_note": "자이로이드의 하향 면 각도 분포는 t·단위포 크기와 거의 무관(45° 초과 ≈ 11.7 %). 오버행은 층 높이·페이스트 지지력(오버행 시험편)·출력 방향으로만 조절된다."},
        "properties_relative": {"E_rel": geo["E_rel"], "k_rel": geo["k_rel"],
                                "note": "격자 유효값 / 벽 재료값(z 방향). 벽 재료 자체 기공(유기물 연소)은 E_s·k_s 실측에 포함시킬 것."},
        "process": pm, "paste": {"density_g_cm3": paste["paste_density_g_cm3"],
                                  "wall_porosity_green": paste["wall_porosity_green"],
                                  "wall_porosity_fired": paste["wall_porosity_fired"],
                                  "print_scale_factor": scale, "printed_size_mm": printed_size},
        "print_time_min_estimate": time_min,
        "total_porosity_fired": (1 - geo["phi"] * (1 - (paste["wall_porosity_fired"] or 0))),
    }
    if wm["E_GPa"]["value"]:
        out["properties_absolute"] = {"E_eff_GPa": geo["E_rel"] * wm["E_GPa"]["value"]}
    if wm["k_W_mK"]["value"]:
        out.setdefault("properties_absolute", {})["k_eff_W_mK"] = geo["k_rel"] * wm["k_W_mK"]["value"]
    cons = {
        "wall_ge_filament": tg["min_wall_over_filament"] - wall10 / w,
        "pore_ge_filament": tg["min_pore_over_filament"] - pore10 / w,
        "cell_ge_6_filaments": tg["min_cell_over_filament"] - cell_mm / w,
        "overhang_supported": unsup - tg["max_unsupported_area_fraction"],
        "extrusion_pressure_ok": pm["extrusion_pressure_kPa"] / cfg["printer"]["max_extrusion_pressure_kPa"] - 1,
        "buildable_height_ok": printed_size[2] / pm["buildable_height_mm"] - 1,
        "stiffness_min": tg["min_E_rel"] - geo["E_rel"],
        "connected": 0.99 - geo["connectivity"],
        "cells_across_part": tg.get("min_cells_across", 4) - min(size) / (cell_mm / scale),
    }
    out["constraints_violation"] = {k: _r(v, 4) for k, v in cons.items()}
    out["feasible"] = all(v <= 0 for v in cons.values())
    out["_cons_vec"] = list(cons.values())
    return out


def _round_tree(d):
    if isinstance(d, dict):
        return {k: _round_tree(v) for k, v in d.items() if not k.startswith("_")}
    if isinstance(d, (list, tuple)):
        return [_round_tree(v) for v in d]
    if isinstance(d, (float, np.floating)):
        return float(f"{d:.5g}")
    return d


# ================================================================ 최적화
OBJ = {
    "insulation": (("k_rel", "minimize"), ("E_rel", "maximize")),
    "lightweight": (("phi", "minimize"), ("E_rel", "maximize")),
    "stiffness": (("E_rel", "maximize"), ("time", "minimize")),
}


def _obj_values(ev, mode):
    m = {"k_rel": ev["properties_relative"]["k_rel"], "E_rel": ev["properties_relative"]["E_rel"],
         "phi": ev["geometry"]["relative_density"], "time": ev["print_time_min_estimate"]}
    return [m[k] for k, _ in OBJ[mode]]


def cmd_optimize(cfg, cal, trials=400, seed=0, mode=None):
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    mode = mode or cfg["design_targets"]["objective"]
    pr = cfg["printer"]; part = cfg["part"]

    def suggest(trial):
        kind = trial.suggest_categorical("kind", ["network", "sheet"])
        u = trial.suggest_float("u", 0.0, 1.0)
        lo, hi = T_RANGE[kind]
        return dict(kind=kind, t=lo + u * (hi - lo),
                    cell_mm=trial.suggest_float("cell_mm", *part["unit_cell_range_mm"]),
                    d_mm=trial.suggest_categorical("nozzle_mm", pr["nozzle_inner_diameter_mm"]),
                    layer_ratio=trial.suggest_float("layer_ratio", *pr["layer_height_to_nozzle_ratio"]),
                    v_mm_s=trial.suggest_float("speed_mm_s", *pr["speed_range_mm_s"]))

    def objective(trial):
        p = suggest(trial)
        ev = evaluate(cfg, cal, p["kind"], p["t"], p["cell_mm"], p["d_mm"], p["layer_ratio"], p["v_mm_s"])
        trial.set_user_attr("cons", ev["_cons_vec"])
        trial.set_user_attr("params", p)
        return _obj_values(ev, mode)

    sampler = optuna.samplers.NSGAIISampler(seed=seed, population_size=40,
                                            constraints_func=lambda tr: tr.user_attrs["cons"])
    study = optuna.create_study(directions=[d for _, d in OBJ[mode]], sampler=sampler)
    study.optimize(objective, n_trials=trials)
    feas = [tr for tr in study.trials if tr.values and all(c <= 0 for c in tr.user_attrs["cons"])]
    if not feas:
        ev0 = evaluate(cfg, cal, **study.trials[0].user_attrs["params"])
        return {"mode": mode, "trials": trials, "feasible": 0,
                "error": "제약을 모두 만족하는 설계 없음 — 레올로지(항복응력)·노즐·압력 한계·부품 높이를 재검토",
                "most_violated_share_of_trials": _most_violated(study),
                "required_tau0_Pa_for_part_height": _r(ev0["process"]["required_tau0_Pa_for_part_height"], 1),
                "configured_tau0_Pa": cfg["rheology_herschel_bulkley"]["tau0_Pa"],
                "assumptions_in_config": assumptions(cfg)}
    # 같은 형상(종류·t)은 물성 목표값이 같다 → 형상별로 묶고 그 안에서 출력시간 최소 공정을 고른다
    def ev_of(tr):
        p = tr.user_attrs["params"]
        return evaluate(cfg, cal, p["kind"], p["t"], p["cell_mm"], p["d_mm"], p["layer_ratio"], p["v_mm_s"])
    groups = {}
    for tr in feas:
        p = tr.user_attrs["params"]
        key = (p["kind"], round(p["t"], 2))
        ev = ev_of(tr)
        if key not in groups or ev["print_time_min_estimate"] < groups[key][1]["print_time_min_estimate"]:
            groups[key] = (tr, ev)
    items = list(groups.values())
    sign = [1 if d == "minimize" else -1 for _, d in OBJ[mode]]
    vals = np.array([[s_ * v for s_, v in zip(sign, tr.values)] for tr, _ in items])
    pareto = [i for i in range(len(items)) if not any(np.all(vals[j] <= vals[i]) and np.any(vals[j] < vals[i]) for j in range(len(items)))]
    P = vals[pareto]
    rng = np.ptp(P, 0)
    norm = (P - P.min(0)) / np.where(rng > 0, rng, 1)
    knee = pareto[int(np.argmin(np.linalg.norm(norm, axis=1)))]      # 이상점(utopia)에 가장 가까운 해

    def summarize(item):
        tr, ev = item
        return _round_tree({"objectives": dict(zip([k for k, _ in OBJ[mode]], tr.values)), **ev})
    front = sorted((summarize(items[i]) for i in pareto), key=lambda e: list(e["objectives"].values())[0])
    feasible_windows = {}
    for tr in feas:
        p = tr.user_attrs["params"]
        w = feasible_windows.setdefault(p["kind"], {"t": [9, -9], "cell_mm": [1e9, 0], "nozzle_mm": set()})
        w["t"] = [min(w["t"][0], p["t"]), max(w["t"][1], p["t"])]
        w["cell_mm"] = [min(w["cell_mm"][0], p["cell_mm"]), max(w["cell_mm"][1], p["cell_mm"])]
        w["nozzle_mm"].add(p["d_mm"])
    for w in feasible_windows.values():
        w["nozzle_mm"] = sorted(w["nozzle_mm"])
    return {"mode": mode, "objectives": [f"{k}:{d}" for k, d in OBJ[mode]], "trials": trials, "seed": seed,
            "feasible": len(feas), "distinct_geometries": len(items), "pareto_size": len(front),
            "recommended": summarize(items[knee]),
            "picks": {
                f"{OBJ[mode][0][0]}_first": front[0],
                "balanced_knee": summarize(items[knee]),
                f"{OBJ[mode][1][0]}_first": front[-1],
                "_note": "파레토 양 끝과 무릎점. 어느 쪽을 택할지는 용도(단열재·구조재) 판단 — 'stl' 명령에 해당 design 값을 넣는다.",
            },
            "pareto_front": front[:15],
            "feasible_windows_printed": _round_tree(feasible_windows),
            "assumptions_in_config": assumptions(cfg)}


def _most_violated(study):
    keys = ["wall_ge_filament", "pore_ge_filament", "cell_ge_6_filaments", "overhang_supported",
            "extrusion_pressure_ok", "buildable_height_ok", "stiffness_min", "connected", "cells_across_part"]
    C = np.array([tr.user_attrs["cons"] for tr in study.trials if "cons" in tr.user_attrs])
    share = (C > 0).mean(0)
    return {k: _r(s, 3) for k, s in sorted(zip(keys, share), key=lambda x: -x[1])}


# ================================================================ 유변
def cmd_rheo(path):
    from lmfit import Model
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            parts = line.replace(",", " ").split()
            try:
                rows.append([float(p) for p in parts[:2]])
            except ValueError:
                continue
    a = np.array(rows); gd, tau = a[:, 0], a[:, 1]
    m = Model(lambda g, tau0, K, n: tau0 + K * g ** n, independent_vars=["g"])
    p = m.make_params(tau0=max(tau.min() * 0.8, 1e-3), K=max((tau.max() - tau.min()) / max(gd.max(), 1e-9) ** 0.5, 1e-3), n=0.5)
    p["tau0"].set(min=0); p["K"].set(min=0); p["n"].set(min=0.05, max=1.5)
    r = m.fit(tau, p, g=gd, weights=1 / np.maximum(tau, 1e-9))
    pred = r.best_fit
    R2 = 1 - np.sum((tau - pred) ** 2) / np.sum((tau - tau.mean()) ** 2)
    v = {k: r.params[k].value for k in ("tau0", "K", "n")}
    e = {k: r.params[k].stderr for k in ("tau0", "K", "n")}
    return {"input": path, "model": "τ = τ0 + K·γ̇ⁿ (Herschel–Bulkley)",
            "tau0_Pa": _r(v["tau0"], 4), "K_Pa_s_n": _r(v["K"], 4), "n": _r(v["n"], 4),
            "stderr": {k: (_r(x, 4) if x else None) for k, x in e.items()}, "R2": _r(R2, 5),
            "shear_rate_range_s-1": [_r(gd.min(), 4), _r(gd.max(), 4)],
            "printability_hint": ("전단담화(n<1)·항복응력 있음 — DIW 적합 범주" if v["n"] < 1 and v["tau0"] > 50
                                  else "항복응력이 작거나 전단담화가 약함 — 적층·형상유지 불리"),
            "next": "gyroid_seion_config.json 의 rheology_herschel_bulkley 에 τ0·K·n 을 넣고 grade 를 '실측'으로, source 에 장비·온도·날짜 기입",
            "grade": "E1 (실측 피팅)"}


# ================================================================ STL
def cmd_stl(cfg, kind, t, cell_mm, out, voxel_mm=None):
    import trimesh
    from skimage.measure import marching_cubes
    paste = paste_props(cfg)
    scale = paste["print_scale_factor"]
    size = np.array(cfg["part"]["size_mm"]) * scale
    vox = voxel_mm or min(cell_mm / 16, 0.3)
    n = np.ceil(size / vox).astype(int) + 1
    axes = [np.linspace(0, size[i], n[i]) for i in range(3)]
    X, Y, Z = np.meshgrid(*axes, indexing="ij")
    k = 2 * np.pi / cell_mm
    f = gyroid(k * X, k * Y, k * Z)
    g = (t - f) if kind == "network" else (t - np.abs(f))
    g_mm = g / k                                          # 레벨셋 → 근사 거리(mm)
    d_box = np.minimum.reduce([X, size[0] - X, Y, size[1] - Y, Z, size[2] - Z])
    field = np.minimum(g_mm, d_box)
    field = np.pad(field, 1, constant_values=-1.0)
    verts, faces, _, _ = marching_cubes(field, 0.0, spacing=(vox, vox, vox))
    verts -= vox
    mesh = trimesh.Trimesh(verts, faces, process=True)
    mesh.fix_normals()
    mesh.export(out)
    phi_mesh = abs(mesh.volume) / float(np.prod(size))
    return _round_tree({
        "stl": out, "kind": kind, "t": t, "unit_cell_printed_mm": cell_mm,
        "printed_size_mm": list(size), "final_size_mm": cfg["part"]["size_mm"], "print_scale_factor": scale,
        "voxel_mm": vox, "triangles": len(mesh.faces), "watertight": bool(mesh.is_watertight),
        "relative_density_mesh": phi_mesh,
        "note": "슬라이서(PrusaSlicer·Cura 등)에서 DIW 프로파일로 G-code 생성. 출력 크기는 수축 보정이 이미 반영됨 — 슬라이서에서 다시 키우지 말 것.",
    })


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=CFG_PATH)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("calibrate"); p.add_argument("--points", type=int, default=9)
    p.add_argument("--n-geo", type=int, default=24); p.add_argument("--n-fem", type=int, default=18)
    p = sub.add_parser("rheo"); p.add_argument("csv")
    sub.add_parser("paste")
    for name in ("evaluate", "stl"):
        p = sub.add_parser(name)
        p.add_argument("--kind", choices=["network", "sheet"], required=True)
        p.add_argument("--t", type=float, required=True); p.add_argument("--cell", type=float, required=True)
        if name == "evaluate":
            p.add_argument("--nozzle", type=float, required=True); p.add_argument("--layer-ratio", type=float, default=0.7)
            p.add_argument("--speed", type=float, default=10.0)
        else:
            p.add_argument("--out", required=True); p.add_argument("--voxel", type=float)
    p = sub.add_parser("optimize"); p.add_argument("--trials", type=int, default=400)
    p.add_argument("--seed", type=int, default=0); p.add_argument("--mode", choices=list(OBJ))
    a = ap.parse_args(argv)
    cfg = load_cfg(a.config)
    if a.cmd == "calibrate":
        res = cmd_calibrate(a.n_geo, a.n_fem, a.points)
    elif a.cmd == "rheo":
        res = cmd_rheo(a.csv)
    elif a.cmd == "paste":
        res = _round_tree(paste_props(cfg)); res["assumptions_in_config"] = assumptions(cfg)
    elif a.cmd == "evaluate":
        res = _round_tree(evaluate(cfg, load_cal(), a.kind, a.t, a.cell, a.nozzle, a.layer_ratio, a.speed))
        res["assumptions_in_config"] = assumptions(cfg)
    elif a.cmd == "optimize":
        res = cmd_optimize(cfg, load_cal(), a.trials, a.seed, a.mode)
    else:
        res = cmd_stl(cfg, a.kind, a.t, a.cell, a.out, a.voxel)
    res["grade"] = res.get("grade", "P0 (모델 계산) — 설정의 '가정' 값에 의존")
    res["versions"] = _versions()
    res["command"] = " ".join(["seion_gyroid.py"] + (argv if argv is not None else sys.argv[1:]))
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
