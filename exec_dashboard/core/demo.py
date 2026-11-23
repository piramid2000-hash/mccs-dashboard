"""예시(익명) 자료: 구글 플레이 심사·스토어 스크린샷·시연용.

실제 업무현황의 '모양'(공사 수, 일정 흐름)만 빌리고 공사명·업체명·금액은 모두 가짜로 바꾼다.
실제 매입매출(금액) 파일은 전혀 쓰지 않는다.
"""
from __future__ import annotations

import datetime as dt

from .parser import Workbook
from .template import demo_finance

REAL_WORDS = ["200톤", "에이스", "탤런트", "탈렌트", "나라냉열", "썬테크", "동일조선", "영광", "제이에스", "ATND", "캐리어",
              "레프코리아", "하이시스", "미스미"]


def anonymize(wb: Workbook, asof: dt.date) -> Workbook:
    for i, p in enumerate(wb.projects):
        p.name = f"예시현장 {chr(65 + i // 4)}-{i % 4 + 1}호"
        p.client = "예시조선" if i < len(wb.projects) - 2 else "예시플랜트"
        p.timeline_notes, p.remark, p.raw = [], "", {}
    names = iter(["협력사 가", "협력사 나", "협력사 다", "협력사 라", "협력사 마", "협력사 바"] + [f"구매처 {k}" for k in range(1, 50)])
    for v in wb.vendors:
        v.name, v.contact, v.phone_mail, v.traits = next(names), "", "", ""
        v.item = v.item.split("(")[0].strip()
    orders, cols, outs = demo_finance(wb.projects, asof)
    vend = {"장비": "협력사 다", "서포트·하우징": "협력사 나", "설치": "협력사 라"}
    for o in outs:
        o["vendor"] = vend.get(o["item"], "협력사 마")
    wb.orders, wb.collections, wb.outsourcing = orders, cols, outs
    wb.finance_as_of = asof
    wb.warnings = [("check", "[예시현장 A-3호] 승인도 제출이 장비 발주보다 늦습니다. 오기 여부 확인 필요."),
                   ("check", "[예시현장 B-1·2호 설치/협력사 라] 발주 − 지급 ≠ 미지급 (차이 10,000,000원). 지급 기록 확인.")]
    wb.file_name = "예시자료.xlsx"
    return wb


def assert_anonymous(text: str):
    leaked = [w for w in REAL_WORDS if w in text]
    if leaked:
        raise AssertionError(f"예시 자료에 실제 이름이 남아 있습니다: {leaked}")
