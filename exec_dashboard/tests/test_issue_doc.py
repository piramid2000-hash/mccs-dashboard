"""doc-qr-issuer: 도장 발행·서명 PDF 표지 발행·중복 차단·등록부 왕복·변환."""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.convert import ConvertError, inspect_pdf, to_pdf  # noqa: E402
from core.drawings import parse_doc_registry               # noqa: E402

ENV = {**os.environ, "DOC_SECRET": "test-doc-secret-0123456789", "APP_URL": "http://localhost:8710/"}


def _pdf(text="시험성적서 본문"):
    b = io.BytesIO(); c = canvas.Canvas(b, pagesize=A4); c.drawString(60, 700, "report"); c.showPage(); c.save()
    return b.getvalue()


def _run(tmp, src, *args):
    p = subprocess.run([sys.executable, str(ROOT / "scripts/issue_doc.py"), str(src), "--registry", str(tmp / "문서등록부.xlsx"),
                        *args], capture_output=True, text=True, env=ENV)
    out = p.stdout.strip().splitlines()
    return p.returncode, (json.loads(out[-1]) if out and out[-1].startswith("{") else None), p.stderr


def test_stamp_mode_and_registry_roundtrip(tmp_path):
    src = tmp_path / "tr.pdf"; src.write_bytes(_pdf())
    rc, res, err = _run(tmp_path, src, "--type", "시험성적서", "--no", "TR-1", "--title", "성능시험", "--rev", "1",
                        "--date", "2026-11-20", "--fields", "시험일=2026-11-20; 결과=합격", "--issuer", "품질팀")
    assert rc == 0, err
    assert res["mode"] == "도장" and res["verify_url"].startswith("http://localhost:8710/d.html#v1/")
    issued = Path(res["issued"]).read_bytes()
    assert "TR-1" in PdfReader(io.BytesIO(issued)).pages[0].extract_text()
    assert hashlib.sha256(issued).hexdigest() == res["sha_issued"]
    warnings, rcp = [], {}
    docs = parse_doc_registry((tmp_path / "문서등록부.xlsx").read_bytes(), warnings, rcp)
    assert len(docs) == 1 and docs[0].kind == "시험성적서"
    lt = docs[0].revisions[-1]
    assert lt.extra["fields"] == {"시험일": "2026-11-20", "결과": "합격"}
    assert lt.extra["sha_original"] == hashlib.sha256(src.read_bytes()).hexdigest()
    assert lt.extra["sha_issued"] == res["sha_issued"] and lt.extra["mode"] == "도장"

    # 같은 번호·판은 막고, --force 면 허용
    rc, _, err = _run(tmp_path, src, "--type", "시험성적서", "--no", "TR-1", "--title", "성능시험", "--rev", "1")
    assert rc != 0 and "이미 발행" in err
    rc, res2, _ = _run(tmp_path, src, "--type", "시험성적서", "--no", "TR-1", "--title", "성능시험", "--rev", "1", "--force")
    assert rc == 0
    docs = parse_doc_registry((tmp_path / "문서등록부.xlsx").read_bytes(), [], {})
    assert len(docs[0].revisions) == 1                                   # 줄이 늘지 않고 바뀜
    assert docs[0].revisions[0].extra["sha_issued"] == res2["sha_issued"]


def test_signed_pdf_kept_byte_identical_with_cover(tmp_path):
    pytest.importorskip("pyhanko")
    from pyhanko.sign import signers
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    import datetime as dt
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")])
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(1).not_valid_before(dt.datetime(2026, 1, 1)).not_valid_after(dt.datetime(2030, 1, 1))
            .sign(key, hashes.SHA256()))
    (tmp_path / "k.pem").write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                       serialization.NoEncryption()))
    (tmp_path / "c.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    signer = signers.SimpleSigner.load(str(tmp_path / "k.pem"), str(tmp_path / "c.pem"))
    out = io.BytesIO()
    signers.sign_pdf(IncrementalPdfFileWriter(io.BytesIO(_pdf())), signers.PdfSignatureMetadata(field_name="Sig1"),
                     signer=signer, output=out)
    src = tmp_path / "signed.pdf"; src.write_bytes(out.getvalue())
    assert inspect_pdf(src.read_bytes())["signed"]

    rc, res, err = _run(tmp_path, src, "--type", "시험성적서", "--no", "TR-2", "--title", "서명본")
    assert rc == 0, err
    assert res["mode"] == "표지" and res["cover"]
    assert Path(res["issued"]).read_bytes() == src.read_bytes()      # 한 바이트도 안 바뀜
    cover = PdfReader(res["cover"])
    assert len(cover.pages) == 1 and "TR-2" in cover.pages[0].extract_text()


def test_convert_passthrough_and_errors(tmp_path):
    p = tmp_path / "a.pdf"; p.write_bytes(_pdf())
    assert to_pdf(p) == p.read_bytes()
    bad = tmp_path / "x.zzz"; bad.write_bytes(b"nope")
    with pytest.raises(ConvertError):
        to_pdf(bad)


@pytest.mark.skipif(not shutil.which("soffice"), reason="LibreOffice 없음")
def test_convert_xlsx(tmp_path):
    import openpyxl
    wb = openpyxl.Workbook(); wb.active["A1"] = "점검표"; x = tmp_path / "c.xlsx"; wb.save(x)
    pdf = to_pdf(x)
    assert pdf[:4] == b"%PDF" and inspect_pdf(pdf)["pages"] >= 1
