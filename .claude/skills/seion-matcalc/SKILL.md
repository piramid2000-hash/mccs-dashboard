---
name: seion-matcalc
description: "세이온 소재·이론·실험·3D 프린팅 계산을 실제로 실행하는 도구 사용법. 결정 MLIP 이완·포논·열팽창·이온확산 MD(seion_crystal), XRD·Raman 피크·상 대조·임피던스·아레니우스(seion_expdata), 자이로이드 메타물질 페이스트 DIW 레올로지·적층·오버행·수축·다목적 최적화·STL(seion_gyroid), SEM·CT 기공·굴곡도·베이지안 실험설계(seion_micro) 포함. 조성·배합 환산(질량%↔몰%), 산화물 기준 조성, CIF 이론 밀도·공간군, 혼합칙, Materials Project 안정성(seion_matcalc.py)과 병진운동·통계열역학(분배함수·Sackur–Tetrode·분자속도·평균자유행로), 분자 오비탈·양자화학(PySCF HF/DFT, HOMO-LUMO, 전하, 쌍극자), 진동수 기반 엔트로피·엔탈피·자유에너지, 기체 화학평형·단열화염온도(Cantera)(seion_theory.py)를 계산할 때 사용. 트리거 - \"조성 계산\", \"산화물 조성\", \"이론 밀도\", \"CIF\", \"혼합칙\", \"병진\", \"분배함수\", \"엔트로피 계산\", \"오비탈\", \"HOMO LUMO\", \"밴드갭 추정\", \"양자화학\", \"DFT\", \"진동수\", \"화학평형\", \"화염온도\"."
---

# 세이온 소재 계산 실행 (seion-materials-check 의 실행 도구)

원칙·보고 형식은 **seion-materials-check** 를 따른다. 이 스킬은 "어떻게 실행하나"만 정한다.
즉석 코드 대신 검증된 스크립트를 실행하고, **출력 JSON 을 그대로 재현 자료로 보관**한다.

## 1. 준비 (세션마다 1회)
이 컨테이너의 시스템 Python 에서는 pymatgen 의존성 빌드가 실패하므로 전용 가상환경을 쓴다.
```bash
test -x ~/.seion-venv/bin/python || { python3 -m venv ~/.seion-venv && ~/.seion-venv/bin/pip install -q -r tools/materials/requirements.txt; }
PY=~/.seion-venv/bin/python
$PY -m pytest -q -p no:cacheprovider tools/materials   # 41개 통과해야 계산 시작 (~1분)
```
설치나 테스트가 실패하면 계산값을 내지 말고 그 사실을 보고한다.

## 2. 명령
| 하려는 것 | 명령 |
|---|---|
| 화학식 → 분자량·원소 wt%·**산화물 기준 wt%** | `$PY tools/materials/seion_matcalc.py formula "K0.65Al2.65Si3.35O10(OH)2"` |
| 산화물 기준 바꾸기(예: Fe²⁺) | `... formula "<식>" --oxide Fe=FeO` |
| 배합 질량% → 몰% (또는 반대) | `... convert --basis wt --to mol "SiO2=60,Al2O3=25,K2O=15"` |
| CIF → 격자·Z·이론 밀도·공간군 | `... cif <파일.cif>` |
| 혼합칙 밀도·물성 상하한 | `... mix --basis wt "석영:frac=0.7,rho=2.65,prop=7.7" "수지:frac=0.3,rho=1.2,prop=0.2"` |
| Materials Project 안정성 | `... hull Li-P-S-Cl` (키 `MP_API_KEY` + `pip install mp-api` 필요) |

## 2-1. 이론 계산 명령 (`tools/materials/seion_theory.py`)
분자 입력은 ASE G2 이름(H2O, CO2, CH4, NH3, C6H6 …) 또는 `.xyz` 파일.

| 이론 | 하려는 것 | 명령 |
|---|---|---|
| 병진(기체분자운동·통계역학) | 병진 분배함수, Sackur–Tetrode S, 평균·rms·최빈 속도, 평균자유행로 | `$PY tools/materials/seion_theory.py trans N2 --T 298.15 --P 101325 --diameter 3.7` |
| 오비탈 | 오비탈 에너지, HOMO·LUMO·갭, Mulliken 전하, 쌍극자 | `... mo H2O --method b3lyp --basis def2-svp` |
| 양자 + 통계열역학 | 구조 최적화 → 진동수 → 병진·회전·진동별 S, ZPE, H, G | `... thermo H2O --method hf --basis 6-31g* --T 298.15` |
| 열역학(기체 평형) | T·P 평형 조성, 단열화염온도 | `... equil --X "CH4:1,O2:2,N2:7.52" --mode HP --T 300` |

