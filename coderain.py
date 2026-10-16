"""Falling-code wall for the desktop window in Normie Mode (a dim, Matrix-style green rain).

The texture is built once per window size (rounded up to 64px) and every frame is just one crop-and-paste
per column, so it costs a few ms at ~12 fps. Pure Pillow, no VR needed."""
import os
import random
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
CELL = 16
GLYPHS = "01{}[]()<>;=+-/&|!?#$%@:_~^abcdefxyz0123456789"
BRIGHTNESS = 0.78            # keep it a wall behind the UI, not a spotlight


def _font():
    try:
        return ImageFont.truetype(os.path.join(HERE, "fonts", "DejaVuSans.ttf"), 13)
    except Exception:
        return ImageFont.load_default()


@lru_cache(maxsize=4)
def _texture(wq, hq):
    """wq x hq*2 picture of code streams that tiles vertically, plus a (speed, phase) per column"""
    th = hq * 2
    rnd = random.Random(1337)
    cols = wq // CELL
    tex = Image.new("RGB", (wq, th), (0, 0, 0))
    d = ImageDraw.Draw(tex)
    f = _font()
    info = []
    for c in range(cols):
        x = c * CELL + 2
        info.append((rnd.uniform(40, 140), rnd.uniform(0, th)))
        y = rnd.uniform(0, th)
        while y < th + th:                       # a few streams per column, each with a fading tail
            length = rnd.randint(8, 26)
            for k in range(length):
                fade = (1 - k / length) ** 1.4 * BRIGHTNESS
                col = (int(190 * fade), int(255 * fade), int(200 * fade)) if k == 0 else (0, int(235 * fade), int(60 * fade))
                ch = rnd.choice(GLYPHS)
                for yy in (y - k * CELL, y - k * CELL - th):      # drawn twice so the wrap-around is seamless
                    if -CELL < yy < th:
                        d.text((x, yy), ch, font=f, fill=col)
            y += length * CELL + rnd.uniform(2, 14) * CELL
    return tex, tuple(info)


def behind(card, now, size=None, origin=(0, 0), card_alpha=0.86):
    """`card` (RGBA) drawn over the code rain. With `size` the rain fills that bigger canvas and the card sits at
    `origin` (desktop window / fullscreen); otherwise the rain fills the card's own box (VR menu + wrist). Returns RGBA."""
    card = card.convert("RGBA")
    cw, ch = size or card.size
    base = frame(cw, ch, now).convert("RGBA")
    mask = card.getchannel("A").point(lambda v: int(v * card_alpha))
    base.paste(card, origin, mask)
    if not size:                       # VR overlays keep their own see-through edges
        base.putalpha(card.getchannel("A").point(lambda v: 255 if v > 0 else 0))
    return base


def frame(w, h, t):
    """RGB picture w x h of the rain at time t (seconds)"""
    w, h = max(1, int(w)), max(1, int(h))
    wq, hq = -(-w // 64) * 64, -(-h // 64) * 64
    tex, info = _texture(wq, hq)
    th = tex.height
    out = Image.new("RGB", (wq, h), (0, 0, 0))
    for c, (speed, phase) in enumerate(info):
        off = int(t * speed + phase) % th
        x = c * CELL
        first = min(h, th - off)
        out.paste(tex.crop((x, off, x + CELL, off + first)), (x, 0))
        if first < h:
            out.paste(tex.crop((x, 0, x + CELL, h - first)), (x, first))
    return out.crop((0, 0, w, h)) if wq != w else out
