#!/usr/bin/env bash
# KIPRIS 특허 검색 MCP(chrisryugj/korean-patent-mcp)를 검토한 커밋으로 고정해 설치한다.
#
# 주의: npm 레지스트리의 "korean-patent-mcp" 는 다른 사람이 만든 별개 패키지다.
#       npx/npm install 로 설치하지 말고 이 스크립트로 GitHub 원본을 받는다.
#
# 사용: bash tools/mcp/setup_korean_patent_mcp.sh
# 결과: ~/.seion-mcp/korean-patent-mcp/build/index.js  (.mcp.json 이 이 경로를 쓴다)
set -euo pipefail

REPO="https://github.com/chrisryugj/korean-patent-mcp.git"
COMMIT="f9e042e568c1aa26d1578d200c5c8ee7e58d6204"   # 2026-11-17, v0.2.3 — README·소스 검토한 판
DEST="${HOME}/.seion-mcp/korean-patent-mcp"

command -v git  >/dev/null || { echo "git 이 필요합니다."; exit 1; }
command -v node >/dev/null || { echo "Node.js 18 이상이 필요합니다 (https://nodejs.org)."; exit 1; }

if [ ! -d "$DEST/.git" ]; then
  mkdir -p "$(dirname "$DEST")"
  git clone --quiet "$REPO" "$DEST"
fi
cd "$DEST"
git fetch --quiet origin
git checkout --quiet --detach "$COMMIT"

# 의존성 설치 스크립트(postinstall 등)는 실행하지 않는다.
npm ci --ignore-scripts --no-audit --no-fund
npm run build

echo
echo "설치 완료: $DEST/build/index.js (커밋 ${COMMIT:0:7})"
if [ -z "${KIPRIS_KEY:-}" ]; then
  echo "다음 단계: KIPRIS Plus 키를 환경변수 KIPRIS_KEY 로 설정하세요 (docs/kipris-setup.md 참고)."
fi
