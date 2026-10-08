"""
Startup intro, shown in front of your face for ~3.7s, synced with assets/startup.wav.

  0.00  pride stripe streaks in with speed lines
  0.62  BOOM: furry card slams in (overshoot + screen shake + flash)
  0.70  sticker drops in with a bounce, light rays spin behind it
  0.85  title letters pop in one by one
  2.15  ":3" pops, hearts + sparkles burst out
  3.10  everything shrinks + fades (main.py fades the overlay alpha)
Every frame is built from cached layers, so it renders in a few ms.
"""
import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter
from lang import ImageDraw  # translates drawn text (Settings -> Language)

import ui
from logo import sticker_frames
from themes import from_key, mix

W, H = 960, 600
CARD = (40, 96, 920, 560)
EAR = 66
DURATION = 3.7
FADE_START = 3.1
T_SLAM, T_STICKER, T_TITLE, T_POP = 0.62, 0.70, 0.85, 2.15
LINE1, LINE2 = "Fluff VR", "Stats"
STICKER_H = 330


def _ease_out_back(x, s=1.9):
    x = min(max(x, 0.0), 1.0) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def _bounce(x):
    x = min(max(x, 0.0), 1.0)
    n, d = 7.5625, 2.75
    if x < 1 / d:
        return n * x * x
    if x < 2 / d:
        x -= 1.5 / d
        return n * x * x + 0.75
    if x < 2.5 / d:
        x -= 2.25 / d
        return n * x * x + 0.9375
    x -= 2.625 / d
    return n * x * x + 0.984375


@lru_cache(maxsize=4)
def _card(key):
    return ui.furry_frame(key, W, H, CARD, 44, EAR)


RAY_STEPS = 15
RAY_STEP = (math.pi / 6) / RAY_STEPS     # rays repeat every 30 degrees


@lru_cache(maxsize=RAY_STEPS * 2)
def _card_rays(key, step):
    th = from_key(key)
    scene = _card(key).copy()
    rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rays)
    rcx, rcy = 230, (CARD[1] + CARD[3]) / 2 + 20
    rot = step * RAY_STEP
    for i in range(12):
        a0 = rot + i * math.pi / 6
        rd.polygon([(rcx, rcy), (rcx + math.cos(a0 - 0.12) * 330, rcy + math.sin(a0 - 0.12) * 330),
                    (rcx + math.cos(a0 + 0.12) * 330, rcy + math.sin(a0 + 0.12) * 330)],
                   fill=th["primary"] + (55,))
    cm = Image.new("L", (W, H), 0)
    ImageDraw.Draw(cm).rounded_rectangle(CARD, radius=44, fill=255)
    rays.putalpha(Image.composite(rays.getchannel("A"), Image.new("L", (W, H), 0), cm))
    scene.alpha_composite(rays)
    return scene


@lru_cache(maxsize=4)
def _glow(key):
    """Soft dark backdrop so the intro reads in bright worlds too."""
    t = from_key(key)
    g = Image.new("RGBA", (W // 4, H // 4), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([10, 10, W // 4 - 10, H // 4 - 10], fill=t["bg"][:3] + (170,))
    return g.filter(ImageFilter.GaussianBlur(12)).resize((W, H), Image.BILINEAR)


@lru_cache(maxsize=64)
def _glyph(ch, size, color):
    f = ui.font("title", size)
    l, tp, r, b = f.getbbox(ch)
    pad = 12
    img = Image.new("RGBA", (r - l + pad * 2, b - tp + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # ink outline behind each letter, like hand-lettered stickers
    for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2), (-2, 2), (2, -2)):
        d.text((pad - l + dx, pad - tp + dy), ch, font=f, fill=(40, 30, 58))
    d.text((pad - l, pad - tp), ch, font=f, fill=color)
    return img, f.getlength(ch), pad - l, pad - tp


def _letters(text, size, color, x, baseline):
    """[(glyph img, x, y)] laid out along a baseline."""
    out = []
    f = ui.font("title", size)
    asc = f.getmetrics()[0]
    for ch in text:
        if ch == " ":
            x += f.getlength(" ")
            continue
        img, adv, ox, oy = _glyph(ch, size, color)
        out.append((img, x - ox, baseline - asc - oy))
        x += adv
    return out


@lru_cache(maxsize=4)
def _particles(seed):
    rnd = random.Random(seed)
    hearts = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(220, 520), rnd.uniform(9, 18),
               rnd.uniform(-0.15, 0.15), rnd.random() < 0.6) for _ in range(26)]
    lines = [(rnd.uniform(0, H), rnd.uniform(80, 260), rnd.uniform(1.5, 3.5), rnd.uniform(0, 1))
             for _ in range(26)]
    return hearts, lines


