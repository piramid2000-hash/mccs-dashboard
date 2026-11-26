#!/usr/bin/env python3
"""세이온 실험 데이터 해석 — 스펙트럼·회절 피크, XRD 상 대조, 임피던스(EIS), 아레니우스.

실측 데이터를 정량화하는 도구다. 입력이 실측이면 결과는 E1(실측 해석값)이지만,
피팅 모델·기준선 선택에 따라 값이 달라지므로 그 선택을 출력에 남긴다.

하위 명령
  peaks      2열 데이터(XRD·Raman·FTIR) → 기준선 제거 → 피크 자동 검출 → pseudo-Voigt 피팅
             (위치·반치폭·면적·높이, 선택: Scherrer 결정자 크기)
  xrdmatch   실측 XRD vs CIF 들의 시뮬레이션 패턴 → 상 후보 순위
  eis        임피던스(주파수, Z', Z'') → 등가회로 피팅 → 저항·이온전도도
  arrhenius  (온도, 전도도 또는 확산계수) → 활성화에너지, 지정 온도로 외삽

CSV 는 머리줄 없이 숫자 열이거나, 머리줄이 있으면 --xcol/--ycol 로 열 번호(0부터) 지정.

예
  python seion_expdata.py peaks xrd.csv --baseline arpls --scherrer 1.5406
  python seion_expdata.py xrdmatch xrd.csv illite.cif quartz.cif kaolinite.cif
  python seion_expdata.py eis eis.csv --circuit "R0-p(R1,CPE1)-CPE2" --thickness 0.1 --area 0.785
  python seion_expdata.py arrhenius sigma_T.csv --kind sigmaT --at 298.15
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from importlib.metadata import PackageNotFoundError, version

import numpy as np

warnings.filterwarnings("ignore")
KB_EV = 8.617333262e-5


def _versions():
    out = {"python": sys.version.split()[0]}
    for p in ("numpy", "scipy", "lmfit", "pybaselines", "impedance", "pymatgen"):
        try:
            out[p] = version(p)
        except PackageNotFoundError:
            pass
    return out


def _r(x, n=6):
    return None if x is None else round(float(x), n)


def _sig(x, n=6):
    """유효숫자 n 자리 — 1e-9 같은 작은 값이 반올림으로 0 이 되지 않게."""
    return None if x is None else float(f"{float(x):.{n}g}")


def load_xy(path, xcol=0, ycol=1, skip=None):
    """숫자로 시작하지 않는 줄은 머리줄로 보고 건너뛴다. 쉼표·탭·공백 구분 모두 허용."""
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            parts = line.replace(",", " ").replace(";", " ").split()
            try:
                vals = [float(p) for p in parts]
            except ValueError:
                continue
            if len(vals) > max(xcol, ycol):
                rows.append(vals)
    a = np.array(rows)
    return a[:, xcol], a[:, ycol], a


# ---------------------------------------------------------------- peaks
def baseline(x, y, method="arpls", lam=1e6):
    from pybaselines import Baseline
    b = Baseline(x_data=x)
    if method == "arpls":
        base, _ = b.arpls(y, lam=lam)
    elif method == "asls":
        base, _ = b.asls(y, lam=lam, p=0.01)
    elif method == "modpoly":
        base, _ = b.modpoly(y, poly_order=3)
    elif method == "snip":
        base, _ = b.snip(y, max_half_window=max(5, len(y) // 40))
    elif method == "none":
        base = np.zeros_like(y)
    else:
        raise SystemExit(f"알 수 없는 기준선 방법 {method}")
    return base


def fit_peaks(x, y, centers=None, prominence=0.05, method="arpls", lam=1e6, window=None):
    from lmfit.models import PseudoVoigtModel
    from scipy.signal import find_peaks
    base = baseline(x, y, method, lam)
    yc = y - base
    dx = float(np.median(np.diff(x)))
    if centers is None:
        idx, _ = find_peaks(yc, prominence=prominence * yc.max(), distance=max(1, int(0.1 / abs(dx)) if dx else 1))
        centers = list(x[idx])
    if not centers:
        return base, yc, None, []
    model, params = None, None
    span = (x.max() - x.min())
    for i, c0 in enumerate(centers):
        m = PseudoVoigtModel(prefix=f"p{i}_")
        h0 = float(np.interp(c0, x, yc))
        sig0 = max(abs(dx) * 3, span / 400)
        pr = m.make_params(center=c0, sigma=sig0, amplitude=max(h0, 1e-12) * sig0 * 2.5, fraction=0.5)
        w = window or max(sig0 * 6, abs(dx) * 10)
        pr[f"p{i}_center"].set(min=c0 - w, max=c0 + w)
        pr[f"p{i}_sigma"].set(min=abs(dx) / 2, max=span / 4)
        pr[f"p{i}_amplitude"].set(min=0)
        pr[f"p{i}_fraction"].set(min=0, max=1)
        model = m if model is None else model + m
        params = pr if params is None else params.update(pr) or params
    res = model.fit(yc, params, x=x)
    out = []
    for i in range(len(centers)):
        p = res.params
        out.append({
            "center": _r(p[f"p{i}_center"].value, 5),
            "center_stderr": _r(p[f"p{i}_center"].stderr, 5) if p[f"p{i}_center"].stderr else None,
            "fwhm": _r(p[f"p{i}_fwhm"].value, 5),
            "height": _r(p[f"p{i}_height"].value, 5),
            "area": _r(p[f"p{i}_amplitude"].value, 5),
            "lorentz_fraction": _r(p[f"p{i}_fraction"].value, 4),
        })
    return base, yc, res, out


def scherrer(two_theta_deg, fwhm_deg, wavelength_A, K=0.9, instrument_fwhm_deg=0.0):
    beta2 = fwhm_deg ** 2 - instrument_fwhm_deg ** 2
    if beta2 <= 0:
        return None
    beta = np.radians(np.sqrt(beta2))
    theta = np.radians(two_theta_deg / 2)
    return K * wavelength_A / (beta * np.cos(theta)) / 10  # nm


def cmd_peaks(path, xcol=0, ycol=1, method="arpls", lam=1e6, prominence=0.05, centers=None,
              wavelength=None, K=0.9, instrument_fwhm=0.0):
    x, y, _ = load_xy(path, xcol, ycol)
    o = np.argsort(x); x, y = x[o], y[o]
    base, yc, res, peaks = fit_peaks(x, y, centers, prominence, method, lam)
    if res is None:
        return {"input": path, "error": "피크를 찾지 못함 — --prominence 를 낮추거나 --centers 지정"}
    ss_res = float(np.sum(res.residual ** 2)); ss_tot = float(np.sum((yc - yc.mean()) ** 2))
    if wavelength:
        for p in peaks:
            d = scherrer(p["center"], p["fwhm"], wavelength, K, instrument_fwhm)
            p["scherrer_size_nm"] = _r(d, 3) if d else None
    return {
        "input": path, "n_points": len(x), "baseline": {"method": method, "lam": lam},
        "auto_detect": centers is None, "prominence_rel": prominence,
        "peaks": sorted(peaks, key=lambda p: p["center"]),
        "fit_R2": _r(1 - ss_res / ss_tot, 6), "reduced_chi2": _r(res.redchi, 6),
        "scherrer": {"wavelength_A": wavelength, "K": K, "instrument_fwhm_deg": instrument_fwhm,
                     "note": "기기 퍼짐 미보정이면 크기 과소. 변형(strain) 퍼짐 분리 안 됨 — 필요 시 Williamson–Hall."} if wavelength else None,
        "grade": "E1 (실측 해석) — 기준선·피크 모델 선택에 의존",
    }


# ---------------------------------------------------------------- xrdmatch
def simulate_xrd(cif, wavelength="CuKa", two_theta=(5, 80)):
    from pymatgen.analysis.diffraction.xrd import XRDCalculator
    from pymatgen.core import Structure
    st = Structure.from_file(cif)
    pat = XRDCalculator(wavelength=wavelength).get_pattern(st, two_theta_range=two_theta)
    return st.composition.reduced_formula, np.array(pat.x), np.array(pat.y)


def cmd_xrdmatch(path, cifs, xcol=0, ycol=1, wavelength="CuKa", tol=0.25, min_rel=10.0, prominence=0.03):
    from scipy.signal import find_peaks
    x, y, _ = load_xy(path, xcol, ycol)
    o = np.argsort(x); x, y = x[o], y[o]
    yc = y - baseline(x, y, "arpls")
    idx, _ = find_peaks(yc, prominence=prominence * yc.max())
    exp_pk = x[idx]
    exp_int = yc[idx] / yc[idx].max() * 100
    rng = (float(x.min()), float(x.max()))
    out = []
    for cif in cifs:
        name, sx, sy = simulate_xrd(cif, wavelength, rng)
        major = sy >= min_rel
        matched, weight_hit, weight_all = 0, 0.0, 0.0
        for px, py in zip(sx[major], sy[major]):
            weight_all += py
            if len(exp_pk) and np.min(abs(exp_pk - px)) <= tol:
                matched += 1; weight_hit += py
        explained = sum(1 for e in exp_pk if np.min(abs(sx[major] - e)) <= tol) if major.any() else 0
        out.append({"cif": cif, "formula": name, "sim_major_peaks": int(major.sum()),
                    "matched_major_peaks": matched,
                    "weighted_match": _r(weight_hit / weight_all if weight_all else 0, 4),
                    "exp_peaks_explained": f"{explained}/{len(exp_pk)}"})
    out.sort(key=lambda r: -r["weighted_match"])
    return {
        "input": path, "wavelength": wavelength, "tolerance_2theta_deg": tol,
        "experimental_peaks_2theta": [_r(v, 3) for v in exp_pk],
        "experimental_rel_intensity": [_r(v, 1) for v in exp_int],
        "candidates": out,
        "note": "피크 위치 기반 후보 순위일 뿐 상 확정이 아님. 우선배향·고용체 격자 변화·비정질 혼재·중첩 피크를 고려하고, 확정은 Rietveld 정량으로.",
        "grade": "E1 (실측) + P0 (시뮬레이션 패턴) 비교",
    }


# ---------------------------------------------------------------- eis
def cmd_eis(path, circuit="R0-p(R1,CPE1)", initial=None, thickness_cm=None, area_cm2=None,
            r_bulk="R1", fmin=None, fmax=None):
    from impedance.models.circuits import CustomCircuit
    _, _, a = load_xy(path, 0, 1)
    f, zr, zi = a[:, 0], a[:, 1], a[:, 2]
    if np.median(zi) > 0:          # 많은 장비가 -Z'' 를 저장
        zi = -zi
    m = np.ones_like(f, bool)
    if fmin: m &= f >= fmin
    if fmax: m &= f <= fmax
    f, Z = f[m], zr[m] + 1j * zi[m]
    from impedance.models.circuits.fitting import wrapCircuit
    from scipy.optimize import least_squares
    names, units = CustomCircuit(circuit, initial_guess=_initial_for(circuit, Z, f)).get_param_names()
    is_exp = np.array([n.startswith("CPE") and n.endswith("_1") for n in names])   # CPE 지수 n
    model = wrapCircuit(circuit, {})
    mod = np.abs(Z)
    target = np.hstack([Z.real / mod, Z.imag / mod])

    def unpack(u):
        return np.where(is_exp, u, np.exp(u))   # 양수 파라미터는 로그 공간 → 크기 차 10¹² 도 안정

    def resid(u):
        zz = model(f, *unpack(u))
        n = len(f)
        return np.hstack([zz[:n] / mod, zz[n:] / mod]) - target

    lo = np.where(is_exp, 0.3, -60.0); hi = np.where(is_exp, 1.0, 60.0)
    starts = [list(initial)] if initial is not None else _multistart(circuit, f, Z)
    best = None
    for guess in starts:
        g = np.asarray(guess, float)
        u0 = np.clip(np.where(is_exp, g, np.log(np.maximum(g, 1e-300))), lo + 1e-9, hi - 1e-9)
        try:
            sol = least_squares(resid, u0, bounds=(lo, hi), x_scale="jac", max_nfev=2000)
        except Exception:  # noqa: BLE001 — 한 시작점 실패는 다음 시작점으로
            continue
        if best is None or sol.cost < best.cost:
            best = sol
        if np.sqrt(2 * best.cost / len(best.fun)) < 0.005:   # 상대오차 0.5 % 이내면 충분
            break
    if best is None:
        return {"input": path, "error": "피팅 실패 — --initial 로 초기값 지정 또는 회로 재검토"}
    p = unpack(best.x)
    params = {n: _sig(v) for n, v in zip(names, p)}
    conf = None
    try:   # 1σ: 로그 공간 공분산 → 선형 공간(상대오차 × 값)
        J = best.jac
        dof = max(len(best.fun) - len(p), 1)
        cov = np.linalg.pinv(J.T @ J) * (2 * best.cost / dof)
        su = np.sqrt(np.diag(cov))
        conf = {n: _sig(s if e_ else s * v) for n, s, v, e_ in zip(names, su, p, is_exp)}
    except Exception:  # noqa: BLE001
        pass
    zz = model(f, *p)
    Zfit = zz[: len(f)] + 1j * zz[len(f):]
    rel_err = float(np.sqrt(np.mean(np.abs((Z - Zfit) / Z) ** 2)))
    out = {"input": path, "circuit": circuit, "n_points": len(f),
           "freq_range_Hz": [_r(f.min(), 4), _r(f.max(), 4)],
           "parameters": params, "units": dict(zip(names, units)), "conf_1sigma": conf,
           "rms_relative_error": _r(rel_err, 5)}
    if thickness_cm and area_cm2 and r_bulk in params:
        R = params[r_bulk]
        out["conductivity_S_cm"] = thickness_cm / (R * area_cm2)
        out["conductivity_basis"] = f"σ = L/(R·A), R = {r_bulk}, L = {thickness_cm} cm, A = {area_cm2} cm²"
        if "R2" in params and r_bulk == "R1":
            out["total_conductivity_S_cm"] = thickness_cm / ((params["R1"] + params["R2"]) * area_cm2)
    out["note"] = "등가회로 선택에 따라 벌크/입계 구분이 달라진다. CPE 지수 n<0.7 이면 축전 해석에 주의. 상대오차 > 5% 면 회로 재검토."
    out["grade"] = "E1 (실측 해석) — 등가회로 모델 의존"
    return out


def _elements(circuit):
    import re
    return re.findall(r"(CPE\d+|R\d+|C\d+|Wo\d+|Ws\d+|W\d+|L\d+)", circuit)


def _arc_features(f, Z):
    """나이퀴스트 반원 특징: 고주파 절편 R0, 첫 반원 지름, 꼭짓점 각주파수, 저주파 꼬리."""
    o = np.argsort(f)[::-1]                     # 고주파 → 저주파
    fz, zr, mzi = f[o], Z.real[o], -Z.imag[o]
    r0 = max(float(zr[0]), 1e-6)
    i_apex = int(np.argmax(mzi[: max(3, len(mzi) // 2)]))
    after = mzi[i_apex:]
    i_min = i_apex + int(np.argmin(after)) if len(after) > 2 else len(mzi) - 1
    r_arc = max(float(zr[i_min] - r0), float(np.ptp(zr)) * 0.05, 1e-6)
    w_apex = 2 * np.pi * float(fz[i_apex])
    w_low = 2 * np.pi * float(fz[-1])
    q_low = 1.0 / (w_low * max(float(mzi[-1]), 1e-12))
    return r0, r_arc, w_apex, q_low


def _initial_for(circuit, Z, f=None, r_scale=1.0, q_scale=1.0):
    if f is None:
        f = np.logspace(0, 6, len(Z))
    r0, r_arc, w_apex, q_low = _arc_features(f, Z)
    q_arc = 1.0 / (w_apex * r_arc)
    init, n_cpe, n_r = [], 0, 0
    for el in _elements(circuit):
        if el.startswith("CPE"):
            n_cpe += 1
            init += ([q_arc * q_scale, 0.9] if n_cpe == 1 else [q_low * q_scale, 0.8])
        elif el == "R0":
            init.append(r0)
        elif el.startswith("R"):
            n_r += 1
            init.append(r_arc * r_scale * (1 if n_r == 1 else 2))
        elif el.startswith("C"):
            init.append(q_arc * q_scale)
        elif el.startswith("W"):
            init += [r_arc, 1.0] if el[:2] in ("Wo", "Ws") else [r_arc]
        elif el.startswith("L"):
            init.append(1e-7)
    return init


def _multistart(circuit, f, Z):
    return [_initial_for(circuit, Z, f, rs, qs) for rs in (1.0, 0.3, 3.0) for qs in (1.0, 0.1, 10.0)]


# ---------------------------------------------------------------- arrhenius
def cmd_arrhenius(path, kind="sigmaT", at=None, T_unit="K"):
    T, v, _ = load_xy(path, 0, 1)
    if T_unit == "C":
        T = T + 273.15
    if kind == "sigmaT":          # σT = A exp(-Ea/kT)  (이온 전도 표준)
        yv = np.log(v * T)
    else:                          # sigma 또는 D: y = A exp(-Ea/kT)
        yv = np.log(v)
    x = 1 / T
    A = np.vstack([x, np.ones_like(x)]).T
    (slope, icpt), res, *_ = np.linalg.lstsq(A, yv, rcond=None)
    pred = slope * x + icpt
    r2 = 1 - np.sum((yv - pred) ** 2) / np.sum((yv - yv.mean()) ** 2)
    n = len(x)
    s_err = np.sqrt(np.sum((yv - pred) ** 2) / max(n - 2, 1)) / np.sqrt(np.sum((x - x.mean()) ** 2))
    Ea = -slope * KB_EV
    out = {"input": path, "model": "σT = A·exp(-Ea/kT)" if kind == "sigmaT" else "y = A·exp(-Ea/kT)",
           "n_points": n, "T_range_K": [_r(T.min(), 2), _r(T.max(), 2)],
           "Ea_eV": _r(Ea, 5), "Ea_eV_stderr": _r(s_err * KB_EV, 5), "Ea_kJ_mol": _r(Ea * 96.485, 3),
           "prefactor_A": float(np.exp(icpt)), "R2": _r(r2, 6)}
    if at:
        val = np.exp(slope / at + icpt)
        out["extrapolated"] = {"T_K": at, "value": float(val / at if kind == "sigmaT" else val),
                               "outside_measured_range": bool(at < T.min() or at > T.max())}
        if out["extrapolated"]["outside_measured_range"]:
            out["warning"] = "측정 범위 밖 외삽 — 상전이·입계 기여 변화가 있으면 틀릴 수 있음(MD 고온값 외삽 시 특히)."
    out["grade"] = "입력 등급을 따름(실측이면 E1, MD 결과면 P0)"
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("peaks"); p.add_argument("csv")
    p.add_argument("--xcol", type=int, default=0); p.add_argument("--ycol", type=int, default=1)
    p.add_argument("--baseline", default="arpls", choices=["arpls", "asls", "modpoly", "snip", "none"])
    p.add_argument("--lam", type=float, default=1e6); p.add_argument("--prominence", type=float, default=0.05)
    p.add_argument("--centers", type=float, nargs="+")
    p.add_argument("--scherrer", type=float, metavar="WAVELENGTH_A"); p.add_argument("--K", type=float, default=0.9)
    p.add_argument("--instrument-fwhm", type=float, default=0.0)
    p = sub.add_parser("xrdmatch"); p.add_argument("csv"); p.add_argument("cifs", nargs="+")
    p.add_argument("--wavelength", default="CuKa"); p.add_argument("--tol", type=float, default=0.25)
    p = sub.add_parser("eis"); p.add_argument("csv"); p.add_argument("--circuit", default="R0-p(R1,CPE1)")
    p.add_argument("--initial", type=float, nargs="+"); p.add_argument("--thickness", type=float)
    p.add_argument("--area", type=float); p.add_argument("--r-bulk", default="R1")
    p.add_argument("--fmin", type=float); p.add_argument("--fmax", type=float)
    p = sub.add_parser("arrhenius"); p.add_argument("csv")
    p.add_argument("--kind", choices=["sigmaT", "plain"], default="sigmaT")
    p.add_argument("--at", type=float); p.add_argument("--celsius", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "peaks":
        res = cmd_peaks(a.csv, a.xcol, a.ycol, a.baseline, a.lam, a.prominence, a.centers, a.scherrer, a.K, a.instrument_fwhm)
    elif a.cmd == "xrdmatch":
        res = cmd_xrdmatch(a.csv, a.cifs, wavelength=a.wavelength, tol=a.tol)
    elif a.cmd == "eis":
        res = cmd_eis(a.csv, a.circuit, a.initial, a.thickness, a.area, a.r_bulk, a.fmin, a.fmax)
    else:
        res = cmd_arrhenius(a.csv, a.kind, a.at, "C" if a.celsius else "K")
    res["versions"] = _versions()
    res["command"] = " ".join(["seion_expdata.py"] + (argv if argv is not None else sys.argv[1:]))
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
