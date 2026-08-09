#!/usr/bin/env python3
"""F1~F5 실패 지문 판별기 (의존성 없음 — 표준 라이브러리만).

사용법:
    python3 scan.py <파일.csv> --list-columns
    python3 scan.py <파일.csv> [--time-col t] [--map v_cell=Ecell,dp=deltaP] [--window 21]

판별 규칙은 CLAUDE.md §2.1의 표준 지문(방향 × 시간척도 × 가역성)을 따른다.
출력은 [S] 해석값이며, 점수는 확률이 아니라 상대 지표다.
"""
from __future__ import annotations

import argparse
import csv
import math
import statistics as st
import sys
from pathlib import Path

# ---------------------------------------------------------------- 컬럼 인식
ALIASES: dict[str, list[str]] = {
    "t":        ["t", "time", "elapsed", "hours", "hour", "h", "시간", "경과"],
    "v_cell":   ["v_cell", "vcell", "voltage", "cell_voltage", "ecell", "전압"],
    "hfr":      ["hfr", "asr", "r_ohm", "ohmic", "resistance", "저항"],
    "dp":       ["dp", "delta_p", "deltap", "dp_bar", "pressure_drop", "차압"],
    "fe_co":    ["fe_co", "feco", "fe_carbonmonoxide", "co_fe", "co_selectivity"],
    "fe_h2":    ["fe_h2", "feh2", "h2_fe", "hydrogen_fe"],
    "t_cell":   ["t_cell", "temp", "temperature", "t_bulk", "온도"],
    "nh3":      ["nh3", "nh3_out", "ammonia", "nh3_ppm", "암모니아"],
    "nh3_in":   ["nh3_in", "nh3_inlet", "scrubber_in"],
    "crossover": ["crossover", "co2_anode", "gas_crossover", "o2_cathode"],
    "cell_sigma": ["cell_sigma", "sigma", "v_std", "cell_std"],
    "imu":      ["imu", "roll", "pitch", "motion", "요동"],
    "current":  ["current", "j", "current_density", "i", "전류"],
}


