"""배포용 PDF 도장: 쪽 수 유지, 모든 쪽에 찍힘, 회전 쪽 처리, 암호 PDF 거절."""
import io
import sys
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.pdfgen import canvas

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.pdfstamp import stamp  # noqa: E402

URL = "https://example.github.io/app/d.html#v1/0123456789abcdef/C/key"
LINES = ["200톤10척3호정-승인도", "Rev C · 26.11.20 승인", "QR 스캔: 최신 판인지 확인"]


def _pdf(*sizes, rotate=None):
    b = io.BytesIO()
    c = canvas.Canvas(b)
    for s in sizes:
        c.setPageSize(s); c.drawString(50, 50, "drawing"); c.showPage()
    c.save()
    if rotate is None:
        return b.getvalue()
    w = PdfWriter()
    for i, pg in enumerate(PdfReader(io.BytesIO(b.getvalue())).pages):
        if i == rotate:
            pg.rotate(90)
        w.add_page(pg)
    o = io.BytesIO(); w.write(o); return o.getvalue()


def test_every_page_stamped_and_sizes_kept():
    src = _pdf(landscape(A4), landscape(A3), rotate=1)
    out = PdfReader(io.BytesIO(stamp(src, URL, LINES)))
    assert len(out.pages) == 2
    for pg in out.pages:
        assert "Rev C" in pg.extract_text()  # 도장 글자가 실제로 들어감
    assert round(float(out.pages[0].cropbox.width)) == round(landscape(A4)[0])
    assert out.pages[1].get("/Rotate", 0) == 0  # 회전을 내용에 반영하고 똑바로 찍음


@pytest.mark.parametrize("pos", ["우상", "우하", "좌상", "좌하", "엉뚱한값"])
def test_positions(pos):
    assert PdfReader(io.BytesIO(stamp(_pdf(A4), URL, LINES, pos))).pages[0].extract_text()


def test_encrypted_pdf_is_refused():
    w = PdfWriter(); w.add_page(PdfReader(io.BytesIO(_pdf(A4))).pages[0]); w.encrypt("pw")
    o = io.BytesIO(); w.write(o)
    with pytest.raises(ValueError):
        stamp(o.getvalue(), URL, LINES)
