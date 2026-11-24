"""도면대장 · 배포처 · 수령확인 읽기와 배포 현황 계산.

도면대장 시트 (한 줄 = 도면 한 판(Rev)):
  도면번호 | 도면명 | 공사명 | Rev | 승인일 | 개정내용 | 파일 | 배포처 | 상태
  - 같은 도면번호의 여러 줄 중 승인일이 가장 늦은 줄(같으면 아래 줄)이 최신 판
  - 파일   : 같은 드라이브 폴더에 올린 PDF 파일 이름 (없어도 됨)
  - 배포처 : 배포처 시트의 '키'를 쉼표로 (예: talent, nara)
  - 상태   : '폐기'라고 쓰면 그 도면 전체를 폐기로 표시
배포처 시트: 키 | 이름 | 회사 | 역할
수령확인 시트(구글 시트, 앱스 스크립트가 자동 기록): 시각 | 도면번호 | Rev | 수신자 | 확인
"""
from __future__ import annotations

import datetime as dt
import io
import re
from dataclasses import dataclass, field

import openpyxl

from .dates import normalize_cell, to_date


@dataclass
class Revision:
    rev: str
    date: dt.date | None
    note: str
    file: str
    recipients: list
    row: int


@dataclass
class Drawing:
    no: str
    title: str
    project: str
    revisions: list = field(default_factory=list)
    withdrawn: bool = False

    @property
    def latest(self) -> Revision:
        return max(self.revisions, key=lambda r: (r.date or dt.date.min, r.row))

    def rev_index(self, rev: str) -> int:
        order = sorted(self.revisions, key=lambda r: (r.date or dt.date.min, r.row))
        revs = [r.rev for r in order]
        return revs.index(rev) if rev in revs else -1


@dataclass
class Recipient:
    key: str
    name: str
    company: str
    role: str


def _clean(v) -> str:
    return re.sub(r"\s+", " ", normalize_cell(v)).strip()


def _table(ws, must: str):
    """'must' 머리글이 있는 행을 찾아 {머리글: 열} 과 그 행 번호."""
    for r in range(1, min(ws.max_row, 15) + 1):
        heads = {_clean(c.value).replace(" ", ""): c.column for c in ws[r] if c.value not in (None, "")}
        if must in heads:
            return heads, r
    return None, None


def _find_ws(wb, word):
    return next((ws for ws in wb.worksheets if word in ws.title.replace(" ", "")), None)


def parse_register(data: bytes, warnings: list) -> tuple[list, dict]:
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    reg, rcp = _find_ws(wb, "도면대장"), _find_ws(wb, "배포처")
    drawings: dict[str, Drawing] = {}
    recipients: dict[str, Recipient] = {}
    if rcp is not None:
        heads, r0 = _table(rcp, "키")
        if heads:
            g = lambda r, k: _clean(rcp.cell(r, heads[k]).value) if k in heads else ""  # noqa: E731
            for r in range(r0 + 1, rcp.max_row + 1):
                k = g(r, "키")
                if k:
                    recipients[k] = Recipient(k, g(r, "이름") or k, g(r, "회사"), g(r, "역할"))
    if reg is None:
        return [], recipients
    heads, r0 = _table(reg, "도면번호")
    if not heads:
        warnings.append(("error", "도면대장 시트에서 '도면번호' 머리글을 찾지 못했습니다."))
        return [], recipients
    col = lambda name: next((c for h, c in heads.items() if h.startswith(name)), None)  # noqa: E731
    cols = {k: col(k) for k in ("도면번호", "도면명", "공사명", "Rev", "승인일", "개정내용", "파일", "배포처", "상태")}
    v = lambda r, k: reg.cell(r, cols[k]).value if cols[k] else None  # noqa: E731
    for r in range(r0 + 1, reg.max_row + 1):
        no = _clean(v(r, "도면번호"))
        if not no:
            continue
        rev = _clean(v(r, "Rev"))
        if not rev:
            warnings.append(("warn", f"[도면 {no}] {r}행에 Rev 가 없어 건너뜁니다."))
            continue
        d = drawings.setdefault(no, Drawing(no, _clean(v(r, "도면명")), _clean(v(r, "공사명"))))
        d.title = _clean(v(r, "도면명")) or d.title
        d.project = _clean(v(r, "공사명")) or d.project
        keys = [k.strip() for k in re.split(r"[,，/·\s]+", _clean(v(r, "배포처"))) if k.strip()]
        for k in keys:
            if k not in recipients:
                warnings.append(("warn", f"[도면 {no} Rev {rev}] 배포처 '{k}'가 배포처 시트에 없습니다."))
        date = to_date(v(r, "승인일"))
        if date is None:
            warnings.append(("warn", f"[도면 {no} Rev {rev}] 승인일이 없습니다."))
        if any(x.rev == rev for x in d.revisions):
            warnings.append(("check", f"[도면 {no}] Rev {rev} 가 두 번 적혀 있습니다."))
        d.revisions.append(Revision(rev, date, _clean(v(r, "개정내용")), _clean(v(r, "파일")),
                                    [k for k in keys if k in recipients], r))
        if "폐기" in _clean(v(r, "상태")):
            d.withdrawn = True
    return list(drawings.values()), recipients


