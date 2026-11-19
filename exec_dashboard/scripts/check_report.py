"""엑셀 한 개(또는 폴더)를 대시보드와 똑같은 규칙으로 읽고 요약·점검 결과를 출력한다.

사용:
  python exec_dashboard/scripts/check_report.py <파일.xlsx | 폴더> [--asof 2026-11-19] [--json]
  python exec_dashboard/scripts/check_report.py <업무현황.xlsx> --make-template 수주수금_입력양식.xlsx
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import analytics as A                      # noqa: E402
from core.parser import parse_workbook               # noqa: E402
from core.sources import LocalFolderSource           # noqa: E402
from core.template import build_finance_template     # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--asof", default=dt.date.today().isoformat())
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--make-template")
    a = ap.parse_args()
    asof = dt.date.fromisoformat(a.asof)
    p = Path(a.path)
    if p.is_dir():
        files = LocalFolderSource(str(p)).list_files()
        wbs = [parse_workbook(f.load(), f.name) for f in files]
        wb = next((w for w in wbs if w.projects), None)
        fin = next((w for w in wbs if w.has_finance), None)
        if wb and fin and not wb.has_finance:
            wb.orders, wb.collections, wb.outsourcing = fin.orders, fin.collections, fin.outsourcing
    else:
        wb = parse_workbook(p.read_bytes(), p.name)
    if wb is None:
        print("업무 현황 형식의 엑셀이 없습니다."); sys.exit(2)

    if a.make_template:
        Path(a.make_template).write_bytes(build_finance_template([x.name for x in wb.projects],
                                                                 {x.name: x.client for x in wb.projects}))
        print(f"양식 생성: {a.make_template}")
        return

    t = A.project_table(wb, asof)
    fin = A.finance_summary(wb, asof)
    out = {
        "file": wb.file_name, "report_date": str(wb.report_date), "asof": str(asof),
        "projects": len(wb.projects), "vendors": len(wb.vendors),
        "finance_rows": {"수주": len(wb.orders), "수금": len(wb.collections), "외주비": len(wb.outsourcing)},
        "status_counts": t["상태"].value_counts().to_dict(),
        "flagged": t[t["상태"].isin(["위험", "주의"])][["공사명", "상태", "사유"]].to_dict("records"),
        "finance": {k: v for k, v in fin.items() if not isinstance(v, list)},
        "warnings": [{"level": l, "msg": m} for l, m in wb.warnings],
    }
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1, default=str)); return
    print(f"# {wb.file_name}  (기준일 {asof}, 보고서 {wb.report_date})")
    print(f"공사 {len(wb.projects)}건 · 업체 {len(wb.vendors)}곳 · 금액행 {out['finance_rows']}")
    print("\n## 공사 현황")
    print(t[["상태", "공사명", "현재 단계", "진척도", "다음 일정", "인도일"]].to_string(index=False))
    if out["flagged"]:
        print("\n## 확인 필요")
        for r in out["flagged"]:
            print(f"- [{r['상태']}] {r['공사명']}: {r['사유']}")
    print("\n## 데이터 점검")
    for w in out["warnings"] or [{"level": "ok", "msg": "문제 없음"}]:
        print(f"- ({w['level']}) {w['msg']}")


if __name__ == "__main__":
    main()
