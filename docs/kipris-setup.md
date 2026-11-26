# KIPRIS 특허 검색 연결 (세이온연구소 ① 단계)

이 저장소에 두 가지가 들어 있다.

| 구성 | 위치 | 하는 일 |
|---|---|---|
| **patent-search 스킬** | `.claude/skills/patent-search/` | 선행기술조사 리포트 + claim chart + 청구항 차별화 가이드. 검색 전 검색어 승인 단계가 있다. |
| **korean-patent MCP** | `.mcp.json` → `~/.seion-mcp/korean-patent-mcp` | Claude 가 KIPRIS 를 직접 조회하는 도구 7개 (키워드·항목·출원인·권리자 검색, 서지상세, 상표, 디자인). |

둘 다 **같은 키 하나(`KIPRIS_KEY`)** 를 쓴다.

## 1. KIPRIS Plus 키 발급 (무료)
1. https://plus.kipris.or.kr 회원가입
2. 데이터 → 특허·실용신안 정보 **활용신청** (필요하면 상표·디자인도)
3. 마이페이지 → APIKEY 관리 에서 키 복사

## 2. 키 등록 — 채팅창에 붙여넣지 말 것
**macOS / Linux** — `~/.zshrc` 또는 `~/.bashrc` 끝에:
```bash
export KIPRIS_KEY='발급받은키'
```
**Windows (PowerShell)**:
```powershell
[Environment]::SetEnvironmentVariable("KIPRIS_KEY", "발급받은키", "User")
```
등록 후 터미널·Claude 를 다시 시작한다.

## 3. MCP 설치 (대표 PC 에서 1회)
저장소 폴더에서:
```bash
bash tools/mcp/setup_korean_patent_mcp.sh          # macOS / Linux
```
```powershell
powershell -ExecutionPolicy Bypass -File tools\mcp\setup_korean_patent_mcp.ps1   # Windows
```
> npm 의 `korean-patent-mcp` 는 **다른 사람이 만든 같은 이름의 패키지**다. `npx korean-patent-mcp` 로 설치하지 말 것.

## 4. 확인
저장소 폴더에서 Claude Code 실행 → 처음 한 번 "korean-patent MCP 를 허용할까요?" 에 승인 → `/mcp` 에서 `korean-patent` 가 connected 인지 본다.
예: "전고체 전해질 황화물 출원 동향을 KIPRIS 에서 찾아줘"

## 쓸 때 원칙
- 출원 전 발명은 **일반화된 기술 키워드만** 검색어로 쓴다 (스킬이 검색 전 목록을 보여주고 승인을 받는다).
- 공개 원격 서버(`mcp.gomdori.app`)는 쓰지 않는다 — 검색어가 남의 서버를 거친다.
- 결과는 법적 판단이 아니다. 출원 전 변리사 검토 필수.
- 무료 키 한도(월 1,000회 수준)를 넘기지 않도록 큰 조사는 범위(`quick`/`standard`)를 먼저 정한다.
