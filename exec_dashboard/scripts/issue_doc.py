"""문서 QR 발행 (doc-qr-issuer 스킬이 쓰는 명령)

한 건을 넣으면:
  1) PDF 로 변환 (워드·엑셀·파워포인트·그림, 한글은 가능한 경우)
  2) 전자서명·암호 PDF 면 원본을 그대로 두고 'QR 확인 표지'를 따로 만들고,
     아니면 모든 쪽 모서리에 QR 도장을 찍은 '발행본' PDF 를 만든다
  3) 원본·발행본의 지문(SHA-256)과 함께 '문서등록부' 엑셀에 한 줄 기록
  4) 다음 자동 업데이트 때 확인 페이지·대표 앱 '문서' 탭에 반영 (발행본은 등록부와 같은 폴더에 저장)

사용:
  DOC_SECRET=... APP_URL=https://<계정>.github.io/<저장소>/ \\
  python exec_dashboard/scripts/issue_doc.py 시험성적서.pdf --type 시험성적서 --no TR-2026-0142 \\
      --title "HVAC 유닛 성능시험" --rev 1 --fields "시험일=2026-11-20; 로트=L2611-07; 결과=합격" \\
      --to 탤런트엘엔지,현장반장 --issuer "품질팀 김OO" --registry "<드라이브 폴더>/문서등록부.xlsx"

옵션: --date (기본 오늘), --project, --note(개정 내용), --position 우상|우하|좌상|좌하, --outdir(기본 등록부 폴더),
      --force (같은 번호·판 재발행), --dry-run (파일·등록부를 쓰지 않고 점검만)
결과는 마지막 줄에 JSON 으로 출력한다 (스킬이 읽어 사용자에게 보고).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import openpyxl
from openpyxl.styles import Font, PatternFill

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import doclinks as L                               # noqa: E402
from core.convert import ConvertError, inspect_pdf, to_pdf    # noqa: E402
from core.drawings import DOC_HEADS                           # noqa: E402
from core.pdfstamp import cover_sheet, stamp                  # noqa: E402

KST = ZoneInfo("Asia/Seoul")
GUIDE = [
    "■ 문서등록부 (doc-qr-issuer 가 한 줄씩 기록합니다. 직접 고쳐도 됩니다)",
    "· 같은 문서번호의 가장 늦은 발행일 줄이 최신 판입니다. 옛 줄은 지우지 마세요 (개정 이력).",
    "· 상태에 '폐기'라고 쓰면 QR 을 찍었을 때 '폐기된 문서' 경고가 뜹니다.",
    "· 핵심값: '항목=값; 항목=값' 형식. 확인 페이지에 그대로 보여 종이와 대조할 수 있습니다.",
    "· SHA-256: 파일 지문. 받은 사람이 확인 페이지에서 자기 파일이 원본과 같은지 대조할 때 씁니다.",
    "· 배포처 키는 '배포처' 시트 (도면대장 파일의 배포처도 함께 쓰입니다).",
]


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def safe(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", s).strip("_")[:80] or "문서"


def open_registry(path: Path):
    if path.exists():
        wb = openpyxl.load_workbook(path)
        if "문서등록부" not in wb.sheetnames:
            raise SystemExit(f"'{path.name}' 에 '문서등록부' 시트가 없습니다.")
        return wb
    wb = openpyxl.Workbook()
    g = wb.active
    g.title = "작성안내"
    for i, line in enumerate(GUIDE, 1):
        g.cell(i, 1, line).font = Font(bold=(i == 1))
    g.column_dimensions["A"].width = 110
    ws = wb.create_sheet("문서등록부")
    ws.append(DOC_HEADS)
    for c in ws[1]:
        c.font, c.fill = Font(bold=True), PatternFill("solid", fgColor="DCE7F7")
    for col, w in zip("ABCDEFGHIJKLMNOPQ", [18, 12, 28, 18, 6, 12, 24, 36, 28, 30, 30, 8, 18, 18, 24, 6, 14]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"
    rs = wb.create_sheet("배포처")
    rs.append(["키", "이름", "회사", "역할"])
    return wb


def main():
    ap = argparse.ArgumentParser(description="문서 QR 발행")
    ap.add_argument("input")
    ap.add_argument("--type", required=True, help="문서종류: 시험성적서, MSDS, 작업표준서, 도면 …")
    ap.add_argument("--no", required=True, help="문서번호 (회사 규칙)")
    ap.add_argument("--title", required=True)
    ap.add_argument("--rev", default="1")
    ap.add_argument("--date", default=None)
    ap.add_argument("--project", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--fields", default="", help="'항목=값; 항목=값'")
    ap.add_argument("--to", default="", help="배포처 키, 쉼표로")
    ap.add_argument("--issuer", default="")
    ap.add_argument("--position", default="우상")
    ap.add_argument("--registry", required=True)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--base-url", default=os.environ.get("APP_URL", ""))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    secret = os.environ.get("DOC_SECRET", "")
    if len(secret) < 16:
        sys.exit("DOC_SECRET(16자 이상)이 필요합니다. 매일 업데이트(GitHub Secrets)와 같은 값을 쓰세요.")
    if not a.base_url.startswith("https://") and not a.base_url.startswith("http://localhost"):
        sys.exit("앱 주소(APP_URL 또는 --base-url, https://…)가 필요합니다.")
    src = Path(a.input)
    if not src.exists():
        sys.exit(f"파일이 없습니다: {src}")
    reg_path = Path(a.registry)
    outdir = Path(a.outdir) if a.outdir else reg_path.parent
    date = dt.date.fromisoformat(a.date) if a.date else dt.datetime.now(KST).date()
    no, rev = a.no.strip(), str(a.rev).strip()

    # 등록부: 같은 번호·판 중복, 날짜 역행 점검
    wb = open_registry(reg_path)
    ws = wb["문서등록부"]
    head = {c.value: c.column for c in ws[1] if c.value}
    rows = [{h: ws.cell(r, c).value for h, c in head.items()} for r in range(2, ws.max_row + 1)]
    same = [r for r in rows if str(r.get("문서번호") or "").strip() == no]
    notes = []
    if any(str(r.get("판") or "").strip() == rev for r in same) and not a.force:
        sys.exit(f"'{no}' 판 {rev} 은 이미 발행되어 있습니다. 개정이면 --rev 를 올리고, 재발행이면 --force.")
    later = [r for r in same if isinstance(r.get("발행일"), dt.datetime) and r["발행일"].date() > date]
    if later:
        notes.append(f"주의: 등록부에 이보다 늦은 발행일({later[0]['발행일']:%Y-%m-%d})의 판이 있어, 이 판은 최신이 아닙니다.")
    keys = [k.strip() for k in re.split(r"[,，]", a.to) if k.strip()]
    known = set()
    if "배포처" in wb.sheetnames:
        rs = wb["배포처"]
        known = {str(rs.cell(r, 1).value).strip() for r in range(2, rs.max_row + 1) if rs.cell(r, 1).value}
    unknown = [k for k in keys if k not in known]
    if unknown:
        notes.append(f"배포처 시트에 없는 키: {', '.join(unknown)} (도면대장 파일의 배포처에 있으면 괜찮습니다)")

    # 1) PDF 로
    raw = src.read_bytes()
    try:
        pdf = to_pdf(src)
    except ConvertError as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(2)
    info = inspect_pdf(pdf)

    # 2) 도장 또는 확인 표지
    url = L.link(a.base_url, secret, no, rev)
    base = safe(f"{no}_{'판' if a.type != '도면' else 'Rev'}{rev}")
    lines = [f"{a.type} {no}", f"{'Rev' if a.type == '도면' else '판'} {rev} · {date:%y.%m.%d} 발행", "QR 스캔: 최신 판·원본 확인"]
    cover_name = ""
    if info["signed"] or info["encrypted"]:
        mode = "표지"
        issued_name = f"{base}_원본.pdf"
        issued = pdf  # 서명·암호 보존: 한 바이트도 바꾸지 않음
        cover_name = f"{base}_확인표지.pdf"
        why = "전자서명" if info["signed"] else "암호 설정"
        fields = [x for x in a.fields.split(";") if "=" in x]
        cover = cover_sheet(url, a.title, [("문서종류", a.type), ("문서번호", no), ("판", rev), ("발행일", f"{date:%Y-%m-%d}")]
                            + [(k.strip(), v.strip()) for k, v in (x.split("=", 1) for x in fields)]
                            + ([("발행", a.issuer)] if a.issuer else []) + [("원본 SHA-256", sha256(issued))],
                            f"이 문서는 {why}을 보존하기 위해 원본을 수정하지 않았습니다. 원본과 함께 이 표지를 출력·보관하고, "
                            "QR 을 스캔해 최신 판인지와 받은 파일이 원본인지 확인하세요.")
    else:
        mode = "도장"
        issued_name = f"{base}_발행본.pdf"
        issued = stamp(pdf, url, lines, a.position)
        cover = None

    rec = {"문서번호": no, "문서종류": a.type, "제목": a.title, "공사명": a.project, "판": rev,
           "발행일": dt.datetime(date.year, date.month, date.day), "개정내용": a.note, "핵심값": a.fields.strip(),
           "원본파일": src.name, "발행본": issued_name, "확인표지": cover_name, "발행방식": mode,
           "원본SHA256": sha256(raw), "발행본SHA256": sha256(issued), "배포처": ", ".join(keys), "상태": "",
           "발행자": a.issuer}
    result = {"ok": True, "mode": mode, "pages": info["pages"], "signed": info["signed"], "encrypted": info["encrypted"],
              "issued": str(outdir / issued_name), "cover": str(outdir / cover_name) if cover_name else "",
              "registry": str(reg_path), "verify_url": url, "sha_issued": rec["발행본SHA256"], "notes": notes,
              "dry_run": a.dry_run}
    if not a.dry_run:
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / issued_name).write_bytes(issued)
        if cover is not None:
            (outdir / cover_name).write_bytes(cover)
        if a.force:  # 재발행: 같은 번호·판의 옛 줄을 지우고 새 줄로 (지문이 바뀌므로)
            for r in range(ws.max_row, 1, -1):
                if (str(ws.cell(r, head["문서번호"]).value or "").strip() == no
                        and str(ws.cell(r, head["판"]).value or "").strip() == rev):
                    ws.delete_rows(r)
                    notes.append(f"재발행: 등록부의 옛 '{no}' 판 {rev} 줄을 새 줄로 바꿨습니다.")
        ws.append([rec.get(h, "") for h in [c.value for c in ws[1]]])
        ws.cell(ws.max_row, head["발행일"]).number_format = "yyyy-mm-dd"
        wb.save(reg_path)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
