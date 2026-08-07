# 신규 AEM 제조 레시피 제안 — R2.5 "Co-Cast Gradient Janus AEM (AEM-G2)"

> SEION LAB | NH₄HCO₃ Direct-Conversion CO₂ Electrolysis Platform — 부속 레시피 제안서
>
> 본 문서의 모든 조성·두께·성능 수치는 통합 기술보고서의 증거 태그 규칙을 따른다.
> **[M] 실측 / [L] 문헌 / [S] 시뮬레이션 / [H] 가설·설계목표.** 실측 전에는 어떤 값도 성능 보증으로 사용하지 않는다.

---

## 1. 설계 의도와 포지셔닝

| 구분 | R1 (현실형) | R2 (특허형) | **R2.5 (본 제안, AEM-G2)** | R3 (차세대형) |
|---|---|---|---|---|
| 막 구조 | PAP/ePTFE 90/10 단일막 30–60 μm [H] | R1 core + Janus skins 0.5–3 μm [H] | **Janus skins + Zone-I 수화층을 막에 co-cast 통합, 총 30–50 μm [H]** | BPM + ultrathin AEM [H] |
| Interposer | 3-zone 별도 코팅 (G/R/I) | 3-zone 별도 코팅 | **Zone-I를 막측으로 흡수 → interposer는 G/R 2-zone으로 단순화** | 10–30 μm 초박형 |
| 핵심 가설 | 기준선 확보 | crossover·열화 저감 | **계면(interface) 수 감소로 접촉저항·박리 failure mode 자체를 제거** | 국부 CO₂ 생성 |
| 개발단계 | TRL 3→5 | TRL 3→6 | **TRL 3→5, R2와 병렬 A/B** | TRL 2→5 |

**설계 논리.** R1/R2 구조에서 막–interposer Zone-I 사이 계면은 (1) 접촉저항, (2) 수화 불연속, (3) 압축·팽윤 사이클에서의 박리라는 세 가지 잠재 failure mode를 갖는다 [H]. R2.5는 Zone-I(친수·이온연결층)를 별도 interposer 코팅이 아니라 **막 캐스팅 공정의 마지막 pass로 co-cast**하여 계면을 화학적으로 연속화한다. 동시에 R2의 Janus skin 개념(음극 선택층 / 양극 보호층)을 유지해 carbonate crossover와 양극측 산화열화 저감 가설을 그대로 검증한다.

주의: Zone-I 원조성(PAP/carbon/ZrO₂ = 75/20/5)의 carbon은 전자전도성이므로 **막 통합 시 단락(soft short) 위험**이 있다. 따라서 막 통합형 수화층은 carbon을 제거하고 **PAP/ZrO₂ = 90/10 [H]** 으로 재설계한다. interposer 측에 남는 Zone-G/R가 전자전도 경로를 담당한다.

---

## 2. 막 단면 구조 (음극 → 양극 방향)

| # | 층 | 조성 (solids) | 건조 두께 | 기능 | 태그 |
|---|---|---|---|---|---|
| L1 | Cathode-selective skin | 가교 PAP (diamine crosslinker 5–10 mol%) | 0.5–2 μm | carbonate/water crossover 저감 | [H] |
| L2 | Integrated hydration layer (구 Zone-I) | PAP/ZrO₂ = 90/10 | 3–8 μm | 촉매측 수화·이온 연결, carbon-free | [H] |
| L3 | Reinforced conductive core | PAP/ePTFE = 90/10, PAP IEC 2.0–2.4 meq/g | 22–35 μm | 전도·치수안정 | [H] |
| L4 | Anode-protective skin | 산화내성 PAP 변형체 (benzylic 위치 최소화) | 0.5–2 μm | 양극측 화학열화 저감 | [H] |
| — | **총 두께** | — | **30–50 μm** | R1 범위(30–60 μm) 내 유지 | [H] |

Embedded sensing(micro-RTD 2–4점)은 R2와 동일하게 optional arm으로 두고, 센서 삽입 전후 ASR/누설/압축 균일성 비교를 acceptance로 한다 [H].

---

## 3. 원재료 BOM 추가·변경분

기존 BOM(통합보고서 표 10)에 다음을 추가한다.

| 원재료 | 입고사양·검사 | 역할 | 취급·리스크 |
|---|---|---|---|
| PAP (high-IEC grade) | IEC 2.0–2.4 meq/g, MW, solids, halide form COA | L2/L3 매트릭스 | 알칼리 안정성 lot별 확인 |
| Diamine crosslinker (예: DABCO계 또는 alkyl diamine) | purity, 수분 | L1 가교 선택층 | 반응성 시약, pot life 관리 |
| 산화내성 PAP 변형체 | NMR로 benzylic-free 확인, IEC | L4 양극 보호층 | 소량 합성 lot 분산 |
| ZrO₂ nanopowder | 입도(≤100 nm), 표면기, 수분 | L2 수화 완충 | 분산 안정성; 막 bulk(L3)에는 미투입 |
| 캐스팅 용매 (DMSO 또는 NMP, 공급자 SDS 우선) | 수분, purity | dope 제조 | VOC·방폭, 회수 |

---

## 4. 100 cm² 단위 배치 레시피 (캐스팅 유효면적 ~150 cm², 마진 포함)

모든 질량은 활성면적 × 목표 로딩으로 면적비례 스케일링하고, 실제 고형분은 매 배치 건조감량으로 확인한다.

