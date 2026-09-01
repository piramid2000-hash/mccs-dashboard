"""
Phase-3 적응형 제어 확장 (특허 고도화안 반영).

네 가지 물리적 공백에 대한 정량 설계:
  A. k(f,T) 공간 전달계수 표류 — 물리 모델에 의한 상한과, 그것을 기준값으로 삼는
     기계적 고장(공극 변화) 검출기
  B. 공차 강건 이조(detuning) 공진 뱅크 — 양측 구속(전압 상한 + 전압 하한)
  C. 샴 유속 비대칭에 대한 차동 열정합
  D. Dwell-time 인터록 — 조건별로 적용 여부를 구분

이 모듈의 모든 값은 계산값(P0)이며 실측값이 아니다.
"""
import math
import random
from dataclasses import dataclass
from typing import List, Tuple

from constants import MU0, PI, CP_WATER, RHO_M_WATER

ALPHA_FE = 12.0e-6        # 1/K, 연자성 강 및 규소강의 선팽창계수 (P0)
ALPHA_PVDF = 130.0e-6     # 1/K, PVDF (P0)


# ===========================================================================
# A. k(f, T) 공간 전달계수 표류
# ===========================================================================
@dataclass
class KDrift:
    """
    k = B_ECV / I  [T/A] 의 상대 표류.

        k(f, T) / k0 = 1 + a_f (f/f_ref)^2 + a_T (T - T_ref)

    계수는 자유 파라미터가 아니라 물리 모델로부터 상한이 유도된다.
    """
    a_f: float
    a_T: float
    f_ref: float = 3000.0
    T_ref: float = 20.0
    detail: dict = None

    def __call__(self, f, T):
        return 1.0 + self.a_f * (f / self.f_ref) ** 2 + self.a_T * (T - self.T_ref)


def thermal_gap_coefficient(gap_m, member_len_m, uniform=True):
    """
    공극 길이의 온도 계수 [1/K].

    균일 가열: 구조 전체가 상사 확대되므로 공극도 같은 비율로 늘어난다.
        dg/g = alpha * dT              -> B/I 는 -alpha*dT 만큼 변화
    부분 가열(자극편·각부만 가열, 요크는 냉각판 온도): 가열된 부재가 공극 쪽으로
    팽창하여 공극을 좁힌다.
        dg = -alpha * dT * L_member    -> dg/g = -alpha * L_member / g * dT
    후자가 g 대비 L_member 배만큼 크므로 지배적이다.
    """
    if uniform:
        return -ALPHA_FE            # dk/k per K  (공극 증가 -> B/I 감소)
    return +ALPHA_FE * member_len_m / gap_m


def core_permeability_rolloff(f, mu_r, sigma, lam_t):
    """
    적층 두께 방향 와전류에 의한 실효 투자율 저하.
        mu_eff/mu = tanh(gamma d/2) / (gamma d/2),  gamma = (1+j)/delta
    """
    if f <= 0 or sigma <= 0:
        return 1.0
    mu = MU0 * mu_r
    delta = math.sqrt(2.0 / (2 * PI * f * mu * sigma))
    z = complex(1, 1) / delta * (lam_t / 2.0)
    return abs(cmath_tanh(z) / z)


def cmath_tanh(z):
    import cmath
    return cmath.tanh(z)


def build_kdrift(core, mat, gain, reluct_gap_frac=0.999,
                 member_len=0.20, dT_max=65.0):
    """
    물리 모델로부터 (a_f, a_T) 의 상한을 산출한다.
    """
    # --- 온도항 -------------------------------------------------------------
    a_T_uniform = thermal_gap_coefficient(core.gap, member_len, uniform=True)
    a_T_diff = thermal_gap_coefficient(core.gap, member_len, uniform=False)
    a_T = a_T_diff                      # 지배항(부분 가열)을 채택
    # --- 주파수항 -----------------------------------------------------------
    # 자심 투자율 저하 -> 자심 자기저항 증가 -> 전체 자기저항 증가
    ro = core_permeability_rolloff(3000.0, mat.mu_r_init, mat.sigma, mat.lam_t)
    core_frac = 1.0 - reluct_gap_frac
    a_f = -core_frac * (1.0 / ro - 1.0)   # 3 kHz 에서의 상대 변화
    return KDrift(a_f=a_f, a_T=a_T,
                  detail=dict(a_T_uniform=a_T_uniform, a_T_diff=a_T_diff,
                              mu_rolloff_3k=ro, core_reluct_frac=core_frac,
                              dT_max=dT_max))


