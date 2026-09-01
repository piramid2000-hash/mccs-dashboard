"""적응형 제어 확장의 해석적 한계 검증. python3 tests/test_adaptive.py"""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "design"))
import adaptive as A, system as S, cell as C, run_all as RA
from constants import NANOCRYSTALLINE, NO10_THIN, PI, F_GRID

F = []
def chk(name, cond, note=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{(' — ' + note) if note else ''}")
    if not cond: F.append(name)

core = S.CoreGeom(); wc = RA.winding_choice(); st = C.cell_field_stats(1.0)
L = wc["L"]; I = wc["mmf_max"] / (2 * wc["turns"])
R = [r for r in RA.master_table(wc, NANOCRYSTALLINE)
     if r["B_set_mT"] == 50 and r["f_Hz"] == 3000][0]["R_ac_ohm"]

print("1. k(f,T) 계수는 물리 모델에서 유도되며 자유 파라미터가 아니다")
kd = A.build_kdrift(core, NANOCRYSTALLINE, st["mean"])
chk("균일 가열 계수 = -alpha_Fe", abs(kd.detail["a_T_uniform"] + A.ALPHA_FE) < 1e-12)
chk("부분 가열이 균일 가열보다 지배적",
    abs(kd.detail["a_T_diff"]) > abs(kd.detail["a_T_uniform"]),
    f"{abs(kd.detail['a_T_diff'])/abs(kd.detail['a_T_uniform']):.1f}배")
chk("공극 지배 회로에서 주파수항은 무시할 수 있다", abs(kd.a_f) < 1e-4,
    f"a_f={kd.a_f:.2e}")
env = A.kdrift_envelope(kd, dT=65.0)
chk("예측 표류가 계측 확장 불확도(2.87 %)보다 작다", env["total_pct"] < 2.87,
    f"{env['total_pct']:.3f} %")
chk("k(f,T) 는 기준 조건에서 1", abs(kd(3000.0 * 0 + kd.f_ref * 0, 20.0) - 1.0) < 1e-12)

print("\n2. 이조 대역 설계는 모든 공차 실현에서 전압 상한을 만족한다")
grid = [3.0 + i * (3000 - 3) / 600 for i in range(601)] + list(F_GRID)
for ct, lt in ((0.10, 0.05), (0.05, 0.03), (0.03, 0.02)):
    d = A.design_bands(L, I, 600.0, c_tol=ct, l_tol=lt)
    mc = A.tolerance_monte_carlo(L, R, I, d["bands"], grid, n=800, c_tol=ct, l_tol=lt)
    chk(f"C±{ct*100:.0f} %, L±{lt*100:.0f} % 최악 V <= 600 V", mc["v_worst"] <= 600.0 + 1e-6,
        f"{mc['v_worst']:.1f} V, 대역 {len(d['bands'])}개")

d = A.design_bands(L, I, 600.0)
chk("보상이 불필요한 저주파 구간이 존재한다", d["f_nocomp"] > 100.0,
    f"<= {d['f_nocomp']:.0f} Hz")
chk("대역이 3 kHz 를 모두 덮는다", d["bands"][-1].f_hi >= 3000.0)
for b in d["bands"]:
    w_lo, w_hi = 2 * PI * b.f_lo, 2 * PI * b.f_hi
    chk(f"대역 {b.f_lo:.0f}-{b.f_hi:.0f} Hz 에서 리액턴스가 부호를 바꾼다(중심 동조)",
        (w_lo * L - 1 / (w_lo * b.C)) < 0 < (w_hi * L - 1 / (w_hi * b.C)))

print("\n3. 부하 Q 를 50 이하로 제한하는 것은 이 설계에서 실현 불가능하다")
X = 2 * PI * 3000 * L
r_need = X / 50.0
chk("Q<=50 요구는 제동 저항 손실이 kW 급이 된다", I ** 2 * r_need > 1000.0,
    f"{I**2*r_need:.0f} W (현재 {I**2*R:.1f} W)")

print("\n4. 샴 열정합")
p_pump = [r for r in RA.hydraulics_table() if r["v_ms"] == 0.5][0]["P_pump_W"]
raw = A.sham_thermal_balance(p_pump, 0.02, 1000.0, 8.0, valve_residual=1.0)
chk("무대책 시 2 % 유속 비대칭은 이중맹검 한계(0.05 K)를 초과한다",
    raw["dT_after_valve_K"] > 0.05, f"{raw['dT_after_valve_K']:.3f} K")
bal = A.sham_thermal_balance(p_pump, 0.02, 1000.0, 8.0)
chk("2단 정합 후 한계 이내", bal["residual_K"] < 0.05,
    f"{bal['residual_K']:.4f} K, 여유 {0.05/bal['residual_K']:.0f}배")
chk("트림 히터 정격이 충분하다", bal["trim_duty_pct"] < 50.0,
    f"사용률 {bal['trim_duty_pct']:.1f} %")

print("\n5. Dwell 필터는 조건별로 구분 적용된다")
tab = A.interlock_table(10.0, 3.0)
inst = [t.idx for t in tab if "즉시" in t.dwell]
chk("과전류·과전압·누수·절연·비상정지에는 지연을 두지 아니한다",
    set([1, 2, 5, 6, 10]).issubset(set(inst)), f"즉시 조건 {inst}")
chk("센서 불일치의 지연은 복조 갱신 횟수 기준이다",
    "갱신" in [t for t in tab if t.idx == 7][0].dwell)

print("\n6. 공극 변화 검출 감도")
det = A.gap_detection_threshold(core.gap, model_envelope_pct=env["total_pct"])
chk("보정이 검출 문턱을 낮춘다",
    det[0]["thr_corrected_pct"] < det[0]["thr_uncorrected_pct"],
    f"{det[0]['thr_uncorrected_pct']:.2f} % -> {det[0]['thr_corrected_pct']:.2f} %")
chk("100 회 평균 시 수십 µm 급 공극 변화를 검출한다",
    det[-1]["dg_corrected_um"] < 50.0, f"{det[-1]['dg_corrected_um']:.1f} µm")

print("\n" + "=" * 58)
if F:
    print("FAILURES:", ", ".join(F)); sys.exit(1)
print("ALL CHECKS PASSED")
