---
name: seion-matcalc
description: "세이온 소재 계산을 실제로 실행하는 도구 사용법. seion-materials-check 로 조성·배합 환산(질량%↔몰%), 산화물 기준 조성, CIF 이론 밀도·공간군, 혼합칙 범위, Materials Project 안정성을 계산할 때 이 저장소의 tools/materials/seion_matcalc.py 를 먼저 쓴다. 트리거 - \"조성 계산\", \"산화물 조성\", \"배합비 환산\", \"이론 밀도\", \"CIF\", \"공간군\", \"혼합칙\", \"hull\", 일라이트·점토·세라믹·전고체 전해질 조성 점검."
---

# 세이온 소재 계산 실행 (seion-materials-check 의 실행 도구)

원칙·보고 형식은 **seion-materials-check** 를 따른다. 이 스킬은 "어떻게 실행하나"만 정한다.
즉석 코드 대신 검증된 스크립트를 실행하고, **출력 JSON 을 그대로 재현 자료로 보관**한다.

## 1. 준비 (세션마다 1회)
이 컨테이너의 시스템 Python 에서는 pymatgen 의존성 빌드가 실패하므로 전용 가상환경을 쓴다.
```bash
test -x ~/.seion-venv/bin/python || { python3 -m venv ~/.seion-venv && ~/.seion-venv/bin/pip install -q -r tools/materials/requirements.txt; }
PY=~/.seion-venv/bin/python
$PY -m pytest -q -p no:cacheprovider tools/materials   # 9개 통과해야 계산 시작
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
