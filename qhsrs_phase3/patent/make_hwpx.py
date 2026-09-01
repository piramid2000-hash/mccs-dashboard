# -*- coding: utf-8 -*-
"""
명세서 Markdown -> HWPX (특허청 전자출원 서식용).

report 템플릿의 스타일 ID를 사용한다.
  charPr 0  : 10pt 본문
  charPr 7  : 20pt 볼드   (발명의 명칭)
  charPr 9  : 10pt 볼드   (표 헤더, 청구항 표제)
  charPr 11 : 9pt        (표 본문)
  charPr 13 : 12pt 볼드 고딕 (【 】 표제)
  paraPr 0  : JUSTIFY 160%
  paraPr 20 : CENTER
  paraPr 21 : CENTER 130% (표 셀)
  paraPr 22 : JUSTIFY 130% (표 셀)
  paraPr 24 : 들여쓰기 600
  borderFill 3 : 실선 4면 / 4 : 실선 + 음영
"""
import html, json, os, re, subprocess, sys, tempfile

H = os.path.dirname(os.path.abspath(__file__))
SKILL = "/root/.claude/skills/synced/8b8d4895-6ce8-464a-836f-c3247cb5cb55_ff919e78-7715-481a-aaae-29f4a6303440/hwpx"
BODY_W = 42520
TABLES = json.load(open(os.path.join(H, "tables.json"), encoding="utf-8"))

_id = [1000000000]
def nid():
    _id[0] += 1
    return _id[0]

def esc(t):
    return html.escape(t, quote=False)

def para(text, cp=0, pp=0):
    if not text:
        return (f'<hp:p id="{nid()}" paraPrIDRef="{pp}" styleIDRef="0" pageBreak="0" '
                f'columnBreak="0" merged="0"><hp:run charPrIDRef="{cp}"><hp:t/></hp:run></hp:p>')
    return (f'<hp:p id="{nid()}" paraPrIDRef="{pp}" styleIDRef="0" pageBreak="0" '
            f'columnBreak="0" merged="0"><hp:run charPrIDRef="{cp}">'
            f'<hp:t>{esc(text)}</hp:t></hp:run></hp:p>')

def cell(text, col, row, w, h, cp, pp, bf):
    return (f'<hp:tc name="" header="{1 if row == 0 else 0}" hasMargin="1" protect="0" '
            f'editable="0" dirty="0" borderFillIDRef="{bf}">'
            f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" '
            f'linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" '
            f'hasTextRef="0" hasNumRef="0">'
            f'<hp:p id="{nid()}" paraPrIDRef="{pp}" styleIDRef="0" pageBreak="0" '
            f'columnBreak="0" merged="0"><hp:run charPrIDRef="{cp}">'
            f'<hp:t>{esc(text)}</hp:t></hp:run></hp:p></hp:subList>'
            f'<hp:cellAddr colAddr="{col}" rowAddr="{row}"/>'
            f'<hp:cellSpan colSpan="1" rowSpan="1"/>'
            f'<hp:cellSz width="{w}" height="{h}"/>'
            f'<hp:cellMargin left="141" right="141" top="70" bottom="70"/></hp:tc>')

def table(spec):
    head, rows, wf = spec["head"], spec["rows"], spec["w"]
    n = len(head)
    widths = [int(BODY_W * f) for f in wf]
    widths[-1] += BODY_W - sum(widths)
    hrow, drow = 900, 750
    total = hrow + drow * len(rows)
    out = [f'<hp:p id="{nid()}" paraPrIDRef="20" styleIDRef="0" pageBreak="0" '
           f'columnBreak="0" merged="0"><hp:run charPrIDRef="0">'
           f'<hp:tbl id="{nid()}" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" '
           f'textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="CELL" '
           f'repeatHeader="1" rowCnt="{len(rows) + 1}" colCnt="{n}" cellSpacing="0" '
           f'borderFillIDRef="3" noAdjust="0">'
           f'<hp:sz width="{BODY_W}" widthRelTo="ABSOLUTE" height="{total}" '
           f'heightRelTo="ABSOLUTE" protect="0"/>'
           f'<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" '
           f'holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" '
           f'horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
           f'<hp:outMargin left="0" right="0" top="0" bottom="0"/>'
           f'<hp:inMargin left="0" right="0" top="0" bottom="0"/>']
    out.append("<hp:tr>")
    for c, t in enumerate(head):
        out.append(cell(t, c, 0, widths[c], hrow, 9, 21, 4))
    out.append("</hp:tr>")
    for r, row in enumerate(rows, start=1):
        out.append("<hp:tr>")
        for c, t in enumerate(row):
            pp = 22 if (c == 0 and len(t) > 8) else 21
            out.append(cell(t, c, r, widths[c], drow, 11, pp, 3))
        out.append("</hp:tr>")
    out.append("</hp:tbl></hp:run></hp:p>")
    return "".join(out)


