"""카톡 공유용 HTML 한 파일 만들기.

사용:
  python exec_dashboard/scripts/export_html.py <업무현황.xlsx | 폴더> [-o 보고서.html] [--asof 2026-11-19]
폴더를 주면 가장 최근 업무현황 엑셀 + 수주·수금 파일을 합쳐서 만든다.
"""
import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.html_report import build_html          # noqa: E402
from core.parser import parse_workbook           # noqa: E402
from core.sources import LocalFolderSource       # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("-o", "--out")
    ap.add_argument("--asof", default=dt.date.today().isoformat())
    a = ap.parse_args()
    asof = dt.date.fromisoformat(a.asof)
    p = Path(a.path)
    if p.is_dir():
        wbs = [(parse_workbook(f.load(), f.name), f.name) for f in LocalFolderSource(str(p)).list_files()]
        wb, name = next(((w, n) for w, n in wbs if w.projects), (None, ""))
        fin = next((w for w, _ in wbs if w.has_finance), None)
        if wb and fin and not wb.has_finance:
            wb.orders, wb.collections, wb.outsourcing = fin.orders, fin.collections, fin.outsourcing
    else:
        wb, name = parse_workbook(p.read_bytes(), p.name), p.name
    if not wb:
        sys.exit("업무 현황 엑셀을 찾지 못했습니다.")
    out = Path(a.out or f"업무현황_{asof:%y%m%d}.html")
    out.write_text(build_html(wb, asof, name), encoding="utf-8")
    print(f"생성: {out} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
