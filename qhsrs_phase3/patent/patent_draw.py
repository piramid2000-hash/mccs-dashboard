# -*- coding: utf-8 -*-
"""
특허도면 작도 공통 모듈 (KIPO 도면 작성 요령 준거)

규격 준수 사항
--------------
* 흑백 선화만 사용한다. 색채, 음영(shading), 계조(gradation)를 쓰지 않는다.
* 선의 굵기는 균일하고 충분히 진하게 한다(외형선 1.1pt, 보조선·해칭 0.6pt).
* 단면부는 45° 평행 해칭으로 표시하고, 재질이 다르면 해칭 방향·간격을 달리한다.
* 도면에는 설명문자를 기재하지 않는다.
  다만 블록도·흐름도·회로도에는 필요한 문자를 기재할 수 있다(요령 제3조 단서).
* 참조부호는 인출선으로 대상을 지시하며, 모든 도면에서 동일 부호는 동일 부재를 가리킨다.
"""
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, FancyArrowPatch, Arc, PathPatch
from matplotlib.path import Path

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)

LW = 1.1          # 외형선
LW_T = 0.6        # 보조선 / 인출선 / 해칭
FS_NUM = 9.5      # 참조부호
FS_TXT = 8.5      # 블록도·흐름도 문자

plt.rcParams.update({
    "font.family": "NanumGothic",
    "font.size": FS_TXT,
    "hatch.linewidth": 0.45,
    "figure.dpi": 200,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
    "text.color": "black",
    "axes.edgecolor": "black",
    "axes.unicode_minus": False,
})

K = "black"


# ---------------------------------------------------------------------------
def newfig(w, h, xlim, ylim, dono):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(*xlim); ax.set_ylim(*ylim)
    ax.set_aspect("equal"); ax.axis("off")
    ax.text(xlim[0], ylim[1], f"【도 {dono}】", fontsize=10.5, va="top", ha="left")
    return fig, ax


def save(fig, name):
    for ext in ("png", "svg", "pdf"):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"))
    plt.close(fig)
    print("  ", name)


def ln(ax, x1, y1, x2, y2, lw=LW, ls="-"):
    ax.plot([x1, x2], [y1, y2], color=K, lw=lw, ls=ls, solid_capstyle="butt")


def poly(ax, pts, hatch=None, lw=LW, close=True, ls="-"):
    ax.add_patch(Polygon(pts, closed=close, fill=False, ec=K, lw=lw, ls=ls,
                         hatch=hatch, joinstyle="miter"))


def rect(ax, x, y, w, h, hatch=None, lw=LW, ls="-"):
    ax.add_patch(Rectangle((x, y), w, h, fill=False, ec=K, lw=lw, ls=ls, hatch=hatch))


def circ(ax, x, y, r, hatch=None, lw=LW, ls="-"):
    ax.add_patch(Circle((x, y), r, fill=False, ec=K, lw=lw, ls=ls, hatch=hatch))


def arr(ax, p, q, lw=LW, ls="-", scale=8):
    """실선 화살표 (자속·흐름·신호 방향 표시용)."""
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=scale,
                                 lw=lw, ls=ls, color=K, shrinkA=0, shrinkB=0))


def num(ax, text, tip, tail, dot=True, fs=FS_NUM, ha=None, va="center", pad=0.9):
    """
    참조부호 기입.
    tip  : 지시 대상 좌표 (인출선 끝)
    tail : 부호를 놓을 좌표
    """
    ln(ax, tail[0], tail[1], tip[0], tip[1], lw=LW_T)
    if dot:
        ax.add_patch(Circle(tip, 0.0, fill=True, color=K))
        ax.plot([tip[0]], [tip[1]], marker="o", ms=2.0, color=K)
    if ha is None:
        ha = "right" if tail[0] < tip[0] else "left"
    dx = -pad if ha == "right" else pad
    ax.text(tail[0] + dx * 0.35, tail[1], text, fontsize=fs, ha=ha, va=va, color=K)


def num_plain(ax, text, xy, fs=FS_NUM, ha="center", va="center"):
    ax.text(xy[0], xy[1], text, fontsize=fs, ha=ha, va=va, color=K)


def tbox(ax, x, y, w, h, text, fs=FS_TXT, lw=LW, ref=None, ref_dx=0.0, ref_dy=0.0):
    """블록도용 문자 상자 (요령상 블록도에는 문자 기재 허용)."""
    rect(ax, x, y, w, h, lw=lw)
    ax.text(x + w / 2, y + h / 2, text, fontsize=fs, ha="center", va="center",
            color=K, linespacing=1.35)
    if ref:
        ax.text(x + w + 0.10 + ref_dx, y + h + 0.06 + ref_dy, ref,
                fontsize=FS_NUM, ha="left", va="bottom", color=K)


