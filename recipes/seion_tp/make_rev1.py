"""SEION C2C Pad R&D Plan Rev.0 -> Rev.1 (분포형 셀·압축 상태 재해석 반영).

원본 docx-js 서식을 그대로 복제해 삽입한다. 사용: python make_rev1.py <unpacked_dir>
"""
import copy
import re
import sys
from xml.sax.saxutils import escape

from lxml import etree

UN = sys.argv[1]
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
q = lambda t: f"{{{W}}}{t}"
DOC = f"{UN}/word/document.xml"
tree = etree.parse(DOC)
root = tree.getroot()
body = root.find(q("body"))
NSDECL = " ".join(f'xmlns:{k}="{v}"' for k, v in root.nsmap.items() if k) + ' xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"'
FONT = '<w:rFonts w:ascii="Apple SD Gothic Neo" w:cs="Apple SD Gothic Neo" w:eastAsia="Apple SD Gothic Neo" w:hAnsi="Apple SD Gothic Neo"/>'
NAVY, RED, GREEN, GREY = "1F3864", "C0392B", "2E7D32", "7F8C8D"


def X(s):
    return etree.fromstring(f"<w:wrap {NSDECL}>{s}</w:wrap>")[0]


def rpr(sz, bold=False, color="000000"):
    b = "<w:b/><w:bCs/>" if bold else '<w:b w:val="false"/><w:bCs w:val="false"/>'
    return f'<w:rPr>{FONT}{b}<w:i w:val="false"/><w:iCs w:val="false"/><w:color w:val="{color}"/><w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/></w:rPr>'


def runs(text, sz, color="000000", bold=False):
    """**굵게**, !!빨강 굵게!! 마크업 지원."""
    out = []
    for tok in re.split(r"(\*\*.+?\*\*|!!.+?!!)", text):
        if not tok:
            continue
        if tok.startswith("**"):
            out.append((tok[2:-2], True, color))
        elif tok.startswith("!!"):
            out.append((tok[2:-2], True, RED))
        else:
            out.append((tok, bold, color))
    return "".join(f'<w:r>{rpr(sz, b, c)}<w:t xml:space="preserve">{escape(t)}</w:t></w:r>' for t, b, c in out)


def P(text, kind="body"):
    spec = {
        "body": ('<w:spacing w:after="60" w:before="40" w:line="300"/><w:jc w:val="left"/>', 20, "000000", False),
        "note": ('<w:spacing w:after="140" w:before="40" w:line="260"/><w:jc w:val="left"/>', 15, GREY, False),
        "tcap": ('<w:spacing w:after="50" w:before="150" w:line="300"/><w:jc w:val="left"/>', 18, NAVY, True),
        "fcap": ('<w:spacing w:after="170" w:before="0" w:line="300"/><w:jc w:val="center"/>', 17, NAVY, True),
        "h2": ('<w:pStyle w:val="Heading2"/><w:spacing w:after="110" w:before="240" w:line="300"/>', 26, NAVY, True),
        "eq": ('<w:spacing w:after="80" w:before="80" w:line="300"/><w:jc w:val="center"/>', 20, NAVY, True),
    }[kind]
    return X(f"<w:p><w:pPr>{spec[0]}</w:pPr>{runs(text, spec[1], spec[2], spec[3])}</w:p>")


def EMPTY():
    return X('<w:p><w:pPr><w:spacing w:after="0" w:before="0"/></w:pPr></w:p>')


BRD = '<w:tcBorders><w:top w:val="single" w:color="C9D2E3" w:sz="2"/><w:left w:val="single" w:color="C9D2E3" w:sz="2"/><w:bottom w:val="single" w:color="C9D2E3" w:sz="2"/><w:right w:val="single" w:color="C9D2E3" w:sz="2"/></w:tcBorders>'
MAR = '<w:tcMar><w:top w:type="dxa" w:w="50"/><w:left w:type="dxa" w:w="80"/><w:bottom w:type="dxa" w:w="50"/><w:right w:type="dxa" w:w="80"/></w:tcMar>'


def cell(text, w, fill=None, header=False, jc="left", bold=False, color="000000"):
    shd = f'<w:shd w:fill="{fill}" w:val="clear"/>' if fill else ""
    if header:
        r = runs(text, 16, "FFFFFF", True)
    else:
        r = runs(text, 16, color, bold)
    return (f'<w:tc><w:tcPr><w:tcW w:type="dxa" w:w="{w}"/>{BRD}{shd}{MAR}<w:vAlign w:val="center"/></w:tcPr>'
            f'<w:p><w:pPr><w:spacing w:after="10" w:before="10" w:line="250"/><w:jc w:val="{jc}"/></w:pPr>{r}</w:p></w:tc>')


