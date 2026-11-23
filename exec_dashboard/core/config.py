"""대시보드 규칙 설정. 회사 업무 방식이 바뀌면 이 파일만 고치면 된다."""

# 마일스톤 정의: key -> (표시명, 공정 단계, 가중치)
# 가중치는 '전체 진척도(%)' 계산에 쓰인다. 엑셀에 없는 마일스톤은 계산에서 빠진다.
MILESTONES = {
    "DWG_APPROVAL": ("승인도 제출", "설계", 10),
    "DWG_CONSTRUCTION": ("공사도 제출", "설계", 5),
    "PO_SUPPORT": ("서포트 발주", "외주 발주", 4),
    "PO_HOUSING": ("하우징 발주", "외주 발주", 4),
    "PO_EQUIP": ("장비 발주", "외주 발주", 6),
    "DLV_SUPPORT": ("서포트 납품", "외주 납품", 6),
    "DLV_HOUSING": ("하우징 납품", "외주 납품", 6),
    "DLV_EQUIP": ("장비 납품", "외주 납품", 10),
    "PO_INSTALL": ("보온재·설치 발주", "외주 발주", 4),
    "INSTALL_START": ("설치·시운전 착수", "설치·시운전", 5),
    "INSTALL_END": ("설치·시운전 완료", "설치·시운전", 20),
    "DWG_FINAL": ("완성도 제출", "준공", 5),
    "DWG_MANUAL": ("매뉴얼 제출", "준공", 2),
    "HANDOVER": ("인도", "준공", 13),
}

MILESTONE_ORDER = list(MILESTONES.keys())
STAGES = ["설계", "외주 발주", "외주 납품", "설치·시운전", "준공"]

# 엑셀 칸 안의 라벨(예: '장비 : 25.12.08') -> 마일스톤 key. 열 종류별로 해석.
LABEL_MAP = {
    "drawing": {"승인도": "DWG_APPROVAL", "공사도": "DWG_CONSTRUCTION", "완성도": "DWG_FINAL",
                "최종도": "DWG_FINAL", "메뉴얼": "DWG_MANUAL", "매뉴얼": "DWG_MANUAL", "_": "DWG_APPROVAL"},
    "order": {"서포트": "PO_SUPPORT", "하우징": "PO_HOUSING", "케이싱": "PO_HOUSING",
              "장비": "PO_EQUIP", "설치": "PO_INSTALL", "보온재": "PO_INSTALL", "_": "PO_EQUIP"},
    "delivery": {"서포트": "DLV_SUPPORT", "하우징": "DLV_HOUSING", "케이싱": "DLV_HOUSING",
                 "장비": "DLV_EQUIP", "실외기": "DLV_EQUIP", "실내기": "DLV_EQUIP", "_": "DLV_EQUIP"},
}

# 외주 작업 패키지: (패키지명, 발주 마일스톤, 납품/완료 마일스톤, 업체 분류)
WORK_PACKAGES = [
    ("서포트", "PO_SUPPORT", "DLV_SUPPORT", "STRUCT"),
    ("하우징", "PO_HOUSING", "DLV_HOUSING", "STRUCT"),
    ("장비", "PO_EQUIP", "DLV_EQUIP", "EQUIP"),
    ("보온재·설치", "PO_INSTALL", "INSTALL_END", "INSTALL"),
]

# 공사명 키워드 -> 고객사(조선소). 발주업체 시트의 '(강남)' 같은 적용범위와 맞추는 데 쓴다.
CLIENT_RULES = [("200톤", "강남"), ("동일조선", "동일조선"), ("영광", "영광")]

# 발주업체 시트 '품목' 키워드 -> 업체 분류
VENDOR_CATEGORY_RULES = [
    ("서포트", "STRUCT"), ("하우징", "STRUCT"), ("관통관", "STRUCT"),
    ("에어컨 장비", "EQUIP"), ("장비", "EQUIP"),
    ("에어컨 설치", "INSTALL"), ("설치", "INSTALL"),
    ("보온재", "INSULATION"),
]

# 업체 특성 문구 중 대표가 알아야 할 위험 신호
VENDOR_RISK_KEYWORDS = ["거래중지", "업무 중단", "비협조", "1명", "선금"]

# 경보 기준
DUE_SOON_DAYS = 30          # 이 기간 안에 인도/수금 예정이면 '임박'
HANDOVER_RISK_DAYS = 45     # 인도 N일 전인데 장비 납품이 안 끝났으면 '위험'

# 발주 시점 기준 (HVAC&R 사업부 업무현황 보고서): 납품/설치 대비 몇 일 전에 발주해야 하는가
PO_LEAD_DAYS = {
    "PO_SUPPORT": ("DLV_SUPPORT", 45, "서포트 1.5개월"),
    "PO_HOUSING": ("DLV_HOUSING", 75, "하우징 2.5개월"),
    "PO_EQUIP": ("DLV_EQUIP", 75, "장비 2.5개월"),
    "PO_INSTALL": ("INSTALL_START", 30, "설치 1개월"),
}
PO_LEAD_TOLERANCE = 7  # 기준보다 이 일수 이상 짧을 때만 표시

# 같은 업체의 다른 표기 → 대표 표기 (경리부 자료와 업무현황 표기를 맞춤)
VENDOR_ALIASES = {"탈렌트엘엔지": "탤런트엘엔지", "탈렌트": "탤런트엘엔지", "탈랜트엘엔지": "탤런트엘엔지"}
