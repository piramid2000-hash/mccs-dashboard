"""도면 배포 기능을 앱(dist)에 만들어 넣는다.

- dist/docs/<공개id>.enc : 도면 한 장의 정보 + 최신 PDF, 그 도면의 열쇠로만 풀림 (AES-256-GCM)
- dist/docs/config.json  : 수령 확인 주소(앱스 스크립트), 회사 이름 — 비밀 아님
- 대표 앱(data.enc) 안   : '도면' 탭 (수신자별 카톡 보내기·수령 현황), QR 라벨 인쇄 화면
"""
from __future__ import annotations

import base64
import datetime as dt
import html
import json
import secrets as pysecrets
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import doclinks as L
from .drawings import status
from .pdfstamp import stamp

E = html.escape
MAX_PDF = 8 * 1024 * 1024  # 이보다 큰 PDF 는 앱에 넣지 않음 (드라이브 원본 안내)

CSS = """
.docs-tools{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
.btn2{border:1px solid var(--accent);background:var(--card);color:var(--accent);border-radius:10px;padding:9px 14px;font:inherit;font-size:.88rem;font-weight:600;cursor:pointer}
.btn2.solid{background:var(--accent);color:var(--card)}
.btn2:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.dcard{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;display:grid;gap:6px;min-width:0}
.dcard.recent{border-left:4px solid var(--accent)}
.dcard .top{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}
.dcard .no{font-weight:700}
.dcard .rev{margin-left:auto;font-size:.75rem;font-weight:700;padding:2px 9px;border-radius:999px;background:var(--accent-soft);color:var(--accent)}
.dcard .rev.off{background:var(--crit-soft);color:var(--crit)}
.dcard .st{font-size:.82rem;color:var(--ink2)}
.rlist{list-style:none;margin:4px 0 0;padding:0;display:grid;gap:6px}
.rlist li{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:.86rem;border-top:1px dashed var(--line);padding-top:6px}
.rlist .who{flex:1;min-width:120px}
.rlist .who small{color:var(--ink3)}
.ack{font-size:.75rem;font-weight:700;padding:2px 8px;border-radius:999px;white-space:nowrap}
.ack.ok{color:var(--good);border:1px solid var(--good)}
.ack.no{color:var(--warn);border:1px solid var(--warn)}
.rlist button{border:0;background:#FEE500;color:#191600;border-radius:8px;padding:6px 10px;font:inherit;font-size:.8rem;font-weight:700;cursor:pointer}
.labels-bar{display:flex;gap:8px;margin-bottom:12px}
.labels{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px}
.label{background:#fff;color:#111;border:1px solid #bbb;border-radius:8px;padding:10px;display:grid;grid-template-columns:96px 1fr;gap:10px;align-items:center;break-inside:avoid}
.label svg{width:96px;height:96px}
.label b{display:block;font-size:.9rem}
.label span{display:block;font-size:.75rem;color:#333}
.label .hint{color:#555;margin-top:4px}
@media print{.labels-bar{display:none}.labels{grid-template-columns:repeat(3,1fr)}}
"""


def _fmt(d):
    return d.strftime("%y.%m.%d") if d else "-"


