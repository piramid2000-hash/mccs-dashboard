---
name: wonieng-report-ingest
description: ㈜원이엔지 '업무 현황' 엑셀(공사별 승인도·발주·납품·설치·인도 일정, 발주업체 시트, 수주·수금·외주비 시트)을 읽어 대표 보고용 요약을 만들거나, 엑셀 양식이 바뀌어 대시보드(exec_dashboard)가 못 읽을 때 파서를 고칠 때 사용. 트리거 - "업무현황 엑셀 올렸어", "이번 주 현황 요약", "대시보드에 안 나와", "수주수금 양식 만들어줘", "엑셀 점검해줘".
---

# 원이엔지 업무현황 엑셀 → 대표 대시보드

대시보드 코드: `exec_dashboard/` (Streamlit). 파싱 규칙은 대시보드와 이 스킬이 **같은 코드**(`exec_dashboard/core`)를 쓴다. 따로 해석하지 말 것.

## 1. 새 엑셀이 들어왔을 때 (요약·점검)

```bash
python exec_dashboard/scripts/check_report.py <엑셀 또는 폴더> --asof $(date +%F)
python exec_dashboard/scripts/check_report.py <엑셀 또는 폴더> --json   # 수치가 필요하면
```

대표에게는 아래 순서로 5~10줄로 보고한다 (표 덤프 금지):
1. 한 줄 결론: 진행 N건 / 위험 N / 주의 N, 이번 달 인도 예정
2. 위험·주의 공사와 사유 (스크립트 `flagged`)
3. 30일 내 인도·수금 예정
4. 수주·수금: 총 수주, 수금률, 연체 건 (금액 시트가 없으면 "미입력"이라고 명시 — **금액을 추정하거나 지어내지 말 것**)
5. 데이터 점검(`warnings`) 중 `check`/`warn` 항목 → "직원 확인 필요"로 전달

## 1-1. 카톡 공유용 HTML
```bash
python exec_dashboard/scripts/export_html.py <엑셀 또는 폴더> -o 업무현황_YYMMDD.html
```
연락처는 자동 제외. 만든 파일을 사용자에게 보내고 '카톡 파일 보내기'로 공유하라고 안내.

## 2. 날짜 해석 규칙 (core/dates.py)
- `25.07.03` 일 단위, `26.11`·숫자 `27.02` 월 단위(월말로 간주), 숫자 `27.1` = 27년 10월
- `26.02.16 ~ 26.07.11` 기간, `~ 26.10.31` 종료만
- 칸 안 `라벨 : 날짜` 줄 단위 (`장비 : 25.12.08`). 라벨→마일스톤 매핑은 `core/config.py`의 `LABEL_MAP`
- 계획일과 실적일 구분이 엑셀에 없으므로 **기준일 이전 날짜 = 완료**로 간주한다. 보고할 때 이 전제를 밝힌다.

## 3. 엑셀 양식이 바뀌어 못 읽을 때
1. `check_report.py` 의 error/warn 메시지로 어느 시트·열인지 확인
2. 새 라벨(예: '배관') → `config.py` `LABEL_MAP`/`MILESTONES`/`WORK_PACKAGES` 에 추가
3. 새 고객사 → `CLIENT_RULES`, 새 외주업체 분류 → `VENDOR_CATEGORY_RULES`
4. 머리글 탐지가 깨지면 `parser._parse_status_sheet` 의 `col_kind` 판별만 수정
5. 수정 후 원본 엑셀로 다시 `check_report.py` 실행해 공사 수·마일스톤이 이전과 같은지 확인

## 4. 수주·수금 양식
```bash
python exec_dashboard/scripts/check_report.py <업무현황.xlsx> --make-template 수주수금_입력양식.xlsx
```
공사명이 자동 기입된 `수주 / 수금 / 외주비` 시트가 생긴다. 업무현황 파일에 시트로 붙이거나 별도 파일로 같은 폴더에 올리면 대시보드가 합쳐 읽는다.

## 주의
- 엑셀의 외주업체 연락처(전화·메일)는 개인정보다. 요약·커밋·외부 전송에 넣지 말 것. `exec_dashboard/inbox/` 는 git 제외.
- 엑셀 원본은 수정하지 않는다. 오류는 직원에게 고치도록 알린다 (`report-auditor` 에이전트가 메시지 초안 작성).
