"""매일 아침 대표 브리핑: 폴더의 최신 엑셀을 읽어 어제 대비 변화를 정리하고 메일로 보낸다.

사용:
  python exec_dashboard/scripts/morning_brief.py                    # 환경변수 설정대로 (아래)
  python exec_dashboard/scripts/morning_brief.py --folder inbox --dry-run -o 브리핑.html

환경변수
  GDRIVE_FOLDER_ID, GDRIVE_SERVICE_ACCOUNT   구글 드라이브에서 읽을 때 (없으면 --folder)
  HISTORY_DIR                                 어제 버전 요약 저장 위치 (기본 exec_dashboard/.history)
  SMTP_HOST(기본 smtp.gmail.com) SMTP_PORT(465) SMTP_USER SMTP_PASSWORD   보내는 메일 계정 (Gmail 앱 비밀번호)
  BRIEF_TO                                    받는 사람 (쉼표로 여러 명)
  DASHBOARD_URL                               메일에 넣을 대시보드 주소 (선택)

로그에는 금액·공사명을 찍지 않는다 (GitHub Actions 로그가 공개될 수 있음).
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from core import analytics as A                                   # noqa: E402
from core.history import HistoryStore                             # noqa: E402
from core.html_report import build_html, money                    # noqa: E402
from core.loader import combine                                    # noqa: E402
from core.drawings import load_from_files, memoize, status as dstatus  # noqa: E402
from core.parser import to_snapshot                                # noqa: E402
from core.sources import GoogleDriveSource, LocalFolderSource, load_service_account  # noqa: E402

KST = ZoneInfo("Asia/Seoul")
E = html.escape


def eok(v):
    return f"{(v or 0) / 1e8:,.2f}억"


def email_body(b: dict, wb, asof: dt.date, url: str) -> str:
    """메일 본문: 메일 앱 호환을 위해 인라인 스타일만 사용."""
    t = A.project_table(wb, asof)
    fin = A.finance_summary(wb, asof)
    li = "".join(f"<li style='margin:3px 0'>{E(x)}</li>" for x in b["headline"])
    sec = []

    def block(title, rows):
        if rows:
            sec.append(f"<p style='margin:14px 0 4px;font-weight:700'>{E(title)}</p>"
                       f"<ul style='margin:0;padding-left:18px'>{''.join(rows)}</ul>")

    block("어제 이후 들어온 돈", [f"<li>{E(p)} {E(k)} <b>{money(a)}</b></li>" for p, k, a, d in b["new_in"]])
    block("어제 이후 나간 외주 결제", [f"<li>{E(v or '-')} · {E(p)} {E(i)} <b>{money(a)}</b></li>"
                                for p, v, i, a, d in b["new_out"]])
    block("늦춰진 일정", [f"<li>{E(p)} {E(it)} {E(o)}→{E(n)} <b>+{dd}일</b></li>" for p, it, o, n, dd in b["delays"][:8]])
    block("7일 내 받을 돈", [f"<li>{d:%m.%d}{' ⛔연체' if d < asof else ''} {E(p)} {E(k)} <b>{money(a)}</b></li>"
                         for p, k, a, d in b["due_in"]])
    block("7일 내 줄 돈 (외주)", [f"<li>{d:%m.%d}{' ⚠️지남' if d < asof else ''} {E(v or '-')} · {E(p)} {E(i)} <b>{money(a)}</b></li>"
                              for p, v, i, a, d in b["due_out"]])
    flagged = t[t["상태"].isin(["위험", "주의"])]
    block("확인 필요 공사", [f"<li>{'⛔' if r['상태'] == '위험' else '⚠️'} {E(r['공사명'])} – {E(r['사유'])}</li>"
                         for _, r in flagged.iterrows()])
    money_line = (f"총 수주 {eok(fin['total_order'])} · 수금 {eok(fin['collected'])} ({fin['collect_rate']:.0f}%) · "
             f"미수 {eok(fin['receivable'])} · 외주 미지급 {eok(fin['out_unpaid'])}"
             if fin["total_order"] else "수주·수금 금액 미입력")
    link = (f"<p style='margin:18px 0'><a href='{E(url)}' style='background:#1f5fbf;color:#fff;padding:10px 16px;"
            f"border-radius:8px;text-decoration:none'>대시보드 열기</a></p>") if url else ""
    return (f"<div style='font-family:Apple SD Gothic Neo,Malgun Gothic,sans-serif;font-size:15px;color:#16181d;"
            f"max-width:640px'><p style='color:#555a63;margin:0'>{asof:%Y년 %m월 %d일} 아침 브리핑</p>"
            f"<h2 style='margin:4px 0 10px;font-size:20px'>{E(wb.company or '')} 공사·자금 현황</h2>"
            f"<div style='background:#dfe9f8;border-radius:10px;padding:10px 14px'><ul style='margin:0;padding-left:18px;"
            f"font-weight:600'>{li}</ul></div><p style='color:#555a63;font-size:13px'>{money_line}</p>"
            f"{''.join(sec)}{link}<p style='color:#8a8f98;font-size:12px;margin-top:18px'>전체 보고서는 첨부한 HTML 파일을 "
            f"여세요. 카톡으로 그대로 전달할 수 있습니다.</p></div>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder")
    ap.add_argument("--asof")
    ap.add_argument("--dry-run", action="store_true", help="메일을 보내지 않고 파일만 만든다")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    asof = dt.date.fromisoformat(a.asof) if a.asof else dt.datetime.now(KST).date()

    if a.folder:
        src = LocalFolderSource(a.folder)
    elif os.environ.get("GDRIVE_FOLDER_ID"):
        src = GoogleDriveSource(os.environ["GDRIVE_FOLDER_ID"], load_service_account(os.environ.get("GDRIVE_SERVICE_ACCOUNT")))
    else:
        sys.exit("--folder 또는 GDRIVE_FOLDER_ID 가 필요합니다.")
    files = memoize(src.list_files())
    wb, name, fin_name = combine(files)
    if wb is None:
        sys.exit("업무 현황 엑셀을 찾지 못했습니다.")
    newest = files[0].modified if files else None
    print(f"files={len(files)} finance={'yes' if wb.has_finance else 'no'} newest={newest:%Y-%m-%d %H:%M}" if newest else "")

    hist = HistoryStore(os.environ.get("HISTORY_DIR", str(HERE / ".history")))
    snap = to_snapshot(wb)
    prev = hist.previous_of(snap["file_hash"])
    hist.save(snap)
    brief = A.morning_brief(prev, snap, wb, asof)
    drawings, recipients, receipts = load_from_files(files, wb.warnings)
    if drawings:
        ds = dstatus(drawings, recipients, receipts, asof)
        if ds["recent"] or ds["pending"]:
            brief["headline"].append(f"도면 개정 {len(ds['recent'])}건(14일) · 수령 미확인 {ds['pending']}명")
    stale = newest and (dt.datetime.now() - newest).days >= 2
    if stale:
        brief["headline"].insert(0, f"⚠️ 최근 파일이 {newest:%m.%d} 것입니다. 경리부 업로드를 확인하세요.")

    label = name + (f" + {fin_name}" if fin_name and fin_name != name else "")
    report = build_html(wb, asof, label, brief=brief)
    out = Path(a.out or f"업무현황_{asof:%y%m%d}.html")
    out.write_text(report, encoding="utf-8")
    print(f"report written ({out.stat().st_size // 1024} KB), changes: in={len(brief['new_in'])} "
          f"out={len(brief['new_out'])} delays={len(brief['delays'])}")

    to = [x.strip() for x in os.environ.get("BRIEF_TO", "").split(",") if x.strip()]
    if a.dry_run or not to:
        mail_preview = out.with_name(out.stem + "_메일미리보기.html")
        mail_preview.write_text("<meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
                                + email_body(brief, wb, asof, os.environ.get("DASHBOARD_URL", "")), encoding="utf-8")
        print("메일 발송 생략 (dry-run 또는 BRIEF_TO 없음) → 메일 미리보기 파일 생성")
        return
    msg = EmailMessage()
    msg["Subject"] = f"[아침 브리핑] {asof:%m/%d} {brief['headline'][0][:40]}"
    msg["From"] = os.environ["SMTP_USER"]
    msg["To"] = ", ".join(to)
    msg.set_content("HTML 메일입니다. 첨부 파일을 열어 주세요.")
    msg.add_alternative(email_body(brief, wb, asof, os.environ.get("DASHBOARD_URL", "")), subtype="html")
    msg.add_attachment(report.encode("utf-8"), maintype="text", subtype="html", filename=out.name)
    with smtplib.SMTP_SSL(os.environ.get("SMTP_HOST", "smtp.gmail.com"), int(os.environ.get("SMTP_PORT", "465"))) as s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        s.send_message(msg)
    print(f"메일 발송 완료 → {len(to)}명")


if __name__ == "__main__":
    main()