def build_docs(out: Path, drawings: list, recipients: dict, receipts: list, *, secret: str, base_url: str,
               ack_url: str, find_file, company: str, asof: dt.date, generated: str, warnings: list) -> dict:
    """도면 파일들을 dist 에 쓰고, 대표 앱에 넣을 HTML·요약을 돌려준다."""
    st = status(drawings, recipients, receipts, asof)
    ddir = out / "docs"
    ddir.mkdir(parents=True, exist_ok=True)
    (ddir / "config.json").write_text(json.dumps({"ack": ack_url or "", "company": company}, ensure_ascii=False),
                                      encoding="utf-8")
    sent_pdf = stamped = 0
    for d in drawings:
        lt = d.latest
        pdf_b64, pdf_name = None, ""
        if lt.file:
            data = find_file(lt.file)
            if data is None:
                warnings.append(("warn", f"[도면 {d.no} Rev {lt.rev}] 파일 '{lt.file}'을 폴더에서 찾지 못했습니다."))
            elif len(data) > MAX_PDF:
                warnings.append(("warn", f"[도면 {d.no}] '{lt.file}'이 8MB 보다 커서 앱에 넣지 않았습니다."))
            else:
                try:  # 배포용 PDF: 모든 쪽 모서리에 QR + 도면번호·Rev·승인일
                    data = stamp(data, L.link(base_url, secret, d.no, lt.rev),
                                 [d.no, f"Rev {lt.rev} · {_fmt(lt.date)} 승인", "QR 스캔: 최신 판인지 확인"], lt.qr_pos)
                    stamped += 1
                except Exception as e:  # noqa: BLE001 - 도장 실패해도 원본은 배포
                    warnings.append(("warn", f"[도면 {d.no}] PDF 에 QR 을 찍지 못해 원본을 넣었습니다 ({type(e).__name__})."))
                pdf_b64, pdf_name = base64.b64encode(data).decode(), lt.file.rsplit(".", 1)[0] + "_배포용.pdf"
                sent_pdf += 1
        order = sorted(d.revisions, key=lambda r: (r.date or dt.date.min, r.row))
        body = {"no": d.no, "title": d.title, "project": d.project, "withdrawn": d.withdrawn,
                "latest": {"rev": lt.rev, "date": lt.date.isoformat() if lt.date else None, "note": lt.note},
                "revisions": [{"rev": r.rev, "date": r.date.isoformat() if r.date else None, "note": r.note}
                              for r in order],
                "recipients": {k: recipients[k].name for r in d.revisions for k in r.recipients},
                "pdf": pdf_b64, "pdf_name": pdf_name, "company": company, "generated": generated}
        iv = pysecrets.token_bytes(12)
        ct = AESGCM(L.doc_key(secret, d.no)).encrypt(iv, json.dumps(body, ensure_ascii=False).encode("utf-8"), None)
        (ddir / f"{L.public_id(secret, d.no)}.enc").write_text(json.dumps({
            "v": 1, "iv": base64.b64encode(iv).decode(), "ct": base64.b64encode(ct).decode(), "generated": generated}),
            encoding="utf-8")

    # ---- 대표 앱: 도면 탭
    cards = []
    for row in st["rows"]:
        d, lt = row["drawing"], row["latest"]
        items = []
        for w in row["recipients"]:
            url = L.link(base_url, secret, d.no, lt.rev, w["key"])
            msg = (f"[{company}] 도면 개정 안내\n{d.project} {d.title} ({d.no}) Rev {lt.rev} 승인 ({_fmt(lt.date)})"
                   + (f"\n개정 내용: {lt.note}" if lt.note else "")
                   + "\n아래 링크에서 최신 도면을 보고 [수령 확인]을 눌러 주세요.")
            ack = (f"<span class='ack ok'>✓ 확인 {w['at']:%m.%d %H:%M}</span>" if w["acked"] and w["at"]
                   else "<span class='ack ok'>✓ 확인</span>" if w["acked"] else "<span class='ack no'>미확인</span>")
            sub = " ".join(x for x in (w["company"] if w["company"] != w["name"] else "", w["role"]) if x)
            items.append(f"<li><span class='who'>{E(w['name'])} <small>{E(sub)}</small></span>{ack}"
                         f"<button type='button' data-share-url='{E(url)}' data-share-text='{E(msg)}'>카톡 보내기</button></li>")
        staff = L.link(base_url, secret, d.no, lt.rev)
        cards.append(
            f"<div class='dcard{' recent' if row['recent'] else ''}'><div class='top'><span class='no'>{E(d.no)}</span>"
            f"<span>{E(d.title)}</span><span class='rev{' off' if d.withdrawn else ''}'>"
            f"{'폐기' if d.withdrawn else 'Rev ' + E(lt.rev)}</span></div>"
            f"<div class='st'>{E(d.project)} · {_fmt(lt.date)} 승인{(' · ' + E(lt.note)) if lt.note else ''} · "
            f"<a href='{E(staff)}' target='_blank' rel='noopener'>도면 열기</a></div>"
            + (f"<ul class='rlist'>{''.join(items)}</ul>" if items else "<div class='st'>배포처 없음</div>") + "</div>")
    head = (f"<h2>도면 배포 <small>최근 14일 개정 {len(st['recent'])}건 · 수령 미확인 {st['pending']}명</small></h2>"
            "<div class='docs-tools'><button type='button' class='btn2' data-go-labels>QR 라벨 인쇄</button>"
            f"<span class='note'>{'수령 확인 주소 미설정: 받은 사람에게 [수령 확인] 버튼이 보이지 않습니다.' if not ack_url else '수령 확인은 다음 자동 업데이트 때 반영됩니다.'}</span></div>")
    tab = (f"<section data-tab='docs'>{head}<div class='list'>{''.join(cards) or '<p class=note>도면대장이 비어 있습니다.</p>'}</div></section>")

    # ---- QR 라벨 (현장 부착용: 최신 판)
    labels = []
    for d in drawings:
        if d.withdrawn:
            continue
        lt = d.latest
        qr = L.qr_svg(L.link(base_url, secret, d.no, lt.rev))
        labels.append(f"<div class='label'>{qr}<div><b>{E(d.no)}</b><span>{E(d.title)}</span>"
                      f"<span>Rev {E(lt.rev)} · {_fmt(lt.date)} 승인</span><span class='hint'>스캔하면 최신 판인지 확인</span></div></div>")
    lab = ("<section data-tab='labels'><div class='labels-bar'><button type='button' class='btn2 solid' data-print-now>인쇄</button>"
           "<button type='button' class='btn2' data-go-docs>도면 목록으로</button></div>"
           f"<div class='labels'>{''.join(labels)}</div></section>")
    return {"html": tab + lab, "css": CSS, "summary": st, "pdfs": sent_pdf, "stamped": stamped, "count": len(drawings)}
