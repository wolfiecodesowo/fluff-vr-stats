"""Trailer v2: fast beat-synced TikTok edit (9:16), built from the app's real UI.
Usage: python tools/make_trailer2.py out.mp4 music2.wav"""
import math
import os
import random
import subprocess
import sys
import time as _time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont  # noqa: E402

import make_trailer as base  # noqa: E402  (fake world, clock, stats, helpers)
import intro  # noqa: E402
import logo  # noqa: E402
import ui  # noqa: E402
from themes import mix, PRESET_MAP  # noqa: E402

W, H, FPS = 1080, 1920, 30
BPM = 140
BEAT = 60 / BPM
BAR = BEAT * 4
TOTAL = BAR * 11 + 1.6
cfg, st = base.cfg, base.st
INK = (24, 14, 34)

CAP = os.path.join(HERE, "fonts", "LilitaOne-Regular.ttf")
EMOJI_PATHS = ["/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", r"C:\Windows\Fonts\seguiemj.ttf"]
_fc = {}


def capfont(size):
    if size not in _fc:
        _fc[size] = ImageFont.truetype(CAP, size)
    return _fc[size]


_emo = {}


def emoji(ch, size):
    """Color emoji as an RGBA image (Noto renders at 109px, then we scale)."""
    key = (ch, size)
    if key in _emo:
        return _emo[key]
    img = None
    for p in EMOJI_PATHS:
        if os.path.exists(p):
            try:
                f = ImageFont.truetype(p, 109)
                im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
                ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
                bb = im.getbbox()
                if bb:
                    im = im.crop(bb)
                    img = im.resize((size, int(size * im.height / im.width)), Image.LANCZOS)
                    break
            except Exception:
                pass
    _emo[key] = img
    return img


def shadowed(img, off=14, alpha=255):
    """Hard drop shadow = graphic sticker look."""
    out = Image.new("RGBA", (img.width + off, img.height + off), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, INK + (alpha,))
    out.paste(sh, (off, off), img.getchannel("A"))
    out.alpha_composite(img, (0, 0))
    return out


def paste(c, img, cx, cy, scale=1.0, rot=0.0, alpha=1.0):
    base.paste_center(c, img, cx, cy, scale=scale, rot=rot, alpha=alpha)