def _paste(dst, src, x, y):
    """alpha_composite that tolerates negative / out-of-bounds offsets."""
    cx0, cy0 = max(0, -x), max(0, -y)
    cx1, cy1 = min(src.width, dst.width - x), min(src.height, dst.height - y)
    if cx1 > cx0 and cy1 > cy0:
        dst.alpha_composite(src.crop((cx0, cy0, cx1, cy1)), (max(0, x), max(0, y)))


def frame(key, t_sec, logo_idx=0, glow=True):
    """Render the intro at time t_sec. Returns an RGBA image (W x H)."""
    th = from_key(key)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hearts, lines = _particles(1)
    cx, cy = W / 2, (CARD[1] + CARD[3]) / 2

    # backdrop glow
    a = min(1.0, t_sec / 0.4) if glow else 0
    if a > 0:
        g = _glow(key)
        if a < 1:
            g = g.copy()
            g.putalpha(g.getchannel("A").point(lambda v: int(v * a)))
        img.alpha_composite(g)

    # --- A: stripe streak + speed lines (before the slam)
    if t_sec < T_SLAM + 0.15:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        p = min(1.0, t_sec / T_SLAM) ** 2
        for y0, ln, wdt, ph in lines:
            xx = ((ph + t_sec * 2.6) % 1.3 - 0.15) * W
            d.line([(xx, y0), (xx + ln * (0.4 + p), y0)], fill=th["sub"] + (int(150 * p),),
                   width=int(wdt))
        sh = 34
        stripe_w = W * p
        n = len(th["stripe"])
        for i, c in enumerate(th["stripe"]):
            d.rectangle([0, cy - sh / 2 + i * sh / n, stripe_w, cy - sh / 2 + (i + 1) * sh / n + 1],
                        fill=c + (255,))
        # glowing head of the streak
        d.ellipse([stripe_w - 30, cy - 30, stripe_w + 30, cy + 30], fill=(255, 255, 255, 200))
        if t_sec > T_SLAM:   # streak fades as the card lands
            k = 1 - (t_sec - T_SLAM) / 0.15
            lay.putalpha(lay.getchannel("A").point(lambda v: int(v * k)))
        img.alpha_composite(lay)

    if t_sec < T_SLAM:
        return img

    # --- B: the card slams in
    x = t_sec - T_SLAM
    scale = 1 + 0.22 * math.exp(-x * 7) * math.cos(x * 20)
    if t_sec > FADE_START:
        scale *= 1 - 0.08 * (t_sec - FADE_START) / (DURATION - FADE_START)
    shake = 16 * math.exp(-x * 9)
    sx, sy = shake * math.sin(x * 83), shake * math.cos(x * 61)

    scene = _card(key).copy()
    sd = ImageDraw.Draw(scene)

    # spinning light rays behind the sticker (pre-baked rotation steps)
    if t_sec > T_STICKER:
        step = int(t_sec * 0.9 / RAY_STEP) % RAY_STEPS
        scene = _card_rays(key, step).copy()
        sd = ImageDraw.Draw(scene)

    # sticker drop with bounce
    frames, _ = sticker_frames(STICKER_H)
    if frames and t_sec > T_STICKER:
        fr = frames[logo_idx % len(frames)]
        p = _bounce((t_sec - T_STICKER) / 0.6)
        fy_final = CARD[3] - fr.height - 26
        fy = -fr.height + (fy_final + fr.height) * p
        scene.alpha_composite(fr, (int(230 - fr.width / 2), int(fy)))

    # title letters popping in
    tx = 430
    l1 = _letters(LINE1, 112, th["text"], tx, 300)
    l2 = _letters(LINE2, 112, th["text"], tx + 8, 412)
    for i, (g, gx, gy) in enumerate(l1 + l2):
        t0 = T_TITLE + i * 0.075
        if t_sec < t0:
            break
        s = _ease_out_back((t_sec - t0) / 0.22)
        if s <= 0.02:
            continue
        gw, gh = max(1, int(g.width * s)), max(1, int(g.height * s))
        gi = g.resize((gw, gh), Image.BILINEAR) if s != 1 else g
        scene.alpha_composite(gi, (int(gx + (g.width - gw) / 2), int(gy + (g.height - gh) / 2)))

    # ":3" pop
    if t_sec > T_POP:
        s = _ease_out_back((t_sec - T_POP) / 0.3, 2.6)
        g, adv, ox, oy = _glyph(":3", 112, th["primary"])
        gw, gh = max(1, int(g.width * s)), max(1, int(g.height * s))
        f112 = ui.font("title", 112)
        x3 = tx + 8 + f112.getlength(LINE2 + " ")
        y3 = 412 - f112.getmetrics()[0] - oy
        scene.alpha_composite(g.resize((gw, gh), Image.BILINEAR),
                              (int(x3 - ox + (g.width - gw) / 2), int(y3 + (g.height - gh) / 2)))

    # subtitle
    if t_sec > 1.85:
        sa = min(1.0, (t_sec - 1.85) / 0.35)
        sub = Image.new("RGBA", (W, H), (0, 0, 0, 0)) if sa < 1 else None
        if sub is None:
            sd.text((tx + 4, 462), "made with love for the fluffy community <3",
                    font=ui.font("body", 25), fill=th["sub"])
            sub = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        ImageDraw.Draw(sub).text((tx + 4, 462), "made with love for the fluffy community <3",
                                 font=ui.font("body", 25), fill=th["sub"] + (int(255 * sa),))
        scene.alpha_composite(sub, (0, 0))

    # impact flash
    if x < 0.25:
        fa = int(230 * (1 - x / 0.25) ** 2)
        fl = Image.new("RGBA", (W, H), (255, 255, 255, 0))
        fl.putalpha(scene.getchannel("A").point(lambda v: min(v, fa)))
        scene.alpha_composite(fl)

    # apply scale + shake to the whole card scene
    if abs(scale - 1) > 0.002:
        sw, shh = int(W * scale), int(H * scale)
        scene = scene.resize((sw, shh), Image.BILINEAR)
        ox, oy = int((W - sw) / 2 + sx), int((H - shh) / 2 + sy)
    else:
        ox, oy = int(sx), int(sy)
    _paste(img, scene, ox, oy)

    # hearts + sparkles burst (on top, can fly outside the card)
    if t_sec > T_POP:
        bx, by = W * 0.62, 380
        k = t_sec - T_POP
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for ang, spd, size, spin, is_heart in hearts:
            px = bx + math.cos(ang) * spd * k
            py = by + math.sin(ang) * spd * k + 260 * k * k
            al = max(0.0, 1 - k / 1.3)
            if al <= 0:
                continue
            col = (th["primary"] if is_heart else th["warn"]) + (int(255 * al),)
            line = th["line"] + (int(255 * al),)
            if is_heart:
                ui.heart(d, px, py, size + 2, line)
                ui.heart(d, px, py, size, col)
            else:
                ui.sparkle(d, px, py, size * 1.1, col)
        img.alpha_composite(lay)
    return img


def prewarm(key):
    """Bake the cached layers up front so the first second of the intro doesn't stutter."""
    _card(key)
    _glow(key)
    sticker_frames(STICKER_H)
    for k in range(RAY_STEPS):
        _card_rays(key, k)
    for ch in set(LINE1 + LINE2):
        if ch != " ":
            _glyph(ch, 112, from_key(key)["text"])