검증 기준(테스트에 고정): Ar 엔트로피 154.85 (NIST 154.846), H₂O 총 엔트로피 188.3 (NIST 188.84), H₂O 쌍극자 ≈1.99 D(실측 1.85), CH₄–공기 단열화염온도 2225 K.

이론 계산 해석 주의
- `mo` 의 HOMO-LUMO 갭은 **분자** 오비탈 갭이다. 고체 밴드갭·광학 갭과 같다고 쓰지 않는다(HF 과대, DFT 과소).
- `thermo` 에서 `imaginary_modes > 0` 이면 극소점이 아니므로 열역학 값을 쓰지 않는다. HF 진동수는 실측보다 ~10% 높다(보정계수 미적용) — 비교 시 명시.
- `thermo`·`mo` 는 원자 수십 개까지가 현실적이다. 결정(주기계) 전자구조·밴드는 이 도구 범위 밖 — 필요하면 GPAW/Quantum ESPRESSO 별도 검토.
- `equil` 은 기체상만. 소성·세라믹 고상 평형은 pycalphad(TDB) 로.

## 2-2. 결정·실험·3D 프린팅·미세조직 도구

| 묶음 | 도구 | 명령 | 하는 일 |
|---|---|---|---|
| A 결정 | `seion_crystal.py` | `relax` `phonon` `qha` `md` | MLIP(MACE-MP, 기본) 구조 이완, 포논·열용량, **준조화 열팽창**, 이온 확산 MD |
| B 실험 | `seion_expdata.py` | `peaks` `xrdmatch` `eis` `arrhenius` | XRD·Raman 피크 피팅·Scherrer, CIF 상 후보 순위, 임피던스 등가회로·이온전도도, 활성화에너지 |
| C 프린팅 | `seion_gyroid.py` (+ `gyroid_seion_config.json`) | `rheo` `paste` `evaluate` `optimize` `stl` | 일라이트·알지네이트·C38H78O 페이스트 자이로이드 DIW: 레올로지 피팅, 압출압력, 적층 높이, 오버행, 수축 보정, NSGA-II 최적화, 출력용 STL |
| D 미세조직·설계 | `seion_micro.py` (+ `doe_space_paste.json`) | `pores` `doe suggest/status` | SEM·CT 기공률·기공 크기·관통성·굴곡도, 실험 기록 기반 다음 배합 제안(베이지안) |

해석 주의 (검증에서 확인된 한계)
- **A**: CHGNet 은 변형에 대한 퍼텐셜면이 매끄럽지 않아 포논·QHA 에 쓰지 않는다(도구가 막음). MACE 검증: Al·MgO 상온 열팽창·체적탄성률은 실측 ±20 % 안, **Si 열팽창은 4배 과대**(공유결합·음의 열팽창 물질 신뢰 낮음). 고온에서 `unphysical_trend_at_T` 가 나오면 그 온도 결과 폐기.
- **C**: 설정의 '가정' 값이 결과를 좌우한다 — 출력 `assumptions_in_config` 를 보고서에 그대로 옮긴다. 자이로이드 오버행 분포는 형상과 무관(45° 초과 ≈11.7 %). 기본 가정(τ0 300 Pa)으로는 30 mm 부품 적층 불가 — 필요 항복응력을 출력. 설계 노트: `docs/gyroid-diw-design.md`.
- **D**: 2D SEM 기공 크기는 단면 지름(3D 보다 작음). 이진화 임계값 ±5 % 민감도 함께 보고.

## 3. 출력 읽는 법 — 보고서에 반드시 옮길 것
- `oxygen_in_formula` ≠ `oxygen_implied_by_oxides` → 산화수 가정이 다르다. 숨기지 말고 적는다.
- `space_group_consistent: false` → symprec 에 따라 공간군이 달라짐. 세 값 모두 보고.
- `partial_occupancy_sites`, `read_warnings` 가 비어 있지 않으면 그대로 보고.
- `convert` / `mix` 의 `warnings`(분율 합 불일치) → 임의 정규화 금지, 사용자 확인.
- `mix` 는 단일 값이 아니라 **상한(Voigt)–하한(Reuss) 범위**로만 쓴다.
- 모든 값의 등급은 출력의 `grade`(P0) 그대로. E1 로 쓰지 않는다.

## 4. 재현 자료
보고서 부록에 출력 JSON 전체(`command`, `versions` 포함)를 붙인다. seion-rnd-plan 부록 A, seion-patent-spec 데이터 등급표에 그대로 들어간다.

## 5. 이 도구로 못 하는 것
상평형(pycalphad)은 데이터베이스(TDB)가 소재마다 달라 스크립트화하지 않았다. seion-materials-check 4단계 절차대로 TDB 출처·유효 범위를 먼저 확인하고 개별 스크립트로 계산한다.