def norm(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def detect_columns(header: list[str], overrides: dict[str, str]) -> dict[str, str]:
    found: dict[str, str] = {}
    normalized = {norm(h): h for h in header}
    for key, names in ALIASES.items():
        if key in overrides:
            continue
        for cand in names:
            if cand in normalized:
                found[key] = normalized[cand]
                break
    for key, col in overrides.items():
        if col not in header:
            print(f"[경고] --map 의 '{col}' 컬럼이 파일에 없습니다.", file=sys.stderr)
        else:
            found[key] = col
    return found


# ---------------------------------------------------------------- 통계 도구
def to_float(v: str) -> float | None:
    try:
        f = float(str(v).strip())
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def series(rows: list[dict], col: str | None) -> list[float]:
    if not col:
        return []
    out = []
    for r in rows:
        f = to_float(r.get(col, ""))
        if f is not None:
            out.append(f)
    return out


def slope(y: list[float]) -> float:
    """단순 선형회귀 기울기 (단위: y/샘플)."""
    n = len(y)
    if n < 3:
        return 0.0
    xm, ym = (n - 1) / 2, sum(y) / n
    num = sum((i - xm) * (v - ym) for i, v in enumerate(y))
    den = sum((i - xm) ** 2 for i in range(n))
    return num / den if den else 0.0


def rolling_var_ratio(y: list[float], w: int) -> float:
    """후반부 이동분산 / 전반부 이동분산 — 맥동 증가 지표."""
    if len(y) < 2 * w:
        return 1.0
    def mvar(seg: list[float]) -> float:
        vs = [st.pvariance(seg[i:i + w]) for i in range(0, len(seg) - w + 1, max(1, w // 2))]
        vs = [v for v in vs if v > 0]
        return st.median(vs) if vs else 0.0
    half = len(y) // 2
    a, b = mvar(y[:half]), mvar(y[half:])
    if a <= 0:
        return 1.0 if b <= 0 else 3.0
    return b / a


def cusum_steps(y: list[float], k_sigma: float = 4.0) -> int:
    """계단형 상승 횟수 (CUSUM). 염 석출의 이산 폐색 이벤트를 센다."""
    if len(y) < 10:
        return 0
    base = y[:max(5, len(y) // 10)]
    mu = sum(base) / len(base)
    sd = st.pstdev(base) or (abs(mu) * 0.01 + 1e-9)
    thresh, s, steps, armed = k_sigma * sd, 0.0, 0, True
    for v in y:
        s = max(0.0, s + (v - mu - 0.5 * sd))
        if s > thresh and armed:
            steps += 1
            armed, s = False, 0.0
            mu = v
        elif s == 0.0:
            armed = True
    return steps


def corr(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    if n < 5:
        return 0.0
    a, b = a[:n], b[:n]
    ma, mb = sum(a) / n, sum(b) / n
    va = math.sqrt(sum((x - ma) ** 2 for x in a))
    vb = math.sqrt(sum((x - mb) ** 2 for x in b))
    if va == 0 or vb == 0:
        return 0.0
    return sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / (va * vb)


def rel_slope(y: list[float]) -> float:
    """전 구간 상대 변화율 (기울기 × 길이 / 초기값)."""
    if len(y) < 3:
        return 0.0
    base = abs(sum(y[:max(3, len(y) // 20)]) / max(3, len(y) // 20)) or 1e-9
    return slope(y) * len(y) / base


# ---------------------------------------------------------------- 판별
def scan(rows: list[dict], cols: dict[str, str], window: int) -> dict:
    s = {k: series(rows, cols.get(k)) for k in ALIASES}
    n = len(rows)
    span_h = None
    if s["t"]:
        span_h = max(s["t"]) - min(s["t"])

    ev: dict[str, list[str]] = {f"F{i}": [] for i in range(1, 6)}
    score = {f"F{i}": 0.0 for i in range(1, 6)}
    missing: list[str] = []

    dp, hfr, v, feco, feh2 = s["dp"], s["hfr"], s["v_cell"], s["fe_co"], s["fe_h2"]

    # --- F1 Flooding: ΔP 맥동↑ + HFR 불변
    if dp:
        ratio = rolling_var_ratio(dp, window)
        if ratio > 1.8:
            score["F1"] += min(0.5, 0.25 * math.log2(ratio))
            ev["F1"].append(f"ΔP 이동분산 {ratio:.1f}배 증가(맥동)")
        if hfr:
            hs = abs(rel_slope(hfr))
            if hs < 0.05:
                score["F1"] += 0.25
                ev["F1"].append(f"HFR 평탄(상대변화 {hs*100:.1f}%) — F1 핵심 판별자")
        else:
            missing.append("HFR (F1/F5 판별에 필수)")
        if s["imu"]:
            c = abs(corr(dp, s["imu"]))
            ev["F1"].append(f"IMU–ΔP 교차상관 {c:.2f} → " +
                            ("요동 유발" if c > 0.5 else "젖음성 열화 의심"))
            if c > 0.5:
                score["F1"] += 0.2
    else:
        missing.append("ΔP (F1/F2 판별에 필수)")

    # --- F2 염 석출: ΔP 계단·비가역 + 국부 온도
    if dp:
        steps = cusum_steps(dp)
        if steps:
            score["F2"] += min(0.6, 0.2 * steps)
            ev["F2"].append(f"ΔP 계단형 상승 {steps}회(CUSUM) — 이산 폐색 이벤트")
        if rel_slope(dp) > 0.15 and rolling_var_ratio(dp, window) < 1.5:
            score["F2"] += 0.2
            ev["F2"].append("ΔP 단조 상승(맥동 없음)")
    if s["t_cell"]:
        tv = rolling_var_ratio(s["t_cell"], window)
        if tv > 2.0:
            score["F2"] += 0.15
            ev["F2"].append(f"온도 분산 {tv:.1f}배↑ — 국부 핫스팟 가능")

    # --- F3 HER 우점: FE 교차 + V_cell 하락 착시
    her_illusion = False
    if feh2 and feco:
        if rel_slope(feh2) > 0.1 and rel_slope(feco) < -0.05:
            score["F3"] += 0.5
            ev["F3"].append("FE_H₂ 상승 + FE_CO 하락(교차 진행)")
        cross = [i for i in range(len(feh2)) if i < len(feco) and feh2[i] > feco[i]]
        if cross:
            score["F3"] += 0.3
            ev["F3"].append(f"FE 교차점 발생(샘플 {cross[0]} 이후)")
    else:
        missing.append("FE_CO/FE_H₂ (F3 판별에 필수)")
    if v:
        vs = rel_slope(v)
        if vs < -0.02:
            ev["F3"].append(f"V_cell 하락({vs*100:.1f}%) — ⚠ 착시 주의")
            if feh2 and rel_slope(feh2) > 0.05:
                score["F3"] += 0.35
                her_illusion = True
                ev["F3"].append("V_cell↓ + FE_H₂↑ 동시 → F3 착시 경보 조건 성립")

    # --- F4 NH₃ slip
    if s["nh3"]:
        ns = rel_slope(s["nh3"])
        if ns > 0.15:
            score["F4"] += min(0.6, ns)
            ev["F4"].append(f"출구 NH₃ 상승(상대 {ns*100:.0f}%)")
        if s["nh3_in"]:
            ratio_ok = corr(s["nh3"], s["nh3_in"])
            ev["F4"].append(f"전/후단 상관 {ratio_ok:.2f} → " +
                            ("동반 이동(센서 드리프트 의심)" if ratio_ok > 0.8 else "실제 슬립 가능"))
            if ratio_ok <= 0.8:
                score["F4"] += 0.2
        else:
            missing.append("NH₃ 전단 측정 (드리프트 배제에 필요)")
    else:
        missing.append("출구 NH₃ (F4 판별에 필수)")

    # --- F5 막 열화: HFR 만성 드리프트 / crossover 급성
    if hfr:
        hs = rel_slope(hfr)
        if hs > 0.05:
            score["F5"] += min(0.5, hs * 2)
            ev["F5"].append(f"HFR 단조 드리프트(상대 {hs*100:.1f}%) — 만성 모드")
            if span_h is not None and span_h < 100:
                ev["F5"].append(f"※ 관측 {span_h:.0f} h — 만성 판정에는 수백 시간 필요")
    if s["crossover"]:
        cs = rel_slope(s["crossover"])
        if cs > 0.3:
            score["F5"] += 0.4
            ev["F5"].append(f"crossover 급증(상대 {cs*100:.0f}%) — 급성(핀홀) 의심")
    if s["cell_sigma"]:
        ss = rel_slope(s["cell_sigma"])
        if ss > 0.2:
            score["F5"] += 0.25
            ev["F5"].append(f"셀 간 전압 편차 σ 확대({ss*100:.0f}%) — 열화 셀 존재")

    for k in score:
        score[k] = round(min(score[k], 1.0), 2)
    return {"score": score, "evidence": ev, "n": n, "span_h": span_h,
            "missing": missing, "her_illusion": her_illusion}


# ---------------------------------------------------------------- 출력
TIMESCALE = {"F1": "분~수십 분", "F2": "수 시간", "F3": "수 분",
             "F4": "수십 분", "F5": "수백 시간"}
NAMES = {"F1": "Flooding (범람)", "F2": "Salt Precipitation (염 석출)",
         "F3": "HER Dominant (수소 우점)", "F4": "NH₃ Slip (암모니아 유출)",
         "F5": "Membrane Degradation (막·삽입층 열화)"}


def main() -> int:
    ap = argparse.ArgumentParser(description="F1~F5 실패 지문 판별기")
    ap.add_argument("csv", type=Path)
    ap.add_argument("--list-columns", action="store_true")
    ap.add_argument("--time-col")
    ap.add_argument("--map", default="", help="key=column,... (예: v_cell=Ecell,dp=deltaP)")
    ap.add_argument("--window", type=int, default=21, help="이동통계 창 크기")
    a = ap.parse_args()

    if not a.csv.exists():
        print(f"파일 없음: {a.csv}", file=sys.stderr)
        return 1

    with a.csv.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        print("빈 파일입니다.", file=sys.stderr)
        return 1
    header = list(rows[0].keys())

    if a.list_columns:
        print("컬럼 목록:")
        for h in header:
            print(f"  - {h}")
        auto = detect_columns(header, {})
        print("\n자동 인식 결과:")
        for k, v in auto.items():
            print(f"  {k:11s} → {v}")
        un = [k for k in ("v_cell", "hfr", "dp", "fe_co", "fe_h2") if k not in auto]
        if un:
            print(f"\n미인식(판별 정확도 저하): {', '.join(un)}")
            print("  --map v_cell=<컬럼>,dp=<컬럼> 형식으로 지정하세요.")
        return 0

    overrides = {}
    if a.map:
        for pair in a.map.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                overrides[k.strip()] = v.strip()
    if a.time_col:
        overrides["t"] = a.time_col

    cols = detect_columns(header, overrides)
    res = scan(rows, cols, a.window)

    span = f", t={res['span_h']:.1f}" if res["span_h"] is not None else ""
    print(f"\n=== signature-scan [S] — {a.csv.name} ({res['n']}행{span}) ===\n")
    print(f"{'모드':<34} {'점수':>5}  시간척도")
    print("-" * 62)
    for k in sorted(res["score"], key=lambda x: -res["score"][x]):
        print(f"{k} {NAMES[k]:<30} {res['score'][k]:>5.2f}  {TIMESCALE[k]}")

    print("\n--- 근거 ---")
    any_ev = False
    for k in ("F1", "F2", "F3", "F4", "F5"):
        if res["evidence"][k]:
            any_ev = True
            print(f"\n[{k}] {NAMES[k]}")
            for e in res["evidence"][k]:
                print(f"  · {e}")
    if not any_ev:
        print("  뚜렷한 지문 없음 — 정상 운전 범위이거나 관측 항목 부족")

    if res["her_illusion"]:
        print("\n⚠⚠ F3 착시 경보: V_cell 하락 + FE_H₂ 상승이 동시 관측됨.")
        print("   전압 하락을 '성능 개선'으로 해석하지 마십시오 (CLAUDE.md §1.2 금지 표현).")

    if res["missing"]:
        print("\n--- 미계측 항목 (판별 신뢰도 제한) ---")
        for m in dict.fromkeys(res["missing"]):
            print(f"  · {m}")

    print("\n※ 본 출력은 [S] 해석값이다. 점수는 확률이 아니라 상대 지표이며,")
    print("  Signature 라벨의 [검증값] 승격은 Gate 3 의도적 경계 접근 실험으로만 가능하다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