# ---------------------------------------------------------------------------
def convert(md_path):
    lines = open(md_path, encoding="utf-8").read().split("\n")
    body, buf, i = [], [], 0
    HEAD = re.compile(r"^【(.+)】\s*$")
    CAP = re.compile(r"^\s*\[표 (\d+)\]")
    RULE = re.compile(r"^\s*-{6,}\s*$")

    def flush(cp=0, pp=0):
        if buf:
            body.append(para(" ".join(x.strip() for x in buf if x.strip()), cp, pp))
            buf.clear()

    title_next = False
    in_signs = False
    in_claims = False
    while i < len(lines):
        ln = lines[i]
        st = ln.strip()

        if st == "---":
            flush(); body.append(para("")); i += 1; continue

        m = HEAD.match(st)
        if m:
            flush(); body.append(para(""))
            name = m.group(1)
            body.append(para(st, 9 if name.startswith("청구항") else 13,
                             0 if name.startswith("청구항") else 0))
            title_next = (name == "발명의 명칭")
            in_signs = (name == "부호의 설명")
            in_claims = name.startswith("청구항") or in_claims
            i += 1; continue

        cm = CAP.match(ln)
        if cm:
            flush()
            body.append(para(""))
            body.append(para(st, 9, 20))
            body.append(table(TABLES[cm.group(1)]))
            body.append(para(""))
            # ASCII 표 블록(구분선 사이)을 건너뛴다
            j = i + 1
            seen = 0
            while j < len(lines):
                if RULE.match(lines[j]):
                    seen += 1
                    if seen == 3:
                        j += 1; break
                j += 1
            i = j; continue

        if not st:
            flush(); i += 1; continue

        if title_next:
            flush()
            body.append(para(""))
            body.append(para(st, 7, 20))
            j = i + 1
            while j < len(lines) and lines[j].strip():
                body.append(para(lines[j].strip(), 11, 20))
                j += 1
            title_next = False
            i = j; continue

        if in_signs and " : " in st:
            flush(); body.append(para(st, 0, 24)); i += 1; continue

        if st.startswith("[0") and buf:
            flush()
        buf.append(ln)
        i += 1
    flush()
    return "".join(body)


if __name__ == "__main__":
    md = os.path.join(H, "QHSRS_특허명세서.md")
    base = open(os.path.join(SKILL, "templates", "base", "Contents", "section0.xml"),
                encoding="utf-8").read()
    first_end = base.index("</hp:p>") + len("</hp:p>")
    header = base[:base.index("<hp:p ")]
    first_p = base[base.index("<hp:p "):first_end]
    sec = header + first_p + convert(md) + "\n</hs:sec>"
    tmp = os.path.join(tempfile.gettempdir(), "spec_section0.xml")
    open(tmp, "w", encoding="utf-8").write(sec)
    out = os.path.join(H, "QHSRS_특허명세서.hwpx")
    subprocess.run([sys.executable, os.path.join(SKILL, "scripts", "build_hwpx.py"),
                    "--template", "report", "--section", tmp,
                    "--title", "극저주파 자기장 수계 노출 장치 및 그 제어 방법",
                    "--creator", "Q-HSRS", "--output", out], check=True)
    subprocess.run([sys.executable, os.path.join(SKILL, "scripts", "validate.py"), out],
                   check=True)
    print("wrote", out, os.path.getsize(out) // 1024, "KB")
