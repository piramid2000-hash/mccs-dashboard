"""자이로이드 DIW 도구 검증 — 해석해·물리 한계·합성 데이터 복원."""
import copy
import json
import math
import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import seion_gyroid as g  # noqa: E402
import seion_voxelfem as v  # noqa: E402


# ---- 복셀 FEM: 해석해
def test_fem_full_block_is_exact():
    s = np.ones((5, 5, 5), bool)
    assert v.effective_modulus(s)[0] == pytest.approx(1.0, rel=1e-9)
    assert v.effective_conductivity(s)[0] == pytest.approx(1.0, rel=1e-9)


def test_fem_parallel_columns_rule_of_mixtures():
    s = np.zeros((8, 8, 8), bool); s[:2] = True                     # 25 % 기둥 (하중 방향과 평행)
    assert v.effective_modulus(s)[0] == pytest.approx(0.25, rel=1e-6)
    assert v.effective_conductivity(s)[0] == pytest.approx(0.25, rel=1e-6)


def test_fem_gyroid_below_hashin_shtrikman_bound():
    X, Y, Z = g.grid(12, 2)
    s = g.solid_of(g.gyroid(X, Y, Z), "network", 0.0)
    phi = s.mean()
    k = v.effective_conductivity(s)[0]
    assert 0 < k < 2 * phi / (3 - phi)                                 # 빈 상과 섞인 HS 상한


# ---- 형상
def test_gyroid_network_half_density_at_t0():
    geo = g.geometry_metrics("network", 0.0, n=16)
    assert geo["phi"] == pytest.approx(0.5, abs=0.02)
    assert geo["connectivity"] > 0.99
    assert sum(geo["downfacing_alpha_hist"]) == pytest.approx(0.5, abs=0.02)   # 전체 면의 절반이 아래를 향함


def test_calibration_file_and_gibson_ashby_exponents():
    cal = g.load_cal()
    ga = cal["gibson_ashby"]
    assert 2.0 <= ga["network_E_rel"]["n"] <= 2.7      # 골격형: 굽힘 지배
    assert 1.4 <= ga["sheet_E_rel"]["n"] <= 2.0         # 막형: 신장 성분으로 지수 낮음
    for kind in ("network", "sheet"):
        rows = sorted([r for r in cal["rows"] if r["kind"] == kind], key=lambda r: r["t"])
        phis = [r["phi"] for r in rows]; Es = [r["E_rel"] for r in rows]
        assert phis == sorted(phis) and Es == sorted(Es)                # t ↑ → φ ↑, E ↑


# ---- 공정 물리
def test_hb_reduces_to_hagen_poiseuille():
    mu, R, Q = 2.0, 0.5e-3, 1e-8
    tw = g.hb_wall_stress(Q, R, tau0=0.0, K=mu, n=1.0)
    assert tw == pytest.approx(4 * mu * Q / (math.pi * R ** 3), rel=1e-5)


def test_hb_yield_stress_raises_wall_stress():
    R, Q = 0.5e-3, 1e-8
    assert g.hb_wall_stress(Q, R, 300, 50, 0.45) > g.hb_wall_stress(Q, R, 0, 50, 0.45) > 0


def test_paste_volume_balance():
    cfg = g.load_cfg()
    p = g.paste_props(cfg)
    assert sum(p["volume_fraction_in_paste"].values()) == pytest.approx(1.0)
    wt = cfg["formulation_wt_percent"]; rho = cfg["component_density_g_cm3"]
    expected = 100 / sum(wt[k] / rho[k]["value"] for k in ("expanded_illite", "sodium_alginate", "C38H78O", "water"))
    assert p["paste_density_g_cm3"] == pytest.approx(expected)
    assert p["print_scale_factor"] == pytest.approx(1 / (0.95 * 0.92))


def test_buildability_matches_hand_formula():
    cfg = g.load_cfg(); cal = g.load_cal()
    ev = g.evaluate(cfg, cal, "network", 0.0, 6.0, 1.19, 0.7, 10.0)
    rho = g.paste_props(cfg)["paste_density_g_cm3"] * 1000
    H = math.sqrt(3) * 300 / (rho * 9.80665 * 1.5) * 1000
    assert ev["process"]["buildable_height_mm"] == pytest.approx(H, rel=1e-6)


# ---- 최적화: 기본(가정) 설정은 적층 높이로 막히고, 가교 시나리오는 풀린다
def test_default_config_reports_required_yield_stress():
    res = g.cmd_optimize(g.load_cfg(), g.load_cal(), trials=80, seed=1)
    assert res["feasible"] == 0
    assert res["most_violated_share_of_trials"]["buildable_height_ok"] == 1.0
    assert res["required_tau0_Pa_for_part_height"] > res["configured_tau0_Pa"]


def test_crosslink_scenario_has_pareto_and_picks():
    cfg = copy.deepcopy(g.load_cfg())
    cfg["rheology_herschel_bulkley"]["crosslink_yield_multiplier"]["value"] = 2.0
    res = g.cmd_optimize(cfg, g.load_cal(), trials=200, seed=0)
    assert res["feasible"] > 0 and res["pareto_size"] > 0
    first = res["picks"]["k_rel_first"]
    assert first["feasible"] and first["objectives"]["k_rel"] <= res["picks"]["balanced_knee"]["objectives"]["k_rel"]


# ---- STL
def test_stl_is_watertight_and_density_consistent(tmp_path):
    cfg = copy.deepcopy(g.load_cfg())
    cfg["part"]["size_mm"] = [12.0, 12.0, 12.0]
    r = g.cmd_stl(cfg, "network", 0.0, 6.0, str(tmp_path / "g.stl"), voxel_mm=0.25)
    assert r["watertight"]
    assert r["relative_density_mesh"] == pytest.approx(0.5, abs=0.05)


# ---- 유변 피팅
def test_rheo_recovers_herschel_bulkley(tmp_path):
    gd = np.logspace(-1, 2, 25)
    tau = 300 + 50 * gd ** 0.45
    tau *= 1 + np.random.default_rng(0).normal(0, 0.01, gd.size)
    f = tmp_path / "rheo.csv"
    np.savetxt(f, np.c_[gd, tau], delimiter=",", header="shear_rate,stress")
    r = g.cmd_rheo(str(f))
    assert r["tau0_Pa"] == pytest.approx(300, rel=0.08)
    assert r["n"] == pytest.approx(0.45, abs=0.05)
    assert r["R2"] > 0.99
