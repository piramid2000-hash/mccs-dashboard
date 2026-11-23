"""안드로이드 런처 아이콘·스플래시·구글 플레이 그래픽 생성 (웹앱 아이콘과 같은 '공정표' 마크).

python android/tools/make_assets.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "app/src/main/res"
PLAY = ROOT / "play"
BLUE = (31, 95, 191, 255)
WHITE = (255, 255, 255, 255)
YELLOW = (255, 201, 77, 255)


def mark(d, S, cx, cy, w, alpha_line=140):
    """가운데 (cx,cy), 폭 w 인 공정표 마크."""
    h, gap = w * 0.13, w * 0.12
    x0, top = cx - w / 2, cy - (3 * h + 2 * gap) / 2
    for i, (a, b, col) in enumerate([(0, .55, WHITE), (.22, .82, WHITE), (.45, .88, YELLOW)]):
        y = top + i * (h + gap)
        d.rounded_rectangle([x0 + w * a, y, x0 + w * b, y + h], radius=h / 2, fill=col)
    dx, dy, r = x0 + w * .97, top + 2 * (h + gap) + h / 2, h * .95
    d.polygon([(dx, dy - r), (dx + r, dy), (dx, dy + r), (dx - r, dy)], fill=WHITE)
    tx = x0 + w * .36
    d.rectangle([tx - S * .006, top - h * .8, tx + S * .006, top + 3 * h + 2 * gap + h * .8], fill=(255, 255, 255, alpha_line))


def square(size, rounded=True, content=0.64, bg=BLUE):
    S = size * 4
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if bg:
        if rounded:
            d.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * .22), fill=bg)
        else:
            d.rectangle([0, 0, S, S], fill=bg)
    mark(d, S, S / 2, S / 2, S * content)
    return im.resize((size, size), Image.LANCZOS)


def main():
    dens = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}
    for name, k in dens.items():
        d = RES / f"mipmap-{name}"
        d.mkdir(parents=True, exist_ok=True)
        square(int(48 * k)).save(d / "ic_launcher.png")
        # 적응형 아이콘 전경: 108dp 캔버스, 마크는 가운데 66dp 안전영역 안
        square(int(108 * k), bg=None, content=0.40).save(d / "ic_launcher_foreground.png")
    any_ = RES / "mipmap-anydpi-v26"
    any_.mkdir(parents=True, exist_ok=True)
    (any_ / "ic_launcher.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
        '    <background android:drawable="@color/colorPrimary" />\n'
        '    <foreground android:drawable="@mipmap/ic_launcher_foreground" />\n'
        '    <monochrome android:drawable="@mipmap/ic_launcher_foreground" />\n'
        '</adaptive-icon>\n', encoding="utf-8")
    sp = RES / "drawable-xxhdpi"
    sp.mkdir(parents=True, exist_ok=True)
    square(288).save(sp / "splash.png")   # 96dp

    PLAY.mkdir(exist_ok=True)
    square(512, rounded=False, content=0.62).convert("RGB").save(PLAY / "icon-512.png")  # Play 는 직접 모서리를 깎음
    # 기능 그래픽 1024x500
    W, H = 1024, 500
    S = 4
    fg = Image.new("RGB", (W * S, H * S), BLUE[:3])
    d = ImageDraw.Draw(fg)
    mark(d, W * S, W * S * .22, H * S / 2, W * S * .26, alpha_line=160)
    font_path = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
    f1 = ImageFont.truetype(font_path, 74 * S)
    f2 = ImageFont.truetype(font_path, 34 * S)
    d.text((W * S * .43, H * S * .30), "원이엔지 경영", font=f1, fill=WHITE)
    d.text((W * S * .43, H * S * .56), "공사·외주 진척과 수주·수금을", font=f2, fill=(223, 233, 248))
    d.text((W * S * .43, H * S * .66), "매일 아침 한 화면에", font=f2, fill=(223, 233, 248))
    fg.resize((W, H), Image.LANCZOS).save(PLAY / "feature-graphic-1024x500.png")
    print("assets written")


if __name__ == "__main__":
    main()
