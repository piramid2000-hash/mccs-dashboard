# 출처 (외부 스킬 반입 기록)

- 원본: https://github.com/djfksjd/patent-search-skill  (`skills/patent-search/`)
- 고정 커밋: `6d238d4bf351863a5343d686dc5cdff71dbc1395` (2026-07-30)
- 라이선스: MIT (같은 폴더 `LICENSE`)
- 반입일: 2026-11-26 — 원본과 파일 동일(LICENSE·이 파일만 추가)

## 반입 전 확인한 것
- 스크립트는 Python 표준 라이브러리만 사용, 외부 패키지 없음.
- 네트워크 접속 대상: `plus.kipris.or.kr`, `patents.google.com` 뿐.
- `subprocess`·`eval`·`exec`·파일 삭제 등 위험 호출 없음.
- 키(`KIPRIS_KEY`)는 환경변수 또는 이 폴더의 `.env` 에서 읽고, 로그·오류에 마스킹, 리다이렉트로 키가 새지 않게 차단.
- SKILL.md 에 **첫 외부 검색 전 검색어 승인(STOP GATE)** 과 "발명 상세·수치는 검색어에 넣지 않음" 규칙이 있음 — 출원 전 기밀 보호에 맞음.

## 업데이트할 때
원본 새 커밋을 다시 검토한 뒤 폴더를 통째로 교체하고 위 커밋·날짜를 갱신한다.
세이온 쪽 수정이 필요하면 SKILL.md 를 직접 고치지 말고 `seion-prior-art` 스킬에서 이 스킬을 불러 쓰는 방식을 권장한다(업데이트 충돌 방지).