def kdrift_envelope(kd: KDrift, f_max=3000.0, dT=65.0):
    """예측 표류 포락선 [%] — 기계적 고장 검출의 기준선이 된다."""
    return dict(freq_pct=100 * abs(kd.a_f) * (f_max / kd.f_ref) ** 2,
                temp_pct=100 * abs(kd.a_T) * dT,
                total_pct=100 * (abs(kd.a_f) * (f_max / kd.f_ref) ** 2
                                 + abs(kd.a_T) * dT))


def gap_change_from_k_residual(residual_pct, gap_m, member_len_m):
    """
    보정 후에도 남는 k 잔차를 공극 변화량으로 환산한다.
    k ~ 1/g 이므로  dg/g = -dk/k.
    """
    return residual_pct / 100.0 * gap_m * 1e6       # µm


# ===========================================================================
# B. 공차 강건 이조 공진 뱅크
# ===========================================================================
@dataclass
class Band:
    f_lo: float
    f_hi: float
    f_tune: float
    C: float

    def X(self, f, L):
        w = 2 * PI * f
        return w * L - 1.0 / (w * self.C)


def band_upper_edge(f_lo, L, x_allow, c_tol, l_tol):
    """
    기하 중심 동조(f_t = sqrt(f_lo f_hi)) 대역에서, 소자 편차를 포함하여
    전압 상한을 만족하는 대역 상단 f_hi 의 닫힌 해.

    X(f) = 2*pi*f*L(1+dL) - 2*pi*L*f_lo*f_hi/(f(1+dC)) 는 f 에 대하여 단조 증가하므로
    최악값은 대역의 두 끝에서만 발생한다.

      상단(유도성) 최악  dL=+l, dC=+c :  f_hi <= [K + f_lo/(1+c)] / (1+l)
      하단(용량성) 최악  dL=-l, dC=-c :  f_hi <= (1-c) [K + f_lo(1-l)]
      여기서 K = x_allow / (2*pi*L)
    """
    K = x_allow / (2 * PI * L)
    b1 = (K + f_lo / (1 + c_tol)) / (1 + l_tol)
    b2 = (1 - c_tol) * (K + f_lo * (1 - l_tol))
    return min(b1, b2)


def design_bands(L, I, v_max, f_top=3300.0, f_min=3.0,
                 c_tol=0.03, l_tol=0.02):
    """
    공차 강건 이조 공진 뱅크.

    설계 원칙
    ---------
    * 구동은 전류 제어이므로, 공진 이탈의 고장 모드는 '과전류 발산'이 아니라
      '증폭기 전압 포화'이다. 따라서 구속은 전압 상한의 단측 구속이다.
    * 각 대역은 기하 중심에서 동조시키되, 대역폭을 소자 편차가 전압 상한을 넘지
      못하도록 좁힌다. 이것이 '의도적 이조'의 정량적 정의이다.
    * c_tol, l_tol 은 부품의 제조 공차가 아니라 **제작 후 실측 동정을 마친 뒤
      남는 잔여 불확도**(경년 변화 + 온도계수)이다.
    * 2*pi*f*L <= x_allow 인 저주파 구간은 보상 자체가 불필요하다.
    """
    x_allow = v_max / I
    f_nocomp = x_allow / (2 * PI * L * (1 + l_tol))
    bands: List[Band] = []
    f_lo = max(f_min, f_nocomp)
    guard = 0
    while f_lo < f_top and guard < 60:
        guard += 1
        f_hi = min(band_upper_edge(f_lo, L, x_allow, c_tol, l_tol), f_top)
        if f_hi <= f_lo * 1.001:
            break
        f_t = math.sqrt(f_lo * f_hi)
        bands.append(Band(f_lo, f_hi, f_t,
                          1.0 / ((2 * PI * f_t) ** 2 * L)))
        if f_hi >= f_top:
            break
        f_lo = f_hi
    return dict(f_nocomp=f_nocomp, x_allow=x_allow, bands=bands,
                c_tol=c_tol, l_tol=l_tol, kappa=None, x_floor=0.0)