| 배치 | 고형분 기준 | 액상/두께 기준 | 공정 |
|---|---|---|---|
| L3 core dope | PAP solids 1.8 g + ePTFE web(12–15 μm, 공극률 ≥80%) [H] | 18–22 wt% 용액, 목표 dry 22–35 μm [H] | ePTFE 함침(dip 또는 slot-die) → 60 °C 30 min → 80 °C 60 min 단계건조 [H] |
| L2 hydration ink | PAP 0.45 g + ZrO₂ 0.05 g (90/10) [H] | 8–10 wt%, 목표 dry 3–8 μm [H] | L3 건조 직후(완전 어닐링 전) co-cast 1 pass → 동일 건조 [H] |
| L1 skin solution | PAP 0.10 g + crosslinker 5–10 mol% [H] | 2–4 wt% 희박용액, 목표 dry 0.5–2 μm [H] | spray 또는 dip 1 pass → 100–120 °C 30 min 가교 [H] |
| L4 skin solution | 산화내성 PAP 0.10 g [H] | 2–4 wt%, 목표 dry 0.5–2 μm [H] | 반대면 spray 1 pass → 건조 [H] |
| 이온형 전환 | — | 1 M NH₄HCO₃(또는 KHCO₃) 3회 교체 침지, 각 ≥4 h, 25–35 °C [H] | halide → bicarbonate form 전환 → DI 세척 → 습윤 보관 |

**공정 순서 요약:** ePTFE 함침(L3) → 부분건조 → L2 co-cast → 건조 → L1 가교 skin → L4 보호 skin → 이온형 전환 → 세척·검사. L2를 L3 완전 어닐링 전에 올리는 것이 계면 연속화의 핵심 가설이다 [H].

---

## 5. CTQ와 합격판정 (초기 가설 기준)

| CTQ | 측정법 | 초기 기준 | 주의사항 |
|---|---|---|---|
| 총 두께 | 9-point gauge/SEM | 30–50 μm, 범위 ≤±10% [H] | 최소값·범위 동시관리 |
| 층별 두께 (L1/L2/L4) | cross-section SEM | 설계범위 내 [H] | 배치당 ≥1 시편 |
| IEC (전체막) | 적정법 | 1.6–2.1 meq/g [H] | skin 가교로 bulk 대비 하락 예상 |
| ASR (bicarbonate form) | EIS, T·수화조건 명기 | <0.045 Ω·cm² [H] | R1 기준(<0.05)보다 강화 목표 |
| In-plane swelling | 습윤/건조 치수 | <12% [H] | ePTFE 방향성(MD/TD) 별도 기록 |
| Water uptake | 건조감량 | 40–70 wt% [H] | L2 통합 효과 관측변수 |
| Pinhole/leak | dye/pressure/He | 검출 0 [H] | 시험해상도 명시 |
| 계면 박리 | 90° peel 또는 단면 SEM (습윤·건조 사이클 20회 후) [H] | 박리 없음 [H] | **R2.5의 핵심 검증항목** |
| Soft short | 막 단독 절연저항 | 기준 DOE [H] | L2 carbon-free 검증 |

---

## 6. DOE 계획 (Phase 1 screening 편입)

통합보고서 8장 단계형 DOE에 다음 인자를 추가·치환한다.

- **핵심 인자 [H]:** L3 IEC(2.0/2.4) × L1 가교도(5/10 mol%) × L2 두께(3/8 μm) × L2 ZrO₂(0/10 wt%) — 2⁴⁻¹ fractional + center, 8–10 runs.
- **우선 상호작용 [H]:** skin thickness × IEC × water uptake (R2 Pareto trade-off와 공유), L2 두께 × a_w × Ψ_interposer (2-zone 단순화 영향).
- **A/B 비교군:** R1 단일막, R2 skin막(별도 Zone-I interposer), 상용 AEM control [L] — 동일 Ag cathode·동일 운전창에서 G2(5–25 cm²) 셀 비교, ≥3 반복 [H].
- **판정(Go/No-Go) [H]:** R2 대비 (1) ASR 동등 이상, (2) 습윤·건조 사이클 후 박리·ASR drift 유의 감소, (3) FECO·crossover 동등 이상일 때 G3(100 cm²) 진입.

---

## 7. 리스크와 검증 질문

| 리스크 | 징후 | 완화책 |
|---|---|---|
| L2/L3 co-cast 시 용매 재용해로 core 결함 | pinhole 증가, 두께 불균일 | L3 부분건조 조건(잔류용매 %) DOE; slot-die 정량화 |
| 가교 skin의 취성/균열 | 습건 사이클 후 crossover 급증 | 가교도 상한 10 mol%, 굽힘시험 추가 |
| ZrO₂ 응집 | L2 표면조도, 국부 저항 | 분산 초음파 에너지·점도 기록, 여과 |
| carbon 제거로 L2–촉매층 전자접촉 저하 | HFR 상승 | interposer Zone-R가 접촉 담당; 압축 DOE와 결합 |
| 공정 pass 증가(4 pass)로 수율 하락 | lot 변동성 | slot-die multilayer route로 통합 검토 (표 12 연계) |

**최종 원칙(통합보고서와 동일).** 본 레시피는 고정된 정답이 아니라 검증 가능한 가설이다. "달성", "보장" 표현은 [M] 데이터와 실패경계·covariance가 확보된 뒤에만 사용한다.
