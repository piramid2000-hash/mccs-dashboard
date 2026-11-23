# 원이엔지 경영 — 안드로이드 앱 / 구글 플레이 등록 가이드

웹앱(https://piramid2000-hash.github.io/mccs-dashboard/)을 구글 공식 방식인 **TWA(Trusted Web Activity)** 로 감싼
안드로이드 앱입니다. 화면·기능·자료는 웹앱과 같고, 크롬 엔진으로 주소창 없이 전체 화면으로 열립니다.
웹앱을 고치면 앱은 다시 올리지 않아도 바로 바뀝니다. 앱 껍데기(아이콘·이름·패키지)를 바꿀 때만 새 버전을 올립니다.

| 항목 | 값 |
|---|---|
| 패키지 | `kr.co.oneeng.ceo` |
| 최소/대상 안드로이드 | 7.0 (API 24) / 16 (API 36) |
| 빌드 | GitHub Actions `안드로이드 앱 빌드` (`.github/workflows/android.yml`) |
| 등록 자료 | `play/` (설명문·아이콘·그래픽·스크린샷·정책 답변), 개인정보처리방침은 웹앱 `privacy.html` |

---

## 0. 어떤 방식으로 올릴까 (먼저 결정)

| 방식 | 누가 받나 | 심사·조건 | 추천 |
|---|---|---|---|
| **내부 테스트** | 등록한 이메일 최대 100명 (대표·임원) | 개발자 계정만 있으면 바로. 테스터 링크로 플레이 스토어에서 설치·자동 업데이트 | ✅ 사내 전용이면 이것으로 충분 |
| 비공개 테스트 → 프로덕션 | 누구나 검색·설치 | 2023.11 이후 만든 **개인** 계정은 테스터 12명 이상이 14일간 비공개 테스트를 거쳐야 프로덕션 신청 가능. **회사(조직) 계정**은 이 조건 없음 | 외부 공개가 필요할 때 |

> 회사 이름으로 올리려면 **조직 계정**(D-U-N-S 번호 필요, 무료 발급 1~2주)이 좋습니다. 개발자 등록비 US$25 (1회).

## 1. GitHub 에 서명 키 등록 (5분)

전달받은 `업로드키_보관용.txt` 를 열고, 저장소 **Settings → Secrets and variables → Actions → New repository secret** 으로 추가:

| 이름 | 값 |
|---|---|
| `ANDROID_KEYSTORE_BASE64` | `upload-keystore.base64.txt` 내용 전체 |
| `ANDROID_KEYSTORE_PASSWORD` | 보관용 파일의 키 비밀번호 |
| `ANDROID_KEY_ALIAS` | `upload` |
| `DEMO_PASSWORD` | 구글 심사용 비밀번호 (대표 비밀번호와 **다르게**, 예시 자료만 열림) |

`upload-keystore.jks` 와 보관용 파일은 회사 금고/USB 등 **오프라인 2곳**에 보관하세요. 저장소에는 올리지 않습니다.

## 2. 앱 파일 만들기 (클릭 3번)
1. **Actions → 매일 업데이트 → Run workflow** (DEMO_PASSWORD 를 반영해 심사용 예시 자료 생성)
2. **Actions → 안드로이드 앱 빌드 → Run workflow** (표시 버전 `1.0.0`)
3. 끝나면 실행 화면 아래 **Artifacts** 에서 `wonieng-android-1.0.0` 내려받기 → 안에 `app-release.aab`(플레이 업로드용), `app-release.apk`(휴대폰 직접 설치 시험용)

## 3. Play Console 등록 (30~40분)
play.google.com/console → **앱 만들기**
1. 앱 이름 `원이엔지 경영`, 기본 언어 한국어, 앱, 무료 → 선언 체크 → 만들기
2. **대시보드 → 앱 설정** 의 항목을 `play/store-listing.md` 의 답대로 채움
   (개인정보처리방침 URL, 앱 액세스(심사용 비밀번호), 광고 없음, 콘텐츠 등급, 타겟층 18+, 데이터 보안 '수집 안 함', 금융 기능 없음)
3. **기본 스토어 등록정보**: 간단한/자세한 설명, 아이콘 `play/icon-512.png`, 그래픽 `play/feature-graphic-1024x500.png`, 스크린샷 `play/screenshots/1~5`
4. **테스트 → 내부 테스트 → 테스터** 탭: 이메일 목록 만들기(대표·임원 구글 계정) → 저장
5. **새 버전 만들기** → 'Play 앱 서명' 사용(기본값 그대로 동의) → `app-release.aab` 업로드 → 출시 노트 `첫 버전` → 검토 → **내부 테스트로 출시**
6. 테스터 탭의 **참여 링크**를 대표 휴대폰으로 보내 → 링크 열기 → '테스터 되기' → 플레이 스토어에서 **설치**

## 4. 주소창 없애기 — 소유 증명 파일 올리기 (10분, 꼭 필요)
앱과 웹 주소가 같은 주인임을 증명해야 크롬 주소창 없이 앱처럼 열립니다. (안 하면 위쪽에 주소 표시줄이 보임)
1. Play Console → **테스트 및 출시 → 앱 무결성 → 앱 서명** → **앱 서명 키 인증서의 SHA-256** 복사
2. `play/user-site/.well-known/assetlinks.json` 의 `여기에_Play_Console_앱서명키_SHA256_지문을_붙여넣기` 를 그 값으로 바꿈
   (첫 번째 값은 업로드 키 지문으로 이미 들어 있음)
3. GitHub 에서 새 저장소 **`piramid2000-hash.github.io`** (이름 정확히, Public) 만들기 →
   `play/user-site/` 안의 `.well-known/assetlinks.json`, `.nojekyll`, `index.html` 을 그대로 올리기
4. 그 저장소 Settings → Pages → Source: **Deploy from a branch**, Branch: `main` / root → 저장
5. 1~2분 뒤 https://piramid2000-hash.github.io/.well-known/assetlinks.json 이 열리면 완료.
   앱을 한 번 지웠다 다시 설치하면 주소창 없이 열립니다.

## 5. 새 버전 올리기
아이콘·이름 등 앱 껍데기를 바꿨을 때만: Actions → 안드로이드 앱 빌드 → Run workflow (버전 `1.0.1` 등) →
Play Console 내부 테스트 → 새 버전 만들기 → .aab 업로드. 내부 버전 번호는 실행 번호로 자동 증가합니다.
(공사·금액 자료와 화면 개선은 웹앱이 매일 자동 갱신되므로 새 버전이 필요 없습니다.)

## 파일 구성
```
android/
  app/build.gradle              앱 이름·주소·색·버전·서명 설정
  app/src/main/AndroidManifest.xml   TWA 실행 화면, 주소 연결, 크롬 없을 때 웹뷰 대체
  app/src/main/res/             런처 아이콘(적응형 포함), 스플래시
  tools/make_assets.py          아이콘·그래픽 다시 그리기
  play/                         스토어 등록 자료, assetlinks.json
```