def word_img(text, size, fill, stroke=None, tilt=0):
    f = capfont(size)
    l, t, r, b = f.getbbox(text, stroke_width=stroke or max(6, size // 9))
    img = Image.new("RGBA", (r - l + 30, b - t + 30), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((15 - l, 15 - t), text, font=f, fill=fill,
                             stroke_width=stroke or max(6, size // 9), stroke_fill=INK)
    return img


def caption(c, words, times, t, y, size=120, hl=(), hl_col=(255, 226, 70), tilt=-3, max_w=980):
    """CapCut-style: words pop in on the beat, highlighted words in color, wraps to lines."""
    imgs = []
    for i, w_ in enumerate(words):
        col = hl_col if i in hl else (255, 255, 255)
        imgs.append(word_img(w_, size, col))
    # wrap
    lines, cur, cw = [], [], 0
    for i, im in enumerate(imgs):
        if cur and cw + im.width > max_w:
            lines.append(cur)
            cur, cw = [], 0
        cur.append(i)
        cw += im.width - 8
    if cur:
        lines.append(cur)
    yy = y
    for ln in lines:
        lw = sum(imgs[i].width - 8 for i in ln)
        x = W / 2 - lw / 2
        lh = max(imgs[i].height for i in ln)
        for i in ln:
            k = (t - times[i]) / 0.16
            if k > 0:
                s = base.ease_out_back(k, 3.0)
                paste(c, imgs[i], x + imgs[i].width / 2, yy + lh / 2, scale=max(0.05, s),
                      rot=tilt + (2 if i % 2 else -1))
            x += imgs[i].width - 8
        yy += lh - 18


def scribble_circle(d, cx, cy, rx, ry, col, seed=1, k=1.0):
    rnd = random.Random(seed)
    pts = []
    n = int(60 * k)
    for i in range(n + 1):
        a = -1.2 + i / 60 * 2 * math.pi * 1.08
        rr = 1 + rnd.uniform(-0.04, 0.04)
        pts.append((cx + math.cos(a) * rx * rr, cy + math.sin(a) * ry * rr))
    if len(pts) > 1:
        d.line(pts, fill=INK, width=14, joint="curve")
        d.line(pts, fill=col, width=8, joint="curve")


def scribble_arrow(d, x0, y0, x1, y1, col, k=1.0):
    mx, my = (x0 + x1) / 2 + (y1 - y0) * 0.25, (y0 + y1) / 2 - (x1 - x0) * 0.25
    pts = []
    for i in range(int(30 * k) + 1):
        u = i / 30
        pts.append(((1 - u) ** 2 * x0 + 2 * (1 - u) * u * mx + u * u * x1,
                    (1 - u) ** 2 * y0 + 2 * (1 - u) * u * my + u * u * y1))
    if len(pts) > 1:
        d.line(pts, fill=INK, width=14, joint="curve")
        d.line(pts, fill=col, width=8, joint="curve")
    if k >= 1:
        ang = math.atan2(y1 - pts[-4][1], x1 - pts[-4][0])
        for s in (2.5, -2.5):
            hx, hy = x1 - math.cos(ang + s * 0.25) * 50, y1 - math.sin(ang + s * 0.25) * 50
            d.line([(x1, y1), (hx, hy)], fill=INK, width=14)
            d.line([(x1, y1), (hx, hy)], fill=col, width=8)


# ---------------------------------------------------------------- backgrounds ---
PALS = {"pink": ((255, 92, 178), (255, 140, 206)), "cyan": ((60, 210, 240), (120, 230, 250)),
        "lime": ((180, 240, 80), (210, 250, 140)), "purple": ((120, 70, 230), (160, 110, 250)),
        "yellow": ((255, 214, 60), (255, 230, 120)), "black": ((22, 14, 30), (40, 26, 52))}
GRAIN = [Image.effect_noise((W // 2, H // 2), 40).convert("L").resize((W, H)) for _ in range(4)]


def bg(t, pal="pink", pattern="checker"):
    a, b = PALS[pal]
    img = Image.new("RGBA", (W, H), a + (255,))
    d = ImageDraw.Draw(img)
    if pattern == "checker":
        s = 120
        off = (t * 60) % (s * 2)
        for yy in range(-2, H // s + 3):
            for xx in range(-2, W // s + 3):
                if (xx + yy) % 2 == 0:
                    x0, y0 = xx * s + off, yy * s + off * 0.5
                    d.rectangle([x0, y0, x0 + s, y0 + s], fill=b)
    elif pattern == "stripes":
        s = 90
        off = (t * 140) % (s * 2)
        for i in range(-30, 40):
            x = i * s * 2 + off
            d.polygon([(x, 0), (x + s, 0), (x + s - H * 0.5, H), (x - H * 0.5, H)], fill=b)
    elif pattern == "dots":
        s = 70
        for yy in range(0, H // s + 2):
            for xx in range(0, W // s + 2):
                r = 10 + 8 * math.sin(t * 4 + xx * 0.6 + yy * 0.4)
                cx, cy = xx * s + (s / 2 if yy % 2 else 0), yy * s
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=b)
    elif pattern == "pride":
        th = ui.get_theme(cfg)
        cols = th["stripe"]
        hgt = H / len(cols)
        for i, col in enumerate(cols):
            d.rectangle([0, i * hgt, W, (i + 1) * hgt], fill=col)
        d.rectangle([0, 0, W, H], fill=None)
    # sticker-bomb paws
    rnd = random.Random(pal + pattern)
    for i in range(10):
        x, y = rnd.uniform(0, W), (rnd.uniform(0, H) - t * rnd.uniform(40, 90)) % H
        r = rnd.uniform(26, 50)
        ui.paw(d, x, y, r * 0.75, INK)
        ui.paw(d, x - 3, y - 3, r * 0.6, (255, 255, 255))
    return img


# ------------------------------------------------------------------- content ---
STICK, _ = logo.sticker_frames(620)
ERRS, _ = logo.sticker_frames(560, logo.ERROR_ART)
BIGSTICK = [shadowed(s, 18) for s in STICK]
ERRSTICK = [shadowed(s, 18) for s in ERRS]


def beat_of(t, start):
    return int((t - start) / BEAT)


def kick_pulse(t, start):
    x = (t - start) % BEAT
    return 1 + 0.045 * math.exp(-x * 14)


def hook(c, t):                       # bar 0
    caption(c, ["i", "made", "a", "VR", "overlay"], [0.0, 0.1, 0.2, BEAT * 0.9, BEAT * 1.15], t, 260, 128,
            hl=(3, 4))
    if t > BEAT * 2:
        k = base.ease_out_back((t - BEAT * 2) / 0.22, 2.6)
        fr = BIGSTICK[int(t * 10) % len(BIGSTICK)]
        paste(c, fr, W / 2, 1060, scale=max(0.05, k * 0.95), rot=-6 + math.sin(t * 8) * 3)
    caption(c, ["and", "it's", "SO", "FURRY"], [BEAT * 2, BEAT * 2.2, BEAT * 3, BEAT * 3.2], t, 1480, 140,
            hl=(2, 3), hl_col=(255, 120, 200))
    e = emoji("😭", 170)
    if e and t > BEAT * 3.3:
        paste(c, shadowed(e, 10), 900, 1260, scale=base.ease_out_back((t - BEAT * 3.3) / 0.2, 3), rot=12)


def wrist(c, t):                      # bar 1
    hud = ui.render_hud(st)
    paste(c, shadowed(hud, 16), W / 2 + 30, 1060, scale=1.6 * kick_pulse(t, 0), rot=-3 + math.sin(t * 3) * 1.5)
    caption(c, ["fps", "on", "ur", "WRIST"], [0, 0.1, 0.2, BEAT], t, 260, 140, hl=(3,))


def tail(c, t):                       # bar 2: zoom on the tail
    hud = ui.render_hud(st)
    z = 1.6 + 1.1 * base.ease(t / 0.35)
    # zoom so the tail comes into view (tail lives at the HUD's bottom-right)
    cx = W / 2 + 30 - (hud.width * 0.36) * (z - 1.6) / 1.1 * 1.6
    cy = 1060 - (hud.height * 0.3) * (z - 1.6) / 1.1 * 1.6
    paste(c, shadowed(hud, 16), cx, cy, scale=z * kick_pulse(t, 0))
    d = ImageDraw.Draw(c)
    if t > 0.35:
        k = min(1, (t - 0.35) / 0.3)
        scribble_circle(d, 790, 1150, 230, 330, (255, 226, 70), seed=3, k=k)
    if t > 0.6:
        k = min(1, (t - 0.6) / 0.25)
        scribble_arrow(d, 300, 1640, 600, 1360, (255, 226, 70), k=k)
        if k >= 1:
            paste(c, word_img("it has a TAIL.", 104, (255, 255, 255)), 330, 1700, rot=-6)
    caption(c, ["wait", "look"], [0, 0.12], t, 260, 130, hl=(1,))


THEMES_SEQ = ["trans_soft", "lava_dragon", "gay_ocean", "cotton_candy"]
PAL_SEQ = ["cyan", "yellow", "lime", "pink"]


def themes(c, t):                     # bar 3: theme per beat
    i = min(3, beat_of(t, 0))
    cfg["theme"], cfg["style"]["ears"] = THEMES_SEQ[i], "cat"
    hud = ui.render_hud(st)
    pop = 1 + 0.12 * math.exp(-((t % BEAT)) * 12)
    paste(c, shadowed(hud, 16), W / 2 + 30, 1080, scale=1.55 * pop, rot=(-4, 3, -2, 4)[i])
    caption(c, ["24", "THEMES"], [0, 0.1], t, 260, 170, hl=(1,), hl_col=(255, 120, 200))
    th = ui.get_theme(cfg)
    chip = word_img(th["label"], 80, th["primary"])
    paste(c, chip, W / 2, 1700, scale=pop)


EARS_SEQ = ["fox", "bunny", "wolf", "bear", "dragon", "cat", "fox", "bunny"]


def ears(c, t):                       # bar 4: ears per half-beat
    i = min(7, int(t / (BEAT / 2)))
    cfg["theme"], cfg["style"]["ears"] = ("pride_pastel", "bi_night", "honey_bear", "frost_wolf",
                                          "lava_dragon", "neon_rave", "sunset_fox", "strawberry_milk")[i], EARS_SEQ[i]
    hud = ui.render_hud(st)
    pop = 1 + 0.1 * math.exp(-((t % (BEAT / 2))) * 16)
    paste(c, shadowed(hud, 16), W / 2 + 30, 1100, scale=1.55 * pop)
    caption(c, ["pick", "ur", "EARS"], [0, 0.1, 0.2], t, 260, 150, hl=(2,))
    paste(c, word_img(EARS_SEQ[i] + " ears", 96, (255, 255, 255)), W / 2, 1720, scale=pop, rot=-3)


def music(c, t):                      # bar 5
    cfg["theme"], cfg["style"]["ears"] = "pride_pastel", "cat"
    st.tab = "Music"
    st.music["playing"] = t < BEAT * 2
    st.logo_frame = None
    basei, hit = ui.render_dashboard(st)
    th = ui.get_theme(cfg)
    img = ui.add_logo(basei, int(t * 10), st.anim_slots)
    play = base._hit_center(hit, "music", "play_pause")
    k = base.ease(t / (BEAT * 1.8))
    cur = (520 + (play[0] - 520) * k, 560 + (play[1] - 560) * k)
    img = ui.draw_hover(img, hit.find_box(*cur), th)
    clicks = [(play[0], play[1], t - BEAT * 2)] if t > BEAT * 2 else []
    img = ui.draw_cursor(img, cur, [], [cl for cl in clicks if cl[2] < 0.6], th)
    paste(c, shadowed(img, 16), W / 2, 1080, scale=1.04 * kick_pulse(t, 0), rot=-2)
    caption(c, ["music", "controls"], [0, 0.12], t, 280, 140, hl=(1,))
    e = emoji("🎧", 150)
    if e:
        paste(c, shadowed(e, 10), 910, 1560, scale=base.ease_out_back(t / 0.25, 3), rot=14)


def chatbox_s(c, t):                  # bar 6
    import chatbox as cbx
    text = cbx.compose(cfg, st.stats, st.extras, st.music, base.CLOCK.t)
    lines = text.split("\n")
    shown = max(1, min(len(lines), beat_of(t, 0) + 2))
    bw, lh = 920, 66
    bh = 60 + lh * len(lines)
    bub = Image.new("RGBA", (bw + 20, bh + 60), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bub)
    bd.rounded_rectangle([10, 10, bw + 10, bh + 10], radius=44, fill=(18, 18, 24, 245), outline=(255, 255, 255), width=5)
    bd.polygon([(bw / 2 - 20, bh + 10), (bw / 2 + 44, bh + 10), (bw / 2 + 10, bh + 54)], fill=(18, 18, 24, 245))
    for i, ln in enumerate(lines[:shown]):
        ui.rich_text(bd, (bw / 2 + 10, 40 + i * lh), ln, 50, (255, 255, 255), center=True)
    k = base.ease_out_back(t / 0.25, 2.5)
    paste(c, shadowed(bub, 16), W / 2, 1050, scale=max(0.05, k) * kick_pulse(t, 0), rot=2)
    caption(c, ["VRChat", "chatbox", "FLEX"], [0, 0.1, BEAT], t, 300, 140, hl=(2,), hl_col=(120, 230, 250))
    e = emoji("💬", 150)
    if e:
        paste(c, shadowed(e, 10), 170, 1560, scale=base.ease_out_back((t - 0.2) / 0.25, 3), rot=-12)


CHAT = [(0.0, "user", "fluff am i lagging??"), (BEAT * 1.2, "assistant", "nope!! 88 fps, smooth as ur tail fur :3"),
        (BEAT * 2.6, "user", "ily fluff"), (BEAT * 3.2, "assistant", "ily too!! *headpats*")]


def ai_s(c, t):                       # bar 7
    st.tab = "Chat"
    st.chat = [(r, m) for t0, r, m in CHAT if t >= t0]
    st.thinking = False
    st.logo_frame = None
    basei, hit = ui.render_dashboard(st)
    img = ui.add_logo(basei, int(t * 10), st.anim_slots)
    paste(c, shadowed(img, 16), W / 2, 1080, scale=1.04 * kick_pulse(t, 0), rot=2)
    caption(c, ["an", "AI", "bestie"], [0, 0.1, 0.2], t, 280, 150, hl=(2,), hl_col=(255, 120, 200))
    e = emoji("💕", 150)
    if e:
        paste(c, shadowed(e, 10), 890, 1620, scale=base.ease_out_back((t - BEAT) / 0.25, 3), rot=10)


def error_s(c, t):                    # bar 8: record scratch gag
    k = base.ease_out_back((t - 0.4) / 0.25, 3)
    if t > 0.4:
        fr = ERRSTICK[int(t * 10) % len(ERRSTICK)]
        shake = 14 * max(0, 1 - (t - 0.4) / 0.4) * math.sin(t * 80)
        paste(c, fr, W / 2 + shake, 1000, scale=max(0.05, k), rot=-4)
    if t < 0.4:
        caption(c, ["wait..."], [0], t, 900, 150)
    else:
        caption(c, ["even", "the", "ERROR", "screen", "is", "cute"], [0.4 + i * 0.07 for i in range(6)], t, 300, 112,
                hl=(2,), hl_col=(255, 120, 200))
        e = emoji("😭", 180)
        if e:
            paste(c, shadowed(e, 10), 860, 1440, scale=base.ease_out_back((t - 0.9) / 0.2, 3), rot=-10)
        if t > 1.1:
            d = ImageDraw.Draw(c)
            d.text((W / 2, 1640), "(it never crashes btw)", font=ui.font("title", 64), fill=(255, 255, 255),
                   anchor="mm", stroke_width=6, stroke_fill=INK)


def outro(c, t):                      # bars 9-10 + tail
    cfg["theme"] = "pride_pastel"
    fr = BIGSTICK[int(t * 10) % len(BIGSTICK)]
    k = base.ease_out_back(t / 0.3, 2.4)
    pulse = kick_pulse(t, 0) if t < BAR * 2 else 1
    paste(c, fr, W / 2, 640, scale=max(0.05, k * 0.78) * pulse, rot=math.sin(t * 4) * 4)
    caption(c, ["Fluff", "VR", "Stats", ":3"], [0.1, 0.2, 0.3, BEAT], t, 1000, 150, hl=(3,), hl_col=(255, 120, 200))
    if t > BEAT * 2:
        stamp = word_img("COMING SOON", 120, (255, 226, 70))
        paste(c, shadowed(stamp, 12), W / 2, 1430, scale=base.ease_out_back((t - BEAT * 2) / 0.2, 3), rot=-7)
    if t > BAR:
        paste(c, word_img("follow so u don't miss it", 70, (255, 255, 255)), W / 2 - 40, 1590,
              scale=base.ease_out_back((t - BAR) / 0.2, 3), rot=-2)
        e = emoji("🐾", 110)
        if e:
            paste(c, shadowed(e, 8), 960, 1580, scale=base.ease_out_back((t - BAR) / 0.2, 3), rot=15)
    # heart burst on the final drop
    th = ui.get_theme(cfg)
    d = ImageDraw.Draw(c)
    for burst_t in (0.0, BAR * 2):
        kk = t - burst_t
        if 0 < kk < 1.6:
            rnd = random.Random(int(burst_t * 10) + 3)
            for i in range(26):
                ang = rnd.uniform(0, 6.28)
                spd = rnd.uniform(500, 1100)
                x = W / 2 + math.cos(ang) * spd * kk
                y = 640 + math.sin(ang) * spd * kk + 700 * kk * kk
                if i % 3:
                    ui.heart(d, x, y, 22, INK)
                    ui.heart(d, x, y, 18, th["primary"] if i % 2 else (255, 226, 70))
                else:
                    ui.sparkle(d, x, y, 22, (255, 255, 255))


SCENES = [  # (start, end, fn, bg palette, pattern)
    (0.0, BAR, hook, "pink", "checker"),
    (BAR, BAR * 2, wrist, "purple", "stripes"),
    (BAR * 2, BAR * 3, tail, "yellow", "dots"),
    (BAR * 3, BAR * 4, themes, None, "checker"),
    (BAR * 4, BAR * 5, ears, "lime", "stripes"),
    (BAR * 5, BAR * 6, music, "cyan", "dots"),
    (BAR * 6, BAR * 7, chatbox_s, "purple", "checker"),
    (BAR * 7, BAR * 8, ai_s, "pink", "stripes"),
    (BAR * 8, BAR * 9, error_s, "black", "dots"),
    (BAR * 9, TOTAL, outro, None, "pride"),
]


def rgb_split(img, amt):
    if amt < 1:
        return img
    r, g, b, a = img.split()
    r = ImageChops.offset(r, int(amt), 0)
    b = ImageChops.offset(b, -int(amt), 0)
    return Image.merge("RGBA", (r, g, b, a))


def frame(t):
    base.tick_stats(t)
    for a, b_, fn, pal, pat in SCENES:
        if a <= t < b_:
            tl = t - a
            if pal is None:
                pal = PAL_SEQ[min(3, beat_of(tl, 0))] if fn is themes else "pink"
            c = bg(t, pal, pat)
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            fn(layer, tl)
            # camera: punch-in on each section start + tiny shake
            punch = 1 + 0.08 * math.exp(-tl * 10)
            if punch > 1.003:
                lw, lh = int(W * punch), int(H * punch)
                layer = layer.resize((lw, lh), Image.BILINEAR).crop(((lw - W) // 2, (lh - H) // 2,
                                                                     (lw - W) // 2 + W, (lh - H) // 2 + H))
            c.alpha_composite(layer)
            # flash frame at every cut (not into the quiet gag)
            if tl < 0.07 and fn is not error_s:
                c = Image.blend(c, Image.new("RGBA", (W, H), (255, 255, 255, 255)), 0.75 * (1 - tl / 0.07))
            # chromatic split on the drops
            for drop in (BAR, BAR * 9):
                if 0 <= t - drop < 0.3:
                    c = rgb_split(c, 22 * (1 - (t - drop) / 0.3))
            break
    # film grain for that "real edit" texture
    g = GRAIN[int(t * FPS) % len(GRAIN)]
    c = Image.composite(c, Image.blend(c, Image.merge("RGBA", (g, g, g, Image.new("L", (W, H), 255))), 0.06),
                        Image.new("L", (W, H), 0))
    c = Image.blend(c, Image.merge("RGBA", (g, g, g, Image.new("L", (W, H), 255))), 0.035)
    # fade out at the very end
    if t > TOTAL - 0.4:
        c = Image.blend(c, Image.new("RGBA", (W, H), (0, 0, 0, 255)), (t - (TOTAL - 0.4)) / 0.4)
    return c.convert("RGB")


if __name__ == "__main__":
    out = sys.argv[1]
    music_wav = sys.argv[2] if len(sys.argv) > 2 else None
    n = int(TOTAL * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-"]
    if music_wav:
        cmd += ["-i", music_wav, "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = _time.time()
    for i in range(n):
        try:
            p.stdin.write(frame(i / FPS).tobytes())
        except BrokenPipeError:
            break
        if i % 150 == 0:
            print(f"  frame {i}/{n} ({_time.time() - t0:.0f}s)", flush=True)
    p.stdin.close()
    p.wait()
    print("done", out, p.returncode)
