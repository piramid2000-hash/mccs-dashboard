"""엑셀 셀에 적힌 한국식 약식 날짜를 해석한다.

지원 형식 (현업 엑셀에서 실제로 쓰이는 형태):
  25.07.03 / 2025.07.03 / 25-07-03      -> 일 단위
  26.11 / 27.02(숫자) / 27.1(숫자=10월)  -> 월 단위 (해당 월 말일로 간주)
  26.02.16 ~ 26.07.11                    -> 기간
  ~ 26.10.31                             -> 종료일만
  datetime 객체                          -> 그대로
"""
from __future__ import annotations

import calendar
import datetime as dt
import re
from dataclasses import dataclass
from typing import Optional

_DATE_RE = re.compile(r"(?<!\d)(\d{2}|\d{4})[.\-/](\d{1,2})(?:[.\-/](\d{1,2}))?(?!\d)")


@dataclass(frozen=True)
class ParsedDate:
    date: dt.date
    precision: str  # "day" | "month"
    raw: str

    @property
    def label(self) -> str:
        if self.precision == "month":
            return self.date.strftime("%y.%m")
        return self.date.strftime("%y.%m.%d")


def _mk(y: str, m: str, d: Optional[str], raw: str) -> Optional[ParsedDate]:
    year = int(y)
    if year < 100:
        year += 2000
    month = int(m)
    if not 1 <= month <= 12 or not 2000 <= year <= 2100:
        return None
    if d:
        day = int(d)
        last = calendar.monthrange(year, month)[1]
        if not 1 <= day <= last:
            return None
        return ParsedDate(dt.date(year, month, day), "day", raw)
    last = calendar.monthrange(year, month)[1]
    return ParsedDate(dt.date(year, month, last), "month", raw)


def normalize_cell(value) -> str:
    """셀 값을 문자열로. 숫자 27.1 은 '27.10'(10월)로 복원한다."""
    if value is None:
        return ""
    if isinstance(value, dt.datetime):
        return value.strftime("%Y.%m.%d")
    if isinstance(value, dt.date):
        return value.strftime("%Y.%m.%d")
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def find_dates(text) -> list[ParsedDate]:
    """문자열에서 등장 순서대로 모든 날짜를 찾는다."""
    if isinstance(text, (dt.date, dt.datetime)):
        d = text.date() if isinstance(text, dt.datetime) else text
        return [ParsedDate(d, "day", str(text))]
    s = normalize_cell(text)
    out = []
    for m in _DATE_RE.finditer(s):
        p = _mk(m.group(1), m.group(2), m.group(3), m.group(0))
        if p:
            out.append(p)
    return out


def parse_range(text) -> tuple[Optional[ParsedDate], Optional[ParsedDate]]:
    """'26.02.16 ~ 26.07.11' -> (시작, 종료). '~ 26.10.31' -> (None, 종료)."""
    s = normalize_cell(text)
    if "~" in s:
        left, right = s.split("~", 1)
        ls, rs = find_dates(left), find_dates(right)
        return (ls[0] if ls else None, rs[0] if rs else None)
    ds = find_dates(s)
    if len(ds) >= 2:
        return ds[0], ds[1]
    if len(ds) == 1:
        return None, ds[0]
    return None, None


def to_date(value) -> Optional[dt.date]:
    """금액 시트 등에서 쓰는 단일 날짜 변환 (엑셀 날짜·문자열 모두)."""
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    ds = find_dates(value)
    return ds[0].date if ds else None
