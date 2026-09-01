# -*- coding: utf-8 -*-
"""특허출원용 도면 18매 작도. KIPO 도면 작성 요령 준거 (흑백 선화)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "design"))
from patent_draw import *
import numpy as np


# ===========================================================================
def do01():
    """전체 시스템 구성도 (블록도 — 문자 기재 허용)"""
    fig, ax = newfig(10.0, 6.6, (0, 20), (0, 13.2), 1)
    # --- 구동 계통 (상단 행) ---
    tbox(ax, 0.6, 9.5, 3.1, 1.5, "파형 발생부\n(3~3,000 Hz)", ref="151")
    tbox(ax, 4.4, 9.5, 3.2, 1.5, "전류 제어형\n전력 증폭부", ref="152")
    tbox(ax, 8.3, 9.5, 3.2, 1.5, "대역 전환\n직렬 보상부", ref="153")
    tbox(ax, 12.2, 9.3, 3.4, 1.9, "노출 셀\n140a, 140b, 140c")
    ax.text(15.75, 11.25, "140", fontsize=FS_NUM, ha="left", va="bottom")
    for p, q in (((3.7, 10.25), (4.4, 10.25)), ((7.6, 10.25), (8.3, 10.25)),
                 ((11.5, 10.25), (12.2, 10.25))):
        arr(ax, p, q)

    # --- 수처리 계통 ---
    tbox(ax, 12.2, 6.7, 3.4, 1.6, "비금속 노출 덕트\n(수로 132)")
    ax.text(11.05, 8.3, "130", fontsize=FS_NUM, ha="left", va="bottom")
    arr(ax, (13.9, 9.3), (13.9, 8.3))
    ax.text(14.1, 8.75, "자기장", fontsize=FS_TXT, va="center")
    tbox(ax, 12.2, 3.9, 3.4, 1.6, "저장조\n(도전성 금속제)")
    ax.text(15.75, 5.45, "110", fontsize=FS_NUM, ha="left", va="bottom")
    arr(ax, (13.9, 6.7), (13.9, 5.5))
    tbox(ax, 7.4, 3.9, 3.4, 1.6, "순환 펌프 121\n유량계 122\n항온기 123", ref="120")
    arr(ax, (12.2, 4.7), (10.8, 4.7))
    ln(ax, 7.4, 4.7, 6.5, 4.7); ln(ax, 6.5, 4.7, 6.5, 7.5); ln(ax, 6.5, 7.5, 11.6, 7.5)
    arr(ax, (11.6, 7.5), (12.2, 7.5))

    # --- 계측 및 제어 ---
    tbox(ax, 0.6, 6.4, 4.4, 2.2,
         "계측부\n161 코일 전류\n162 외부 기준 자장\n163 수중 자장", ref="160")
    tbox(ax, 0.6, 3.9, 4.4, 1.7, "제어부\n171 자속밀도 루프\n172 전류 루프", ref="170")
    ln(ax, 12.6, 6.7, 12.6, 2.9); ln(ax, 12.6, 2.9, 2.8, 2.9)
    arr(ax, (2.8, 2.9), (2.8, 3.9))
    ax.text(7.7, 3.15, "자속밀도 되먹임", fontsize=FS_TXT, ha="center")
    ln(ax, 2.8, 5.6, 2.8, 6.4)
    ln(ax, 5.0, 4.75, 5.9, 4.75); ln(ax, 5.9, 4.75, 5.9, 9.0)
    ln(ax, 5.9, 9.0, 6.0, 9.0); arr(ax, (6.0, 9.0), (6.0, 9.5))

    # --- 안전 계통 : 최상단으로 우회 배선 ---
    tbox(ax, 16.5, 6.7, 3.0, 4.5, "안전부\n181 인터록\n182 안전 릴레이\n183 인에이블\n접점")
    ax.text(16.35, 11.2, "180", fontsize=FS_NUM, ha="right", va="bottom")
    ln(ax, 18.0, 11.2, 18.0, 12.3); ln(ax, 18.0, 12.3, 5.2, 12.3)
    arr(ax, (5.2, 12.3), (5.2, 11.0))
    ax.text(11.6, 12.5, "증폭기 차단", fontsize=FS_TXT, ha="center")

    # --- 부대 계통 ---
    tbox(ax, 16.5, 3.9, 3.0, 2.0, "수질 계측부\nEC, pH, ORP\nDO, 온도")
    ax.text(16.35, 5.9, "210", fontsize=FS_NUM, ha="right", va="bottom")
    ln(ax, 15.6, 4.7, 16.5, 4.7)
    tbox(ax, 8.2, 0.9, 5.4, 1.5, "대조부 (샴)\n191 대조 덕트\n192 바이파일러 상쇄 권선")
    ax.text(13.75, 2.4, "190", fontsize=FS_NUM, ha="left", va="bottom")
    ln(ax, 13.6, 1.65, 14.6, 1.65); ln(ax, 14.6, 1.65, 14.6, 3.9)
    tbox(ax, 0.6, 0.9, 6.4, 1.5, "디지털 트윈부 174 / 열관리부 200")
    ax.text(0.45, 2.4, "174", fontsize=FS_NUM, ha="right", va="bottom")
    ln(ax, 7.0, 1.65, 8.2, 1.65)
    ln(ax, 3.8, 2.4, 3.8, 2.9)
    num_plain(ax, "100", (10.0, 0.25), fs=11)
    ln(ax, 0.3, 0.6, 19.7, 0.6, lw=LW_T)
    save(fig, "DO01_system")


# ===========================================================================
def do02():
    """저장조 및 노출 루프 배치도 (부호만 기재)"""
    fig, ax = newfig(9.2, 6.0, (0, 18.4), (0, 12.0), 2)
    # 저장조
    rect(ax, 1.2, 2.2, 4.6, 6.4)
    rect(ax, 1.45, 2.45, 4.1, 5.9, lw=LW_T)
    for i in range(9):
        ln(ax, 1.6, 3.0 + i * 0.6, 5.4, 3.0 + i * 0.6, lw=0.35)
    ln(ax, 1.45, 7.9, 5.55, 7.9, lw=LW_T)
    num(ax, "110", (1.2, 6.6), (0.35, 7.8), ha="left")
    num(ax, "111", (1.32, 4.6), (0.35, 3.6), ha="left")
    # 배관 및 펌프
    ln(ax, 5.8, 3.2, 7.6, 3.2); ln(ax, 7.6, 3.2, 7.6, 4.9)
    circ(ax, 6.9, 3.2, 0.55)
    poly(ax, [(6.6, 2.9), (6.6, 3.5), (7.3, 3.2)], lw=LW_T)
    num(ax, "121", (6.9, 2.65), (6.2, 1.5))
    num(ax, "120", (7.6, 4.2), (8.6, 3.9), ha="left")
    rect(ax, 7.2, 4.9, 0.8, 0.9)
    num(ax, "122", (8.0, 5.35), (8.8, 5.1), ha="left")
    # 노출 덕트 및 셀
    rect(ax, 7.15, 6.1, 0.9, 4.6)
    rect(ax, 7.32, 6.1, 0.56, 4.6, lw=LW_T)
    ln(ax, 8.0, 5.8, 8.0, 6.1); ln(ax, 7.2, 5.8, 7.2, 6.1)
    num(ax, "130", (7.15, 10.2), (5.9, 11.2), ha="right")
    num(ax, "132", (7.6, 6.35), (5.9, 5.9), ha="right")
    for i, yy in enumerate((6.5, 7.9, 9.3)):
        hatch_core(ax, 6.55, yy, 0.6, 1.0)
        hatch_core(ax, 8.05, yy, 0.6, 1.0)
        ln(ax, 6.55, yy, 6.15, yy); ln(ax, 6.15, yy, 6.15, yy + 1.0)
        ln(ax, 6.15, yy + 1.0, 6.55, yy + 1.0)
        ln(ax, 8.65, yy, 9.05, yy); ln(ax, 9.05, yy, 9.05, yy + 1.0)
        ln(ax, 9.05, yy + 1.0, 8.65, yy + 1.0)
        for k in range(3):
            arr(ax, (7.2, yy + 0.22 + k * 0.28), (8.0, yy + 0.22 + k * 0.28),
                lw=LW_T, scale=5)
    num(ax, "140a", (8.65, 6.9), (10.2, 6.6), ha="left")
    num(ax, "140b", (8.65, 8.3), (10.2, 8.2), ha="left")
    num(ax, "140c", (8.65, 9.7), (10.2, 9.8), ha="left")
    # 복귀 배관
    ln(ax, 7.6, 10.7, 7.6, 11.5); ln(ax, 7.6, 11.5, 3.5, 11.5)
    ln(ax, 3.5, 11.5, 3.5, 9.0); arr(ax, (3.5, 9.4), (3.5, 8.6))
    # 항온기
    rect(ax, 12.6, 3.4, 2.4, 2.2)
    for i in range(5):
        ln(ax, 12.9, 3.75 + i * 0.4, 14.7, 3.75 + i * 0.4, lw=LW_T)
    num(ax, "123", (15.0, 4.5), (15.9, 5.4), ha="left")
    ln(ax, 8.0, 5.35, 12.6, 5.35)
    ln(ax, 15.0, 4.0, 15.6, 4.0); ln(ax, 15.6, 4.0, 15.6, 2.6)
    ln(ax, 15.6, 2.6, 5.8, 2.6); arr(ax, (6.8, 2.6), (5.8, 2.6))
    # 시료 채취부
    rect(ax, 10.0, 0.7, 1.8, 1.5)
    circ(ax, 10.9, 1.45, 0.42, lw=LW_T)
    num(ax, "124", (11.8, 1.45), (12.8, 1.1), ha="left")
    ln(ax, 9.05, 1.45, 10.0, 1.45); ln(ax, 9.05, 1.45, 9.05, 2.6)
    # 대조 계통
    rect(ax, 16.2, 6.1, 0.9, 4.6, ls="--")
    for yy in (6.5, 7.9, 9.3):
        rect(ax, 15.6, yy, 0.6, 1.0, ls="--", lw=LW_T)
        rect(ax, 17.1, yy, 0.6, 1.0, ls="--", lw=LW_T)
    num(ax, "191", (16.65, 10.4), (17.9, 11.2), ha="left")
    num(ax, "190", (17.7, 8.4), (18.2, 7.4), ha="left")
    ln(ax, 8.05, 11.9, 16.65, 11.9, lw=LW_T, ls="--")
    ln(ax, 16.65, 11.9, 16.65, 10.7, lw=LW_T, ls="--")
    save(fig, "DO02_layout")


# ===========================================================================
def do03():
    """노출 셀 사시도 (부호만 기재)"""
    fig, ax = newfig(9.0, 6.4, (0, 18), (0, 12.8), 3)
    D = 0.42

    def iso(x, y, z): return (x + D * y, z + 0.60 * D * y)

    def prism(o, dx, dy, dz, lw=LW, ls="-"):
        x, y, z = o
        for f in ([(x, y, z), (x+dx, y, z), (x+dx, y, z+dz), (x, y, z+dz)],
                  [(x, y, z+dz), (x+dx, y, z+dz), (x+dx, y+dy, z+dz), (x, y+dy, z+dz)],
                  [(x+dx, y, z), (x+dx, y+dy, z), (x+dx, y+dy, z+dz), (x+dx, y, z+dz)]):
            poly(ax, [iso(*p) for p in f], lw=lw, ls=ls)

    DY = 3.2
    prism((1.4, 0.6, 0.5), 9.0, DY, 1.4)                    # 145 요크
    prism((1.4, 0.6, 1.9), 1.6, DY, 4.4)                    # 143 각부
    prism((8.8, 0.6, 1.9), 1.6, DY, 4.4)                    # 144 각부
    prism((1.4, 0.6, 6.3), 3.3, DY, 1.4)                    # 141 자극편
    prism((7.1, 0.6, 6.3), 3.3, DY, 1.4)                    # 142 자극편
    # 코일 : 각부를 감싸는 단일 블록 + 권선선
    for lx in (1.0, 8.4):
        prism((lx, 0.25, 2.6), 2.4, DY + 0.7, 3.0, lw=LW_T)
        for k in range(5):
            zz = 2.85 + k * 0.55
            ln(ax, *iso(lx, 0.25, zz), *iso(lx + 2.4, 0.25, zz), lw=0.5)
    # 130 덕트 : 공극을 관통
    prism((4.4, 0.15, 5.6), 2.4, DY + 0.9, 3.0, lw=LW_T, ls="--")
    for k in range(4):
        yy = 0.95 + k * 0.68
        arr(ax, iso(4.75, yy, 7.0), iso(7.05, yy, 7.0), lw=LW)
    arr(ax, iso(2.4, 4.6, 7.0), iso(4.3, 4.6, 7.0), lw=LW)

    num(ax, "141", iso(2.6, 0.6, 7.0), (1.6, 11.9), ha="right")
    num(ax, "142", iso(9.4, 0.6, 7.0), (13.0, 11.9), ha="left")
    num(ax, "146", iso(5.9, 0.6, 6.9), (8.0, 11.2), ha="left")
    num(ax, "143", iso(2.2, 0.6, 2.2), (1.0, 1.0), ha="right")
    num(ax, "144", iso(9.6, 0.6, 2.2), (11.4, 0.9), ha="left")
    num(ax, "145", iso(6.4, 0.6, 1.1), (7.9, 0.35), ha="left")
    num(ax, "147", iso(1.0, 0.25, 4.1), (0.4, 5.4), ha="right")
    num(ax, "148", iso(10.8, 0.25, 4.1), (14.6, 5.4), ha="left")
    num(ax, "130", iso(4.4, 0.15, 8.6), (2.6, 10.4), ha="right")
    num(ax, "132", iso(5.9, 1.6, 6.1), (14.6, 6.9), ha="left")
    num(ax, "149", iso(5.9, 1.0, 7.6), (14.6, 9.2), ha="left")
    num_plain(ax, "140", (16.8, 2.2), fs=11)
    ln(ax, 15.8, 2.2, 16.3, 2.2, lw=LW_T)
    save(fig, "DO03_cell_perspective")


# ===========================================================================
def do04():
    """노출 셀 종단면도 A-A 및 공극부 부분 확대도 (부호만 기재, 45° 해칭)"""
    fig, ax = newfig(10.4, 6.0, (0, 21.6), (0, 12.4), 4)
    # ---- 주단면: 공극을 가진 폐자로형 자심 ----
    X0, Y0, W, H, T = 1.4, 1.2, 9.6, 8.2, 1.9
    GW, GX = 1.05, X0 + W / 2                      # 공극 폭 / 중심
    # 하부 요크
    hatch_core(ax, X0, Y0, W, T)
    # 좌우 각부
    hatch_core(ax, X0, Y0 + T, T, H - 2 * T)
    hatch_core(ax, X0 + W - T, Y0 + T, T, H - 2 * T)
    # 상부 부재 (공극으로 분단된 제1·제2 자극편)
    hatch_core(ax, X0, Y0 + H - T, (W - GW) / 2, T)
    hatch_core(ax, GX + GW / 2, Y0 + H - T, (W - GW) / 2, T)
    # 코일 (각부 양측에 표기)
    coil_on_leg(ax, X0, T, Y0 + T + 0.45, H - 2 * T - 0.9, n=7, cw=0.95)
    coil_on_leg(ax, X0 + W - T, T, Y0 + T + 0.45, H - 2 * T - 0.9, n=7, cw=0.95)
    # 덕트 및 수로 (공극 관통)
    rect(ax, GX - GW / 2, Y0 + H - T - 0.9, 0.22, T + 1.8, hatch="...", lw=LW_T)
    rect(ax, GX + GW / 2 - 0.22, Y0 + H - T - 0.9, 0.22, T + 1.8, hatch="...", lw=LW_T)
    rect(ax, GX - GW / 2 + 0.22, Y0 + H - T - 0.9, GW - 0.44, T + 1.8, lw=LW_T)
    for k in range(4):
        yy = Y0 + H - T + 0.3 + k * 0.45
        arr(ax, (GX - GW / 2 + 0.30, yy), (GX + GW / 2 - 0.30, yy), lw=LW_T, scale=5)
    # 확대 지시 원
    circ(ax, GX, Y0 + H - T / 2, 1.55, lw=LW_T, ls="--")
    num_plain(ax, "C", (GX + 1.75, Y0 + H + 0.55), fs=FS_NUM)

    num(ax, "141", (X0 + 2.4, Y0 + H - T / 2), (0.7, 11.5), ha="right")
    num(ax, "142", (X0 + W - 2.4, Y0 + H - T / 2), (11.9, 11.5), ha="left")
    num(ax, "143", (X0 + T / 2, Y0 + H / 2 + 1.4), (0.5, 7.9), ha="right")
    num(ax, "144", (X0 + W - T / 2, Y0 + H / 2 + 1.4), (12.1, 7.9), ha="left")
    num(ax, "145", (X0 + W / 2, Y0 + T / 2), (7.6, 0.35), ha="left")
    num(ax, "147", (X0 - 0.48, Y0 + H / 2 - 1.4), (0.5, 2.6), ha="right")
    num(ax, "148", (X0 + W + 0.48, Y0 + H / 2 - 1.4), (12.1, 2.6), ha="left")

    # ---- 부분 확대도 C ----
    cx, cy = 14.6, 4.0
    CW, CH = 4.9, 6.6
    hatch_core(ax, cx, cy, 1.5, CH)
    hatch_core(ax, cx + CW - 1.5, cy, 1.5, CH)
    rect(ax, cx + 1.5, cy, 0.42, CH, hatch="...", lw=LW_T)
    rect(ax, cx + CW - 1.92, cy, 0.42, CH, hatch="...", lw=LW_T)
    rect(ax, cx + 1.92, cy, CW - 3.84, CH, lw=LW_T)
    rect(ax, cx + 2.02, cy + 0.75, CW - 4.04, CH - 1.5, ls="--", lw=LW_T)
    for k in range(7):
        yy = cy + 0.45 + k * 0.9
        arr(ax, (cx + 1.58, yy), (cx + CW - 1.58, yy), lw=LW_T, scale=6)
    num_plain(ax, "C", (cx + CW / 2, cy + CH + 1.55), fs=11)
    ln(ax, cx + CW / 2 - 0.55, cy + CH + 1.25, cx + CW / 2 + 0.55, cy + CH + 1.25, lw=LW_T)
    num(ax, "141", (cx + 0.8, cy + CH - 0.6), (cx - 1.5, cy + CH + 0.6), ha="right")
    num(ax, "142", (cx + CW - 0.8, cy + CH - 0.6), (cx + CW + 1.3, cy + CH + 0.9), ha="left")
    num(ax, "146", (cx + CW / 2, cy + CH), (cx + CW / 2, cy + CH + 0.85), ha="left")
    num(ax, "131", (cx + 1.71, cy + 0.55), (cx + 0.2, cy - 1.5), ha="right")
    num(ax, "132", (cx + CW / 2, cy + 0.35), (cx + CW / 2 + 1.5, cy - 2.4), ha="left")
    num(ax, "149", (cx + CW / 2 + 0.55, cy + 2.3), (cx + CW + 1.3, cy + 1.1), ha="left")

    ln(ax, 0.9, 11.9, 12.0, 11.9, lw=LW_T, ls="-.")
    num_plain(ax, "A", (0.55, 11.9), fs=FS_NUM)
    num_plain(ax, "A", (12.35, 11.9), fs=FS_NUM)
    save(fig, "DO04_cell_section")


# ===========================================================================
def do05():
    """자속 경로도 및 등가 자기회로 (부호 + 회로기호)"""
    fig, ax = newfig(9.8, 5.4, (0, 19.6), (0, 10.8), 5)
    X0, Y0, W, H, T = 1.4, 1.4, 9.0, 7.6, 1.7
    GW, GX = 1.0, X0 + W / 2
    hatch_core(ax, X0, Y0, W, T)
    hatch_core(ax, X0, Y0 + T, T, H - 2 * T)
    hatch_core(ax, X0 + W - T, Y0 + T, T, H - 2 * T)
    hatch_core(ax, X0, Y0 + H - T, (W - GW) / 2, T)
    hatch_core(ax, GX + GW / 2, Y0 + H - T, (W - GW) / 2, T)
    rect(ax, GX - GW / 2, Y0 + H - T, GW, T, ls="--", lw=LW_T)
    coil_on_leg(ax, X0, T, Y0 + T + 0.45, H - 2 * T - 0.9, n=6, cw=0.85)
    coil_on_leg(ax, X0 + W - T, T, Y0 + T + 0.45, H - 2 * T - 0.9, n=6, cw=0.85)

    # 자속 폐루프 (일관된 순환 방향)
    mx = T / 2
    loop = [(X0 + mx, Y0 + H - T + mx), (GX - GW / 2, Y0 + H - T + mx),
            (GX + GW / 2, Y0 + H - T + mx), (X0 + W - mx, Y0 + H - T + mx),
            (X0 + W - mx, Y0 + mx), (X0 + mx, Y0 + mx), (X0 + mx, Y0 + H - T + mx)]
    for i in range(len(loop) - 1):
        arr(ax, loop[i], loop[i + 1], lw=LW)
    num_plain(ax, "Φ", (X0 + W / 2, Y0 + mx + 0.55), fs=12)

    num(ax, "141", (X0 + 2.2, Y0 + H - T / 2), (0.6, 10.1), ha="right")
    num(ax, "142", (X0 + W - 2.2, Y0 + H - T / 2), (11.2, 10.1), ha="left")
    num(ax, "146", (GX, Y0 + H), (GX + 1.9, Y0 + H + 1.3), ha="left")
    num(ax, "143", (X0 + T / 2, Y0 + H / 2 + 1.2), (0.4, 7.0), ha="right")
    num(ax, "144", (X0 + W - T / 2, Y0 + H / 2 + 1.2), (11.4, 7.0), ha="left")
    num(ax, "145", (X0 + W / 2 - 2.2, Y0 + T / 2), (2.4, 0.3), ha="right")
    num(ax, "147", (X0 - 0.42, Y0 + H / 2 - 1.2), (0.4, 2.3), ha="right")
    num(ax, "148", (X0 + W + 0.42, Y0 + H / 2 - 1.2), (11.4, 2.3), ha="left")

    # ---- 등가 자기회로 ----
    ex, ey, ew, eh = 13.6, 3.2, 5.0, 4.6
    ln(ax, ex, ey, ex + ew, ey); ln(ax, ex, ey + eh, ex + ew, ey + eh)
    ln(ax, ex, ey, ex, ey + eh); ln(ax, ex + ew, ey, ex + ew, ey + eh)
    circ(ax, ex, ey + eh / 2, 0.45)
    ln(ax, ex - 0.45, ey + eh / 2, ex + 0.45, ey + eh / 2, lw=LW_T)
    num_plain(ax, "NI", (ex - 1.1, ey + eh / 2), fs=FS_NUM)
    rect(ax, ex + 0.9, ey + eh - 0.42, 1.2, 0.84)
    num_plain(ax, "R1", (ex + 1.5, ey + eh + 0.85), fs=FS_NUM)
    rect(ax, ex + 2.9, ey + eh - 0.42, 1.2, 0.84)
    num_plain(ax, "R2", (ex + 3.5, ey + eh + 0.85), fs=FS_NUM)
    rect(ax, ex + 1.9, ey - 0.42, 1.2, 0.84, ls="--")
    num_plain(ax, "R3", (ex + 2.5, ey - 1.15), fs=FS_NUM)
    for i, t in enumerate(("R1 : 공극 자기저항", "R2 : 자심 자기저항", "R3 : 누설 자기저항")):
        num_plain(ax, t, (ex - 1.2, 2.0 - i * 0.62), fs=FS_TXT, ha="left")
    save(fig, "DO05_magnetic_circuit")


# ===========================================================================
def do06():
    """코일 권선 부분 확대 단면도 (부호만 기재)"""
    fig, ax = newfig(8.0, 5.4, (0, 16), (0, 10.8), 6)
    hatch_core(ax, 4.6, 3.0, 4.0, 4.0)
    num(ax, "143", (7.4, 5.6), (11.0, 4.4), ha="left")
    rect(ax, 4.25, 2.65, 4.7, 4.7, lw=LW_T)
    num(ax, "1472", (4.42, 6.9), (2.0, 8.6), ha="right")
    for r in range(2):
        for c in range(9):
            circ(ax, 4.55 + c * 0.51, 2.15 - r * 0.52, 0.22, lw=LW_T)
            circ(ax, 4.55 + c * 0.51, 7.85 + r * 0.52, 0.22, lw=LW_T)
    num(ax, "147", (5.06, 8.37), (1.4, 9.1), ha="right")
    circ(ax, 12.0, 7.2, 1.7)
    ln(ax, 4.77, 8.37, 10.6, 8.9, lw=LW_T, ls="--")
    ln(ax, 4.77, 7.85, 10.9, 5.8, lw=LW_T, ls="--")
    for a in range(7):
        for b in range(7):
            xx = 11.0 + a * 0.33; yy = 6.2 + b * 0.33
            if (xx - 12.0) ** 2 + (yy - 7.2) ** 2 < 1.35 ** 2:
                circ(ax, xx, yy, 0.13, lw=0.5)
    num(ax, "1471", (11.7, 7.5), (14.6, 9.6), ha="left")
    rect(ax, 3.9, 1.2, 5.4, 7.6, ls="--", lw=LW_T)
    num(ax, "1473", (9.3, 2.2), (11.0, 1.6), ha="left")
    rect(ax, 3.6, 0.4, 6.0, 0.7, hatch="xxx", lw=LW)
    num(ax, "201", (9.6, 0.75), (11.4, 0.75), ha="left")
    for xx in (5.0, 6.6, 8.2):
        arr(ax, (xx, 1.9), (xx, 1.2), lw=LW_T, scale=6)
    circ(ax, 4.0, 8.9, 0.30, lw=LW_T)
    num(ax, "203", (4.0, 9.2), (2.4, 10.4), ha="right")
    save(fig, "DO06_coil_detail")


if __name__ == "__main__":
    print("특허도면 작도:")
    for f in (do01, do02, do03, do04, do05, do06):
        try:
            f()
        except Exception as e:
            import traceback; print("  FAILED", f.__name__, e); traceback.print_exc()


# ===========================================================================
def do07():
    """제1 내지 제3 실시형태의 자극 배치 및 자속 경로 비교도"""
    fig, ax = newfig(9.0, 6.7, (0, 18.0), (0, 13.4), 7)
    PW, PH, GP, YK, PITCH = 2.1, 0.62, 0.95, 0.52, 3.3
    X0 = 2.9

    def poles(y, sgns, top=False):
        for i, sg in enumerate(sgns):
            xc = X0 + i * PITCH
            hatch_core(ax, xc - PW / 2, y, PW, PH)
            num_plain(ax, sg, (xc, y + PH / 2), fs=FS_NUM)

    # ---------- (a) 제1 실시형태 : 편측 자극, 자속이 수중으로 환류 ----------
    ya = 9.4
    hatch_core(ax, X0 - PW / 2, ya, 2 * PITCH + PW, YK)
    poles(ya + YK, ["N", "S", "N"])
    yp = ya + YK + PH
    rect(ax, X0 - PW / 2 - 0.6, yp, 2 * PITCH + PW + 1.2, GP + 0.5, ls="--", lw=LW_T)
    for i in range(2):
        xc = X0 + i * PITCH
        ax.add_patch(Arc((xc + PITCH / 2, yp), PITCH, 2 * (GP + 0.35),
                         theta1=0, theta2=180, ec=K, lw=LW))
        arr(ax, (xc + PITCH / 2 + 0.02, yp + GP + 0.30),
            (xc + PITCH / 2 + 0.35, yp + GP + 0.25), lw=LW, scale=7)
    num_plain(ax, "(a)", (0.9, ya + 1.1), fs=11)
    num(ax, "145", (X0 + PITCH, ya + YK / 2), (14.6, ya + YK / 2), ha="left")
    num(ax, "141", (X0 + 2 * PITCH - PW * 0.36, ya + YK + PH * 0.75), (14.6, ya + YK + PH + 0.35), ha="left")
    num(ax, "132", (X0 + 2 * PITCH + PW / 2 + 0.45, yp + GP), (14.6, yp + GP + 0.5), ha="left")

    # ---------- (b) 제2 실시형태 : 대향 이중, 공유 요크 → 극성 교번 ----------
    yb = 4.9
    hatch_core(ax, X0 - PW / 2, yb, 2 * PITCH + PW, YK)
    poles(yb + YK, ["N", "S", "N"])
    yg = yb + YK + PH
    poles(yg + GP, ["S", "N", "S"])
    hatch_core(ax, X0 - PW / 2, yg + GP + PH, 2 * PITCH + PW, YK)
    rect(ax, X0 - PW / 2, yg, 2 * PITCH + PW, GP, ls="--", lw=LW_T)
    for i in range(3):
        xc = X0 + i * PITCH
        up = (i % 2 == 0)
        for k in range(3):
            xx = xc - 0.55 + k * 0.55
            if up:
                arr(ax, (xx, yg + 0.10), (xx, yg + GP - 0.10), lw=LW_T, scale=5)
            else:
                arr(ax, (xx, yg + GP - 0.10), (xx, yg + 0.10), lw=LW_T, scale=5)
        if i < 2:
            ax.plot([xc + PITCH / 2], [yg + GP / 2], marker="x", ms=6, color=K, mew=1.2)
    num_plain(ax, "(b)", (0.9, yb + 1.4), fs=11)
    num(ax, "145", (X0 + PITCH, yb + YK / 2), (14.6, yb + YK / 2), ha="left")
    num(ax, "141", (X0 + 2 * PITCH - PW * 0.36, yb + YK + PH * 0.72), (14.6, yb + YK + PH / 2), ha="left")
    num(ax, "142", (X0 + 2 * PITCH - PW * 0.36, yg + GP + PH * 0.72), (14.6, yg + GP + PH / 2), ha="left")
    num(ax, "146", (X0 + 2 * PITCH + PW / 2, yg + GP / 2), (14.6, yg + GP / 2 - 0.1), ha="left")
    num(ax, "N1", (X0 + PITCH / 2, yg + GP / 2), (X0 + PITCH / 2 - 0.2, yb - 0.7), ha="right")

    # ---------- (c) 제3 실시형태 : 셀별 독립 환류로 → 동일 극성 ----------
    yc = 0.5
    for i in range(3):
        xc = X0 + i * PITCH
        hatch_core(ax, xc - PW / 2, yc, PW, YK)
        hatch_core(ax, xc - PW / 2, yc + YK, PW, PH)
        hatch_core(ax, xc - PW / 2, yc + YK + PH + GP, PW, PH)
        hatch_core(ax, xc - PW / 2, yc + YK + 2 * PH + GP, PW, YK)
        hatch_core(ax, xc - PW / 2 - 0.5, yc, 0.5, 2 * YK + 2 * PH + GP)
        num_plain(ax, "N", (xc, yc + YK + PH / 2), fs=FS_NUM)
        num_plain(ax, "S", (xc, yc + YK + PH + GP + PH / 2), fs=FS_NUM)
        for k in range(3):
            xx = xc - 0.55 + k * 0.55
            arr(ax, (xx, yc + YK + PH + 0.10), (xx, yc + YK + PH + GP - 0.10),
                lw=LW_T, scale=5)
    ygc = yc + YK + PH
    rect(ax, X0 - PW / 2 - 0.5, ygc, 2 * PITCH + PW + 0.5, GP, ls="--", lw=LW_T)
    num_plain(ax, "(c)", (0.9, yc + 1.4), fs=11)
    num(ax, "140", (X0 - PW / 2 - 0.25, ygc - 0.35), (0.35, ygc + 1.9), ha="left")
    num(ax, "145", (X0 + 2 * PITCH - PW / 2 - 0.25, yc + 0.9), (14.6, yc + 0.4), ha="left")
    num(ax, "146", (X0 + 2 * PITCH + PW / 2, ygc + GP / 2), (14.6, ygc + GP / 2), ha="left")
    num(ax, "132", (X0 + PITCH + PW * 0.36, ygc + GP - 0.14), (14.6, ygc + GP + 0.9), ha="left")
    num_plain(ax, "N1 : 자속 반전에 의한 자속밀도 영점",
              (5.2, 12.9), fs=FS_TXT, ha="left")
    save(fig, "DO07_architecture_compare")


# ===========================================================================
def do08():
    """구동부 회로도 (회로기호 + 부호)"""
    fig, ax = newfig(9.8, 5.4, (0, 19.6), (0, 10.8), 8)
    tbox(ax, 0.5, 8.4, 2.9, 1.4, "파형 발생부")
    ax.text(0.5, 9.95, "151", fontsize=FS_NUM, ha="left", va="bottom")
    # 증폭기 (삼각 기호)
    poly(ax, [(4.4, 8.1), (4.4, 10.1), (6.8, 9.1)])
    ax.text(4.4, 10.3, "152", fontsize=FS_NUM, ha="left", va="bottom")
    arr(ax, (3.4, 9.1), (4.4, 9.1))
    ln(ax, 6.8, 9.1, 8.0, 9.1)
    # 제1 계층 전류 센서
    circ(ax, 8.4, 9.1, 0.40)
    ln(ax, 8.8, 9.1, 9.6, 9.1)
    num(ax, "161", (8.4, 8.70), (7.5, 7.0), ha="right")
    # 대역 전환 직렬 보상부 (병렬 4 분기)
    rect(ax, 9.6, 3.2, 5.0, 6.6, ls="--", lw=LW_T)
    ax.text(9.6, 9.9, "153", fontsize=FS_NUM, ha="left", va="bottom")
    ln(ax, 10.2, 9.1, 10.2, 4.0)          # 좌측 모선
    ln(ax, 14.0, 9.1, 14.0, 4.0)          # 우측 모선
    ln(ax, 9.6, 9.1, 14.6, 9.1)
    for i in range(4):
        yy = 8.2 - i * 1.4
        ln(ax, 10.2, yy, 10.9, yy)
        circ(ax, 10.9, yy, 0.09, lw=LW_T); circ(ax, 11.65, yy, 0.09, lw=LW_T)
        ln(ax, 10.9, yy, 11.55, yy + 0.42)          # 접점
        ln(ax, 11.65, yy, 12.35, yy)
        ln(ax, 12.35, yy - 0.40, 12.35, yy + 0.40)  # 커패시터
        ln(ax, 12.70, yy - 0.40, 12.70, yy + 0.40)
        ln(ax, 12.70, yy, 14.0, yy)
    num(ax, "155", (11.28, 8.42), (10.0, 10.35), ha="right")
    num(ax, "154", (12.53, 8.35), (13.1, 10.35), ha="left")
    # 코일 (인덕터 기호) 및 노출 셀
    ln(ax, 14.6, 9.1, 15.3, 9.1)
    for k in range(4):
        ax.add_patch(Arc((15.65 + k * 0.7, 9.1), 0.7, 0.7, theta1=0, theta2=180,
                         ec=K, lw=LW))
    ln(ax, 18.45, 9.1, 19.1, 9.1); ln(ax, 19.1, 9.1, 19.1, 5.6)
    num(ax, "147", (16.35, 9.45), (16.6, 10.35), ha="left")
    tbox(ax, 15.0, 4.0, 4.0, 1.6, "노출 셀 140\n공극 146")
    ax.text(19.0, 5.7, "140", fontsize=FS_NUM, ha="right", va="bottom")
    ln(ax, 15.0, 4.8, 14.0, 4.8) if False else None
    ln(ax, 15.0, 4.8, 7.6, 4.8); ln(ax, 7.6, 4.8, 7.6, 8.6)
    arr(ax, (7.6, 8.6), (7.6, 8.7))
    ln(ax, 7.6, 8.7, 6.8, 8.7) if False else None
    # 제어부 및 되먹임
    tbox(ax, 0.5, 5.4, 3.4, 1.7, "제어부\n171 / 172")
    ax.text(0.5, 7.25, "170", fontsize=FS_NUM, ha="left", va="bottom")
    arr(ax, (1.95, 7.1), (1.95, 8.4))
    ln(ax, 7.5, 7.0, 3.9, 7.0); arr(ax, (4.4, 7.0), (3.9, 7.0))
    tbox(ax, 5.6, 1.0, 5.4, 1.6, "제3 계층 수중 자기 센서\n및 동기 복조부")
    ax.text(5.6, 2.75, "163", fontsize=FS_NUM, ha="left", va="bottom")
    ln(ax, 11.0, 1.8, 17.0, 1.8); ln(ax, 17.0, 1.8, 17.0, 4.0)
    ln(ax, 5.6, 1.8, 1.95, 1.8); arr(ax, (1.95, 1.8), (1.95, 5.4))
    save(fig, "DO08_driver")


# ===========================================================================
def do09():
    """3계층 자기 계측 구성도 (블록도)"""
    fig, ax = newfig(9.8, 5.6, (0, 19.6), (0, 11.2), 9)
    tbox(ax, 0.6, 8.4, 4.6, 1.7, "제1 계층\n코일 전류 센서", ref="161")
    tbox(ax, 0.6, 5.9, 4.6, 1.7, "제2 계층\n외부 기준 자기 센서", ref="162")
    tbox(ax, 0.6, 3.4, 4.6, 1.7, "제3 계층\n수중 자기 센서", ref="163")
    tbox(ax, 6.8, 5.4, 3.6, 2.7, "동기 복조부\nT = max(3 s, 30/f)", ref="164")
    for y in (9.25, 6.75, 4.25):
        ln(ax, 5.2, y, 6.0, y); ln(ax, 6.0, y, 6.0, 6.75)
    arr(ax, (6.0, 6.75), (6.8, 6.75))
    tbox(ax, 12.0, 7.6, 3.4, 1.7, "제어부", ref="170")
    tbox(ax, 12.0, 4.2, 3.4, 2.4, "상호 검증부\n(2 계층 이상\n불일치 판정)")
    arr(ax, (10.4, 7.4), (12.0, 8.2)); arr(ax, (10.4, 6.1), (12.0, 5.6))
    tbox(ax, 16.4, 4.2, 2.8, 5.1, "안전부\n181\n인터록\n183\n인에이블\n접점 개방", ref="180",
         ref_dx=-2.9, ref_dy=0.0)
    arr(ax, (15.4, 5.4), (16.4, 5.9))
    tbox(ax, 6.8, 1.0, 8.6, 1.7,
         "교정 계통\n국가표준 → 헬름홀츠 교정 코일 166 → 162 → 163", ref="166",
         ref_dx=-8.7)
    ln(ax, 6.8, 1.85, 2.9, 1.85); arr(ax, (2.9, 1.85), (2.9, 3.4))
    tbox(ax, 12.0, 9.7, 3.4, 1.3, "3차원 프로브 이송부", ref="165", ref_dx=-3.5)
    ln(ax, 12.0, 10.35, 11.2, 10.35); ln(ax, 11.2, 10.35, 11.2, 2.6)
    arr(ax, (11.2, 2.6), (11.2, 2.6))
    ln(ax, 11.2, 2.6, 11.2, 1.85); ln(ax, 11.2, 1.85, 15.4, 1.85)
    save(fig, "DO09_sensor")


# ===========================================================================
def do10():
    """노출 제어 체적 및 자장 측정 위치도 (부호만 기재, 등자속밀도선)"""
    import cell as CELL, system as SYS
    from magnetics import ForkGeometry, Bmag
    from architectures import BUILDERS
    core = SYS.CoreGeom()
    st = CELL.cell_field_stats(1.0)
    fk = ForkGeometry(n_prong=1, prong_w=core.pole_w, prong_h=core.pole_h,
                      prong_len=core.leg_len, gap=core.gap)
    sheets = BUILDERS["R3"](fk, 50e-3 / st["mean"])
    ex = CELL.ecv_geometry()

    fig, ax = newfig(9.6, 5.0, (0, 19.2), (0, 10.0), 10)
    # 좌: 공극 중앙면 (x-y)
    sx, sy, S = 1.4, 1.2, 22.0
    n = 90
    X = np.linspace(-0.155, 0.155, n); Y = np.linspace(-0.155, 0.155, n)
    Z = np.array([[Bmag((x, y, core.gap / 2), sheets) * 1e3 for x in X] for y in Y])
    ax.contour(sx + (X + 0.155) * S, sy + (Y + 0.155) * S, Z,
               levels=[30, 40, 45, 48, 50, 52], colors=K, linewidths=LW_T)
    rect(ax, sx + (0.155 - core.pole_w / 2) * S, sy + (0.155 - core.pole_h / 2) * S,
         core.pole_w * S, core.pole_h * S, lw=LW)
    rect(ax, sx + (0.155 - ex["x_half"]) * S, sy + (0.155 - ex["y_half"]) * S,
         2 * ex["x_half"] * S, 2 * ex["y_half"] * S, lw=LW, ls="--")
    cx0, cy0 = sx + 0.155 * S, sy + 0.155 * S
    for lab, dx, dy in (("1491", 0, 0), ("1494", 0, ex["y_half"]), ("1495", 0, -ex["y_half"])):
        ax.plot([cx0 + dx * S], [cy0 + dy * S], marker="+", ms=7, color=K, mew=1.1)
    num(ax, "1491", (cx0, cy0), (cx0 + 2.6, cy0 - 1.2), ha="left")
    num(ax, "1494", (cx0, cy0 + ex["y_half"] * S), (cx0 + 2.9, cy0 + ex["y_half"] * S + 1.0), ha="left")
    num(ax, "1495", (cx0, cy0 - ex["y_half"] * S), (cx0 + 2.9, cy0 - ex["y_half"] * S - 1.0), ha="left")
    num(ax, "141", (sx + (0.155 - core.pole_w / 2) * S + 0.9,
                     sy + (0.155 + core.pole_h / 2) * S), (0.4, 9.3), ha="left")
    num(ax, "149", (cx0 - ex["x_half"] * S, cy0 + ex["y_half"] * S), (0.5, 1.0), ha="left")
    num_plain(ax, "(a)", (cx0, 9.6), fs=11)

    # 우: 공극 횡단면 (z 방향 traverse)
    gx, gy, GS = 12.6, 1.2, 5.4
    rect(ax, gx, gy, core.gap * 1000 / 30 * 1.6, 7.4, lw=LW)
    W2 = core.gap * 1000 / 30 * 1.6
    rect(ax, gx, gy, W2 * 0.1, 7.4, hatch="...", lw=LW_T)
    rect(ax, gx + W2 * 0.9, gy, W2 * 0.1, 7.4, hatch="...", lw=LW_T)
    rect(ax, gx + W2 * 0.1, gy + 0.9, W2 * 0.8, 5.6, ls="--", lw=LW_T)
    for lab, fx in (("1492", 0.12), ("1491", 0.5), ("1493", 0.88)):
        ax.plot([gx + W2 * fx], [gy + 3.7], marker="+", ms=7, color=K, mew=1.1)
    num(ax, "1492", (gx + W2 * 0.12, gy + 3.7), (gx - 1.4, gy + 5.6), ha="right")
    num(ax, "1491", (gx + W2 * 0.5, gy + 3.7), (gx + W2 * 0.5 + 1.9, gy + 7.4), ha="left")
    num(ax, "1493", (gx + W2 * 0.88, gy + 3.7), (gx + W2 + 1.4, gy + 5.6), ha="left")
    num(ax, "131", (gx + W2 * 0.05, gy + 1.4), (gx - 1.4, gy + 0.4), ha="right")
    num(ax, "132", (gx + W2 * 0.5, gy + 1.0), (gx + W2 + 1.4, gy + 0.4), ha="left")
    num_plain(ax, "(b)", (gx + W2 / 2, 9.2), fs=11)
    save(fig, "DO10_ecv_map")


# ===========================================================================
def do11():
    """정자속밀도 폐루프 제어 블록도"""
    fig, ax = newfig(9.6, 4.4, (0, 19.2), (0, 8.8), 11)
    y = 5.4
    circ(ax, 1.5, y, 0.45)
    ln(ax, 1.05, y, 1.95, y, lw=LW_T); ln(ax, 1.5, y - 0.45, 1.5, y + 0.45, lw=LW_T)
    arr(ax, (0.3, y), (1.05, y))
    num_plain(ax, "B*", (0.35, y + 0.55), fs=FS_NUM)
    tbox(ax, 2.6, y - 0.9, 2.9, 1.8, "외측 자속밀도\n제어 루프", ref="171")
    arr(ax, (1.95, y), (2.6, y))
    circ(ax, 6.4, y, 0.45)
    ln(ax, 5.95, y, 6.85, y, lw=LW_T); ln(ax, 6.4, y - 0.45, 6.4, y + 0.45, lw=LW_T)
    arr(ax, (5.5, y), (5.95, y))
    tbox(ax, 7.5, y - 0.9, 2.9, 1.8, "내측 전류\n제어 루프", ref="172")
    arr(ax, (6.85, y), (7.5, y))
    tbox(ax, 11.0, y - 0.9, 2.9, 1.8, "전력 증폭부\n및 보상부", ref="152")
    arr(ax, (10.4, y), (11.0, y))
    tbox(ax, 14.6, y - 0.9, 2.9, 1.8, "노출 셀\nB = k · I", ref="140")
    arr(ax, (13.9, y), (14.6, y))
    arr(ax, (17.5, y), (18.9, y))
    num_plain(ax, "B", (18.5, y + 0.55), fs=FS_NUM)
    tbox(ax, 6.0, 7.2, 6.4, 1.3, "앞먹임 : I* = B* / k(형상) · 전달계수", ref="173")
    ln(ax, 9.2, 7.2, 9.2, 6.6); ln(ax, 9.2, 6.6, 6.4, 6.6)
    arr(ax, (6.4, 6.6), (6.4, y + 0.45))
    tbox(ax, 12.6, 0.6, 4.6, 1.5, "제3 계층 센서 163\n동기 복조부 164")
    ax.text(17.3, 2.1, "164", fontsize=FS_NUM, ha="left", va="bottom")
    ln(ax, 16.0, y - 0.9, 16.0, 2.1)
    ln(ax, 12.6, 1.35, 1.5, 1.35)
    arr(ax, (1.5, 1.35), (1.5, y - 0.45))
    tbox(ax, 6.0, 2.9, 5.2, 1.3, "제1·제2 계층 관측 161 / 162")
    ax.text(11.3, 4.2, "160", fontsize=FS_NUM, ha="left", va="bottom")
    ln(ax, 11.2, 3.55, 12.0, 3.55); ln(ax, 12.0, 3.55, 12.0, y - 0.9)
    ln(ax, 6.0, 3.55, 3.4, 3.55); arr(ax, (3.4, 3.55), (3.4, y - 0.9))
    save(fig, "DO11_control_loop")


# ===========================================================================
def do12():
    """열관리 계통도 (블록도)"""
    fig, ax = newfig(9.4, 4.6, (0, 18.8), (0, 9.2), 12)
    tbox(ax, 0.6, 7.0, 3.4, 1.4, "코일 손실", ref="147")
    tbox(ax, 0.6, 5.2, 3.4, 1.4, "자심 손실", ref="140")
    tbox(ax, 0.6, 3.4, 3.4, 1.4, "구동부 손실", ref="152")
    tbox(ax, 0.6, 1.6, 3.4, 1.4, "펌프 입력 열", ref="121")
    tbox(ax, 5.6, 5.0, 3.4, 3.4, "건식 냉각 계통\n냉각판 201\n냉매 유로 202", ref="200")
    arr(ax, (4.0, 7.7), (5.6, 7.4)); arr(ax, (4.0, 5.9), (5.6, 6.2))
    tbox(ax, 5.6, 3.0, 3.4, 1.4, "강제 공랭")
    arr(ax, (4.0, 4.1), (5.6, 3.7))
    tbox(ax, 11.0, 1.2, 3.6, 2.2, "공정수\n저장조 110\n항온기 123", ref="110")
    arr(ax, (4.0, 2.3), (11.0, 2.3))
    tbox(ax, 11.0, 4.4, 3.6, 1.8, "수중 유도 전계에\n의한 옴 손실", ref="132")
    arr(ax, (12.8, 4.4), (12.8, 3.4))
    tbox(ax, 15.8, 5.4, 2.6, 2.6, "온도 센서\n203\n(부위별\n개별 한계)", ref="203")
    ln(ax, 9.0, 6.7, 15.8, 6.7)
    ln(ax, 14.6, 2.3, 15.4, 2.3); ln(ax, 15.4, 2.3, 15.4, 5.4)
    save(fig, "DO12_thermal")


# ===========================================================================
def do13():
    """안전 인터록 회로도 (직렬 하드와이어 체인)"""
    fig, ax = newfig(9.8, 5.5, (0, 19.6), (0, 11.0), 13)
    conds = ["과전류", "과전압", "코일 과온", "구동부 과온", "누수",
             "절연 저하", "센서 불일치", "자장 폭주", "통신 두절", "비상 정지"]

    def contact(x, y, i):
        ln(ax, x - 0.55, y, x - 0.13, y, lw=LW)
        circ(ax, x - 0.13, y, 0.09, lw=LW_T)
        circ(ax, x + 0.62, y, 0.09, lw=LW_T)
        ln(ax, x - 0.13, y, x + 0.55, y + 0.40, lw=LW)
        ln(ax, x + 0.62, y, x + 1.15, y, lw=LW)
        ax.text(x + 0.25, y - 0.42, f"{i+1}", fontsize=FS_NUM, ha="center", va="top")
        ax.text(x + 0.25, y - 0.98, conds[i], fontsize=FS_TXT, ha="center", va="top")

    y1, y2 = 9.3, 6.1
    ln(ax, 0.7, y1, 1.35, y1)
    for i in range(5):
        contact(1.9 + i * 3.0, y1, i)
        if i < 4:
            ln(ax, 1.9 + i * 3.0 + 1.15, y1, 1.9 + (i + 1) * 3.0 - 0.55, y1, lw=LW)
    ln(ax, 14.05, y1, 16.6, y1); ln(ax, 16.6, y1, 16.6, y2); ln(ax, 16.6, y2, 14.0, y2)
    for i in range(5):
        xx = 12.85 - i * 3.0
        contact(xx, y2, 5 + i)
        if i < 4:
            ln(ax, xx - 0.55, y2, xx - 3.0 + 1.15, y2, lw=LW)
    ln(ax, 1.35, y2, 0.7, y2)
    circ(ax, 0.7, y1, 0.13, lw=LW)                       # 전원 단자
    ln(ax, 0.83, y1, 1.35, y1)
    num(ax, "181", (2.2, y1 + 0.20), (2.6, 10.4), ha="left")
    ln(ax, 0.7, y2, 0.7, 2.2)                            # 체인 종단 -> 안전 릴레이
    arr(ax, (0.7, 2.2), (1.7, 2.2))
    tbox(ax, 1.7, 1.4, 3.6, 1.6, "안전 릴레이\n(2 채널)")
    ax.text(1.55, 3.1, "182", fontsize=FS_NUM, ha="left", va="bottom")
    arr(ax, (5.3, 2.2), (7.1, 2.2))
    tbox(ax, 7.1, 1.4, 3.6, 1.6, "인에이블 접점")
    ax.text(6.95, 3.1, "183", fontsize=FS_NUM, ha="left", va="bottom")
    arr(ax, (10.7, 2.2), (12.5, 2.2))
    tbox(ax, 12.5, 1.4, 3.2, 1.6, "전력 증폭부")
    ax.text(12.35, 3.1, "152", fontsize=FS_NUM, ha="left", va="bottom")
    ax.text(0.7, 0.45,
            "제어 소프트웨어 경보는 통보 전용이며, 어떠한 소프트웨어 경로도 인에이블 접점을 "
            "유지시킬 수 없다. 무전압 시 차단되는 구조이다.", fontsize=FS_TXT, va="center")
    save(fig, "DO13_interlock")


# ===========================================================================
def do14():
    """실험군 및 대조군(샴) 구성도"""
    fig, ax = newfig(9.4, 4.8, (0, 18.8), (0, 9.6), 14)
    for j, (ox, ttl, ref) in enumerate(((0.8, "실험군", "140"), (10.0, "대조군 (샴)", "190"))):
        rect(ax, ox, 1.0, 8.0, 7.4, lw=LW, ls="-" if j == 0 else "--")
        ax.text(ox + 4.0, 8.75, ttl, fontsize=10, ha="center")
        tbox(ax, ox + 0.4, 6.6, 3.4, 1.3, "동일 펌프 duty")
        tbox(ax, ox + 4.2, 6.6, 3.4, 1.3, "동일 유로 형상\n동일 차압")
        tbox(ax, ox + 0.4, 4.9, 3.4, 1.3, "동일 수배치\n동일 채수")
        tbox(ax, ox + 4.2, 4.9, 3.4, 1.3, "동일 항온\n동일 체류시간")
        tbox(ax, ox + 0.4, 2.9, 7.2, 1.5,
             "코일 통전\nB = 설정값" if j == 0 else "코일 통전, 단 바이파일러\n상쇄 권선으로 B ≈ 0")
        tbox(ax, ox + 0.4, 1.3, 7.2, 1.2, "제3 계층 센서로 매 회차 잔류 자장 측정")
        ax.text(ox + 8.15, 8.4, ref, fontsize=FS_NUM, ha="left", va="bottom")
    # 바이파일러 상쇄 권선 상세
    dx, dy = 12.6, 0.0
    save(fig, "DO14_sham")


# ===========================================================================
def do15():
    """제어 방법 흐름도"""
    fig, ax = newfig(8.4, 10.2, (0, 19.0), (0, 23.0), 15)
    BX, BW = 4.2, 9.4
    CX = BX + BW / 2
    steps = [("S110", "노출 제어 체적을 정의하고 3차원 자장 분포를\n측정하여 형상계수 및 전달계수를 취득", 2.2),
             ("S120", "목표 주파수 f 및 목표 자속밀도 B*를 설정", 1.6),
             ("S130", "f에 대응하는 보상 대역을 선택하여\n직렬 보상부를 전환", 1.9),
             ("S140", "앞먹임 전류 지령 I* = B* / k 를 산출", 1.6),
             ("S150", "제3 계층 센서 출력을 T = max(3 s, 30/f)\n구간에서 동기 복조하여 B를 산출", 1.9)]
    y = 21.0
    for ref, txt, h in steps:
        rbox(ax, BX, y - h, BW, h, txt, ref=ref)
        arr(ax, (CX, y - h), (CX, y - h - 1.15))
        y = y - h - 1.15
    dbox(ax, BX + 1.1, y - 2.3, BW - 2.2, 2.3, "3 계층 상호\n검증 통과 ?")
    ax.text(BX - 0.25, y - 1.15, "S160", fontsize=FS_NUM, ha="right", va="center")
    yd = y - 2.3
    ax.text(CX + 0.35, yd - 0.55, "예", fontsize=FS_TXT, va="top")
    arr(ax, (CX, yd), (CX, yd - 1.35))
    rbox(ax, BX, yd - 3.0, BW, 1.65,
         "전류 지령을 보정하여\n|B - B*| / B* ≤ 5 % 를 유지", ref="S170")
    ln(ax, BX + BW / 2 + BW / 2 - 0.6, yd + 1.15, BX + BW - 1.1 + 1.5, yd + 1.15)
    arr(ax, (BX + BW - 1.1, yd + 1.15), (BX + BW + 1.4, yd + 1.15))
    ax.text(BX + BW + 0.55, yd + 1.55, "아니오", fontsize=FS_TXT, ha="center")
    rbox(ax, BX + BW + 1.4, yd + 0.35, 3.0, 1.6,
         "인에이블 접점\n개방 및 차단", ref=None)
    ax.text(BX + BW + 1.4, yd + 2.15, "S180", fontsize=FS_NUM, ha="left", va="bottom")
    # 되먹임 (S170 -> S150)
    ln(ax, BX, yd - 2.2, 1.9, yd - 2.2)
    ln(ax, 1.9, yd - 2.2, 1.9, y + 1.9 + 0.0)
    arr(ax, (1.9, y + 1.15), (BX, y + 1.15))
    save(fig, "DO15_flow")


# ===========================================================================
def do16():
    """도전성 저장조의 자기 차폐 전달함수 (그래프)"""
    import tank_coupling as TC
    from constants import MU_R_SUS316L_COLDWORK
    t = TC.TankGeometry()
    f = np.logspace(0, math.log10(6000), 400)
    fig = plt.figure(figsize=(7.2, 5.0))
    fig.text(0.02, 0.97, "【도 16】", fontsize=10.5, va="top")
    ax1 = fig.add_subplot(2, 1, 1)
    ax2 = fig.add_subplot(2, 1, 2)
    for ax, kind in ((ax1, "mag"), (ax2, "ph")):
        for mur, ls in ((1.005, "-"), (MU_R_SUS316L_COLDWORK.value, "--")):
            H = [TC.H_tank(x, t, mu_r=mur) for x in f]
            v = [20 * math.log10(abs(h)) for h in H] if kind == "mag" \
                else [math.degrees(np.angle(h)) for h in H]
            ax.semilogx(f, v, color=K, lw=1.2, ls=ls)
        ax.axvline(TC.corner_frequency(t), color=K, lw=0.7, ls=":")
        ax.grid(True, which="both", color="0.75", lw=0.35)
        ax.tick_params(labelsize=8, color=K)
        for sp in ax.spines.values():
            sp.set_color(K); sp.set_linewidth(0.9)
        ax.set_xlim(1, 6000)
    ax1.set_ylabel("|H(f)|  [dB]", fontsize=9)
    ax2.set_ylabel("위상  [도]", fontsize=9)
    ax2.set_xlabel("주파수  [Hz]", fontsize=9)
    ax1.annotate("fc", xy=(TC.corner_frequency(t), -3),
                 xytext=(TC.corner_frequency(t) * 1.35, -6), fontsize=8.5, color=K)
    ax1.annotate("실선 : 어닐링 상태\n파선 : 냉간가공 상태", xy=(1.4, -22), fontsize=8.5, color=K)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    save(fig, "DO16_shielding")


# ===========================================================================
def do17():
    """주파수-자속밀도 성능 포락선 (그래프)"""
    import run_all as RA
    from constants import NANOCRYSTALLINE, B_LADDER_T, B_LADDER_LABEL
    wc = RA.winding_choice()
    fe = RA.feasibility_envelope(wc, NANOCRYSTALLINE)
    fig = plt.figure(figsize=(6.6, 4.8))
    fig.text(0.02, 0.97, "【도 17】", fontsize=10.5, va="top")
    ax = fig.add_subplot(1, 1, 1)
    ax.loglog([r["f_Hz"] for r in fe], [r["B_max_mT"] for r in fe],
              color=K, lw=1.4, marker="o", ms=3.5, mfc="white", mec=K)
    for b in B_LADDER_T:
        if b == 0: continue
        ax.axhline(b * 1e3, color=K, lw=0.6, ls=":")
        ax.text(3.2, b * 1e3 * 1.08, f"{b*1e3:g} mT", fontsize=8, color=K)
    ax.set_xlim(2.5, 4000); ax.set_ylim(0.3, 300)
    ax.set_xlabel("주파수  [Hz]", fontsize=9)
    ax.set_ylabel("노출 제어 체적 내 자속밀도  [mT rms]", fontsize=9)
    ax.grid(True, which="both", color="0.78", lw=0.35)
    ax.tick_params(labelsize=8)
    for sp in ax.spines.values():
        sp.set_color(K); sp.set_linewidth(0.9)
    ax.annotate("자심 포화 한계", xy=(6, 150), fontsize=8.5, color=K)
    ax.annotate("증폭기 전압 한계", xy=(900, 95), fontsize=8.5, color=K)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    save(fig, "DO17_envelope")


# ===========================================================================
def do18():
    """단계적 규모 확대 흐름도"""
    fig, ax = newfig(9.2, 3.4, (0, 18.4), (0, 6.8), 18)
    stages = [("제1 단계", "단일 셀\n5 L 폐루프"), ("제2 단계", "3 셀\n50~100 L"),
              ("제3 단계", "3 셀\n1,000 L"), ("제4 단계", "다중 셀 배열\n다중 저장조")]
    x = 0.8
    for i, (a, b) in enumerate(stages):
        tbox(ax, x, 3.2, 3.4, 2.2, f"{a}\n{b}")
        if i < 3:
            arr(ax, (x + 3.4, 4.3), (x + 4.4, 4.3))
            poly(ax, [(x + 3.35, 1.5), (x + 4.45, 1.5), (x + 4.45, 2.5), (x + 3.35, 2.5)])
            ax.text(x + 3.9, 2.0, "관문", fontsize=FS_TXT, ha="center", va="center")
            ln(ax, x + 3.9, 2.5, x + 3.9, 3.2, lw=LW_T)
        x += 4.4
    ax.text(0.8, 0.7, "각 관문에서 검증 항목 전 항 통과 및 노출 제어 체적 대 처리 체적비의 재산출을 요구한다.",
            fontsize=FS_TXT, va="center")
    save(fig, "DO18_scaleup")
