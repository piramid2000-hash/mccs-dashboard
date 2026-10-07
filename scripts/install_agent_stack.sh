#!/usr/bin/env bash
# 세이온연구소 AI 에이전트 도구 스택 설치 (macOS / Linux)
# 사용법: bash scripts/install_agent_stack.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "🧪 [1/3] 시스템 도구 (Pandoc, Typst, Tesseract 한국어+영어)"
if [[ "$(uname)" == "Darwin" ]]; then
  command -v brew >/dev/null || { echo "Homebrew가 필요합니다: https://brew.sh"; exit 1; }
  brew install pandoc typst tesseract tesseract-lang
else
  sudo_cmd=""; [[ $EUID -ne 0 ]] && sudo_cmd="sudo"
  $sudo_cmd apt-get update -qq
  $sudo_cmd apt-get install -y -qq pandoc tesseract-ocr tesseract-ocr-kor
fi

echo "🐍 [2/3] Python 가상환경 (.venv-agents)"
python3 -m venv .venv-agents
.venv-agents/bin/pip install -q --upgrade pip setuptools wheel
.venv-agents/bin/pip install -q -r requirements-agents.txt

echo "✅ [3/3] 설치 확인"
.venv-agents/bin/python - <<'PY'
import importlib
mods = ["arxiv","semanticscholar","pymatgen.core","rdkit","ase","impedance",
        "pdfplumber","pymupdf","pytesseract","chromadb","fastmcp","typst","pypandoc"]
bad = []
for m in mods:
    try: importlib.import_module(m)
    except Exception as e: bad.append(f"{m}: {e}")
print("모든 모듈 정상" if not bad else "실패:\n" + "\n".join(bad))
PY
tesseract --list-langs 2>/dev/null | grep -q kor && echo "Tesseract 한국어 OK" || echo "⚠️ Tesseract 한국어 데이터 없음"
