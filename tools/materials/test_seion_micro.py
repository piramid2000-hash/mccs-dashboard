"""미세조직·실험설계 검증 — 답을 아는 합성 이미지와 합성 실험."""
import csv
import json
import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import seion_micro as m  # noqa: E402


def _disks(shape, centers, r):
    yy, xx = np.mgrid[: shape[0], : shape[1]]
    im = np.zeros(shape, bool)
    for cy, cx in centers:
        im |= (yy - cy) ** 2 + (xx - cx) ** 2 <= r ** 2
    return im


def test_pores_2d_disks_porosity_and_size(tmp_path):
    centers = [(y, x) for y in range(30, 300, 60) for x in range(30, 300, 60)]   # 25 개, 겹치지 않음
    pores = _disks((300, 300), centers, 15)
    gray = np.where(pores, 40.0, 200.0) + np.random.default_rng(0).normal(0, 5, pores.shape)
    f = tmp_path / "sem.npy"; np.save(f, gray)
    r = m.cmd_pores(str(f), pixel_um=0.5, pores_dark=True)
    assert r["porosity"] == pytest.approx(pores.mean(), abs=0.005)
    assert r["pore_count_connected_regions"] == 25
    # 원판 지름 31 px × 0.5 µm ≈ 15.5 µm — 국소두께 분포의 상위값이 지름
    assert r["pore_diameter_um"]["d90"] == pytest.approx(15.5, abs=1.5)
    assert not any(r["percolating_axes"].values())                            # 고립 기공


def test_pores_3d_channel_percolates_with_tortuosity_one(tmp_path):
    im = np.zeros((30, 30, 30), bool)
    im[:, 10:20, 10:20] = True                                                  # x 방향 직선 관통 채널
    f = tmp_path / "ct.npy"; np.save(f, im)
    r = m.cmd_pores(str(f), pixel_um=2.0, pores_dark=False, tortuosity=True)
    assert r["porosity"] == pytest.approx(100 / 900, abs=1e-6)
    assert r["percolating_axes"]["x"] and not r["percolating_axes"]["y"]
    assert r["tortuosity"]["x"] == pytest.approx(1.0, abs=0.05)


def test_doe_balance_and_finds_better_than_start(tmp_path):
    space = {
        "factors": {"a": {"type": "float", "low": 0.0, "high": 10.0, "round": 3},
                    "b": {"type": "float", "low": 0.0, "high": 10.0, "round": 3}},
        "derived": {"rest": {"type": "balance", "total": 20.0, "of": ["a", "b"], "low": 2.0, "high": 18.0}},
        "objectives": [{"name": "y", "direction": "minimize"}],
        "n_startup": 5,
    }
    sp = tmp_path / "space.json"; sp.write_text(json.dumps(space))
    log = tmp_path / "log.csv"

    def experiment(a, b):                       # 숨은 최적점 (3, 7)
        return (a - 3) ** 2 + (b - 7) ** 2

    best = []
    for it in range(18):
        s = m.cmd_doe_suggest(str(sp), str(log), n=1, seed=it)["suggestions"][0]
        assert 2.0 <= s["rest"] <= 18.0                                         # 파생 인자 범위 준수
        y = experiment(s["a"], s["b"])
        new = not log.exists()
        with open(log, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["a", "b", "y"])
            if new:
                w.writeheader()
            w.writerow({"a": s["a"], "b": s["b"], "y": y})
        best.append(y if not best else min(best[-1], y))
    st = m.cmd_doe_status(str(sp), str(log))
    assert st["completed_experiments"] == 18
    assert best[-1] < 0.5 and best[-1] < best[4]                                # 초기 탐색보다 개선, 최적점 근처