def select_band(bands: List[Band], f):
    for b in bands:
        if b.f_lo <= f <= b.f_hi:
            return b
    return None


def drive_voltage(f, L, R, I, bands, dC=0.0, dL=0.0):
    """소자 공차를 반영한 구동 전압 [V]."""
    Le = L * (1 + dL)
    b = select_band(bands, f)
    w = 2 * PI * f
    if b is None:
        X = w * Le
    else:
        X = w * Le - 1.0 / (w * b.C * (1 + dC))
    return I * math.hypot(R, X), X


def tolerance_monte_carlo(L, R, I, bands, f_grid, n=4000, c_tol=0.10,
                          l_tol=0.05, seed=11):
    """C ±c_tol, L ±l_tol 균등분포에 대한 최악 구동 전압."""
    rng = random.Random(seed)
    worst_v, worst_f, vmin = 0.0, 0.0, 1e18
    for _ in range(n):
        dC = rng.uniform(-c_tol, c_tol)
        dL = rng.uniform(-l_tol, l_tol)
        for f in f_grid:
            v, _ = drive_voltage(f, L, R, I, bands, dC, dL)
            if v > worst_v:
                worst_v, worst_f = v, f
            vmin = min(vmin, v)
    return dict(v_worst=worst_v, f_worst=worst_f, v_min=vmin, n=n,
                c_tol=c_tol, l_tol=l_tol)


# ===========================================================================
# C. 샴 유속 비대칭 열정합
# ===========================================================================
def pump_power_asymmetry(p_pump, flow_asym, exponent=2.75):
    """
    난류 관로에서 dP ~ Q^1.75 이므로 펌프 동력 P = dP*Q ~ Q^2.75.
    유량 비대칭 eps 에 대한 동력 차 [W].
    """
    return p_pump * (abs((1 + flow_asym) ** exponent - 1.0))


def dT_rate(p_w, volume_L):
    """K/h"""
    return p_w / (volume_L * RHO_M_WATER.value / 1000.0 * CP_WATER.value) * 3600.0


def sham_thermal_balance(p_pump, flow_asym, volume_L, run_h,
                         valve_residual=0.10, dT_sensor_mK=1.0,
                         control_margin=3.0, heater_w=100.0, heater_bits=16):
    """
    2단 정합:
      1단 — 전동 트림 밸브로 유량 비대칭을 valve_residual 배까지 축소
      2단 — 차동 온도(정합 서미스터 쌍) 되먹임으로 트림 히터를 제어

    잔차는 차동 온도 센서의 분해능과 제어 여유에 의하여 결정된다.
    """
    dP_raw = pump_power_asymmetry(p_pump, flow_asym)
    dP_valve = pump_power_asymmetry(p_pump, flow_asym * valve_residual)
    raw_K = dT_rate(dP_raw, volume_L) * run_h
    valve_K = dT_rate(dP_valve, volume_L) * run_h
    heater_step = heater_w / (2 ** heater_bits)
    heater_K = dT_rate(heater_step, volume_L) * run_h
    resid_mK = max(dT_sensor_mK * control_margin, heater_K * 1e3)
    return dict(dP_raw_W=dP_raw, dP_after_valve_W=dP_valve,
                dT_raw_K=raw_K, dT_after_valve_K=valve_K,
                heater_step_W=heater_step, heater_quant_K=heater_K,
                residual_K=resid_mK / 1e3, heater_span_W=heater_w,
                trim_duty_pct=100 * dP_valve / heater_w)


# ===========================================================================
# D. Dwell-time 인터록
# ===========================================================================
@dataclass
class Interlock:
    idx: int
    name: str
    dwell: str
    rationale: str


