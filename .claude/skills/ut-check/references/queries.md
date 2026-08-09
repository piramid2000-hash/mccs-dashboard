# UT별 반증 질의 시드

각 UT마다 **반증 방향**(가설을 죽이는 검색어)을 우선 배치했다. 지지 문헌 검색어는 대조용이다.
V4.1 운전창과 비교할 조건을 함께 적어, 문헌 결과를 그대로 적용하지 않도록 한다.

---

## UT-00 — 탄소·이온·물 수지 폐합 ≥95%

**반증 방향**: 폐루프 전해에서 수지가 닫히지 않은 보고, makeup 요구량이 큰 사례
- `carbon balance closure CO2 electrolysis bicarbonate`
- `electrolyte makeup rate closed loop electrolyzer water management`
- `nitrogen balance ammonia capture solution electrolysis loss`
- `unaccounted carbon products formate crossover mass balance`

**대조 조건**: 우리는 NH₄HCO₃ 1.5–2.5 M · 40 °C · 폐루프 환류. 개방계 실험의 수지는 참고치일 뿐.

---

## UT-01 — AOR 극저전압 (1.0–1.2 V)

**반증 방향**: AOR 결합 셀의 실제 전압 페널티, NH₃ 소모·N₂ 선택도 문제
- `ammonia oxidation reaction anode cell voltage electrolyzer penalty`
- `AOR overpotential nickel catalyst deactivation nitrite nitrate byproduct`
- `ammonia oxidation N2 selectivity vs NOx formation electrode`
- `CO2 electrolysis full cell voltage breakdown iR membrane overpotential`

**지지 방향(대조)**: `ammonia assisted electrolysis low cell voltage hydrogen`

**대조 조건**: Base는 ≤3.5 V로 이미 성립. 이 UT는 **업사이드 전용**이므로 기각되어도
사업이 무너지지 않는다 — 판정 시 이 점을 반드시 서술한다.

---

## UT-02 — Interposer(삽입층) 두께 최적창

**반증 방향**: 두꺼운 다공층의 ASR 페널티가 SPC 이득을 상쇄한 보고
- `porous spacer interposer thickness ohmic resistance CO2 electrolyzer`
- `catalyst layer membrane gap effect single pass conversion penalty`
- `McMullin number tortuosity porosity ionic resistance separator`
- `local pH gradient thickness bicarbonate CO2 regeneration electrode`

**대조 조건**: V2는 20–50 μm, Offshore 덱은 130–270 μm. 두 주장이 충돌 중이므로
문헌의 두께 조건을 반드시 함께 기록한다.

---

## UT-03 — 신규 양이온 쿠폰 내구성

**반증 방향**: 알칼리 안정성 주장의 재현 실패, 가속시험과 실셀 수명의 괴리
- `anion exchange membrane alkaline stability discrepancy accelerated test`
- `piperidinium degradation hydroxide 80C ring opening`
- `phosphonium sulfonium AEM stability comparison hydroxide attack`
- `ex-situ soak vs in-situ cell durability anion exchange membrane`

**대조 조건**: soak(침지) 데이터는 화학 안정성만 증명한다. UT-07과 반드시 함께 판정.

---

## UT-04 — AEB 동적제어 > 정상상태

**반증 방향**: 펄스 전해가 이득이 없거나 열화를 가속한 보고
- `pulsed electrolysis CO2 reduction selectivity no improvement`
- `dynamic operation electrolyzer degradation acceleration cycling`
- `intermittent operation membrane electrode assembly lifetime penalty`
- `current interruption salt precipitation recovery gas diffusion electrode`

**대조 조건**: 고정 펄스(100/20 ms)와 상태연동 적응 펄스는 다른 주장이다. 어느 쪽을
검증한 문헌인지 구분한다.

---

## UT-05 — C2+ 다탄소 선택도 (Offshore)

**반증 방향**: 중탄산염·저농도 CO₂ 환경에서 C2+ 선택도가 붕괴한 보고
- `bicarbonate electrolysis ethylene selectivity low copper`
- `C2+ Faradaic efficiency single pass conversion tradeoff copper catalyst`
- `copper catalyst reconstruction degradation carbonate electrolyte`
- `ethylene separation energy penalty electrolyzer downstream`

**대조 조건**: 순수 CO₂ 기상 공급 실험의 C2+ 수치를 포집액 직접전환에 적용하지 않는다.

---

## UT-06 — Closed Loop 실현성 (폐수·유실)

**반증 방향**: 순환 운전에서 불순물 축적으로 blowdown이 불가피했던 사례
- `impurity accumulation recirculating electrolyte sulfate purge`
- `ammonia slip recovery scrubber efficiency capture solution`
- `salt accumulation bleed stream electrolyzer long term operation`

**대조 조건**: 절대치("0%")는 문헌으로도 우리 실험으로도 증명 불가. 구간 추정치로 서술.

---

## UT-07 — 코발토세늄 음극 분극 안정성 ★ 최우선

**반증 방향**: 코발토세늄의 **산화환원 활성**이 음극 전위에서 문제를 일으킨 보고
- `cobaltocenium reduction potential cathodic stability polymer`
- `metallocene cation redox active membrane electrolysis degradation`
- `Co(III)/Co(II) couple demetalation ionomer cathode potential`
- `permethyl cobaltocenium hydroxide stability limitation`

**대조 조건**: 제시된 근거는 1M KOH·140 °C **soak**뿐이다. 음극 분극(−0.5 ~ −1.2 V vs RHE)
하 데이터가 문헌에 있는지가 이 조사의 핵심 질문이다. 없으면 "데이터 부족 → 실험이 유일한 판별".

---

## UT-08 — 자율 pH 스윙 수지

**반증 방향**: BPM 없이 국부 산성층이 유지되지 않는다는 물리·실험적 근거
- `local acidification without bipolar membrane bicarbonate electrolyzer`
- `proton source cathode bicarbonate CO2 regeneration in situ`
- `pH gradient porous layer buffer capacity neutralization electrolysis`
- `bipolar membrane water dissociation voltage penalty CO2 electrolysis`

**대조 조건**: "pH 2–4 자율 유지"는 H⁺ 공급원이 명시되지 않은 주장이다. 공급원을 밝힌
문헌이 있는지, 아니면 전부 BPM 구동인지가 판별 기준.

---

## UT-09 — C2+ 제품 체인 경제성 (Offshore)

**반증 방향**: 분리·저장·하역 페널티가 제품 가치를 넘어선 분석
- `techno-economic analysis CO2 electrolysis ethylene separation cost`
- `syngas product separation energy penalty offshore platform`
- `FPSO chemical production logistics offloading feasibility`

**대조 조건**: 육상 대규모 플랜트 TEA를 해상 10 TPD 규모에 그대로 적용하지 않는다.

---

## 공통 검색 팁

- **연도 필터**: 막·촉매 분야는 최근 3년(`year: "2023-"`)이 우선. 단 반증 목적일 때는
  오래된 부정 결과도 유효하다.
- **저널 필터**: `Journal of Membrane Science`, `ACS Energy Letters`, `Joule`,
  `Nature Energy`, `Journal of Power Sources`, `Electrochimica Acta`
- **인용 추적**: 핵심 논문을 찾으면 `search_semantic_scholar`로 후속 인용을 확인한다.
  재현 실패는 대개 인용 논문에 묻혀 있다.
