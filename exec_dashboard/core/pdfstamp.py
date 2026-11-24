"""배포용 도면 PDF: 모든 쪽 모서리에 QR + 도면번호·Rev·승인일 도장을 찍는다.

- QR 은 벡터로 그려 어떤 크기로 출력해도 선명 (기본 24mm: 팔 길이에서 휴대폰으로 읽힘)
- 위치: 우상(기본)·우하·좌상·좌하. 표제란·개정표를 가리면 도면대장 'QR위치' 칸으로 바꿈
- 흰 바탕 상자 위에 찍어 도면 선 위에서도 읽힘
- 회전된 쪽은 회전을 내용에 반영한 뒤 찍어, 보이는 방향 기준으로 모서리를 잡음
- 한글 글꼴(나눔고딕 등)을 PDF 에 넣음. 없으면 영문·숫자만으로 찍음
"""
from __future__ import annotations

import io
import os
import re

from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONT_CANDIDATES = [  # TrueType 한글 글꼴 (CFF 기반 Noto CJK 는 reportlab 이 못 씀)
    ("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 0),
    ("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 0),
    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 0),
    ("/usr/share/fonts/truetype/unfonts-core/UnDotum.ttf", 0),
    ("C:/Windows/Fonts/malgun.ttf", 0),
    ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 0),
]
_FONT = None
POSITIONS = {"우상": "tr", "우하": "br", "좌상": "tl", "좌하": "bl", "tr": "tr", "br": "br", "tl": "tl", "bl": "bl"}


def _font() -> str:
    global _FONT
    if _FONT is None:
        _FONT = "Helvetica"
        extra = os.environ.get("STAMP_FONT")
        for path, idx in ([(extra, 0)] if extra else []) + FONT_CANDIDATES:
            if path and os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont("StampKR", path, subfontIndex=idx))
                    _FONT = "StampKR"
                    break
                except Exception:  # noqa: BLE001 - 다음 후보로
                    continue
    return _FONT


def _ascii(s: str) -> str:
    return re.sub(r"[^\x20-\x7E]", "", s)


def _overlay(w: float, h: float, url: str, lines: list[str], pos: str) -> bytes:
    font = _font()
    if font == "Helvetica":
        lines = [_ascii(x) or "-" for x in lines]
    qr = 24 * mm
    pad, gap, margin = 2.2 * mm, 2.5 * mm, 7 * mm
    sizes = [7.5, 6.5, 6.0]
    tw = max(pdfmetrics.stringWidth(t, font, sz) for t, sz in zip(lines, sizes))
    tw = min(tw, 70 * mm)
    bw, bh = pad + tw + gap + qr + pad, qr + 2 * pad
    x0 = w - margin - bw if pos in ("tr", "br") else margin
    y0 = h - margin - bh if pos in ("tr", "tl") else margin
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))
    c.setFillColorRGB(1, 1, 1)
    c.setStrokeColorRGB(0.12, 0.37, 0.75)
    c.setLineWidth(0.8)
    c.roundRect(x0, y0, bw, bh, 2 * mm, stroke=1, fill=1)
    wd = QrCodeWidget(url, barLevel="M", barBorder=4)
    bx = wd.getBounds()
    d = Drawing(qr, qr, transform=[qr / (bx[2] - bx[0]), 0, 0, qr / (bx[3] - bx[1]), 0, 0])
    d.add(wd)
    renderPDF.draw(d, c, x0 + pad + tw + gap, y0 + pad)
    c.setFillColorRGB(0.07, 0.09, 0.12)
    ty = y0 + bh - pad - 7.5
    for t, sz in zip(lines, sizes):
        while pdfmetrics.stringWidth(t, font, sz) > tw and len(t) > 4:
            t = t[:-2] + "…"
        c.setFont(font, sz)
        c.drawString(x0 + pad, ty, t)
        ty -= sz + 3.2
    c.save()
    return buf.getvalue()