def interlock_table(t_avg_lo, t_avg_hi, n_updates=2, dwell_min_ms=50.0):
    """
    Dwell 필터는 조건별로 구분하여 적용한다.
    즉시성이 요구되는 조건에 지연을 두는 것은 안전 기능의 훼손이므로 금지한다.
    """
    inst = "즉시 (필터 없음)"
    return [
        Interlock(1, "과전류", inst, "권선 손상 및 증폭기 파괴가 밀리초 단위로 진행된다"),
        Interlock(2, "과전압", inst, "보상 커패시터 절연 파괴가 즉시 발생한다"),
        Interlock(3, "코일 과온", "1 s", "열시정수가 수십 초이므로 1 s 지연은 무해하다"),
        Interlock(4, "구동부 과온", "1 s", "동상"),
        Interlock(5, "누수", inst, "감전 및 전기분해 위험"),
        Interlock(6, "절연 저하", inst, "감전 위험"),
        Interlock(7, "센서 계층 불일치",
                  f"연속 {n_updates}회 갱신 (≥ {dwell_min_ms:.0f} ms, "
                  f"{n_updates*t_avg_hi:.0f}~{n_updates*t_avg_lo:.0f} s)",
                  "복조 주기보다 짧은 시간 창은 의미가 없다. 계측 무결성 조건이며 "
                  "즉시 위험이 아니고, 과전류·자장 폭주 경로가 별도로 보호한다"),
        Interlock(8, "자장 폭주", "3 주기", "주기 기준이므로 주파수에 자동 정규화된다"),
        Interlock(9, "통신 두절", "50 ms", "워치독 주기"),
        Interlock(10, "비상 정지", inst, "법규상 지연을 둘 수 없다"),
    ]


def band_switch_mask(t_settle_ms=200.0, max_mask_per_hour=20):
    """
    대역 전환 과도 구간의 마스킹 규정.
    마스킹 자체가 고장 은폐 수단이 되지 않도록 지속시간과 빈도를 구속한다.
    """
    return dict(masked_conditions=[7, 8], t_mask_ms=t_settle_ms,
                max_per_hour=max_mask_per_hour,
                escalation="빈도 초과 시 마스킹을 해제하고 조건 7 을 즉시 트립으로 승격한다")


def gap_detection_threshold(gap_m, sigma_A_pct=0.30, k_sigma=3.0,
                            n_runs=(1, 10, 100), model_envelope_pct=None):
    """
    k 잔차를 이용한 공극 변화(FMEA F-05) 검출 감도.

    k ∝ 1/g 이므로 dg/g = -dk/k 이다. 계통 오차항은 동일 조건의 반복 측정에서
    상쇄되므로 검출 한계를 정하는 것은 A 형 반복성 sigma_A 이다.

    k(f,T) 보정을 적용하지 아니하면 모델 포락선(예측 표류)을 경보 문턱에 더하여야
    하므로 문턱이 그만큼 높아진다. 보정의 실익은 여기에 있다.
    """
    out = []
    for n in n_runs:
        se = sigma_A_pct / math.sqrt(n)
        thr_corr = k_sigma * se
        thr_uncorr = thr_corr + (model_envelope_pct or 0.0)
        out.append(dict(n=n, se_pct=se,
                        thr_corrected_pct=thr_corr,
                        thr_uncorrected_pct=thr_uncorr,
                        dg_corrected_um=thr_corr / 100 * gap_m * 1e6,
                        dg_uncorrected_um=thr_uncorr / 100 * gap_m * 1e6))
    return out


def capacitor_bank_cost_proxy(bands: List[Band], I, L):
    """
    커패시터 뱅크의 규모 지표. 필름 커패시터의 가격과 부피는 대략 저장 에너지
    (0.5 C V^2) 에 비례하므로 이를 대용 지표로 쓴다.
    """
    tot = 0.0
    for b in bands:
        w = 2 * PI * b.f_tune
        v_c = I * (1.0 / (w * b.C))
        tot += 0.5 * b.C * (v_c * math.sqrt(2)) ** 2
    return tot
