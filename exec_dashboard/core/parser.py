"""㈜원이엔지 '업무 현황' 엑셀을 표준 데이터로 변환한다.

시트 구성 (이름에 아래 단어가 들어가면 인식, 순서·위치는 자유):
  업무 현황          : 공사명별 도면/발주/납품/설치/인도 일정  (필수)
  도면 현황          : 승인도/공사도/완성도                     (선택, 업무현황 보완)
  발주업체           : 외주업체·담당자·특성                     (선택)
  수주               : 공사명, 고객사, 수주일, 수주금액          (선택, 템플릿 제공)
  수금               : 공사명, 구분, 청구예정일, 청구금액, 수금일, 수금액
  외주비             : 공사명, 업체, 품목, 발주금액, 지급예정일, 지급일, 지급액
"""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import re
from dataclasses import dataclass, field, asdict
from typing import Optional

import openpyxl

from . import config
from .dates import find_dates, normalize_cell, parse_range, to_date


@dataclass
class Milestone:
    key: str
    date: dt.date
    precision: str
    source: str  # 원문

    @property
    def name(self) -> str:
        return config.MILESTONES.get(self.key, (self.key,))[0]


@dataclass
class Project:
    name: str
    row: int
    client: str = ""
    milestones: dict = field(default_factory=dict)   # key -> Milestone
    raw: dict = field(default_factory=dict)          # 열 이름 -> 원문
    timeline_notes: list = field(default_factory=list)
    remark: str = ""


@dataclass
class Vendor:
    item: str
    name: str
    contact: str
    phone_mail: str
    traits: str
    category: str
    scope_clients: list
    scope_tokens: list
    risk_flags: list


@dataclass
class Workbook:
    file_name: str
    file_hash: str
    report_date: Optional[dt.date]
    revision: str
    company: str
    projects: list
    vendors: list
    orders: list        # dict rows
    collections: list
    outsourcing: list
    warnings: list
    sheets: list

    @property
    def has_finance(self) -> bool:
        return bool(self.orders or self.collections or self.outsourcing)


# ---------------------------------------------------------------- helpers
def _find_sheet(wb, *keywords):
    for ws in wb.worksheets:
        title = ws.title.replace(" ", "")
        if any(k.replace(" ", "") in title for k in keywords):
            return ws
    return None


def _find_cell(ws, text, max_row=15):
    for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, max_row)):
        for c in row:
            if isinstance(c.value, str) and c.value.replace(" ", "").replace("\n", "") == text:
                return c
    return None


def _clean(s) -> str:
    return re.sub(r"\s+", " ", normalize_cell(s)).strip()


def client_of(project_name: str) -> str:
    for kw, client in config.CLIENT_RULES:
        if kw in project_name:
            return client
    return "기타"


def _labeled_dates(text, kind):
    """'승인도 : 25.07.03\\n완성도 : 26.06.05' -> [(key, ParsedDate, 원문줄)]"""
    out = []
    s = normalize_cell(text)
    if not s.strip():
        return out
    labels = config.LABEL_MAP[kind]
    for line in re.split(r"[\n\r]+", s):
        line = line.strip()
        if not line:
            continue
        ds = find_dates(line)
        if not ds:
            continue
        key = labels["_"]
        if ":" in line or "：" in line:
            label = re.split(r"[:：]", line, 1)[0].strip()
            for kw, k in labels.items():
                if kw != "_" and kw in label:
                    key = k
                    break
        else:
            for kw, k in labels.items():
                if kw != "_" and kw in line:
                    key = k
                    break
        out.append((key, ds[-1], line))
    return out


def _put(project: Project, key, pdate, source, prefer="max"):
    cur = project.milestones.get(key)
    if cur is None or (prefer == "max" and pdate.date > cur.date):
        project.milestones[key] = Milestone(key, pdate.date, pdate.precision, source)


