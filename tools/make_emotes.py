"""
Makes the Fluff emote + sticker pack (all drawn in code, same doodle style as the app,
so it's 100% ours to use anywhere - Discord emotes, stickers, merch).

    python tools/make_emotes.py

-> assets/emotes/*.png      128x128 Discord emotes   (upload with Fluff Bot's /emotes)
-> assets/stickers/*.png    512x512 stickers          (Discord stickers, sticker sheets, merch)

Note: Lil Kitty's real art belongs to the anonymous artist, so it's NOT in here. Ask them first
if u want her on merch <3
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import ui  # noqa: E402

PINK, CREAM, INK = (255, 150, 202), (255, 244, 232), (58, 44, 70)
INNER = (255, 190, 220)
S = 512


def canvas():
    return Image.new("RGBA", (S, S), (0, 0, 0, 0))


def outline(img, width=14, color=(255, 255, 255)):
    """white sticker border around everything"""
    a = img.split()[-1].filter(ImageFilter.MaxFilter(width * 2 + 1))
    border = Image.new("RGBA", img.size, color + (255,))
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(border, (0, 0), a)
    out.alpha_composite(img)
    return out


def face(d, cx, cy, r, ears="cat", mood="happy", fur=CREAM):
    # ears
    for side in (-1, 1):
        if ears == "fox":
            pts = [(cx + side * r * 0.25, cy - r * 0.55), (cx + side * r * 0.95, cy - r * 1.45), (cx + side * r * 0.95, cy - r * 0.2)]
        else:
            pts = [(cx + side * r * 0.2, cy - r * 0.62), (cx + side * r * 0.85, cy - r * 1.25), (cx + side * r * 0.95, cy - r * 0.15)]
        d.polygon(pts, fill=fur, outline=INK)
        d.line(pts + [pts[0]], fill=INK, width=10, joint="curve")
        inner = [(x * 0.8 + cx * 0.2 + side * 0, y * 0.85 + (cy - r * 0.6) * 0.15) for x, y in pts]
        d.polygon(inner, fill=INNER)
    d.ellipse([cx - r, cy - r * 0.85, cx + r, cy + r * 0.95], fill=fur, outline=INK, width=10)
    # blush
    for side in (-1, 1):
        d.ellipse([cx + side * r * 0.55 - 30, cy + r * 0.18, cx + side * r * 0.55 + 30, cy + r * 0.38], fill=(255, 170, 200))
    ey = cy - r * 0.05
    if mood in ("happy", "love"):
        for side in (-1, 1):
            ex = cx + side * r * 0.38
            d.arc([ex - 34, ey - 20, ex + 34, ey + 40], 200, 340, fill=INK, width=12)
    elif mood == "wink":
        d.arc([cx - r * 0.38 - 34, ey - 20, cx - r * 0.38 + 34, ey + 40], 200, 340, fill=INK, width=12)
        d.ellipse([cx + r * 0.38 - 22, ey - 26, cx + r * 0.38 + 22, ey + 26], fill=INK)
    elif mood == "shock":
        for side in (-1, 1):
            ex = cx + side * r * 0.38
            d.ellipse([ex - 26, ey - 30, ex + 26, ey + 30], fill=INK)
            d.ellipse([ex - 8, ey - 20, ex + 6, ey - 6], fill=(255, 255, 255))
    else:   # sleepy
        for side in (-1, 1):
            ex = cx + side * r * 0.38
            d.line([(ex - 30, ey + 6), (ex + 30, ey + 6)], fill=INK, width=12)
    # :3 mouth
    my = cy + r * 0.28
    d.arc([cx - 46, my - 22, cx, my + 22], 0, 180, fill=INK, width=10)
    d.arc([cx, my - 22, cx + 46, my + 22], 0, 180, fill=INK, width=10)
    d.ellipse([cx - 12, my - 30, cx + 12, my - 14], fill=(255, 120, 160))


def e_paw():
    img = canvas()
    d = ImageDraw.Draw(img)
    ui.paw(d, S / 2, S / 2 + 30, 125, INK)
    ui.paw(d, S / 2, S / 2 + 30, 112, PINK)
    return img


def e_heart():
    img = canvas()
    d = ImageDraw.Draw(img)
    ui.doodle_heart(d, S / 2, S / 2 + 10, 200, PINK, INK)
    ui.paw(d, S / 2, S / 2 + 10, 50, (255, 255, 255))
    return img


def e_face(mood, ears="cat", fur=CREAM):
    def make():
        img = canvas()
        face(ImageDraw.Draw(img), S / 2, S / 2 + 50, 190, ears, mood, fur)
        return img
    return make


def e_pat():
    img = canvas()
    d = ImageDraw.Draw(img)
    face(d, S / 2, S / 2 + 90, 170, "cat", "happy")
    # a lil hand patting from above
    d.rounded_rectangle([S / 2 - 110, 30, S / 2 + 110, 150], radius=60, fill=(255, 220, 200), outline=INK, width=10)
    for k in range(4):
        x = S / 2 - 80 + k * 54
        d.line([(x, 70), (x, 140)], fill=INK, width=6)
    for k, (x, y) in enumerate(((60, 120), (450, 120), (90, 40), (420, 40))):
        ui.doodle_heart(d, x, y, 26, PINK, INK)
    return img


def e_boop():
    img = canvas()
    d = ImageDraw.Draw(img)
    face(d, S / 2 + 40, S / 2 + 60, 170, "fox", "shock", (255, 200, 150))
    d.rounded_rectangle([20, S / 2 + 40, S / 2 - 10, S / 2 + 100], radius=30, fill=(255, 220, 200), outline=INK, width=10)
    ui.sparkle(d, 120, 130, 40, (255, 222, 120))
    return img


def e_fps():
    img = canvas()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([40, 120, S - 40, S - 120], radius=80, fill=(40, 30, 58), outline=INK, width=12)
    d.text((S / 2, S / 2 - 10), "90", font=ui.font("title", 200), fill=(150, 236, 176), anchor="mm")
    d.text((S / 2, S / 2 + 110), "fps", font=ui.font("head", 70), fill=(255, 246, 252), anchor="mm")
    for side in (-1, 1):
        pts = [(S / 2 + side * 120, 130), (S / 2 + side * 200, 40), (S / 2 + side * 220, 150)]
        d.polygon(pts, fill=PINK, outline=INK)
        d.line(pts + [pts[0]], fill=INK, width=10)
    return img


def e_zoomies():
    img = canvas()
    d = ImageDraw.Draw(img)
    for k in range(4):
        y = 170 + k * 60
        d.line([(30, y), (200 - k * 20, y)], fill=(150, 210, 255), width=18)
    ui.paw(d, S / 2 + 70, S / 2 + 20, 105, INK)
    ui.paw(d, S / 2 + 70, S / 2 + 20, 94, PINK)
    return img


def e_pumpkin():
    img = canvas()
    d = ImageDraw.Draw(img)
    for dx in (-110, 0, 110):
        d.ellipse([S / 2 + dx - 150, 130, S / 2 + dx + 150, 440], fill=(255, 140, 40), outline=INK, width=10)
    d.rounded_rectangle([S / 2 - 22, 60, S / 2 + 22, 150], radius=12, fill=(90, 160, 70), outline=INK, width=8)
    ui.paw(d, S / 2, 310, 90, (255, 230, 120))
    return img


def e_hi():
    img = canvas()
    d = ImageDraw.Draw(img)
    face(d, S / 2 - 30, S / 2 + 60, 170, "cat", "wink")
    d.text((S - 90, 120), "hi!", font=ui.font("title", 120), fill=PINK, anchor="mm", stroke_width=8, stroke_fill=INK)
    return img


PACK = {
    "fluff_paw": e_paw, "fluff_heart": e_heart, "fluff_happy": e_face("happy"), "fluff_wink": e_face("wink"),
    "fluff_shock": e_face("shock"), "fluff_sleepy": e_face("sleepy"), "fluff_fox": e_face("happy", "fox", (255, 200, 150)),
    "fluff_pat": e_pat, "fluff_boop": e_boop, "fluff_fps": e_fps, "fluff_zoomies": e_zoomies,
    "fluff_pumpkin": e_pumpkin, "fluff_hi": e_hi,
}


def main():
    em = os.path.join(HERE, "assets", "emotes")
    st = os.path.join(HERE, "assets", "stickers")
    os.makedirs(em, exist_ok=True)
    os.makedirs(st, exist_ok=True)
    for name, fn in PACK.items():
        big = outline(fn())
        big.save(os.path.join(st, name + ".png"))
        big.resize((128, 128), Image.LANCZOS).save(os.path.join(em, name + ".png"))
    sheet = Image.new("RGBA", (S * 5, S * 3), (40, 30, 58, 255))
    for i, name in enumerate(PACK):
        sheet.alpha_composite(Image.open(os.path.join(st, name + ".png")), ((i % 5) * S, (i // 5) * S))
    sheet.save(os.path.join(st, "_sheet.png"))
    print(f"  made {len(PACK)} emotes (assets/emotes) + stickers (assets/stickers) :3")


if __name__ == "__main__":
    main()
