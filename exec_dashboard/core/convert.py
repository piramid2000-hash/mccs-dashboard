"""어떤 문서든 '배포본 PDF' 로: 변환 + PDF 상태 점검(전자서명·암호).

- PDF          : 그대로
- 그림(png/jpg) : 한 쪽짜리 PDF 로
- 워드·엑셀·파워포인트·한글 등 : LibreOffice(soffice) 로 변환
  한글(.hwp/.hwpx)은 LibreOffice 가 못 여는 경우가 많다 → 실패하면 '한글에서 PDF 로 저장' 안내
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from pypdf import PdfReader

OFFICE_EXT = {".docx", ".doc", ".odt", ".rtf", ".xlsx", ".xls", ".ods", ".csv", ".pptx", ".ppt", ".odp",
              ".hwp", ".hwpx"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}


class ConvertError(Exception):
    """사용자에게 그대로 보여 줄 수 있는 한국어 메시지."""


def _soffice() -> str | None:
    for name in ("soffice", "libreoffice"):
        p = shutil.which(name)
        if p:
            return p
    for p in ("/usr/lib/libreoffice/program/soffice", "/Applications/LibreOffice.app/Contents/MacOS/soffice",
              "C:/Program Files/LibreOffice/program/soffice.exe"):
        if os.path.exists(p):
            return p
    return None


def to_pdf(path: str | Path, timeout: int = 180) -> bytes:
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".pdf":
        return path.read_bytes()
    if ext in IMAGE_EXT:
        from PIL import Image
        im = Image.open(path)
        im = im.convert("RGB")
        buf = io.BytesIO()
        im.save(buf, "PDF", resolution=150)
        return buf.getvalue()
    if ext not in OFFICE_EXT:
        raise ConvertError(f"'{ext}' 형식은 아직 지원하지 않습니다. PDF 로 저장해서 넣어 주세요.")
    office = _soffice()
    if not office:
        raise ConvertError("문서 변환 프로그램(LibreOffice)이 없습니다. 원본 프로그램에서 PDF 로 저장해서 넣어 주세요.")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / ("in" + ext)            # 한글·공백 파일명 문제를 피하려고 복사본으로 변환
        shutil.copyfile(path, src)
        prof = Path(tmp) / "profile"
        cmd = [office, f"-env:UserInstallation=file://{prof}", "--headless", "--norestore",
               "--convert-to", "pdf", "--outdir", tmp, str(src)]
        try:
            subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            raise ConvertError("변환이 너무 오래 걸려 멈췄습니다. 원본 프로그램에서 PDF 로 저장해서 넣어 주세요.")
        out = Path(tmp) / "in.pdf"
        if not out.exists() or out.stat().st_size < 200:
            if ext in (".hwp", ".hwpx"):
                raise ConvertError("한글 문서를 자동으로 PDF 로 바꾸지 못했습니다. 한글에서 [파일 → PDF로 저장하기] 후 그 PDF 를 넣어 주세요.")
            raise ConvertError("PDF 로 바꾸지 못했습니다. 원본 프로그램에서 PDF 로 저장해서 넣어 주세요.")
        return out.read_bytes()


def inspect_pdf(pdf: bytes) -> dict:
    """전자서명·암호·쪽 수. 서명된 PDF 는 원본을 고치면 서명이 깨지므로 QR 표지를 따로 만든다."""
    info = {"pages": 0, "encrypted": False, "signed": False}
    try:
        r = PdfReader(io.BytesIO(pdf))
    except Exception as e:  # noqa: BLE001
        raise ConvertError(f"PDF 를 열 수 없습니다 ({type(e).__name__}). 파일이 손상되지 않았는지 확인해 주세요.")
    info["encrypted"] = bool(r.is_encrypted)
    if r.is_encrypted:
        try:
            r.decrypt("")  # 열기 암호 없이 권한만 걸린 PDF
        except Exception:  # noqa: BLE001
            return info
    try:
        info["pages"] = len(r.pages)
        root = r.trailer["/Root"]
        acro = root.get("/AcroForm")
        acro = acro.get_object() if acro is not None else None
        for f in (acro.get("/Fields", []) if acro else []):
            f = f.get_object()
            if f.get("/FT") == "/Sig" and f.get("/V") is not None:
                info["signed"] = True
                break
        if not info["signed"] and acro and int(acro.get("/SigFlags", 0)) & 1:
            info["signed"] = True
    except Exception:  # noqa: BLE001 - 점검 실패는 '서명 없음'으로 두지 않고 보수적으로
        info["signed"] = True
    return info
