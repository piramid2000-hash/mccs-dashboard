# KIPRIS 특허 검색 MCP(chrisryugj/korean-patent-mcp) Windows 설치 스크립트.
# 주의: npm 의 "korean-patent-mcp" 는 다른 사람의 별개 패키지 — npx 로 설치하지 말 것.
# 사용: powershell -ExecutionPolicy Bypass -File tools\mcp\setup_korean_patent_mcp.ps1
$ErrorActionPreference = "Stop"

$Repo   = "https://github.com/chrisryugj/korean-patent-mcp.git"
$Commit = "f9e042e568c1aa26d1578d200c5c8ee7e58d6204"   # 2026-11-17, v0.2.3
$Dest   = Join-Path $HOME ".seion-mcp\korean-patent-mcp"

if (-not (Get-Command git  -ErrorAction SilentlyContinue)) { throw "git 이 필요합니다." }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Node.js 18 이상이 필요합니다." }

if (-not (Test-Path (Join-Path $Dest ".git"))) {
  New-Item -ItemType Directory -Force -Path (Split-Path $Dest) | Out-Null
  git clone --quiet $Repo $Dest
}
Set-Location $Dest
git fetch --quiet origin
git checkout --quiet --detach $Commit
npm ci --ignore-scripts --no-audit --no-fund
npm run build

Write-Host ""
Write-Host "설치 완료: $Dest\build\index.js"
if (-not $env:KIPRIS_KEY) { Write-Host "다음 단계: 환경변수 KIPRIS_KEY 설정 (docs\kipris-setup.md)" }
