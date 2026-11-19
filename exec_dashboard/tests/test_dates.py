import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.dates import find_dates, parse_range, to_date  # noqa: E402
from core.parser import to_amount  # noqa: E402


def test_day_and_month():
    assert find_dates("승인도 : 25.07.03")[0].date == dt.date(2025, 7, 3)
    m = find_dates("26.11")[0]
    assert m.precision == "month" and m.date == dt.date(2026, 11, 30)
    assert find_dates(27.1)[0].date == dt.date(2027, 10, 31)   # 숫자 27.10 → 27.1
    assert find_dates(27.02)[0].date == dt.date(2027, 2, 28)


def test_range():
    s, e = parse_range("26.02.16 ~ 26.07.11")
    assert s.date == dt.date(2026, 2, 16) and e.date == dt.date(2026, 7, 11)
    s, e = parse_range("~ 26.10.31")
    assert s is None and e.date == dt.date(2026, 10, 31)


def test_amount_and_date():
    assert to_amount("2.1억") == 210_000_000
    assert to_amount("6,300만원") == 63_000_000
    assert to_amount("125,000,000") == 125_000_000
    assert to_date("2026-11-30") == dt.date(2026, 11, 30)