# ---------------------------------------------------------------- 업무 현황
def _parse_status_sheet(ws, warnings):
    name_cell = _find_cell(ws, "공사명", max_row=30)
    if name_cell is None:
        warnings.append(("error", f"'{ws.title}' 시트에서 '공사명' 칸을 찾지 못했습니다."))
        return [], None, ""
    header_row = None
    col_kind = {}
    for r in range(1, name_cell.row):
        for c in ws[r]:
            v = _clean(c.value)
            if not v:
                continue
            if "승인도" in v or ("도면" in v and "제출" in v):
                col_kind[c.column] = "drawing"; header_row = r
            elif v == "발주":
                col_kind[c.column] = "order"; header_row = r
            elif v == "납품":
                col_kind[c.column] = "delivery"; header_row = r
            elif "설치" in v and "시운전" in v:
                col_kind[c.column] = "install"; header_row = r
            elif "인도" in v or "출항" in v:
                col_kind[c.column] = "handover"; header_row = r
            elif v == "비고":
                col_kind[c.column] = "remark"; header_row = r
    if header_row is None:
        warnings.append(("error", "업무 현황 시트의 머리글(승인도/발주/납품/…)을 찾지 못했습니다."))
        return [], None, ""
    timeline_start = max(col_kind) + 1 if col_kind else name_cell.column + 1

    # 보고일/REV
    report_date, revision = None, ""
    for row in ws.iter_rows(min_row=1, max_row=header_row):
        for c in row:
            v = _clean(c.value)
            if v == "DATE":
                for cc in row[c.column:]:
                    if cc.value is not None:
                        report_date = to_date(cc.value); break
            if v.startswith("REV"):
                for cc in row[c.column:]:
                    if cc.value is not None:
                        revision = _clean(cc.value); break

    projects = []
    name_col = name_cell.column + 1 if _clean(ws.cell(name_cell.row, name_cell.column + 1).value) else name_cell.column
    # '공사명' 머리글이 B열이고 실제 이름이 C열에 있는 구조를 지원
    for r in range(name_cell.row, ws.max_row + 1):
        pname = _clean(ws.cell(r, name_col).value)
        if not pname or pname == "공사명":
            continue
        has_schedule = any(_clean(ws.cell(r, c).value) for c, k in col_kind.items() if k != "remark")
        if not has_schedule:
            break  # 범례 영역 시작
        p = Project(name=pname, row=r, client=client_of(pname))
        for col, kind in col_kind.items():
            v = ws.cell(r, col).value
            txt = normalize_cell(v).strip()
            p.raw[kind] = txt
            if not txt:
                continue
            if kind in ("drawing", "order", "delivery"):
                parsed = _labeled_dates(v, kind)
                if not parsed and txt not in ("-", "해당없음"):
                    warnings.append(("warn", f"[{pname}] '{txt}' 날짜를 읽지 못했습니다 (열: {kind})."))
                for key, pd_, line in parsed:
                    _put(p, key, pd_, line)
            elif kind == "install":
                s, e = parse_range(v)
                if s:
                    _put(p, "INSTALL_START", s, txt)
                if e:
                    _put(p, "INSTALL_END", e, txt)
                if not s and not e:
                    warnings.append(("warn", f"[{pname}] 설치·시운전 기간 '{txt}'을 읽지 못했습니다."))
            elif kind == "handover":
                ds = find_dates(v)
                if ds:
                    _put(p, "HANDOVER", ds[0], txt)
                elif txt not in ("해당없음", "-"):
                    warnings.append(("warn", f"[{pname}] 인도일 '{txt}'을 읽지 못했습니다."))
            elif kind == "remark":
                p.remark = txt
        for c in range(timeline_start, ws.max_column + 1):
            t = _clean(ws.cell(r, c).value)
            if t:
                p.timeline_notes.append(t)
        projects.append(p)
    return projects, report_date, revision


def _merge_drawing_sheet(ws, projects, warnings):
    name_cell = _find_cell(ws, "공사명", max_row=30)
    if not name_cell:
        return
    cols = {}
    for r in range(1, name_cell.row):
        for c in ws[r]:
            v = _clean(c.value)
            if v.startswith("승인도"):
                cols[c.column] = "DWG_APPROVAL"
            elif v.startswith("공사도"):
                cols[c.column] = "DWG_CONSTRUCTION"
            elif v.startswith("완성도"):
                cols[c.column] = "DWG_FINAL"
    by_name = {p.name: p for p in projects}
    for r in range(name_cell.row, ws.max_row + 1):
        pname = _clean(ws.cell(r, name_cell.column + 1).value) or _clean(ws.cell(r, name_cell.column).value)
        p = by_name.get(pname)
        if not p:
            continue
        for col, key in cols.items():
            v = ws.cell(r, col).value
            for k2, pd_, line in _labeled_dates(v, "drawing"):
                k = key if ":" not in line else k2
                existing = p.milestones.get(k)
                if existing is None:
                    _put(p, k, pd_, f"도면현황: {line}")
                elif existing.date != pd_.date:
                    warnings.append(("warn", f"[{pname}] {config.MILESTONES[k][0]} 날짜가 시트마다 다릅니다: "
                                             f"업무현황 {existing.date:%y.%m.%d} / 도면현황 {pd_.date:%y.%m.%d}"))