def dbox(ax, x, y, w, h, text, fs=FS_TXT):
    """흐름도용 마름모(판단) 기호."""
    cx, cy = x + w / 2, y + h / 2
    poly(ax, [(cx, y + h), (x + w, cy), (cx, y), (x, cy)])
    ax.text(cx, cy, text, fontsize=fs, ha="center", va="center", linespacing=1.3)


def rbox(ax, x, y, w, h, text, fs=FS_TXT, ref=None):
    """흐름도용 처리 상자 (모서리 직각)."""
    rect(ax, x, y, w, h)
    ax.text(x + w / 2, y + h / 2, text, fontsize=fs, ha="center", va="center",
            linespacing=1.35)
    if ref:
        ax.text(x - 0.12, y + h / 2, ref, fontsize=FS_NUM, ha="right", va="center")


def coil_side(ax, x, y, w, h, n=6, hatch="////"):
    """코일 단면 (권선 다발을 등간격 사각형으로 표기)."""
    for i in range(n):
        yy = y + i * h / n
        rect(ax, x, yy + h / n * 0.12, w, h / n * 0.76, hatch=hatch, lw=LW_T)


def coil_on_leg(ax, lx, lw_, y, h, n=7, cw=1.0):
    """각부(leg) 양측에 코일 단면을 표기한다 (권선을 감싼 형상)."""
    for x in (lx - cw, lx + lw_):
        for i in range(n):
            yy = y + i * h / n
            rect(ax, x, yy + h / n * 0.13, cw, h / n * 0.74, hatch="////", lw=LW_T)


def hatch_core(ax, x, y, w, h):
    rect(ax, x, y, w, h, hatch="\\\\\\", lw=LW)


def leader_bracket(ax, x1, x2, y, text, up=True, fs=FS_NUM):
    """치수선 형태의 범위 지시 (부호 묶음용)."""
    t = 0.12 if up else -0.12
    ln(ax, x1, y, x2, y, lw=LW_T)
    ln(ax, x1, y, x1, y - t, lw=LW_T)
    ln(ax, x2, y, x2, y - t, lw=LW_T)
    ax.text((x1 + x2) / 2, y + (0.16 if up else -0.30), text, fontsize=fs,
            ha="center", va="bottom" if up else "top")


# ---------------------------------------------------------------------------
# 부호의 설명 (모든 도면 공통)
# ---------------------------------------------------------------------------
SIGNS = [
 ("100", "극저주파 자기장 수계 노출 장치"),
 ("110", "저장조 (도전성 금속제 탱크)"),
 ("111", "저장조 벽체"),
 ("120", "순환 유로"),
 ("121", "순환 펌프"),
 ("122", "유량계"),
 ("123", "열교환기 및 항온기"),
 ("124", "시료 채취부"),
 ("130", "비금속 노출 덕트"),
 ("131", "덕트 벽"),
 ("132", "수로"),
 ("140", "노출 셀"),
 ("140a, 140b, 140c", "제1 내지 제3 노출 셀"),
 ("141", "제1 자극편"),
 ("142", "제2 자극편"),
 ("143", "제1 각부"),
 ("144", "제2 각부"),
 ("145", "요크"),
 ("146", "자기 공극"),
 ("147", "제1 코일"),
 ("148", "제2 코일"),
 ("1471", "리츠선 소선"),
 ("1472", "층간 절연층"),
 ("1473", "함침 수지"),
 ("149", "노출 제어 체적"),
 ("1491~1495", "제1 내지 제5 자장 측정 위치"),
 ("150", "구동부"),
 ("151", "파형 발생부"),
 ("152", "전류 제어형 전력 증폭부"),
 ("153", "대역 전환 직렬 보상부"),
 ("154", "보상 커패시터"),
 ("155", "대역 전환 접점"),
 ("160", "계측부"),
 ("161", "제1 계층 코일 전류 센서"),
 ("162", "제2 계층 외부 기준 자기 센서"),
 ("163", "제3 계층 수중 자기 센서"),
 ("164", "동기 복조부"),
 ("165", "3차원 프로브 이송부"),
 ("166", "교정용 헬름홀츠 코일"),
 ("170", "제어부"),
 ("171", "외측 자속밀도 제어 루프"),
 ("172", "내측 전류 제어 루프"),
 ("173", "전달계수 저장부"),
 ("174", "디지털 트윈부"),
 ("180", "안전부"),
 ("181", "하드와이어 인터록 체인"),
 ("182", "안전 릴레이"),
 ("183", "증폭기 인에이블 접점"),
 ("190", "대조부 (샴)"),
 ("191", "대조 덕트"),
 ("192", "바이파일러 상쇄 권선"),
 ("200", "열관리부"),
 ("201", "냉각판"),
 ("202", "냉매 유로"),
 ("203", "온도 센서"),
 ("210", "수질 계측부"),
]
