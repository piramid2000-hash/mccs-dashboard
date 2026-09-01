# -*- coding: utf-8 -*-
"""도면 전체를 1매 1도면의 단일 PDF로 편집한다 (출원 첨부용)."""
import os, sys
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H); sys.path.insert(0, os.path.join(H, "..", "design"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import patent_draw as PD

OUT = os.path.join(H, "QHSRS_도면.pdf")
pdf = PdfPages(OUT)
_orig = PD.save
_n = [0]

def save_hook(fig, name):
    _orig(fig.__class__ and fig, name) if False else None
    for ext in ("png", "svg"):
        fig.savefig(os.path.join(PD.OUT, f"{name}.{ext}"))
    pdf.savefig(fig)
    plt.close(fig)
    _n[0] += 1
    print("  ", _n[0], name)

PD.save = save_hook
import make_patent_figs as M
M.save = save_hook          # 모듈이 이미 import 한 이름도 교체
for i in range(1, 23):
    getattr(M, f"do{i:02d}")()
d = pdf.infodict()
d["Title"] = "극저주파 자기장 수계 노출 장치 및 그 제어 방법 - 도면"
d["Subject"] = "특허출원 첨부 도면 (도 1 내지 도 18)"
pdf.close()
print("wrote", OUT, os.path.getsize(OUT) // 1024, "KB,", _n[0], "매")