def TABLE(headers, rows, widths, center_cols=(), bold_rows=()):
    assert sum(widths) == 9638, sum(widths)
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    xml = (f'<w:tbl><w:tblPr><w:tblW w:type="dxa" w:w="9638"/><w:tblBorders>'
           + "".join(f'<w:{s} w:val="single" w:color="auto" w:sz="4"/>' for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
           + f"</w:tblBorders></w:tblPr><w:tblGrid>{grid}</w:tblGrid>")
    xml += '<w:tr><w:trPr><w:tblHeader/></w:trPr>' + "".join(cell(h, w, NAVY, True, "center") for h, w in zip(headers, widths)) + "</w:tr>"
    for i, row in enumerate(rows):
        fill = "F2F5FA" if i % 2 == 1 else None
        xml += '<w:tr><w:trPr><w:tblHeader w:val="false"/></w:trPr>' + "".join(
            cell(t, w, fill, False, "center" if j in center_cols else "left", i in bold_rows)
            for j, (t, w) in enumerate(zip(row, widths))) + "</w:tr>"
    return X(xml + "</w:tbl>")


def CALLOUT(title, paras, head=NAVY):
    tb = (f'<w:tbl><w:tblPr><w:tblW w:type="dxa" w:w="9638"/><w:tblBorders>'
          + "".join(f'<w:{s} w:val="single" w:color="auto" w:sz="4"/>' for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
          + '</w:tblBorders></w:tblPr><w:tblGrid><w:gridCol w:w="9638"/></w:tblGrid>')
    tb += (f'<w:tr><w:tc><w:tcPr><w:tcW w:type="dxa" w:w="9638"/><w:tcBorders><w:top w:val="single" w:color="{head}" w:sz="6"/><w:left w:val="single" w:color="{head}" w:sz="6"/><w:bottom w:val="none"/><w:right w:val="single" w:color="{head}" w:sz="6"/></w:tcBorders>'
           f'<w:shd w:fill="{head}" w:val="clear"/><w:tcMar><w:top w:type="dxa" w:w="70"/><w:left w:type="dxa" w:w="110"/><w:bottom w:type="dxa" w:w="70"/><w:right w:type="dxa" w:w="110"/></w:tcMar></w:tcPr>'
           f'<w:p><w:pPr><w:spacing w:after="0" w:before="0" w:line="300"/><w:jc w:val="left"/></w:pPr>{runs(title, 20, "FFFFFF", True)}</w:p></w:tc></w:tr>')
    ps = "".join(f'<w:p><w:pPr><w:spacing w:after="70" w:before="40" w:line="300"/><w:jc w:val="left"/></w:pPr>{runs(t, 19)}</w:p>' for t in paras)
    tb += (f'<w:tr><w:tc><w:tcPr><w:tcW w:type="dxa" w:w="9638"/><w:tcBorders><w:top w:val="none"/><w:left w:val="single" w:color="{head}" w:sz="6"/><w:bottom w:val="single" w:color="{head}" w:sz="6"/><w:right w:val="single" w:color="{head}" w:sz="6"/></w:tcBorders>'
           f'<w:shd w:fill="F2F5FA" w:val="clear"/><w:tcMar><w:top w:type="dxa" w:w="90"/><w:left w:type="dxa" w:w="110"/><w:bottom w:type="dxa" w:w="90"/><w:right w:type="dxa" w:w="110"/></w:tcMar></w:tcPr>{ps}</w:tc></w:tr></w:tbl>')
    return X(tb)


def FIG(rid, cx, cy, pid):
    return X(f'<w:p><w:pPr><w:spacing w:after="50" w:before="140"/><w:jc w:val="center"/></w:pPr><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent t="0" r="0" b="0" l="0"/><wp:docPr id="{pid}" name="Fig16" descr="" title=""/><wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="" descr=""/><pic:cNvPicPr><a:picLocks noChangeAspect="1" noChangeArrowheads="1"/></pic:cNvPicPr></pic:nvPicPr><pic:blipFill><a:blip r:embed="{rid}" cstate="none"/><a:srcRect/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr bwMode="auto"><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')


# ---------- 탐색·수정 헬퍼 ----------
def text(el):
    return "".join(el.itertext())


def find(prefix, tag=None):
    for el in body:
        if (tag is None or el.tag == q(tag)) and text(el).startswith(prefix):
            return el
    raise KeyError(prefix)


def set_par(p, new):
    """문단 첫 run 서식을 유지하고 텍스트 교체 (마크업 지원)."""
    rs = p.findall(q("r"))
    r0 = rs[0].find(q("rPr"))
    sz = int(r0.find(q("sz")).get(q("val")))
    color = r0.find(q("color")).get(q("val"))
    bold = r0.find(q("b")) is not None and r0.find(q("b")).get(q("val")) != "false"
    for r in rs:
        p.remove(r)
    for r in X(f"<w:p>{runs(new, sz, color, bold)}</w:p>"):
        p.append(r)


def replace_in_par(p, old, new):
    for t in p.iter(q("t")):
        if old in t.text:
            t.text = t.text.replace(old, new)
            return
    raise KeyError(old)


def rows(tbl):
    return tbl.findall(q("tr"))


def set_cell(tc, new):
    set_par(tc.find(q("p")), new)


def add_row(tbl, texts, like=-1):
    rs = rows(tbl)
    nr = copy.deepcopy(rs[like])
    # 줄무늬: 직전 행과 반대 음영
    prev_fill = rs[-1].find(f".//{q('shd')}")
    for tc, t in zip(nr.findall(q("tc")), texts):
        tcpr = tc.find(q("tcPr"))
        shd = tcpr.find(q("shd"))
        if prev_fill is None and shd is None:
            tcpr.insert(2, X('<w:shd w:fill="F2F5FA" w:val="clear"/>'))
        elif prev_fill is not None and shd is not None:
            tcpr.remove(shd)
        set_cell(tc, t)
    tbl.append(nr)
    return nr


def after(anchor, *els):
    for el in els:
        anchor.addnext(el)
        anchor = el
    return anchor


def callout_body(tbl):
    return rows(tbl)[1].find(q("tc"))


def callout_add(tbl, t):
    tc = callout_body(tbl)
    p = copy.deepcopy(tc.findall(q("p"))[-1])
    set_par(p, t)
    tc.append(p)


# ======================= 개정 =======================
REV = "Rev.1"

# 0. 표지 표·바닥글
cover = find("구분내용과제명", "tbl")
for tr in rows(cover):
    c = tr.findall(q("tc"))
    k = text(c[0])
    if k == "문서 번호":
        set_cell(c[1], "SEION-C2CPAD-RNDPLAN-2026-001 Rev.1")
    elif k == "작성 일자":
        set_cell(c[1], "2026. 10. 07. (Rev.0 2026. 09. 27.)")
    elif k == "핵심 사양":
        set_cell(c[1], text(c[1]) + " — Rev.1: 열 판정은 0.25 MPa 압축 상태·분포형 셀 기준. 총두께는 S0 실측 k_eff로 재결정(1.50 mm는 조건부)")
for fn in ("footer1.xml", "header1.xml"):
    path = f"{UN}/word/{fn}"
    s = open(path, encoding="utf-8").read().replace("RNDPLAN-2026-001 Rev.0", "RNDPLAN-2026-001 Rev.1")
    open(path, "w", encoding="utf-8").write(s)

# 1. Rev.1 개정 요약 박스 (데이터 등급 선언 뒤)
grade = find("데이터 등급 선언", "tbl")
after(grade, EMPTY(), CALLOUT("Rev.1 개정 요약 — 분포형 셀·압축 상태 재해석 반영 (2026. 10. 07.)", [
    "Rev.0의 열해석(실시예 1, 122.2 ℃)은 **비압축 두께와 집중용량 셀** 조건이다. Rev.1에서는 표 5-1 조건의 대리 모델을 실시예 1(최고 122.2 ℃, Fig.1의 시간 거동)에 보정한 뒤 셀 모델과 압축 조건만 바꿔 재해석하였다(신설 5.5절). 원 해석의 셀 방열 조건이 표 5-1에 없어 보정 방식 3종으로 결론의 강건성을 점검하였다.",
    "결과: 0.25 MPa 압축 두께와 분포형 셀을 함께 반영하면 세 보정 모두에서 인접 셀 표면이 !!159.9~390 ℃!!로 기준을 넘는다. 통과에 필요한 코어 k0는 !!0.006~0.008 W/m·K!!로, 정지 공기(0.026)·실리카 에어로겔(0.012~0.015)보다 낮아 **1.50 mm 두께에서는 다공 재료로 도달할 수 없다.**",
    "에어로겔급 k0 0.015에서는 총두께 **2.0~2.5 mm**, 본 레시피의 구조 기반 추정 k0 0.025에서는 **2.5~3.0 mm**가 필요하다(표 5-5). 따라서 총두께(K2)를 S0 실측 k_eff로 재결정하도록 바꾸고, 판정 지표를 **\"압축 상태·분포형 셀·전 구간 최고온도\"**로 확장하였다(K1, K11).",
    "아울러 층분리 기하(n_strata 산정 기준)·CO₂ 확산계수 문헌값·고무 기지 나노기공 형성 가능성·급속감압 장비 사양을 재검토하여, 1년차 착수 직후 **S0 Go/No-go 단계**와 **Plan B(나노 스트라타 → 에어로겔 층 대체)**를 신설하였다.",
    "개정 위치: 표지, Q1·Q2, 표 1-2, 4.3절(표 4-3), 표 5-1, 5.4절, **5.5절(신설)**, 표 7-1·7-5, 8.1·8.3절, 표 9-1, 9.2절, 부록 A·B·C.",
], head=RED))

# 2. Executive Summary Q1
q1 = find("답변 — 가능하다", "tbl")
set_cell(rows(q1)[0].find(q("tc")), "답변 — [Rev.1] 비압축·집중용량 해석에서만 가능하다. 압축 상태(0.25 MPa)·분포형 셀로 재해석하면 1.50 mm로는 성립하지 않으며, 총두께 2.0~3.0 mm가 필요하다.")
callout_add(q1, "**[Rev.1 재해석]** 작동 응력 0.25 MPa에서 코어는 0.90 → 0.34 mm로 압축된다. 이 두께와 분포형 인접 셀(Al 캔 + 젤리롤)을 함께 반영하면, 실시예 1에 보정한 세 가지 대리 모델 모두에서 인접 셀 표면 최고온도가 !!159.9~390 ℃!!로 기준을 넘는다(5.5절, 표 5-4). 통과에 필요한 코어 k0는 0.006~0.008 W/m·K로 에어로겔보다 낮다. 에어로겔급 k0(0.015)를 확보하면 총두께 2.0~2.5 mm에서 성립한다(표 5-5).")

# 3. Q2
q2 = find("답변 — 요구 물성이 문헌 범위", "tbl")
callout_add(q2, "**[Rev.1 보완]** γ_eff보다 앞선 위험이 두 가지 있다. ① 층분리 시점(등온 유지)의 코어는 발포 전 두께 약 126 μm로, 스트라타 주기 310 μm 기준 n_strata는 2.9가 아니라 !!0.41!!이다. 무충전 PDMS의 CO₂ 확산계수 문헌값(약 1~2×10⁻⁹ m²/s[14])을 쓰면 주기가 1.4~2.0 mm로 더 길어진다. ② Tg가 −125 ℃인 고무 기지에서 80 nm·공극률 0.88의 나노기공 상이 유지되는지는 보고 사례가 드물다. 두 항목을 1년차 1~6개월 **S0 Go/No-go**로 먼저 판정한다(표 7-1).")

# 4. 표 1-2 KPI
kpi = find("NoKPI현 수준", "tbl")
for tr in rows(kpi):
    c = tr.findall(q("tc"))
    k = text(c[0])
    if k == "K1":
        set_cell(c[1], "인접 셀 표면 최고온도 (0~7,200 s 전 구간, 초기 10 min 피크 포함)")
        set_cell(c[2], "122.2 ℃ (비압축·집중용량) / 159.9~390 ℃ (Rev.1 압축·분포형)")
    elif k == "K2":
        set_cell(c[3], "≤ 1.50 mm — [Rev.1] S0 실측 k_eff로 재결정 (k_eff 0.015 → 2.0~2.5 mm, 표 5-5)")
    elif k == "K5":
        set_cell(c[3], "≥ 5 (실측) — 문헌 3.1배[3]")
for r in [
    ["K11", "압축상태 코어 유효 열전도도 k_eff (0.25 MPa, 25 ℃)", "0.025 (구조 기반 추정)", "≤ 0.015 W/m·K (총두께 결정 입력값)", "Hot Disk (압축 지그)", "T"],
    ["K12", "압축 응력–변형 곡선 (0~1.0 MPa, 셀 스웰링 말기 포함)", "—", "원자료 제출, 1.0 MPa에서 k_eff 보고", "UTM + Hot Disk", "T"],
    ["K13", "절연 (상온 및 600 ℃·10 min 노출 후)", "—", "BDV ≥ 3 kV, IR ≥ 500 MΩ@1000 VDC", "ASTM D149 / IR 측정", "T"],
    ["K14", "난연 · 저분자 실록산 아웃가스", "—", "UL94 V-0, D3~D10 합계 ≤ 300 ppm", "UL94 / GC-MS", "T"],
    ["K15", "전해액·냉각수 내성 (85 ℃ × 168 h 침지)", "—", "Δ두께 ≤ 5 %", "침지 후 두께·질량", "T"],
]:
    add_row(kpi, r)
note = find('※ "현 수준" 열의 값은')
set_par(note, note_text := text(note) + " Rev.1: K11~K15 신설(수요처 C2C 패드 일반 요구조건 반영), K1 판정 구간을 전 구간으로 확장, K5 목표를 인용 문헌 수준에 맞춰 조정.")

# 5. 4.3절 층분리 — 표 4-3 행 추가, 본문 단서, 정정 박스
t43 = find("항목기호값산출 근거등급유효 CO₂", "tbl")
add_row(t43, ["발포 전 코어 두께 (층분리 시점)", "t_core,0", "126 μm", "0.90 mm × 161.0/1142", "T"])
add_row(t43, ["층분리 시점 기준 주기 수", "n_strata,0", "0.41", "t_core,0 / p", "T [Rev.1]"])
add_row(t43, ["문헌 D_CO₂ 적용 시 주기 (무충전 PDMS)", "p_lit", "1.4 ~ 2.0 mm", "D_CO₂ = 1~2×10⁻⁹ m²/s[14]", "P0 [검증필요]"])
p41 = find("여기서 제조 관점의 중요한 결과가 하나 나온다")
set_par(p41, text(p41) + " **단, 이 둔감성은 n_strata ≥ 1(층이 실제로 형성됨)을 전제로 한다.** n_strata < 1이면 구조는 비교예 4(균질 혼합)가 되어 영구압축률 18.40 %로 탈락한다.")
after(p41, EMPTY(), CALLOUT("Rev.1 정정 — n_strata 는 \"층분리 시점의 두께\"로 산정해야 한다", [
    "Rev.0의 n_strata = 2.9는 발포가 끝난 코어 두께(0.90 mm)를 주기 p(310 μm)로 나눈 값이다. 그러나 스트라타가 갈리는 등온 유지(P3) 시점에 코어는 아직 거의 발포 전 상태이며, 그 두께는 약 126 μm이다. 이 기준으로 n_strata,0 = 0.41로 한 주기도 들어가지 않는다.",
    "D_CO₂ 가정값 5.0×10⁻¹¹ m²/s는 무충전 PDMS 문헌값(약 1~2×10⁻⁹ m²/s)보다 20~40배 작다. 문헌값이 맞다면 p = 310 μm를 얻기 위한 유지시간은 8 min이 아니라 !!12~24 s!!로, 1차 감압(10 s)과 시간이 겹친다.",
    "대응: ① 등온 유지 시점의 부분 발포 두께를 단면 SEM 시계열로 실측(S0), ② 충전량 증가·유지 온도 하향으로 유효 D_CO₂ 저감, ③ n_strata,0 ≥ 1이 확보되지 않으면 Plan B(나노 스트라타를 에어로겔 층으로 대체한 적층 구조)로 전환한다(표 7-5).",
], head=RED))

# 6. 표 5-1 해석 조건 행 추가
t51 = find("구분조건값등급열원", "tbl")
add_row(t51, ["해석 두께", "Rev.0 해석 기준", "비압축 1.50 mm (코어 0.90 mm) — Rev.1에서 0.25 MPa 압축 두께(코어 0.34 mm) 병행", "[검증필요]"])
add_row(t51, ["인접 셀 방열 (Rev.1 지적)", "미기재", "Fig.1의 시간 거동(약 10분 정점 후 120분에 약 87 ℃로 하강)은 셀 방열 경로를 전제함 — 조건 명시 필요", "[검증필요]"])
add_row(t51, ["인접 셀 (Rev.1)", "분포형", "Al 캔 0.8 mm + 젤리롤(두께방향 k 0.3~1.0 W/m·K), 총 90 kg/m²", "P0"])

# 7. 5.4절 박스에 ⑥⑦⑧ 추가, 5.5절 신설
b54 = find("평가위원께 먼저 밝히는 사실 — 본 장의 수치는 전부 해석값이다", "tbl")
tc = callout_body(b54)
last = tc.findall(q("p"))[-1]
for t in [
    "⑥ [Rev.1] 인접 셀을 집중용량(90 kg/m²가 즉시 균일 가열)으로 다루어, 셀 표면이 셀 평균보다 먼저 가열되는 효과가 빠져 있다. Fig.1 거동에 보정한 분포형 모델에서는 이 효과만으로 표면이 225~339 ℃까지 오른다(5.5절).",
    "⑦ [Rev.1] 열해석이 비압축 두께 기준이다. 0.25 MPa 압축(평균 변형률 37.7 %)을 반영하면 판정이 뒤집힌다(5.5절). 해석과 실측 모두 압축 상태를 기준으로 한다.",
    "⑧ [Rev.1] Fig.1의 온도 하강 거동은 인접 셀의 방열 경로를 전제하나, 그 조건이 표 5-1에 없다. 원 해석의 경계조건을 명시해야 한다.",
]:
    p = copy.deepcopy(tc.findall(q("p"))[0])
    set_par(p, t)
    last.addprevious(p)

# 그림 관계 추가
rels_path = f"{UN}/word/_rels/document.xml.rels"
rels = open(rels_path, encoding="utf-8").read()
rels = rels.replace("</Relationships>", '<Relationship Id="rId901" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/rev1_fig16_tp_cellmodel.png"/></Relationships>')
open(rels_path, "w", encoding="utf-8").write(rels)

H = ["케이스", "셀 모델", "해석 두께", "Cal-1 Fig.1 형상", "Cal-2 표 5-1 문언", "Cal-3 열원 감쇠", "판정"]
WID = [1900, 1350, 1350, 1300, 1300, 1300, 1138]
R54 = [
    ["A (Rev.0 조건 재현)", "집중용량", "비압축", "122.3 ℃", "122.2 ℃", "122.2 ℃", "적합"],
    ["C", "분포형 k 0.6", "비압축", "!!290.8 ℃!!", "124.6 ℃", "!!225.5 ℃!!", "보정 의존"],
    ["D", "분포형 k 0.3", "비압축", "!!338.6 ℃!!", "128.2 ℃", "!!269.7 ℃!!", "보정 의존"],
    ["E", "집중용량", "압축 0.25 MPa", "!!182.8 ℃!!", "!!166.0 ℃!!", "!!182.3 ℃!!", "!!부적합!!"],
    ["F", "분포형 k 0.6", "압축 0.25 MPa", "!!390.0 ℃!!", "!!159.9 ℃!!", "!!327.3 ℃!!", "!!부적합!!"],
    ["H (구조 기반 k0 0.025)", "분포형 k 0.6", "비압축", "!!166.4 ℃!!", "!!166.4 ℃!!", "!!160.2 ℃!!", "!!부적합!!"],
    ["(보정된 코어 k0)", "—", "—", "0.088", "0.008", "0.052", "W/m·K"],
]
H5 = ["총두께 (비압축)", "압축 후 코어 두께", "Cal-1 k0 상한", "Cal-2 k0 상한", "판정 (에어로겔 0.012~0.015 / 구조 추정 0.025 기준)"]
WID5 = [1500, 1600, 1400, 1400, 3738]
R55 = [
    ["1.50 mm (현 설계)", "0.33 mm", "0.0075", "0.0058", "!!도달 불가 — 에어로겔보다 낮은 k 필요!!"],
    ["2.00 mm", "0.65 mm", "0.0160", "0.0118", "에어로겔급이면 Cal-1 통과, Cal-2 경계"],
    ["2.50 mm", "0.96 mm", "0.0247", "0.0180", "에어로겔급이면 통과 · 구조 추정(0.025)은 Cal-1 경계"],
    ["3.00 mm", "1.27 mm", "0.0336", "0.0242", "구조 추정(0.025)이면 Cal-1 통과, Cal-2 경계"],
]
anchor = b54
els = [
    EMPTY(),
    P("5.5  판정 여유 재평가 — 분포형 셀·압축 상태 (Rev.1 신설)", "h2"),
    P("Rev.0 해석 코드와 같은 조건(표 5-1: 열원 이력, 셀 90 kg/m², 접촉 컨덕턴스 2,000 W/m²K, 아머 세라믹화, 열분해 흡열)으로 1차원 대리 모델을 구성하였다. 원 해석의 인접 셀 방열 조건이 표 5-1에 없으므로, 실시예 1을 재현하는 보정 방식을 세 가지로 두었다. **Cal-1**은 Fig.1의 시간 거동(약 10분 정점 후 하강)을 재현하도록 셀 방열 120 W/m²K를 둔 것이고, **Cal-2**는 표 5-1 문언 그대로(단열 셀), **Cal-3**은 잔류 열원이 시정수 1,200 s로 식는 경우이다. 각 보정에서 집중용량 셀의 최고온도가 122.2 ℃가 되도록 코어의 고체·기체 열전도도 k0를 맞춘 뒤, **셀 모델과 압축 조건만** 바꾸었다."),
    P("표 5-4. 보정 방식별 인접 셀 표면 최고온도 (0~7,200 s, 판정 기준 150 ℃)", "tcap"),
    TABLE(H, R54, WID, center_cols=(2, 3, 4, 5, 6)),
    P("※ 대리 모델 결과(P0 기반 해석)이며 실측이 아니다. 삭마·벤트 대류·캔 면내 확산은 보정 k0에 흡수되었다. 압축 케이스는 압축에 따른 고체 전도 증가를 반영하지 않아 실제보다 유리한 쪽이다. 재현: recipes/seion_tp/run_cases.py.", "note"),
    P("표 5-5. 총두께별 통과 조건 — 압축 0.25 MPa·분포형 셀(k 0.6)에서 인접 셀 ≤ 150 ℃를 만족하는 코어 k0 상한 [W/m·K]", "tcap"),
    TABLE(H5, R55, WID5, center_cols=(0, 1, 2, 3)),
    P("※ 아머 0.10 mm·천이대 0.20 mm ×2를 유지하고 코어만 늘린 경우. k0 상한은 보정된 k0와 무관하며 경계조건(Cal)에만 의존한다. 재현: recipes/seion_tp/thick_option.py, required_k.py.", "note"),
    FIG("rId901", 5943600, 2278380, 901),
    P("Fig.16  (a) 인접 셀 표면온도 — Cal-1 기준 셀 모델·압축별, (b) 총두께별 통과 가능한 코어 k0 상한 [Rev.1]", "fcap"),
    P("결과는 네 가지로 정리된다."),
    P("첫째, **압축 상태를 반영하면 보정 방식과 무관하게 부적합이다.** 집중용량 셀에서도 166~183 ℃(케이스 E), 분포형 셀에서는 160~390 ℃(케이스 F)로 기준을 넘는다."),
    P("둘째, **1.50 mm 두께는 다공 재료의 물리적 한계를 넘는 k를 요구한다.** 압축 상태에서 통과하려면 코어 k0가 0.006~0.008 W/m·K여야 하는데(표 5-5), 이는 정지 공기(0.026)의 1/4, 실리카 에어로겔(0.012~0.015)의 약 절반이다."),
    P("셋째, **집중용량 셀 가정은 큰 비보수 요인일 수 있다.** Fig.1의 시간 거동을 재현하는 보정(Cal-1·Cal-3)에서는 셀을 분포형으로 바꾸는 것만으로 표면이 225~339 ℃까지 오른다. 표 5-1 문언 그대로(Cal-2)이면 영향은 2~6 ℃이다. 어느 쪽인지는 원 해석의 셀 방열 조건에 달려 있으므로 이를 명시해야 한다."),
    P("넷째, **두께를 늘리면 성립 영역이 생긴다.** 에어로겔급 k0(0.015)이면 총두께 2.0~2.5 mm, 본 레시피의 구조 기반 추정 k0(0.025)이면 2.5~3.0 mm에서 통과한다. 따라서 총두께는 S0에서 실측한 압축 상태 k_eff로 결정해야 한다."),
    EMPTY(),
    CALLOUT("Rev.1 판정 — 설계 성립 조건과 대안", [
        "1.50 mm 설계는 압축 상태에서 성립하지 않는다(표 5-5). **총두께를 “S0 실측 압축상태 k_eff → 표 5-5”로 결정**하는 방식으로 KPI K2를 바꾼다. 에어로겔급 k_eff(0.015)이면 2.0~2.5 mm가 설계 기준이다.",
        "대안: ① 총두께 2.0~2.5 mm 상향(수요처 두께 예산 확인 필요), ② 나노 스트라타를 에어로겔 층으로 대체한 적층 구조(Plan B — 아머·천이대 배합은 그대로 활용), ③ 압축 변형을 코어 밖(아머·천이대 또는 별도 탄성층)으로 옮겨 코어 두께를 보존하는 구조 변경.",
        "후속 해석: 원 해석의 셀 방열 경계조건을 확인하고, 수요처 셀의 실측 열폭주 표면온도 이력과 젤리롤 두께방향 k를 입수하여 표 5-4·5-5를 갱신한다. 쿨링 플레이트와 캔 면내 확산을 포함한 2차원 해석으로 확장한다.",
    ], head=NAVY),
]
after(anchor, *els)

# 8. 7.1 실증 단계 표 — S0 추가
s_tbl = find("단계시기목적산출물판정S1", "tbl")
hdr = rows(s_tbl)[0]
s0 = copy.deepcopy(rows(s_tbl)[1])
for tc_, t in zip(s0.findall(q("tc")), ["S0 Go/No-go [Rev.1]", "1년차 1~6 M",
                                        "고무 기지 나노기공 상 형성 · 층분리(n_strata,0 ≥ 1) · 압축상태 k_eff 확인 (≤ 1 L 소형 고속감압 셀)",
                                        "단면 SEM 시계열, BET, 압축 Hot Disk",
                                        "φ_nano ≥ 0.8 · d ≤ 200 nm · 압축상태 k_eff 실측 → 총두께 결정(표 5-5), 미달 시 Plan B"]):
    set_cell(tc_, t)
hdr.addnext(s0)
for tr in rows(s_tbl)[2:]:
    for tc_ in tr.findall(q("tc")):
        shd = tc_.find(f"{q('tcPr')}/{q('shd')}")
        if shd is not None:
            tc_.find(q("tcPr")).remove(shd)
        else:
            tc_.find(q("tcPr")).insert(2, X('<w:shd w:fill="F2F5FA" w:val="clear"/>'))
p189 = find("따라서 실증은 다음 세 단계로")
replace_in_par(p189, "세 단계", "네 단계(Rev.1: S0 신설)")

# 9. 표 7-5 시나리오 추가
t75 = find("상수가정값이탈 시나리오", "tbl")
add_row(t75, ["D_CO₂ [Rev.1]", "5.0e-11 m²/s", "20~40배 큼 (무충전 PDMS 문헌값)", "유효 확산 저감 또는 유지 단축", "충전량 증가 · P3 온도 50 → 35 ℃, t_hold 12~24 s 검토", "1차 감압과 시간 중첩 — n_strata,0 < 1이면 Plan B"])
add_row(t75, ["나노기공 상 [Rev.1]", "φ 0.88 · d 80 nm", "고무 기지에서 합일·붕괴로 미형성", "Plan B 전환", "나노 스트라타 → 에어로겔 층 적층 (A·천이대 배합 유지)", "scCO₂ 1단 감압으로 공정 단순화, 층 계면 접착 관리 필요"])
add_row(t75, ["k_eff (압축) [Rev.1]", "≤ 0.015 W/m·K", "0.015 초과", "두께 상향 또는 구조 변경", "총두께 2.5~3.0 mm (k_eff 0.025 기준, 표 5-5) 또는 압축 변형을 코어 밖으로 이전", "부피 예산 초과 여부 수요처 확인 필요"])
p212 = find("※ 모든 대응안은 총두께 1.50 mm 제약을 유지하는")
set_par(p212, "※ Rev.0의 네 시나리오는 총두께 1.50 mm 제약 안에서 정의되었다. Rev.1 재해석(5.5절)에 따라 압축 상태에서는 1.50 mm로 성립하지 않으므로, \"k_eff (압축)\" 대응은 1.50 mm 제약을 벗어나며, 이 경우 수요처 두께 예산 협의가 선행되어야 한다.")

# 10. 8.1 약점 박스
b81 = find("본 과제의 세 가지 약점을 먼저 제시한다", "tbl")
set_cell(rows(b81)[0].find(q("tc")), "본 과제의 네 가지 약점을 먼저 제시한다 (Rev.1: 넷째 추가)")
callout_add(b81, "넷째, **[Rev.1] 1.50 mm 두께로는 압축 상태 열 판정을 통과하지 못한다.** 비압축·집중용량 조건의 여유 27.7 ℃는 0.25 MPa 압축을 반영하면 보정 방식과 무관하게 역전되며(5.5절), 통과에 필요한 코어 k0(0.006~0.008 W/m·K)는 에어로겔보다 낮다. 총두께를 2.0~3.0 mm로 재설정하거나 구조를 바꿔야 하며, 그 기준값(압축상태 k_eff)을 1년차 S0에서 먼저 실측한다.")

# 11. 8.3 장비 — 오토클레이브 근거 보강
t82 = find("장비필요성확보 경로금액", "tbl")
for tr in rows(t82):
    c = tr.findall(q("tc"))
    if text(c[0]).startswith("scCO₂ 다단감압 오토클레이브"):
        set_cell(c[4], text(c[4]) + ". [Rev.1] 20 L 용기를 7 MPa에서 0.2 s에 감압하려면 평균 CO₂ 배출 약 16.5 kg/s(DN40급 고속밸브, 줄-톰슨 냉각 대책) 필요 → 시편 단계는 ≤ 1 L 고속감압 셀을 우선 구성하고 동일 예산 내에서 사양 분할")
p228 = find("※ 자체 구축 장비 총 535 백만원")
set_par(p228, text(p228) + " Rev.1: 장비 예산 총액은 변동 없음. 오토클레이브 사양을 \"≤ 1 L 고속감압 셀 + 20 L 스케일업 용기\"로 분할하고, 감압 곡선(속도·균일도)을 구매 사양서에 명시한다.")

# 12. 9.1 TRL 표
t91 = find("연차TRL주요 과업", "tbl")
for tr in rows(t91):
    c = tr.findall(q("tc"))
    if text(c[0]) == "1년차":
        set_cell(c[3], "[Rev.1] S0 Go/No-go 통과(나노기공 상·n_strata,0 ≥ 1) 및 압축상태 k_eff 실측 → 총두께 확정, " + text(c[3]))
    elif text(c[0]) == "2년차":
        set_cell(c[3], text(c[3]) + ", [Rev.1] 확정 두께에서 압축·분포형 셀 조건 TP 해석 여유 ≥ 10 ℃")
p240 = find("각 연차 말에 Stage Gate를 두고")
set_par(p240, text(p240) + " [Rev.1] 1년차 6개월 시점의 S0 판정에서 미달하면 Plan B(에어로겔 층 적층)로 전환하며, 이 경우 2년차 이후 과업은 적층·접착 계면 신뢰성 중심으로 재편한다.")

# 13. 9.2 결론
p243 = find("첫째, 총두께 1.50 mm 셀간 패드로")
set_par(p243, text(p243) + " **단, Rev.1 재해석에서 이 결론은 비압축 두께·집중용량 셀 조건에서만 성립한다. 0.25 MPa 압축 상태에서는 1.50 mm로 성립하지 않으며, 에어로겔급 k_eff 기준 총두께 2.0~2.5 mm가 필요하다(5.5절, 표 5-5).**")
fin = find("최종 결론", "tbl")
callout_add(fin, "[Rev.1] 남은 것은 효과의 크기만이 아니다. 층분리의 실제 형성 여부와 압축 상태 코어 열전도도를 1년차 S0에서 먼저 실측하고, 그 값으로 총두께(2.0~3.0 mm)를 확정한 뒤 본 레시피 또는 Plan B로 진행한다.")

# 14. 부록 A-3, A-4, B, C
ta3 = find("순서스크립트산출", "tbl")
add_row(ta3, ["8 [Rev.1]", "recipes/seion_tp/tp_cellmodel.py, run_cases.py, required_k.py, thick_option.py, figs.py", "보정 3종 대리 모델·두께별 k0 상한 → 표 5-4·5-5, Fig.16"])
ta4 = find("점검 항목조건결과판정스트라타", "tbl")
add_row(ta4, ["셀 모델 (Rev.1)", "집중 → 분포형 k 0.3~1.0", "Cal-2: +2~6 ℃ / Cal-1·3: 225~339 ℃", "보정(셀 방열) 의존 — 조건 명시 필요"])
add_row(ta4, ["압축 상태 (Rev.1)", "0.25 MPa, 코어 0.34 mm", "집중 166~183 ℃ / 분포형 160~390 ℃", "!!부적합 (보정 무관)!!"])
add_row(ta4, ["1.50 mm 통과 k0 (Rev.1)", "압축·분포형 셀", "k0 ≤ 0.006~0.008 W/m·K", "!!다공 재료로 도달 불가!!"])
tb1 = find("파라미터E1 (실측)P0", "tbl")
add_row(tb1, ["압축상태 코어 유효 열전도도 k_eff [Rev.1]", "—", "0.025 (구조 기반 추정)", "≤ 0.015 W/m·K (총두께 결정 입력)", "1년차 S0 — 압축 지그 Hot Disk"])
add_row(tb1, ["원 해석의 인접 셀 방열 조건 [Rev.1]", "—", "Fig.1 거동 역산 시 약 120 W/m²K", "—", "원 해석 코드(sim/model.py) 확인"])
add_row(tb1, ["발포 전 코어 두께 / 층분리 시점 n_strata [Rev.1]", "—", "126 μm / 0.41 (계산)", "n_strata,0 ≥ 1", "1년차 S0 — 단면 SEM 시계열"])
add_row(tb1, ["인접 셀 젤리롤 두께방향 k [Rev.1]", "—", "0.3 ~ 1.0 W/m·K", "—", "수요처 셀 데이터 입수"])
tc1 = find("번호제목본문 위치Fig.1", "tbl")
add_row(tc1, ["Fig.16", "인접 셀 표면온도(셀 모델·압축별) 및 총두께별 통과 k0 상한 [Rev.1]", "5.5"])
ref13 = find("[13] ISO 22007-2")
newref = copy.deepcopy(ref13)
set_par(newref, "[14] T. C. Merkel, V. I. Bondar, K. Nagai, B. D. Freeman, I. Pinnau, \"Gas sorption, diffusion, and permeation in poly(dimethylsiloxane)\", J. Polym. Sci. B: Polym. Phys. 38 (2000) 415–434. (무충전 PDMS의 CO₂ 확산계수 — 값 원문 대조 필요[검증필요])")
ref13.addnext(newref)

# 그림 문단: 줄간격 자동 명시 (LibreOffice·Google Docs 에서 그림 잘림 방지)
for d in body.iter(q("drawing")):
    p_ = d.getparent().getparent()
    sp = p_.find(f"{q('pPr')}/{q('spacing')}")
    sp.set(q("line"), "240")
    sp.set(q("lineRule"), "auto")

tree.write(DOC, xml_declaration=True, encoding="UTF-8", standalone=True)
print("Rev.1 edits applied")