def _parse_vendor_sheet(ws):
    hdr = _find_cell(ws, "발주업체", max_row=15)
    if not hdr:
        return []
    r0 = hdr.row
    heads = {_clean(c.value).replace(" ", ""): c.column for c in ws[r0] if c.value}
    col = lambda *ks: next((heads[k] for k in heads if any(x in k for x in ks)), None)  # noqa: E731
    c_item, c_name, c_person, c_tel, c_trait = col("품목"), col("발주업체"), col("담당"), col("전화", "메일"), col("특성")
    vendors = []
    for r in range(r0 + 1, ws.max_row + 1):
        name = _clean(ws.cell(r, c_name).value) if c_name else ""
        if not name:
            continue
        item_raw = normalize_cell(ws.cell(r, c_item).value) if c_item else ""
        traits = normalize_cell(ws.cell(r, c_trait).value).strip() if c_trait else ""
        item_flat = _clean(item_raw)
        category = next((cat for kw, cat in config.VENDOR_CATEGORY_RULES if kw in item_flat), "MISC")
        scope = re.findall(r"\(([^)]*)\)", item_flat)
        clients, tokens = [], []
        for sc in scope:
            for part in re.split(r"[/,]", sc):
                part = part.strip()
                for kw, client in config.CLIENT_RULES + [("강남", "강남")]:
                    if kw in part and client not in clients:
                        clients.append(client)
                tokens += re.findall(r"\d+척", part)
        vendors.append(Vendor(
            item=item_flat, name=name,
            contact=_clean(ws.cell(r, c_person).value) if c_person else "",
            phone_mail=normalize_cell(ws.cell(r, c_tel).value).strip() if c_tel else "",
            traits=traits, category=category, scope_clients=clients, scope_tokens=tokens,
            risk_flags=[k for k in config.VENDOR_RISK_KEYWORDS if k in traits],
        ))
    return vendors


# ---------------------------------------------------------------- 금액 시트
_AMOUNT_RE = re.compile(r"[^\d.\-]")


def to_amount(v) -> Optional[float]:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    mult = 1
    if s.endswith("억"):
        mult, s = 100_000_000, s[:-1]
    elif s.endswith("만원") or s.endswith("만"):
        mult, s = 10_000, s.rstrip("원").rstrip("만")
    s = _AMOUNT_RE.sub("", s)
    try:
        return float(s) * mult
    except ValueError:
        return None


FIN_SCHEMAS = {
    "orders": {"공사명": "project", "고객사": "client", "수주일": "order_date",
               "수주금액": "amount", "계약조건": "terms", "비고": "note"},
    "collections": {"공사명": "project", "구분": "kind", "청구예정일": "due_date", "청구금액": "billed",
                    "수금일": "paid_date", "수금액": "paid", "비고": "note"},
    "outsourcing": {"공사명": "project", "업체": "vendor", "품목": "item", "발주금액": "amount",
                    "지급예정일": "due_date", "지급일": "paid_date", "지급액": "paid", "비고": "note"},
}
_DATE_FIELDS = {"order_date", "due_date", "paid_date"}
_AMT_FIELDS = {"amount", "billed", "paid"}


def _parse_table(ws, schema, warnings):
    hdr = _find_cell(ws, "공사명", max_row=15)
    if not hdr:
        warnings.append(("warn", f"'{ws.title}' 시트에 '공사명' 머리글이 없어 건너뜁니다."))
        return []
    colmap = {}
    for c in ws[hdr.row]:
        h = _clean(c.value).replace(" ", "")
        h = re.sub(r"\(.*\)", "", h)
        for k, f in schema.items():
            if h.startswith(k):
                colmap[c.column] = f
    rows, last_project = [], ""
    for r in range(hdr.row + 1, ws.max_row + 1):
        rec = {f: ws.cell(r, c).value for c, f in colmap.items()}
        if not any(v not in (None, "") for v in rec.values()):
            continue
        for f in list(rec):
            if f in _DATE_FIELDS:
                rec[f] = to_date(rec[f])
            elif f in _AMT_FIELDS:
                rec[f] = to_amount(rec[f])
            else:
                rec[f] = _clean(rec[f])
        if not rec.get("project"):
            rec["project"] = last_project  # 병합/빈칸이면 윗줄 공사명 이어받기
        last_project = rec["project"]
        if not any(rec.get(f) for f in _AMT_FIELDS):
            continue  # 금액이 하나도 없는 줄(빈 양식)은 무시
        rows.append(rec)
    return rows


