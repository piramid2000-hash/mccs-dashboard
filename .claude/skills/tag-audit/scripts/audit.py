#!/usr/bin/env python3
"""SEION 증거 태그 규율 검수기.

사용법:
    python3 audit.py [파일 또는 디렉터리 ...]

인자가 없으면 저장소 루트의 docs/, *.md, *.html 을 검사한다.
출력: 파일:줄 [규칙] 근거   (사람이 오탐을 걸러내는 것을 전제로 한 넓은 그물)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TAGS = r"\[(?:검증값|설계목표|가설|추가시험|제외|M|H|S|L)\]"

# T1: 태그 없는 성능·경제 수치. 단위가 붙은 값만 잡는다.
NUM_UNIT = re.compile(
    r"(?<![\w/-])(\d[\d,]*\.?\d*)\s?"
    r"(%|V\b|mA/cm²|kWh|kW\b|시간|h\b|년|TPD|톤/일|\$[\dMB]*|억원|μm|°C|배)"
)

# T2: 금지 표현
FORBIDDEN = [
    (r"완전\s?차단", "완전 차단"),
    (r"원천\s?차단", "원천 차단"),
    (r"영구\s?(보존|제거|차단)", "영구 보존/제거"),
    (r"무전력|초저전력", "무전력·초저전력"),
    (r"100\s?%\s?전환", "탄소 100% 전환"),
    (r"수명\s?보증|성능\s?보증|보증값(?!으로)", "성능·수명 보증"),
    (r"상용화\s?완료", "상용화 완료"),
    (r"(폐수|유실|손실)\s?0\s?%", "절대치 0%"),
    (r"고장확률\s?0", "4σ를 고장확률 0으로 서술"),
    (r"절대적\s?우월", "절대적 우월성"),
    (r"달성했|보장한다|보장합니다", "달성·보장 단정"),
]

# T3: 전력 원단위 주장
POWER = re.compile(r"kWh\s?/\s?Nm³|kWh/Nm3")
FARADAY_HINT = re.compile(r"패러데이|2,?390\s?Ah|Faraday|검산")

# T4: 표준 F 택소노미
F_STD = {
    "F1": ["flooding", "범람"],
    "F2": ["salt", "염 석출", "염석출"],
    "F3": ["her", "수소 우점", "우점"],
    "F4": ["nh₃", "nh3", "암모니아", "slip", "슬립"],
    "F5": ["membrane", "막 열화", "막열화", "삽입층"],
}
# 이름을 붙이는 문맥에서만 검사한다: "F1 Flooding", "F1(범람)", "F1 — 범람", "F1: 범람"
# "F1→F3 전이", "F3 경계 접근" 같은 서술적 언급은 대상이 아니다.
F_REF = re.compile(r"\bF([1-5])\s*(?:[(（:：]|—\s|-\s)?\s*([A-Za-z가-힣][^\n,·)）|:—]{0,18})")
F_NARRATIVE = re.compile(r"F[1-5]\s*[→↔~]|경계|전이|유발|가속|판별|연계|기준|접근")

# T5: UT 번호 범위
UT_REF = re.compile(r"\bUT-(\d{2})\b")

# T6: Base/Upside 분리가 필요한 낙관 수치
OPTIMISTIC = re.compile(r"1\.0\s?[-–~]\s?1\.2\s?V|2\.5\s?[-–~]\s?3\.5\s?kWh|4\.5\s?년")
SCENARIO_HINT = re.compile(r"Base|Upside|업사이드|가설|UT-01")

# T7: soak 단독 안정성 주장
SOAK = re.compile(r"soak|침지")
POLARIZATION_HINT = re.compile(r"음극\s?분극|정전위|CV\b|작동\s?조건")

# 오탐이 잦은 줄 — 스크립트 단계에서 미리 뺀다
SKIP_LINE = re.compile(
    r"^\s*(#{1,6}\s|\||<!--|https?://|\d+\.\s*(부록|경영진|시장|기술|핵심|성능|신뢰성|사업화|로드맵|지식재산|리스크))"
)
GLOSSARY_HINT = re.compile(r"용어해설|Glossary|부호의 설명|목차")


def iter_files(targets: list[str]) -> list[Path]:
    out: list[Path] = []
    roots = [Path(t) for t in targets] if targets else [Path("docs"), Path(".")]
    for root in roots:
        if root.is_file():
            out.append(root)
        elif root.is_dir():
            for pat in ("*.md", "*.html", "*.txt"):
                out.extend(
                    p for p in root.rglob(pat)
                    if ".git" not in p.parts and "node_modules" not in p.parts
                )
    seen, uniq = set(), []
    for p in out:
        if p.resolve() not in seen:
            seen.add(p.resolve())
            uniq.append(p)
    return uniq


def audit_file(path: Path) -> list[tuple[int, str, str]]:
    hits: list[tuple[int, str, str]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return [(0, "ERR", f"읽기 실패: {exc}")]

    in_glossary = False
    for i, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line:
            continue
        if GLOSSARY_HINT.search(line):
            in_glossary = True
        if len(line) > 400:  # 압축된 HTML/데이터 줄
            continue

        # T1 — 태그 없는 수치
        if not SKIP_LINE.match(line) and not in_glossary:
            nums = NUM_UNIT.findall(line)
            if nums and not re.search(TAGS, line):
                sample = ", ".join(f"{a}{b}" for a, b in nums[:3])
                hits.append((i, "T1", f"태그 없는 수치: {sample}"))

        # T2 — 금지 표현 (금지 목록을 '나열'하는 문맥은 제외)
        listing = re.search(r"금지|사용하지\s?않|쓰지\s?않|삼간다|위반|폐기|대체|→", line) or re.search(
            r"금지사항|사용하지 않는다|표현을 쓰지|금지 표현", " ".join(lines[max(0, i - 14):i])
        )
        if not listing:
            for pat, label in FORBIDDEN:
                if re.search(pat, line):
                    hits.append((i, "T2", f"금지 표현: {label}"))

        # T3 — 전력 원단위 검산
        if POWER.search(line) and not FARADAY_HINT.search(line):
            ctx = " ".join(lines[max(0, i - 4):i + 3])
            if not FARADAY_HINT.search(ctx):
                hits.append((i, "T3", "전력 원단위 주장에 패러데이 검산 근거 없음"))

        # T4 — F 택소노미 불일치 (서술적 언급은 제외)
        if not F_NARRATIVE.search(line):
            for m in F_REF.finditer(line):
                fid, desc = "F" + m.group(1), m.group(2).lower().strip()
                if desc and not any(k in desc for k in F_STD[fid]):
                    hits.append((i, "T4", f"{fid} 명칭 불일치: '{m.group(2).strip()}'"))

        # T5 — UT 번호 범위
        for m in UT_REF.finditer(line):
            if not 0 <= int(m.group(1)) <= 9:
                hits.append((i, "T5", f"미정의 UT 번호: UT-{m.group(1)}"))

        # T6 — Base/Upside 분리
        if OPTIMISTIC.search(line) and not SCENARIO_HINT.search(line):
            ctx = " ".join(lines[max(0, i - 3):i + 2])
            if not SCENARIO_HINT.search(ctx):
                hits.append((i, "T6", "낙관 수치가 Base/Upside 구분 없이 단독 제시"))

        # T7 — soak 단독 주장
        if SOAK.search(line) and not POLARIZATION_HINT.search(line):
            ctx = " ".join(lines[max(0, i - 3):i + 3])
            if not POLARIZATION_HINT.search(ctx):
                hits.append((i, "T7", "soak 시험만으로 안정성 주장 (음극 분극 언급 없음)"))

    return hits


def main() -> int:
    files = iter_files(sys.argv[1:])
    if not files:
        print("검사 대상 파일이 없습니다.")
        return 1

    total = 0
    by_rule: dict[str, int] = {}
    for path in files:
        hits = audit_file(path)
        if not hits:
            continue
        print(f"\n=== {path} ===")
        for line_no, rule, msg in hits:
            print(f"{path}:{line_no} [{rule}] {msg}")
            by_rule[rule] = by_rule.get(rule, 0) + 1
            total += 1

    print(f"\n--- 검출 {total}건 / 파일 {len(files)}개 ---")
    for rule in sorted(by_rule):
        print(f"  {rule}: {by_rule[rule]}건")
    print("\n※ 넓은 그물이므로 오탐이 포함된다. SKILL.md 2단계에 따라 실제 위반/오탐을 분류할 것.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
