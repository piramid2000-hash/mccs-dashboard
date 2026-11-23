import datetime as dt
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.analytics import morning_brief  # noqa: E402


def snap(paid_mid=None, paid_out=None, handover="2027-03-31"):
    return {
        "projects": {"10척 1호정": {"HANDOVER": handover}},
        "orders": {},
        "collections": [{"p": "10척 1호정", "k": "중도금", "due": "2026-11-20", "billed": 7e7,
                         "pd": "2026-11-24" if paid_mid else None, "paid": paid_mid}],
        "payments": [{"p": "10척 1호정", "v": "에이스기공", "i": "장비", "amt": 5e7, "due": "2026-11-24",
                      "pd": "2026-11-24" if paid_out else None, "paid": paid_out}],
    }


WB = SimpleNamespace(collections=[], outsourcing=[], projects=[])


def test_detects_money_and_delay():
    b = morning_brief(snap(), snap(7e7, 2e7, "2027-04-20"), WB, dt.date(2026, 11, 25))
    assert b["new_in"] == [("10척 1호정", "중도금", 7e7, "2026-11-24")]
    assert b["new_out"][0][1] == "에이스기공" and b["new_out"][0][3] == 2e7
    assert b["delays"][0][4] == 20
    assert b["headline"][0].startswith("수금 1건")


def test_partial_payment_counts_only_the_increase():
    b = morning_brief(snap(paid_out=2e7), snap(paid_out=5e7), WB, dt.date(2026, 11, 25))
    assert b["new_out"][0][3] == 3e7


def test_no_previous_report():
    b = morning_brief(None, snap(), WB, dt.date(2026, 11, 25))
    assert not b["has_prev"] and "이전 보고가 없어" in b["headline"][0]