# ---------------------------------------------------------------- main
def parse_workbook(data: bytes, file_name: str = "") -> Workbook:
    warnings = []
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    status_ws = _find_sheet(wb, "업무현황", "업무 현황")
    if status_ws is None:
        status_ws = wb.worksheets[0]
        warnings.append(("warn", f"'업무 현황' 시트가 없어 첫 시트 '{status_ws.title}'를 읽었습니다."))
    projects, report_date, revision = _parse_status_sheet(status_ws, warnings)
    company = _clean(status_ws["B1"].value) if status_ws["B1"].value else ""

    dws = _find_sheet(wb, "도면현황", "도면")
    if dws is not None and dws is not status_ws:
        _merge_drawing_sheet(dws, projects, warnings)

    vws = _find_sheet(wb, "발주업체")
    vendors = _parse_vendor_sheet(vws) if vws is not None else []

    def fin(key, *names):
        ws = _find_sheet(wb, *names)
        return _parse_table(ws, FIN_SCHEMAS[key], warnings) if ws is not None else []

    orders = fin("orders", "수주")
    collections = fin("collections", "수금")
    outsourcing = fin("outsourcing", "외주비", "외주")

    known = {p.name for p in projects}
    for rows, label in ((orders, "수주"), (collections, "수금"), (outsourcing, "외주비")):
        for rec in rows:
            if rec.get("project") and rec["project"] not in known:
                warnings.append(("warn", f"[{label}] 공사명 '{rec['project']}'이(가) 업무 현황에 없습니다."))

    _sanity_checks(projects, warnings)
    return Workbook(
        file_name=file_name, file_hash=hashlib.sha1(data).hexdigest()[:12],
        report_date=report_date, revision=revision, company=company,
        projects=projects, vendors=vendors, orders=orders, collections=collections,
        outsourcing=outsourcing, warnings=warnings, sheets=wb.sheetnames,
    )


def _sanity_checks(projects, warnings):
    rules = [
        ("DWG_APPROVAL", "PO_EQUIP", "승인도 제출이 장비 발주보다 늦습니다"),
        ("PO_EQUIP", "DLV_EQUIP", "장비 납품이 발주보다 빠릅니다"),
        ("PO_SUPPORT", "DLV_SUPPORT", "서포트 납품이 발주보다 빠릅니다"),
        ("PO_HOUSING", "DLV_HOUSING", "하우징 납품이 발주보다 빠릅니다"),
        ("INSTALL_START", "INSTALL_END", "설치 종료가 착수보다 빠릅니다"),
        ("INSTALL_END", "HANDOVER", "인도일이 설치·시운전 완료보다 빠릅니다"),
    ]
    for p in projects:
        m = p.milestones
        for a, b, msg in rules:
            if a in m and b in m and m[a].date > m[b].date and m[a].precision == "day":
                warnings.append(("check", f"[{p.name}] {msg} ({m[a].date:%y.%m.%d} → {m[b].date:%y.%m.%d}). 오기 여부 확인 필요."))
        if "HANDOVER" not in m:
            warnings.append(("info", f"[{p.name}] 인도일이 없습니다 ({p.raw.get('handover') or '공란'})."))


def _iso(d):
    return d.isoformat() if d else None


def to_snapshot(wb: Workbook) -> dict:
    """버전 비교용 JSON 요약. 일정 + 금액(수주·수금·외주 결제)을 담는다.

    file_hash 는 '내용' 기준이라, 업무현황 파일은 그대로고 경리부 금액 파일만 바뀌어도 새 버전으로 잡힌다.
    """
    import json
    snap = {
        "file_name": wb.file_name,
        "report_date": _iso(wb.report_date),
        "revision": wb.revision,
        "projects": {p.name: {k: m.date.isoformat() for k, m in p.milestones.items()} for p in wb.projects},
        "orders": {r["project"]: r.get("amount") for r in wb.orders},
        "collected": sum(r.get("paid") or 0 for r in wb.collections),
        "collections": [{"p": r.get("project"), "k": r.get("kind") or "", "due": _iso(r.get("due_date")),
                         "billed": r.get("billed"), "pd": _iso(r.get("paid_date")), "paid": r.get("paid")}
                        for r in wb.collections],
        "payments": [{"p": r.get("project"), "v": r.get("vendor") or "", "i": r.get("item") or "",
                      "amt": r.get("amount"), "due": _iso(r.get("due_date")), "pd": _iso(r.get("paid_date")),
                      "paid": r.get("paid")} for r in wb.outsourcing],
    }
    snap["file_hash"] = hashlib.sha1(json.dumps(snap, sort_keys=True, ensure_ascii=False,
                                                default=str).encode()).hexdigest()[:12]
    return snap