def stamp(pdf: bytes, url: str, lines: list[str], position: str = "우상") -> bytes:
    """pdf 의 모든 쪽에 도장을 찍은 새 PDF. 암호가 걸린 PDF 는 ValueError."""
    pos = POSITIONS.get((position or "").strip(), "tr")
    reader = PdfReader(io.BytesIO(pdf))
    if reader.is_encrypted:
        raise ValueError("암호가 걸린 PDF")
    writer = PdfWriter()
    cache = {}
    for page in reader.pages:
        if page.get("/Rotate", 0):
            page.transfer_rotation_to_content()
        box = page.cropbox
        w, h = float(box.width), float(box.height)
        key = (round(w), round(h))
        if key not in cache:
            cache[key] = PdfReader(io.BytesIO(_overlay(w, h, url, lines, pos))).pages[0]
        page.merge_transformed_page(cache[key], Transformation().translate(float(box.left), float(box.bottom)))
        writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def cover_sheet(url: str, title: str, rows: list[tuple[str, str]], note: str) -> bytes:
    """A4 세로 'QR 확인 표지' 한 장. 전자서명·암호 PDF 처럼 원본을 고치면 안 될 때 함께 배포한다."""
    from reportlab.lib.pagesizes import A4
    font = _font()
    if font == "Helvetica":
        title = _ascii(title) or "Document check sheet"
        rows = [(_ascii(k) or "-", _ascii(v) or "-") for k, v in rows]
        note = _ascii(note)
    w, h = A4
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(title)
    m = 22 * mm
    c.setFillColorRGB(0.12, 0.37, 0.75)
    c.rect(0, h - 14 * mm, w, 14 * mm, stroke=0, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont(font, 11)
    c.drawString(m, h - 9.5 * mm, "문서 확인 표지" if font != "Helvetica" else "Document check sheet")
    c.setFillColorRGB(0.07, 0.09, 0.12)
    c.setFont(font, 18)
    t = title
    while pdfmetrics.stringWidth(t, font, 18) > w - 2 * m and len(t) > 4:
        t = t[:-2] + "…"
    c.drawString(m, h - 34 * mm, t)
    q = 62 * mm
    wd = QrCodeWidget(url, barLevel="M", barBorder=4)
    bx = wd.getBounds()
    d = Drawing(q, q, transform=[q / (bx[2] - bx[0]), 0, 0, q / (bx[3] - bx[1]), 0, 0])
    d.add(wd)
    renderPDF.draw(d, c, (w - q) / 2, h - 44 * mm - q)
    c.setFont(font, 10)
    c.setFillColorRGB(0.33, 0.35, 0.39)
    s = "휴대폰 카메라로 스캔하면 원본·최신 여부를 확인합니다" if font != "Helvetica" else "Scan to check the original and its status"
    c.drawCentredString(w / 2, h - 50 * mm - q, s)
    y = h - 66 * mm - q
    for k, v in rows:
        c.setFillColorRGB(0.33, 0.35, 0.39); c.setFont(font, 9.5); c.drawString(m, y, k)
        c.setFillColorRGB(0.07, 0.09, 0.12); c.setFont(font, 10.5)
        vv = v
        size = 10.5 if len(v) < 60 else 7.6  # 해시는 작게 한 줄
        c.setFont(font, size)
        while pdfmetrics.stringWidth(vv, font, size) > w - 2 * m - 34 * mm and len(vv) > 4:
            vv = vv[:-2] + "…"
        c.drawString(m + 34 * mm, y, vv)
        c.setStrokeColorRGB(0.89, 0.88, 0.86); c.setLineWidth(0.5); c.line(m, y - 3 * mm, w - m, y - 3 * mm)
        y -= 9.5 * mm
    if note:
        c.setFillColorRGB(0.33, 0.35, 0.39); c.setFont(font, 9)
        words, line, ly = note.split(" "), "", y - 4 * mm
        for wd_ in words:
            test = (line + " " + wd_).strip()
            if pdfmetrics.stringWidth(test, font, 9) > w - 2 * m:
                c.drawString(m, ly, line); ly -= 5 * mm; line = wd_
            else:
                line = test
        if line:
            c.drawString(m, ly, line)
    c.showPage()
    c.save()
    return buf.getvalue()
