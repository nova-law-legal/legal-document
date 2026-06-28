# -*- coding: utf-8 -*-
"""도장(막도장) 생성 — 도장생성기 make_oval 재현.

이름 → 빨강 세로 타원 막도장(투명 PNG 1000px). 충주김생체 사용.
원본 도장생성기(_v2yb)의 oval 형태를 기준으로 재현.
"""
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import ASSETS  # noqa: E402

SEAL_FONT = os.path.join(ASSETS, "ChungjuKimSaeng.ttf")
GOTHIC_FONT = os.path.join(ASSETS, "NanumGothic-Bold.ttf")

SIZE = 1000

COLORS = {
    "red":    (199, 0, 0, 255),
    "blue":   (0, 40, 160, 255),
    "black":  (15, 15, 15, 255),
    "purple": (90, 20, 120, 255),
}


def split_units(text):
    """연속된 숫자는 한 단위로 묶고, 공백은 제거. '증제11호증'->['증','제','11','호','증']."""
    text = text.strip()
    units = []
    for tok in re.findall(r"\d+|\S", text):
        if tok.strip():
            units.append(tok)
    return units


def _fit_font(font_path, target_px):
    return ImageFont.truetype(font_path, max(8, int(target_px)))


def _char_size(font, ch):
    l, t, r, b = font.getbbox(ch)
    return (r - l), (b - t), l, t


def make_oval(name, color="red", bold=True, size=SIZE):
    """세로 타원 막도장. 투명 RGBA 이미지 반환."""
    rgba = COLORS.get(color, COLORS["red"])
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 타원 윤곽 (세로로 긴 타원, 중앙 정렬)
    ew = 0.66 * size            # 타원 가로
    eh = 0.94 * size            # 타원 세로
    cx, cy = size / 2.0, size / 2.0
    bbox = [cx - ew / 2, cy - eh / 2, cx + ew / 2, cy + eh / 2]
    stroke = int(size * (0.024 if bold else 0.015))
    draw.ellipse(bbox, outline=rgba, width=stroke)

    # 이름 글자 — 세로 1열, 가운데 정렬
    units = split_units(name)
    if not units:
        return img
    n = len(units)
    col_h = eh * 0.80           # 글자 영역 세로
    col_w = ew * 0.66           # 글자 영역 가로
    cell_h = col_h / n
    # 글자 크기: 셀 높이와 글자 폭 한도 중 작은 값
    target = min(cell_h * 0.92, col_w)
    font = _fit_font(SEAL_FONT, target * 1.35)  # 김생체는 실제 글리프가 작아 보정
    stroke_w = int(target * (0.06 if bold else 0.0))

    top = cy - col_h / 2
    for i, ch in enumerate(units):
        cyi = top + (i + 0.5) * cell_h
        draw.text((cx, cyi), ch, font=font, fill=rgba, anchor="mm",
                  stroke_width=stroke_w, stroke_fill=rgba)
    return img


def make_stamp(name, kind="oval", color="red", bold=True, size=SIZE):
    if kind == "oval":
        return make_oval(name, color=color, bold=bold, size=size)
    # 추후: grid / vertical
    return make_oval(name, color=color, bold=bold, size=size)


def save_stamp(name, out_path, kind="oval", color="red", bold=True):
    img = make_stamp(name, kind=kind, color=color, bold=bold)
    img.save(out_path)
    return out_path


if __name__ == "__main__":
    import sys
    out = sys.argv[2] if len(sys.argv) > 2 else "stamp.png"
    save_stamp(sys.argv[1] if len(sys.argv) > 1 else "표은정", out)
    print("saved", out)
