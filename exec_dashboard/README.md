# ㈜원이엔지 경영 대시보드

직원이 **클라우드 폴더에 '업무 현황' 엑셀을 올리기만 하면** 대표가 한 화면에서 보는 앱.

| 탭 | 보는 것 |
|---|---|
| 🏠 한눈에 보기 | 공사별 현재 단계·진척도·다음 일정·인도 D-day, 앞으로 30일 일정, **대표 확인 필요** 경보 |
| 🗓️ 공정 일정 | 전체 공사 간트(설계→외주 발주·납품→설치·시운전→인도), 기준일선 |
| 🏭 외주 진척 | 공사 × (서포트·하우징·장비·보온재/설치) 발주/제작/납품 현황판, 업체별 물량, 업체 리스크 |
| 💰 수주·수금 | 수주액·수금률·미수금·연체, 공사별 수주 대비 수금, 월별 자금 흐름(수금 vs 외주 지급) |
| 🔁 변경 이력 | 직원이 새로 올린 버전과 이전 버전 비교 → **늦춰진 일정** 자동 표시 |
| 🩺 데이터 점검 | 엑셀 오기·시트 간 불일치 자동 탐지 (예: 승인도 연도 25↔26 오타) |

## 1. 실행

```bash
pip install -r exec_dashboard/requirements.txt
cd exec_dashboard && streamlit run app.py
```

## 2. 클라우드 폴더 연결 (택 1)

### A. 동기화 폴더 — 가장 쉬움 (대표 PC/사무실 PC에서 실행)
1. 구글 드라이브(데스크톱용)·원드라이브·드롭박스·시놀로지 NAS 중 하나로 공유 폴더 `업무현황`을 만든다.
2. 직원은 그 폴더에 엑셀을 올린다 (덮어쓰기·새 파일 모두 OK).
3. 대시보드 왼쪽 **폴더 경로**에 PC의 동기화 경로를 넣는다. 예) `G:\내 드라이브\업무현황`, `~/Library/CloudStorage/GoogleDrive-.../업무현황`
   - 매번 입력하기 싫으면 환경변수 `WATCH_DIR` 또는 `.streamlit/secrets.toml` 에 `WATCH_DIR = "..."`.
4. 기본 5분마다 새 파일을 확인해 자동 갱신된다.

### B. Google Drive API — 서버/Streamlit Cloud에 올려 휴대폰으로 볼 때
1. Google Cloud 콘솔 → 서비스 계정 생성 → JSON 키 다운로드, Drive API 사용 설정.
2. 드라이브의 `업무현황` 폴더를 서비스 계정 이메일(`...@...iam.gserviceaccount.com`)에 **뷰어**로 공유.
3. `exec_dashboard/.streamlit/secrets.toml` (git 제외됨):
   ```toml
   GDRIVE_FOLDER_ID = "폴더 URL의 folders/ 뒤 문자열"
   GDRIVE_SERVICE_ACCOUNT = '''{ JSON 키 내용 전체 }'''
   ```
4. 사이드바에 "Google Drive 폴더"가 자동으로 나타난다. 구글 스프레드시트로 올려도 읽는다.

> 외부 공개 배포 시에는 Streamlit Cloud의 **viewer 제한(이메일 허용 목록)** 을 반드시 켤 것 — 금액·업체 연락처가 들어 있음.

## 3. 엑셀 규칙

- 현재 쓰는 `업무 현황 / 도면 현황 / 발주업체 현황과 특성` 양식을 **그대로** 읽는다. 양식을 바꿀 필요 없음.
- **수주금액·수금일은 현재 엑셀에 없다.** 앱의 💰 탭에서 `수주수금_입력양식.xlsx`(공사명 자동 기입)를 받아
  `수주 / 수금 / 외주비` 시트를 채워 같은 폴더에 올리면 된다. 금액은 `125000000`, `1.2억`, `3,500만원` 모두 인식.
- 엑셀엔 계획/실적 구분이 없으므로 **기준일 이전 날짜는 완료로 간주**한다 (기준일은 사이드바에서 변경).
- 진척도(%)는 마일스톤 가중치 합 — `core/config.py` 의 `MILESTONES` 에서 조정.

## 4. 구조

```
exec_dashboard/
  app.py                 Streamlit 화면
  core/dates.py          '25.07.03', '26.11', '26.02.16 ~ 26.07.11' 등 날짜 해석
  core/parser.py         엑셀 → 공사·마일스톤·업체·금액 데이터 + 오류 탐지
  core/analytics.py      진척도·단계·위험도·외주 현황·자금 계산, 버전 비교
  core/sources.py        동기화 폴더 / Google Drive 읽기
  core/history.py        업로드 버전별 요약 저장(.history/)
  core/template.py       수주·수금·외주비 입력 양식 생성
  core/config.py         업무 규칙 (가중치, 라벨, 고객사, 경보 기준)
  scripts/check_report.py  터미널 요약·점검·양식 생성
.claude/skills/wonieng-report-ingest/   Claude용 스킬: 엑셀 요약·양식 변경 대응
.claude/agents/report-auditor.md        Claude용 에이전트: 엑셀 오류 → 직원 정정 요청문
```