def parse_receipts(data: bytes) -> list[dict]:
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    ws = _find_ws(wb, "수령확인")
    if ws is None:
        return []
    heads, r0 = _table(ws, "도면번호")
    if not heads:
        return []
    g = lambda r, k: ws.cell(r, heads[k]).value if k in heads else None  # noqa: E731
    out = []
    for r in range(r0 + 1, ws.max_row + 1):
        no = _clean(g(r, "도면번호"))
        if not no:
            continue
        t = g(r, "시각")
        out.append({"no": no, "rev": _clean(g(r, "Rev")), "who": _clean(g(r, "수신자")),
                    "at": t if isinstance(t, dt.datetime) else None})
    return out


def has_sheet(data: bytes, word: str) -> bool:
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True)
        return any(word in n.replace(" ", "") for n in wb.sheetnames)
    except Exception:  # noqa: BLE001
        return False


def status(drawings: list, recipients: dict, receipts: list, asof: dt.date, recent_days: int = 14) -> dict:
    """최신 판 기준 배포·수령 현황."""
    acks = {}
    for a in receipts:
        k = (a["no"], a["rev"], a["who"])
        if k not in acks:
            acks[k] = a["at"]                       # 처음 확인한 시각을 남김
        elif a["at"] and (acks[k] is None or a["at"] < acks[k]):
            acks[k] = a["at"]
    rows = []
    for d in sorted(drawings, key=lambda x: (x.latest.date or dt.date.min), reverse=True):
        lt = d.latest
        who = []
        for k in lt.recipients:
            rc = recipients[k]
            at = acks.get((d.no, lt.rev, k))
            who.append({"key": k, "name": rc.name, "company": rc.company, "role": rc.role,
                        "acked": (d.no, lt.rev, k) in acks, "at": at})
        rows.append({"drawing": d, "latest": lt, "recipients": who,
                     "pending": sum(1 for w in who if not w["acked"]),
                     "recent": bool(lt.date and 0 <= (asof - lt.date).days <= recent_days)})
    recent = [r for r in rows if r["recent"]]
    return {"rows": rows, "recent": recent, "pending": sum(r["pending"] for r in rows),
            "recent_pending": sum(r["pending"] for r in recent)}


def load_from_files(files, warnings: list):
    """폴더의 파일들 중 가장 최근 '도면대장'(+배포처) 과 '수령확인' 시트를 읽는다. files 는 최신순."""
    drawings, recipients, receipts = [], {}, []
    got_reg = got_ack = False
    for f in files:
        if got_reg and got_ack:
            break
        try:
            data = f.load()
        except Exception:  # noqa: BLE001
            continue
        if not got_reg and has_sheet(data, "도면대장"):
            drawings, recipients = parse_register(data, warnings)
            got_reg = True
        if not got_ack and has_sheet(data, "수령확인"):
            receipts = parse_receipts(data)
            got_ack = True
    return drawings, recipients, receipts


def memoize(files):
    """드라이브 파일을 한 번만 내려받도록 load 를 캐시한다 (업무현황·도면대장을 같은 목록에서 읽으므로)."""
    for f in files:
        orig, box = f.load, {}

        def load(orig=orig, box=box):
            if "d" not in box:
                box["d"] = orig()
            return box["d"]
        f.load = load
    return files
