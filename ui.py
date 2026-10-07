"""
Fluff VR Stats - UI rendering (pure Pillow, no VR needed).

Everything is drawn into RGBA images that main.py pushes to SteamVR.
Static decoration (cards, ears, paws, rainbow strips) is drawn 2x and cached,
so per-update work is just text + a tiny graph. That keeps CPU use tiny and
VRChat smooth.
"""
import math
import os
import random
import time
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")

# themes live in themes.py (presets, custom accent/background, ear styles)
from logo import sticker_frames, ERROR_ART, THANKS_ART
from themes import (mix, get_theme, theme_key, from_key, PRESETS, ACCENTS, BACKGROUNDS,
                    EAR_STYLES, preset_preview)


# ----------------------------------------------------------------- fonts ---
def _first_font(names):
    for n in names:
        for d in (FONT_DIR, r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu"):
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    return None


# Gochi Hand = hand-lettered marker look for titles/numbers; Nunito keeps small text readable
TITLE_FONT = _first_font(["GochiHand-Regular.ttf", "Fredoka-Bold.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"])
HEAD_FONT = _first_font(["GochiHand-Regular.ttf", "Fredoka-SemiBold.ttf", "seguisb.ttf", "DejaVuSans-Bold.ttf"])
BODY_FONT = _first_font(["Nunito-Bold.ttf", "segoeui.ttf", "DejaVuSans.ttf"])
BODY2_FONT = _first_font(["Nunito-SemiBold.ttf", "segoeui.ttf", "DejaVuSans.ttf"])


@lru_cache(maxsize=64)
def font(kind, size):
    path = {"title": TITLE_FONT, "head": HEAD_FONT,
            "body": BODY_FONT, "body2": BODY2_FONT}[kind]
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


# ---- mixed-font text (emoji + symbols like the chatbox preview needs)
SYMBOL_FONT = _first_font(["DejaVuSans.ttf", "seguisym.ttf"])
EMOJI_FONT = _first_font(["seguiemj.ttf"])
_EMOJI_BMP = set("✨⏰⏱⌚☕❤⭐⚡☀☁⛅❄🌡")


def _font_for(ch, size, kind="body"):
    o = ord(ch)
    if o in (0xFE0F, 0xFE0E, 0x200D):
        return None, False
    if o < 0x2000 or ch in "…–—‘’“”•€":
        return font(kind, size), False
    if (o >= 0x1F000 or ch in _EMOJI_BMP) and EMOJI_FONT:
        return _ttf(EMOJI_FONT, size), True
    return _ttf(SYMBOL_FONT, size) if SYMBOL_FONT else font(kind, size), False


@lru_cache(maxsize=32)
def _ttf(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _runs(text, size, kind):
    runs = []
    for ch in text:
        f, emo = _font_for(ch, size, kind)
        if f is None:
            continue
        if runs and runs[-1][1] is f:
            runs[-1][0] += ch
        else:
            runs.append([ch, f, emo])
    return runs


def rich_length(text, size, kind="body"):
    return sum(f.getlength(t) for t, f, _ in _runs(text, size, kind))


def rich_text(d, xy, text, size, fill, kind="body", center=False):
    x, y = xy
    runs = _runs(text, size, kind)
    if center:
        x -= sum(f.getlength(t) for t, f, _ in runs) / 2
    base = font(kind, size)
    asc = base.getmetrics()[0]
    for t_, f, emo in runs:
        dy = asc - f.getmetrics()[0] if not emo else 2
        try:
            d.text((x, y + dy), t_, font=f, fill=fill, embedded_color=emo)
        except Exception:
            d.text((x, y + dy), t_, font=f, fill=fill)
        x += f.getlength(t_)


def rich_wrap(text, size, width, kind="body"):
    out = []
    for para in text.split("\n"):
        line = ""
        for w in para.split(" "):
            test = (line + " " + w).strip()
            if rich_length(test, size, kind) <= width or not line:
                line = test
            else:
                out.append(line)
                line = w
        out.append(line)
    return out


def wrap(text, fnt, width):
    lines = []
    for para in text.split("\n"):
        words, line = para.split(" "), ""
        for w in words:
            test = (line + " " + w).strip()
            if fnt.getlength(test) <= width:
                line = test
            else:
                if line:
                    lines.append(line)
                while fnt.getlength(w) > width and len(w) > 1:  # hard-break long words
                    cut = len(w)
                    while cut > 1 and fnt.getlength(w[:cut]) > width:
                        cut -= 1
                    lines.append(w[:cut])
                    w = w[cut:]
                line = w
        lines.append(line)
    return lines


def ellipsize(text, fnt, width):
    if fnt.getlength(text) <= width:
        return text
    while text and fnt.getlength(text + "…") > width:
        text = text[:-1]
    return text + "…"


# ------------------------------------------------------- cute primitives ---
def paw(d, cx, cy, r, fill):
    """Paw print: pad + 4 toe beans."""
    d.ellipse([cx - r, cy - r * 0.6, cx + r, cy + r * 0.9], fill=fill)
    for dx, dy, s in ((-0.95, -0.95, 0.38), (-0.35, -1.45, 0.4),
                      (0.35, -1.45, 0.4), (0.95, -0.95, 0.38)):
        tx, ty, tr = cx + dx * r, cy + dy * r, s * r
        d.ellipse([tx - tr, ty - tr * 1.1, tx + tr, ty + tr * 1.1], fill=fill)


def heart(d, cx, cy, r, fill):
    d.ellipse([cx - r, cy - r * 0.8, cx, cy + r * 0.2], fill=fill)
    d.ellipse([cx, cy - r * 0.8, cx + r, cy + r * 0.2], fill=fill)
    d.polygon([(cx - r * 0.97, cy - 0.1 * r), (cx + r * 0.97, cy - 0.1 * r),
               (cx, cy + r * 1.05)], fill=fill)


def sparkle(d, cx, cy, r, fill):
    d.polygon([(cx, cy - r), (cx + r * 0.25, cy - r * 0.25), (cx + r, cy),
               (cx + r * 0.25, cy + r * 0.25), (cx, cy + r),
               (cx - r * 0.25, cy + r * 0.25), (cx - r, cy),
               (cx - r * 0.25, cy - r * 0.25)], fill=fill)


def stripe(d, x, y, w, h, colors, radius=0):
    n = len(colors)
    seg = w / n
    for i, c in enumerate(colors):
        d.rectangle([x + i * seg, y, x + (i + 1) * seg + 1, y + h], fill=c)


# how tall each ear style is relative to its width (so the overall height stays fixed)
EAR_HEIGHT = {"cat": 1.1, "fox": 1.55, "wolf": 1.45, "bunny": 2.1, "bear": 0.95,
              "dragon": 1.6, "none": 1.0}


def ears(d, x0, x1, top, margin, t, outer="theme", inner="theme"):
    """Two ears on a card's top edge. `margin` = space reserved above the card.
    outer/inner override the colors (None = don't draw that part)."""
    style = t.get("ears", "cat")
    if style == "none":
        return
    size = margin / EAR_HEIGHT[style]
    if outer == "theme":
        outer = t["bg"][:3] + (255,)
    if inner == "theme":
        inner = t["inner_ear"]
    _poly, _ell = d.polygon, d.ellipse

    class _D:   # skip drawing parts whose color is None
        @staticmethod
        def polygon(pts, fill):
            if fill is not None:
                _poly(pts, fill=fill)

        @staticmethod
        def ellipse(box, fill):
            if fill is not None:
                _ell(box, fill=fill)
    d = _D
    for side, cx in ((-1, x0 + size * 1.6), (1, x1 - size * 1.6)):
        if style == "cat":
            d.polygon([(cx - size, top + size * 0.35), (cx + size, top + size * 0.35),
                       (cx + side * size * 0.15, top - size * 1.05)], fill=outer)
            d.polygon([(cx - size * 0.55, top + size * 0.2), (cx + size * 0.6, top + size * 0.2),
                       (cx + side * size * 0.12, top - size * 0.6)], fill=inner)
        elif style in ("fox", "wolf"):
            tip = side * size * (0.05 if style == "fox" else 0.35)
            h = size * (1.5 if style == "fox" else 1.4)
            d.polygon([(cx - size * 0.95, top + size * 0.35), (cx + size * 0.95, top + size * 0.35),
                       (cx + tip, top - h)], fill=outer)
            d.polygon([(cx - size * 0.5, top + size * 0.2), (cx + size * 0.5, top + size * 0.2),
                       (cx + tip * 0.8, top - h * 0.62)], fill=inner)
            if style == "fox" and inner is not None:   # fluffy white tuft
                d.polygon([(cx - size * 0.35, top + size * 0.2), (cx + size * 0.35, top + size * 0.2),
                           (cx, top - h * 0.18)], fill=(255, 255, 255, 230) if not isinstance(inner, int) else inner)
        elif style == "bunny":
            w, h = size * 0.62, size * 2.05
            ox = cx - side * size * 0.3
            d.ellipse([ox - w, top - h, ox + w, top + size * 0.6], fill=outer)
            d.ellipse([ox - w * 0.5, top - h * 0.85, ox + w * 0.5, top + size * 0.1], fill=inner)
        elif style == "bear":
            r = size * 0.9
            d.ellipse([cx - r, top - r * 0.95, cx + r, top + r * 1.05], fill=outer)
            d.ellipse([cx - r * 0.5, top - r * 0.45, cx + r * 0.5, top + r * 0.55], fill=inner)
        elif style == "dragon":   # curved horns sweeping outward
            pts = [(cx - side * size * 0.55, top + size * 0.3), (cx + side * size * 0.45, top + size * 0.3)]
            for k in range(1, 9):
                f = k / 8
                pts.append((cx + side * (size * 0.45 + size * 0.9 * f * f),
                            top + size * 0.3 - size * 1.6 * f))
            for k in range(8, 0, -1):
                f = k / 8
                pts.append((cx + side * (-size * 0.55 + size * 1.5 * f * f) + side * size * 0.1 * f,
                            top + size * 0.3 - size * 1.6 * f + size * 0.25 * f * (1 - f)))
            d.polygon(pts, fill=inner)


def card(d, box, t, radius, ear=0, strip=True, fill=None):
    x0, y0, x1, y1 = box
    if ear:
        ears(d, x0, x1, y0, ear, t)
    d.rounded_rectangle(box, radius=radius, fill=fill or t["bg"])
    if strip and t.get("show_stripe", True):
        # pride stripe hugging the top edge, inside the rounded corners
        sh = max(4, radius // 3)
        m = Image.new("L", (int(x1 - x0), int(y1 - y0)), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, x1 - x0 - 1, y1 - y0 - 1], radius=radius, fill=255)
        s = Image.new("RGBA", m.size, (0, 0, 0, 0))
        stripe(ImageDraw.Draw(s), 0, 0, m.size[0], sh, t["stripe"])
        s.putalpha(Image.composite(s.getchannel("A"), Image.new("L", m.size, 0), m))
        d._image.alpha_composite(s, (int(x0), int(y0)))


def text_c(d, xy, txt, fnt, fill, anchor="la"):
    d.text(xy, txt, font=fnt, fill=fill, anchor=anchor)


_CUR = {}   # theme currently being drawn (for the soft lineart on inner panels)


def pill(d, box, fill, outline=None, width=2):
    r = (box[3] - box[1]) / 2
    if outline is None and _CUR:
        outline = _CUR["line_soft"]
    elif outline is False:
        outline = None
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def panel(d, box, radius, t, fill=None):
    """Inner panel with a soft hand-inked outline."""
    d.rounded_rectangle(box, radius=radius, fill=fill or t["panel"], outline=t["line_soft"], width=2)


def switch(d, x, y, on, t, scale=1.0):
    w, h = 54 * scale, 30 * scale
    pill(d, [x, y, x + w, y + h], t["primary"] if on else t["panel2"])
    k = h - 8 * scale
    kx = x + w - k - 4 * scale if on else x + 4 * scale
    d.ellipse([kx, y + 4 * scale, kx + k, y + 4 * scale + k], fill=(255, 255, 255))
    if on:
        heart(d, kx + k / 2, y + 4 * scale + k / 2 + 1, k * 0.28, t["primary"])


def color_for_fps(fps, refresh, t):
    if not refresh or fps is None:
        return t["text"]
    r = fps / refresh
    return t["good"] if r >= 0.9 else t["warn"] if r >= 0.6 else t["bad"]


def graph(d, box, values, target, t):
    x0, y0, x1, y1 = box
    panel(d, box, 10, t)
    if not values:
        return
    top = max(max(values), target * 1.6, 1)
    ty = y1 - (target / top) * (y1 - y0 - 8) - 4
    for xx in range(int(x0 + 8), int(x1 - 8), 10):
        d.line([(xx, ty), (xx + 5, ty)], fill=mix(t["panel"], t["sub"], 0.55), width=1)
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        px = x0 + 6 + (x1 - x0 - 12) * i / max(1, n - 1)
        py = y1 - 4 - (min(v, top) / top) * (y1 - y0 - 8)
        pts.append((px, py))
    poly = pts + [(pts[-1][0], y1 - 4), (pts[0][0], y1 - 4)]
    d.polygon(poly, fill=mix(t["panel"], t["primary"], 0.3))
    d.line(pts, fill=t["primary"], width=2, joint="curve")


# ------------------------------------------------------- furry frame art ---
SS = 2  # supersample factor for static art


def _fur_fringe(d, rnd, x0, y0, x1, y1, side, n, fill):
    """Spiky fur tufts poking out of one edge (like doodled fluff)."""
    for _ in range(n):
        if side in ("left", "right"):
            cy = rnd.uniform(y0, y1)
            spikes = rnd.randint(2, 3)
            for k in range(spikes):
                yy = cy + (k - spikes / 2) * 12 * SS
                ln = rnd.uniform(7, 13) * SS
                bw = rnd.uniform(7, 10) * SS
                ex = x0 if side == "left" else x1
                sgn = -1 if side == "left" else 1
                tilt = rnd.uniform(2, 6) * SS
                d.polygon([(ex - sgn * 4 * SS, yy - bw), (ex - sgn * 4 * SS, yy + bw),
                           (ex + sgn * ln, yy + bw * 0.2 + tilt)], fill=fill)
        else:   # bottom
            cx = rnd.uniform(x0, x1)
            spikes = rnd.randint(2, 4)
            for k in range(spikes):
                xx = cx + (k - spikes / 2) * 13 * SS
                ln = rnd.uniform(6, 12) * SS
                bw = rnd.uniform(7, 10) * SS
                tilt = rnd.uniform(-5, 5) * SS
                d.polygon([(xx - bw, y1 - 4 * SS), (xx + bw, y1 - 4 * SS),
                           (xx + tilt, y1 + ln)], fill=fill)


def _tail_shape(rnd, base, ctrl, top):
    """Centerline blobs + fur spikes for a fluffy tail (gif-style spiky floof)."""
    (bx, by), (cx, cy), (tx, ty) = base, ctrl, top
    blobs, spikes = [], []
    n = 30
    for i in range(n + 1):
        u = i / n
        x = (1 - u) ** 2 * bx + 2 * (1 - u) * u * cx + u * u * tx
        y = (1 - u) ** 2 * by + 2 * (1 - u) * u * cy + u * u * ty
        r = (16 + 22 * math.sin(math.pi * min(1.0, 0.2 + u * 0.8))) * SS
        blobs.append((x, y, r, u))
    # fur spikes on the outer side + a spiky tip
    for i in range(6, n, 4):
        x, y, r, u = blobs[i]
        x2, y2 = blobs[min(n, i + 1)][:2]
        dx, dy = x2 - x, y2 - y
        ln = math.hypot(dx, dy) or 1
        nx, ny = dy / ln, -dx / ln               # outward normal (right side of travel)
        if nx < 0:
            nx, ny = -nx, -ny
        L = r + rnd.uniform(6, 11) * SS
        spikes.append(([(x + ny * r * 0.5, y - nx * r * 0.5), (x - ny * r * 0.5, y + nx * r * 0.5),
                        (x + nx * L, y + ny * L)], u))
    x, y, r, u = blobs[-2]
    for k in range(5):
        ang = -math.pi / 2 + (k - 2) * 0.42 + rnd.uniform(-0.08, 0.08)
        L = r + rnd.uniform(9, 15) * SS
        spikes.append(([(x + math.cos(ang - 0.4) * r * 0.6, y + math.sin(ang - 0.4) * r * 0.6),
                        (x + math.cos(ang + 0.4) * r * 0.6, y + math.sin(ang + 0.4) * r * 0.6),
                        (x + math.cos(ang) * L, y + math.sin(ang) * L)], 1.0))
    return blobs, spikes


def _draw_tail(d, blobs, spikes, fill, tip=None, tip_from=0.72):
    for x, y, r, u in blobs:
        c = tip if (tip and u >= tip_from) else fill
        if c is not None:
            d.ellipse([x - r, y - r, x + r, y + r], fill=c)
    for pts, u in spikes:
        c = tip if (tip and u >= tip_from) else fill
        if c is not None:
            d.polygon(pts, fill=c)


@lru_cache(maxsize=24)
def furry_frame(key, W, H, box, radius, ear_margin, tail=False, fluff=True):
    """Hand-drawn furry panel: ink outline, fluffy tufts, ears, optional tail. Cached."""
    t = from_key(key)
    rnd = random.Random(W * 7919 + H * 31 + (1 if tail else 0))
    x0, y0, x1, y1 = box
    BW, BH = W * SS, H * SS
    X0, Y0, X1, Y1 = x0 * SS, y0 * SS, x1 * SS, y1 * SS

    # 1) silhouette (everything that gets the ink outline)
    m = Image.new("L", (BW, BH), 0)
    md = ImageDraw.Draw(m)
    tail_shape = None
    if tail:
        tl = min(190, (y1 - y0) - 10)
        tail_shape = _tail_shape(rnd, (X1 - 50 * SS, Y1 - 24 * SS), (BW - 26 * SS, Y1 + 2 * SS),
                                 (BW - 50 * SS, Y1 - tl * SS))
        _draw_tail(md, *tail_shape, 255)
    md.rounded_rectangle([X0, Y0, X1, Y1], radius=radius * SS, fill=255)
    ears(md, X0, X1, Y0, ear_margin * SS, t, outer=255, inner=255)
    if fluff:
        _fur_fringe(md, rnd, X0, Y0 + radius * SS, X1, Y1 - radius * SS, "left", 2, 255)
        _fur_fringe(md, rnd, X0, Y0 + radius * SS, X1, Y1 - radius * SS, "right", 2, 255)
        _fur_fringe(md, rnd, X0 + radius * SS, Y0, X1 - radius * SS, Y1, "bottom", 3, 255)
    mask = m.resize((W, H), Image.LANCZOS)

    # 2) ink outline = dilated silhouette
    ink = mask.filter(ImageFilter.MaxFilter(7))
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    img.paste(Image.new("RGBA", (W, H), t["line"] + (255,)), (0, 0), ink)
    bgc = t["bg"][:3] + (255,)
    img.paste(Image.new("RGBA", (W, H), bgc), (0, 0), mask)

    # 3) details drawn big then shrunk: inner ears, ear fluff, tail tip, fur strokes
    det = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    dd = ImageDraw.Draw(det)
    ears(dd, X0, X1, Y0, ear_margin * SS, t, outer=None)
    if tail_shape:
        # dyed tail tip in the accent color + a few fur strokes along the floof
        _draw_tail(dd, *tail_shape, None, tip=t["primary"])
        blobs = tail_shape[0]
        for x, y, r, u in blobs[8:20:6]:
            dd.arc([x - r * 0.55, y - r * 0.55, x + r * 0.55, y + r * 0.55], 190, 280,
                   fill=t["line_soft"], width=2 * SS)
    # little fur strokes near the bottom corners, like doodled chest fluff
    for fx in (X0 + radius * SS * 0.8, X1 - radius * SS * 0.8):
        for k in range(2):
            yy = Y1 - (16 + k * 9) * SS
            dd.arc([fx - 8 * SS, yy - 6 * SS, fx + 8 * SS, yy + 6 * SS], 20 + k * 15, 150,
                   fill=t["line_soft"] + (170,), width=2 * SS)
    det = det.resize((W, H), Image.LANCZOS)
    # keep details inside the silhouette
    det.putalpha(ImageChops_multiply(det.getchannel("A"), mask))
    img.alpha_composite(det)

    # 4) pride stripe hugging the card top, like a collar band (with stitch dots)
    if t.get("show_stripe", True):
        sh = max(5, radius // 3)
        cm = Image.new("L", (W, H), 0)
        ImageDraw.Draw(cm).rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=255)
        sl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sl)
        stripe(sd, x0, y0, x1 - x0, sh, t["stripe"])
        for xx in range(int(x0 + radius), int(x1 - radius), 14):
            sd.line([(xx, y0 + sh + 3), (xx + 6, y0 + sh + 3)], fill=t["line_soft"], width=1)
        sl.putalpha(ImageChops_multiply(sl.getchannel("A"), cm))
        img.alpha_composite(sl)
    return img


def ImageChops_multiply(a, b):
    from PIL import ImageChops
    return ImageChops.multiply(a, b)


def doodle_heart(d, cx, cy, r, fill, line):
    heart(d, cx, cy, r + 2, line)
    heart(d, cx, cy, r, fill)


def doodle_star(d, cx, cy, r, fill, line):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.48
        pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
    d.polygon(pts, fill=fill, outline=line, width=2)


@lru_cache(maxsize=16)
def hud_bg(key, w, h):
    t = from_key(key)
    img = furry_frame(key, w, h, (14, HUD_EAR, HUD_W - 14, h - 18), 26, HUD_EAR, tail=True).copy()
    d = ImageDraw.Draw(img)
    d.text((HUD_W - 40, h - 30), ":3", font=font("title", 22), fill=t["sub"], anchor="rs")
    return img


@lru_cache(maxsize=8)
def dash_bg(key, w, h):
    t = from_key(key)
    img = furry_frame(key, w, h, (16, 36, w - 16, h - 18), 36, 36).copy()
    d = ImageDraw.Draw(img)
    # tiny doodles in the bottom corners
    doodle_star(d, w - 60, h - 30, 8, t["warn"], t["line"])
    d.text((44, h - 22), "mrrp~", font=font("title", 18), fill=t["sub"], anchor="ls")
    return img


# ==================================================================== HUD ===
HUD_W = 512      # card width; the image is a bit wider so the tail fits
HUD_IMG_W = 600
HUD_EAR = 40     # space above the HUD card reserved for ears


def note_icon(d, cx, cy, r, fill):
    """Little music note."""
    d.ellipse([cx - r, cy, cx + r * 0.2, cy + r], fill=fill)
    d.rectangle([cx + r * 0.05, cy - r * 1.6, cx + r * 0.3, cy + r * 0.5], fill=fill)
    d.polygon([(cx + r * 0.05, cy - r * 1.6), (cx + r * 1.1, cy - r * 1.1),
               (cx + r * 1.1, cy - r * 0.6), (cx + r * 0.3, cy - r * 1.05)], fill=fill)


def fmt_dur(sec):
    sec = int(sec)
    h, m = sec // 3600, (sec % 3600) // 60
    return f"{h}h {m:02d}m" if h else f"{m}m"


def hud_chips(state):
    """Small info chips for the 'extras' row(s): (label, value, color-key)."""
    m, s, x = state.cfg["modules"], state.stats, state.extras
    out = []
    if m.get("session_timer"):
        out.append(("in VR", fmt_dur(time.time() - x.get("session_start", time.time())), None))
    if m.get("ping"):
        p = x.get("ping")
        out.append(("ping", "--" if p is None else f"{p:.0f}ms",
                    None if p is None else "good" if p < 60 else "warn" if p < 150 else "bad"))
    if m.get("gpu_temp") and s.get("gpu_temp") is not None:
        tmp = s["gpu_temp"]
        val = f"{tmp:.0f}°C"
        if s.get("vram_used") is not None:
            val += f" · {s['vram_used']:.1f}GB"
        out.append(("GPU", val, "good" if tmp < 75 else "warn" if tmp < 85 else "bad"))
    if m.get("weather") and x.get("weather"):
        out.append(("", x["weather"], None))
    if m.get("headpat_counter"):
        out.append(("headpats", str(x.get("headpats", 0)), None))
    if m.get("boop_counter"):
        out.append(("boops", str(x.get("boops", 0)), None))
    if m.get("jump_counter"):
        out.append(("jumps", str(x.get("jumps", 0)), None))
    if m.get("yap_meter") and x.get("talk_s"):
        out.append(("yapped", fmt_dur(x["talk_s"]), None))
    if m.get("avatar_height") and x.get("height_m"):
        out.append(("height", f"{x['height_m']:.2f}m", None))
    if m.get("vr_streak") and x.get("vr_today_s"):
        out.append(("today", fmt_dur(x["vr_today_s"]), None))
        if x.get("vr_streak", 0) > 1:
            out.append(("streak", f"{x['vr_streak']} days", "good"))
    if m.get("countdown"):
        import chatbox as _cb
        c = _cb.countdown_text(state.cfg.get("countdown", {}))
        if c:
            out.append(("", ellipsize(c, font("body", 16), 210), None))
    if m.get("mute_indicator") and x.get("muted") is not None:
        out.append(("mic", "muted" if x["muted"] else "live", "bad" if x["muted"] else "good"))
    if m.get("world_info") and x.get("world_name"):
        out.append(("", ellipsize(x["world_name"], font("body", 16), 210), None))
        out.append(("ppl", str(x.get("world_players", 0)), None))
    if m.get("distance"):
        wk = state.walked
        out.append(("walked", f"{wk / 1000:.2f}km" if wk >= 1000 else f"{wk:.0f}m", None))
        if getattr(state, "speed", 0) > 1.3:
            out.append(("", "ZOOMIES!!", "warn"))
    if m.get("afk_detect") and state.afk:
        out.append(("", "afk " + fmt_dur(time.time() - (state.afk_since or time.time())), "warn"))
    return out


def layout_chips(chips, width, f_lab, f_val, gap=8):
    rows, row, used = [], [], 0
    for c in chips:
        w = (f_lab.getlength(c[0]) + 8 if c[0] else 0) + f_val.getlength(c[1]) + 28
        if row and used + gap + w > width:
            rows.append(row)
            row, used = [], 0
        row.append((c, w))
        used += w + (gap if row else 0)
    if row:
        rows.append(row)
    return rows


def render_hud(state):
    """Wrist HUD. Returns an RGBA image."""
    cfg, s, t = state.cfg, state.stats, get_theme(state.cfg)
    mods = cfg["modules"]
    state.hud_hits = []
    x, R = 34, HUD_W - 34
    global _CUR
    _CUR = t
    f_lab, f_val = font("body2", 15), font("body", 16)

    # figure out height from enabled rows so nothing is empty
    rows = []
    if state.alert and time.time() < state.alert["until"]:
        rows.append(("alert", 84 if state.alert.get("kind") == "error" else 66))
    if mods.get("wrist_pet"):
        rows.append(("pet", 74))
    if mods["fps"] or mods["clock"]:
        rows.append(("top", 92))
    tm = state.timer
    if mods.get("timer") and (tm["running"] or (tm.get("done_at") and time.time() - tm["done_at"] < 8)):
        rows.append(("timer", 46))
    if mods["gpu_cpu_ms"] or mods["reprojection"]:
        rows.append(("ms", 44))
    if mods["frametime_graph"]:
        rows.append(("graph", 66))
    if mods["batteries"] and s.get("batteries"):
        rows.append(("bat", 42))
    if mods["pc_usage"]:
        rows.append(("pc", 42))
    chip_rows = layout_chips(hud_chips(state), R - x, f_lab, f_val)
    for cr in chip_rows:
        rows.append(("chips", 42, cr))
    m = state.music or {}
    song = (f"{m['title']} - {m['artist']}" if m.get("artist") else m.get("title")) if m.get("title") \
        else state.extras.get("song")
    want_ctrl = mods.get("music_controls") or mods.get("zoom_lens")
    if (mods.get("now_playing") and song) or want_ctrl:
        rows.append(("music", 52 if want_ctrl else 44))
    if mods["last_ai_reply"] and state.last_reply():
        rows.append(("ai", 74))
    if not rows:
        rows.append(("empty", 60))
    h = HUD_EAR + 26 + sum(r[1] for r in rows) + 30

    img = hud_bg(theme_key(cfg), HUD_IMG_W, h).copy()
    state.hud_size = (HUD_IMG_W, h)
    d = ImageDraw.Draw(img)
    y = HUD_EAR + 26

    for row in rows:
        kind, rh = row[0], row[1]
        if kind == "alert":
            al = state.alert
            col = t["bad"] if al.get("kind") in ("warn", "error") else t["primary"]
            bh = rh - 10
            d.rounded_rectangle([x, y, R, y + bh], radius=20, fill=col)
            ink = (40, 24, 40) if sum(col[:3]) > 560 else (255, 255, 255)
            text_x = x + 54
            if al.get("kind") == "error":
                fr, _ = sticker_frames(bh - 6, ERROR_ART)
                if fr:
                    img.alpha_composite(fr[0], (int(x + 4), int(y + 3)))
                    text_x = x + 14 + fr[0].width
            elif al.get("kind") == "warn":
                sparkle(d, x + 28, y + 28, 13, ink)
            else:
                heart(d, x + 28, y + 30, 12, ink)
            f = font("head", 19)
            lines = wrap(al["text"], f, R - text_x - 14)[:2]
            ty = y + bh / 2 - (len(lines) - 1) * 11
            for i, ln in enumerate(lines):
                d.text((text_x, ty + i * 22), ln, font=f, fill=ink, anchor="lm")
        elif kind == "pet":
            frames, _ = sticker_frames(64)
            if frames:
                img.alpha_composite(frames[int(time.time() * 2) % len(frames)], (int(x), int(y)))
            bx = x + 78
            f = font("head", 20)
            txt = ellipsize(state.pet_mood, f, R - bx - 36)
            bw = f.getlength(txt) + 36
            d.rounded_rectangle([bx, y + 12, bx + bw, y + 56], radius=18, fill=t["panel2"], outline=t["line_soft"], width=2)
            d.polygon([(bx + 2, y + 30), (bx - 12, y + 36), (bx + 2, y + 42)], fill=t["panel2"])
            d.text((bx + 18, y + 34), txt, font=f, fill=t["text"], anchor="lm")
        elif kind == "timer":
            now = time.time()
            if tm["mode"] == "timer":
                left = max(0.0, tm["end"] - now) if tm["running"] else 0.0
                lab, val = ("timer", f"{int(left // 60)}:{int(left % 60):02d}") if tm["running"] else ("", "DING!! timer done")
                total = max(1.0, tm["end"] - (tm["end"] - left) + left) if tm["running"] else 1
            else:
                el = tm["elapsed"] + (now - tm["start"])
                lab, val = "stopwatch", f"{int(el // 60)}:{int(el % 60):02d}"
            pill(d, [x, y, R, y + 36], t["primary"] if not tm["running"] else t["panel"])
            col = t["on_primary"] if not tm["running"] else t["text"]
            if lab:
                d.text((x + 16, y + 18), lab, font=font("body2", 16), fill=t["sub"] if tm["running"] else col, anchor="lm")
            d.text((R - 16 if lab else (x + R) / 2, y + 18), val, font=font("title", 26), fill=col,
                   anchor="rm" if lab else "mm")
        elif kind == "top":
            if mods["fps"]:
                fps = s.get("fps")
                txt = f"{fps:.0f}" if fps is not None else "--"
                col = color_for_fps(fps, s.get("refresh"), t)
                d.text((x, y + 78), txt, font=font("title", 76), fill=col, anchor="ls")
                fw = font("title", 76).getlength(txt)
                d.text((x + fw + 8, y + 50), "fps", font=font("head", 24), fill=t["sub"], anchor="ls")
                ref = s.get("refresh")
                if ref:
                    d.text((x + fw + 8, y + 76), f"of {ref:.0f}Hz", font=font("body2", 18),
                           fill=t["sub"], anchor="ls")
            if mods["clock"]:
                now = time.localtime()
                hh = time.strftime("%I:%M", now).lstrip("0")
                d.text((R, y + 52), hh, font=font("title", 44), fill=t["text"], anchor="rs")
                d.text((R, y + 78), time.strftime("%p · %a", now), font=font("body2", 18),
                       fill=t["sub"], anchor="rs")
        elif kind == "ms":
            chips = []
            if mods["gpu_cpu_ms"]:
                chips += [("GPU", s.get("gpu_ms"), "ms"), ("CPU", s.get("cpu_ms"), "ms")]
            if mods["reprojection"]:
                chips.append(("Reproj", s.get("reproj_pct"), "%"))
            cw = (R - x - 10 * (len(chips) - 1)) / len(chips)
            for i, (lab, val, unit) in enumerate(chips):
                cx = x + i * (cw + 10)
                pill(d, [cx, y, cx + cw, y + 34], t["panel"])
                v = "--" if val is None else (f"{val:.1f}" if unit == "ms" else f"{val:.0f}")
                d.text((cx + 14, y + 17), lab, font=font("body2", 17), fill=t["sub"], anchor="lm")
                col = t["text"]
                if unit == "%" and val is not None:
                    col = t["good"] if val < 5 else t["warn"] if val < 25 else t["bad"]
                d.text((cx + cw - 14, y + 17), v + unit, font=font("body", 17), fill=col, anchor="rm")
        elif kind == "graph":
            target = 1000.0 / s["refresh"] if s.get("refresh") else 11.1
            graph(d, [x, y, R, y + 56], s.get("frametimes", []), target, t)
            d.text((x + 10, y + 6), "frametime", font=font("body2", 13), fill=t["sub"], anchor="lt")
        elif kind == "bat":
            bats = s["batteries"][:4]
            cw = (R - x - 8 * (len(bats) - 1)) / len(bats)
            for i, (lab, pct, chg) in enumerate(bats):
                cx = x + i * (cw + 8)
                pill(d, [cx, y, cx + cw, y + 32], t["panel"])
                col = t["good"] if pct >= 40 else t["warn"] if pct >= 20 else t["bad"]
                # mini battery bar
                bx = cx + 9
                d.rounded_rectangle([bx, y + 11, bx + 16, y + 21], radius=3, outline=t["sub"], width=2)
                d.rectangle([bx + 3, y + 14, bx + 3 + 10 * pct / 100, y + 18], fill=col)
                d.text((bx + 22, y + 16), lab, font=font("body2", 14), fill=t["sub"], anchor="lm")
                d.text((cx + cw - 9, y + 16), f"{pct:.0f}%" + ("+" if chg else ""),
                       font=font("body", 14), fill=col, anchor="rm")
        elif kind == "pc":
            items = [("CPU", s.get("cpu_pct")), ("RAM", s.get("ram_pct"))]
            if s.get("gpu_pct") is not None:
                items.append(("GPU", s.get("gpu_pct")))
            cw = (R - x - 10 * (len(items) - 1)) / len(items)
            for i, (lab, val) in enumerate(items):
                cx = x + i * (cw + 10)
                pill(d, [cx, y, cx + cw, y + 32], t["panel"])
                if val is not None:
                    fillw = (cw - 4) * min(val, 100) / 100
                    if fillw > 30:
                        pill(d, [cx + 2, y + 2, cx + 2 + fillw, y + 30], mix(t["panel"], t["primary"], 0.28), outline=False)
                d.text((cx + 14, y + 16), lab, font=font("body2", 16), fill=t["text"], anchor="lm")
                d.text((cx + cw - 14, y + 16), "--" if val is None else f"{val:.0f}%",
                       font=font("body", 16), fill=t["text"], anchor="rm")
        elif kind == "chips":
            cx = x
            for (lab, val, ck), w in row[2]:
                pill(d, [cx, y, cx + w, y + 32], t["panel"])
                tx = cx + 14
                if lab:
                    d.text((tx, y + 16), lab, font=f_lab, fill=t["sub"], anchor="lm")
                    tx += f_lab.getlength(lab) + 8
                d.text((tx, y + 16), val, font=f_val, fill=t[ck] if ck else t["text"], anchor="lm")
                cx += w + 8
        elif kind == "music":
            bh = rh - 10
            pill(d, [x, y, R, y + bh], t["panel"])
            note_icon(d, x + 20, y + bh / 2 - 4, 7, t["primary"])
            right = R - 14
            if want_ctrl:
                # tap targets for the other hand's controller (see main.check_touch)
                br = bh / 2 - 3
                pressed = state.hud_pressed if time.time() - state.hud_pressed_t < 0.35 else None
                btns = []
                if mods.get("music_controls"):
                    btns += [("next", "next"), ("pause" if m.get("playing") else "play", "play_pause"), ("prev", "prev")]
                if mods.get("zoom_lens"):
                    btns.append(("zoom", "zoom"))
                zoom_on = state.cfg.get("zoom", {}).get("enabled")
                for i, (kind2, cmd) in enumerate(btns):
                    cx = R - 6 - br - i * (br * 2 + 8)
                    cyy = y + bh / 2
                    fillc = t["primary"] if (cmd == "play_pause" or pressed == cmd
                                             or (cmd == "zoom" and zoom_on)) else t["panel2"]
                    d.ellipse([cx - br, cyy - br, cx + br, cyy + br], fill=fillc, outline=t["line_soft"], width=2)
                    media_icon(d, kind2, cx, cyy, br * 0.62,
                               t["on_primary"] if fillc == t["primary"] else t["text"])
                    state.hud_hits.append(([cx - br - 4, cyy - br - 4, cx + br + 4, cyy + br + 4], cmd))
                right = R - 6 - len(btns) * (br * 2 + 8)
            label = song or "nothing playing"
            d.text((x + 42, y + bh / 2), ellipsize(label, font("body", 16), right - x - 48),
                   font=font("body", 16), fill=t["text"] if song else t["sub"], anchor="lm")
            if m.get("dur") and m.get("title"):     # tiny progress line along the bottom
                k = min(1.0, max(0.0, (m.get("pos") or 0) / m["dur"]))
                d.line([(x + 42, y + bh - 6), (x + 42 + (right - x - 54) * k, y + bh - 6)],
                       fill=t["primary"], width=3)
        elif kind == "ai":
            panel(d, [x, y, R, y + 64], 16, t)
            paw(d, x + 22, y + 34, 9, t["primary"])
            f = font("body", 16)
            lines = wrap(state.last_reply(), f, R - x - 56)
            if len(lines) > 2:
                lines = lines[:2]
                lines[1] = ellipsize(lines[1] + " …", f, R - x - 56)
            for i, ln in enumerate(lines):
                d.text((x + 42, y + 12 + i * 22), ln, font=f, fill=t["text"])
        elif kind == "empty":
            d.text((HUD_W / 2, y + 26), "all mods off ~ open the dashboard!",
                   font=font("body", 18), fill=t["sub"], anchor="mm")
        y += rh
    return img


# ============================================================= DASHBOARD ===
DASH_W, DASH_H = 1024, 640
LOGO_H, LOGO_POS = 92, (32, 50)


def add_logo(base, frame_idx, slots=()):
    """Paste the animated bits (logo + any stickers/hearts listed in `slots`) onto a
    dashboard that was rendered without them. Cheap enough to run at ~10 fps."""
    img = base.copy()
    for slot in [("sticker", LOGO_H, LOGO_POS, None, False)] + list(slots):
        try:
            kind = slot[0]
            if kind == "sticker":
                _, hgt, pos, path, bob = slot
                frames, _ = sticker_frames(hgt) if path is None else sticker_frames(hgt, path)
                if frames:
                    y = pos[1] + (round(math.sin(frame_idx * 0.35) * 6) if bob else 0)
                    img.alpha_composite(frames[frame_idx % len(frames)], (pos[0], y))
            elif kind == "hearts":       # little hearts floating up after a floof pat
                _, start, (hx, hy), t = slot
                k = time.time() - start
                if 0 <= k < 1.4:
                    d = ImageDraw.Draw(img)
                    for i in range(7):
                        a = (1 - k / 1.4)
                        px = hx + math.sin(i * 1.7 + k * 4) * 26 + (i - 3) * 22
                        py = hy - k * (90 + i * 18)
                        c = mix(t["panel"], t["primary"], a)
                        doodle_heart(d, px, py, 7 + (i % 3) * 2, c, mix(t["panel"], t["line"], a))
        except Exception:
            pass
    return img
TABS = ["Stats", "Boost", "Chat", "Music", "Chatbox", "Avatar", "World", "Screen", "Mods", "Style", "Wrist", "<3"]

MOD_CATS = ["Performance", "Wrist", "VRChat", "Counters", "Fun", "Comfy"]
MOD_INFO = {
    "Performance": [
        ("fps", "FPS counter", "Big VRChat FPS number"),
        ("frametime_graph", "Frametime graph", "GPU frametime history"),
        ("gpu_cpu_ms", "GPU / CPU ms", "Frame cost per side"),
        ("reprojection", "Reprojection %", "How often SteamVR fakes frames"),
        ("pc_usage", "PC usage", "CPU, RAM and GPU load"),
        ("gpu_temp", "GPU temp + VRAM", "Heat + video memory (NVIDIA)"),
        ("ping", "Ping", "Your internet latency"),
        ("low_fps_alert", "Low FPS alert", "Wrist pops up when FPS tanks"),
        ("battery_alert", "Low battery alert", "Warns u before a controller dies"),
    ],
    "Wrist": [
        ("clock", "Clock", "Time + day on your wrist"),
        ("batteries", "Batteries", "Headset / controllers / trackers"),
        ("session_timer", "Session timer", "How long you've been in VR"),
        ("now_playing", "Now playing", "Song from Spotify / media"),
        ("music_controls", "Music controls", "Tap ur wrist w/ ur other hand"),
        ("last_ai_reply", "AI reply on wrist", "Show Fluff's last message"),
        ("look_to_show", "Look to show", "HUD fades in when you look"),
        ("wrist_kitty", "Lil Kitty", "Pettable cat on ur other wrist"),
    ],
    "VRChat": [
        ("world_info", "World info", "World name, instance, players"),
        ("join_alerts", "Join / leave alerts", "\"Kitsu joined\" on ur wrist"),
        ("avatar_toggles", "Avatar toggles", "Toggle ur avatar (Avatar tab)"),
        ("chatbox_status", "Chatbox stats", "Status, song, time... (Chatbox tab)"),
        ("ai_to_chatbox", "AI to chatbox", "Others see Fluff's replies"),
        ("typing_indicator", "Typing bubble", "Shows ... while you type to Fluff"),
        ("mute_indicator", "Mute indicator", "Mic muted/live on your wrist"),
        ("mute_reminder", "Still-muted nudge", "Reminds u after 10 min muted"),
        ("afk_detect", "AFK detection", "Knows when u walk away"),
        ("avatar_height", "Avatar height", "How tall ur avi is (m + ft)"),
        ("ai_look", "AI Look", "AI reads ur screen: who's around u"),
    ],
    "Counters": [
        ("headpat_counter", "Headpat counter", "Auto-finds ur avatar's pat contact"),
        ("pat_party", "Pat party", "Big alert for 5 pats in 30s"),
        ("boop_counter", "Boop counter", "Counts nose boops (contact)"),
        ("jump_counter", "Jump counter", "Counts every hop"),
        ("yap_meter", "Yap meter", "How long u've been talking"),
        ("distance", "Zoomies meter", "Distance walked + running"),
        ("vr_streak", "VR streak", "Time in VR today + days in a row"),
    ],
    "Fun": [
        ("wrist_pet", "Lil Fluff pet", "Tiny buddy w/ moods on ur wrist"),
        ("timer", "Timer / stopwatch", "Countdown + ding (World tab)"),
        ("weather", "Weather", "Temp + sky where you are"),
        ("discord_presence", "Discord status", "Shows the app on ur Discord profile"),
        ("zoom_lens", "Zoom lens", "Magnify what u see (Screen tab)"),
        ("song_toast", "Song pop-up", "Wrist pops up on a new song"),
        ("countdown", "Countdown", "Days until ur big day"),
        ("kaomoji", "Kaomoji", "Cute face at the end of ur chatbox"),
        ("quote_of_hour", "Cute quote", "A new sweet quote every hour"),
        ("theme_shuffle", "Theme shuffle", "Random theme every launch"),
    ],
    "Comfy": [
        ("break_reminder", "Break reminder", "Water + stretch nudges"),
        ("hydration_reminder", "Hydration buddy", "A water nudge every 30 min"),
        ("eye_break", "Eye break", "20-20-20 rule for tired eyes"),
        ("posture_reminder", "Posture check", "Sit up straight nudges"),
        ("bedtime_alert", "Bedtime alert", "Gentle nudge at ur bedtime"),
        ("vr_milestones", "VR milestones", "Celebrates every hour in VR"),
    ],
}
# turning these mods on also adds their line to the chatbox
MOD_TO_LINE = {"headpat_counter": "headpats", "boop_counter": "boops", "jump_counter": "jumps", "yap_meter": "yap",
               "avatar_height": "height", "countdown": "countdown", "quote_of_hour": "quote", "kaomoji": "kaomoji"}
# little settings row under some categories: (label fn, action, args)
ALL_MODS = [m for cat in MOD_CATS for m in MOD_INFO[cat]]


class Hit:
    def __init__(self):
        self.areas = []

    def add(self, box, action, *args):
        self.areas.append((box, action, args))

    def find(self, x, y):
        for (x0, y0, x1, y1), a, args in reversed(self.areas):
            if x0 <= x <= x1 and y0 <= y <= y1:
                return a, args
        return None, ()

    def find_box(self, x, y):
        for box, a, args in reversed(self.areas):
            if box[0] <= x <= box[2] and box[1] <= y <= box[3]:
                return tuple(box)
        return None


def draw_cursor(img, pos, trail, clicks, t, style="paw"):
    """Cute laser cursor drawn on the menu (SteamVR's own dot is hidden over our panel).
    trail = [(x, y, age_s)], clicks = [(x, y, age_s)] for heart pops."""
    if pos is None and not clicks:
        return img
    d = ImageDraw.Draw(img)
    for (x, y, age) in trail:                       # fading sparkle trail
        k = max(0.0, 1 - age / 0.45)
        if k > 0.05:
            sparkle(d, x, y, 3 + 4 * k, mix(t["panel"], t["warn"], k))
    for (x, y, age) in clicks:                      # heart pop on click
        k = age / 0.6
        if k < 1:
            for i in range(6):
                ang = i * 1.047 + 0.3
                r = 14 + 34 * k
                c = mix(t["primary"], t["panel"], k)
                doodle_heart(d, x + math.cos(ang) * r, y + math.sin(ang) * r - 10 * k, 6 * (1 - k * 0.5),
                             c, mix(t["line"], t["panel"], k))
    if pos is not None:
        x, y = pos
        if style == "heart":
            doodle_heart(d, x, y, 11, t["primary"], t["line"])
        elif style == "star":
            doodle_star(d, x, y, 13, t["warn"], t["line"])
        else:                                       # paw with ink outline
            paw(d, x, y + 6, 16, t["line"])
            paw(d, x, y + 6, 13, t["primary"])
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=t["on_primary"])   # exact aim point
    return img


def draw_hover(img, box, t):
    """Glowy outline around whatever the laser is pointing at."""
    if not box:
        return img
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    r = min(22, (y1 - y0) / 2)
    d.rounded_rectangle([x0 - 4, y0 - 4, x1 + 4, y1 + 4], radius=r + 4, outline=t["line"], width=6)
    d.rounded_rectangle([x0 - 3, y0 - 3, x1 + 3, y1 + 3], radius=r + 3, outline=t["primary"], width=3)
    return img


def button(d, hit, box, label, t, action, *args, active=False, fsize=20, primary=False):
    fill = t["primary"] if (active or primary) else t["panel2"]
    pill(d, box, fill)
    col = t["on_primary"] if (active or primary) else t["text"]
    d.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), label,
           font=font("head", fsize), fill=col, anchor="mm")
    hit.add(box, action, *args)


def render_dashboard(state):
    cfg, t = state.cfg, get_theme(state.cfg)
    img = dash_bg(theme_key(cfg), DASH_W, DASH_H).copy()
    d = ImageDraw.Draw(img)
    hit = Hit()

    global _CUR
    _CUR = t
    # header: animated sticker logo + hand-lettered name
    top = 54
    frames, _ = sticker_frames(LOGO_H)
    if frames:
        if state.logo_frame is not None:     # None = leave room, main.py animates it
            img.alpha_composite(frames[state.logo_frame % len(frames)], LOGO_POS)
        tx0 = LOGO_POS[0] + frames[0].width + 8
    else:
        paw(d, 56, top + 40, 15, t["primary"])
        tx0 = 84
    ft = font("title", 34)
    d.text((tx0, top + 46), "Fluff VR Stats", font=ft, fill=t["text"], anchor="ls")
    cx3 = tx0 + ft.getlength("Fluff VR Stats") + 8
    d.text((cx3, top + 46), ":3", font=ft, fill=t["primary"], anchor="ls")
    doodle_heart(d, cx3 + ft.getlength(":3") + 14, top + 18, 6, t["primary"], t["line"])
    d.text((tx0 + 2, top + 72), "stats + mods + ur fluffy ai buddy", font=font("body2", 15),
           fill=t["sub"], anchor="ls")

    # doodle icon tabs: the active one also shows its name
    tx = DASH_W - 40
    for name in reversed(TABS):
        active = state.tab == name
        label = "" if name == "<3" else name
        w = (font("head", 17).getlength(label) + 52) if (active and label) else 40
        box = [tx - w, top + 14, tx, top + 58]
        pill(d, box, t["primary"] if active else t["panel2"])
        col = t["on_primary"] if active else t["text"]
        tab_icon(d, name, box[0] + 20, top + 36, col, t)
        if active and label:
            d.text((box[0] + 36, top + 36), label, font=font("head", 17), fill=col, anchor="lm")
        hit.add(box, "tab", name)
        tx -= w + 3

    body = [40, top + 96, DASH_W - 40, DASH_H - 38]
    state.anim_slots = []
    {"Stats": _tab_stats, "Chat": _tab_chat,
     "Screen": _tab_screen, "Mods": _tab_mods, "Style": _tab_style,
     "Music": _tab_music, "Chatbox": _tab_chatbox, "Avatar": _tab_avatar, "World": _tab_world,
     "Boost": _tab_boost,
     "Wrist": _tab_wrist, "<3": _tab_thanks}.get(state.tab, _tab_stats)(d, hit, body, state, t)
    if state.errors and not state.errors_dismissed:
        _error_toast(d, hit, body, state, t)
    return img, hit


def tab_icon(d, name, cx, cy, col, t):
    """Little hand-drawn icons for the tab bar."""
    lw = 3
    if name == "Stats":
        for i, hgt in enumerate((8, 14, 20)):
            x = cx - 9 + i * 7
            d.rounded_rectangle([x, cy + 9 - hgt, x + 4, cy + 9], radius=2, fill=col)
    elif name == "Chat":
        d.rounded_rectangle([cx - 11, cy - 9, cx + 11, cy + 6], radius=6, outline=col, width=lw)
        d.polygon([(cx - 6, cy + 5), (cx - 1, cy + 5), (cx - 8, cy + 11)], fill=col)
        paw(d, cx, cy - 1, 2.6, col)
    elif name == "Music":
        note_icon(d, cx - 2, cy + 1, 6, col)
    elif name == "Chatbox":
        d.rounded_rectangle([cx - 12, cy - 9, cx + 12, cy + 6], radius=6, outline=col, width=lw)
        d.polygon([(cx + 2, cy + 5), (cx + 8, cy + 5), (cx + 9, cy + 11)], fill=col)
        for i in (-6, 0, 6):
            d.ellipse([cx + i - 2, cy - 3, cx + i + 2, cy + 1], fill=col)
    elif name == "Screen":
        d.rounded_rectangle([cx - 12, cy - 10, cx + 12, cy + 5], radius=3, outline=col, width=lw)
        d.line([(cx, cy + 5), (cx, cy + 10)], fill=col, width=lw)
        d.line([(cx - 6, cy + 10), (cx + 6, cy + 10)], fill=col, width=lw)
    elif name == "Mods":
        d.rounded_rectangle([cx - 12, cy - 6, cx + 12, cy + 6], radius=6, outline=col, width=lw)
        d.ellipse([cx + 1, cy - 4, cx + 9, cy + 4], fill=col)
    elif name == "Style":
        d.ellipse([cx - 11, cy - 10, cx + 11, cy + 10], outline=col, width=lw)
        for dx, dy in ((-4, -4), (3, -5), (5, 2)):
            d.ellipse([cx + dx - 2, cy + dy - 2, cx + dx + 2, cy + dy + 2], fill=col)
        d.ellipse([cx - 6, cy + 2, cx - 1, cy + 7], fill=col)
    elif name == "Wrist":
        d.rounded_rectangle([cx - 5, cy - 13, cx + 5, cy + 13], radius=3, fill=col)
        d.ellipse([cx - 9, cy - 8, cx + 9, cy + 8], fill=col)
        d.ellipse([cx - 6, cy - 5, cx + 6, cy + 5], fill=t["panel2"] if col != t["on_primary"] else t["primary"])
        d.line([(cx, cy), (cx, cy - 4)], fill=col, width=2)
        d.line([(cx, cy), (cx + 3, cy)], fill=col, width=2)
    elif name == "Boost":    # lightning bolt
        d.polygon([(cx + 3, cy - 13), (cx - 8, cy + 2), (cx - 1, cy + 2), (cx - 4, cy + 13),
                   (cx + 8, cy - 3), (cx + 1, cy - 3)], fill=col)
    elif name == "Avatar":   # little cat head
        d.polygon([(cx - 10, cy - 2), (cx - 9, cy - 13), (cx - 2, cy - 7)], fill=col)
        d.polygon([(cx + 10, cy - 2), (cx + 9, cy - 13), (cx + 2, cy - 7)], fill=col)
        d.ellipse([cx - 10, cy - 8, cx + 10, cy + 10], fill=col)
        bgc = t["primary"] if col == t["on_primary"] else t["panel2"]
        d.ellipse([cx - 5, cy - 1, cx - 2, cy + 2], fill=bgc)
        d.ellipse([cx + 2, cy - 1, cx + 5, cy + 2], fill=bgc)
    elif name == "World":    # globe
        d.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], outline=col, width=lw)
        d.ellipse([cx - 5, cy - 11, cx + 5, cy + 11], outline=col, width=2)
        d.line([(cx - 11, cy), (cx + 11, cy)], fill=col, width=2)
    elif name == "<3":
        doodle_heart(d, cx, cy + 1, 9, col if col != t["text"] else t["primary"], t["line"])


def media_icon(d, kind, cx, cy, r, col):
    """prev / next / play / pause / vol_up / vol_down / mute / zoom glyphs."""
    if kind == "zoom":                       # magnifying glass
        rr = r * 0.48
        d.ellipse([cx - r * 0.55, cy - r * 0.55, cx - r * 0.55 + rr * 2, cy - r * 0.55 + rr * 2],
                  outline=col, width=max(2, int(r * 0.22)))
        d.line([(cx + r * 0.25, cy + r * 0.25), (cx + r * 0.7, cy + r * 0.7)], fill=col, width=max(3, int(r * 0.3)))
        return
    if kind == "play":
        d.polygon([(cx - r * 0.45, cy - r * 0.7), (cx - r * 0.45, cy + r * 0.7), (cx + r * 0.75, cy)], fill=col)
    elif kind == "pause":
        d.rounded_rectangle([cx - r * 0.55, cy - r * 0.65, cx - r * 0.15, cy + r * 0.65], radius=2, fill=col)
        d.rounded_rectangle([cx + r * 0.15, cy - r * 0.65, cx + r * 0.55, cy + r * 0.65], radius=2, fill=col)
    elif kind in ("next", "prev"):
        s = 1 if kind == "next" else -1
        for off in (-0.45, 0.15):
            x0 = cx + s * r * off
            d.polygon([(x0, cy - r * 0.55), (x0, cy + r * 0.55), (x0 + s * r * 0.6, cy)], fill=col)
        xb = cx + s * r * 0.8
        d.rectangle([min(xb, xb + s * r * 0.15), cy - r * 0.55, max(xb, xb + s * r * 0.15), cy + r * 0.55], fill=col)
    elif kind in ("vol_up", "vol_down", "mute"):
        d.polygon([(cx - r * 0.8, cy - r * 0.3), (cx - r * 0.45, cy - r * 0.3), (cx - r * 0.05, cy - r * 0.7),
                   (cx - r * 0.05, cy + r * 0.7), (cx - r * 0.45, cy + r * 0.3), (cx - r * 0.8, cy + r * 0.3)], fill=col)
        if kind == "mute":
            d.line([(cx + r * 0.2, cy - r * 0.35), (cx + r * 0.75, cy + r * 0.35)], fill=col, width=3)
            d.line([(cx + r * 0.2, cy + r * 0.35), (cx + r * 0.75, cy - r * 0.35)], fill=col, width=3)
        else:
            d.line([(cx + r * 0.2, cy), (cx + r * 0.8, cy)], fill=col, width=3)
            if kind == "vol_up":
                d.line([(cx + r * 0.5, cy - r * 0.3), (cx + r * 0.5, cy + r * 0.3)], fill=col, width=3)


def icon_button(d, hit, box, kind, t, action, *args, primary=False):
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    r = min(box[2] - box[0], box[3] - box[1]) / 2
    if primary:
        d.ellipse([cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3], fill=t["line"])
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=t["primary"])
        media_icon(d, kind, cx, cy, r * 0.62, t["on_primary"])
    else:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=t["panel2"], outline=t["line_soft"], width=2)
        media_icon(d, kind, cx, cy, r * 0.62, t["text"])
    hit.add(box, action, *args)


def _fmt_t(sec):
    sec = max(0, int(sec or 0))
    return f"{sec // 60}:{sec % 60:02d}"


def _tab_music(d, hit, box, state, t):
    x0, y0, x1, y1 = box
    m = state.music or {}
    has = bool(m.get("title"))
    # album art card
    A = 300
    ax, ay = x0 + 10, y0 + (y1 - y0 - A) / 2 - 6
    d.rounded_rectangle([ax - 5, ay - 5, ax + A + 5, ay + A + 5], radius=34, fill=t["line"])
    art = m.get("art")
    if art is not None:
        a = art.convert("RGBA").resize((A, A), Image.LANCZOS)
        mask = Image.new("L", (A * 2, A * 2), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, A * 2 - 1, A * 2 - 1], radius=60, fill=255)
        d._image.paste(a, (int(ax), int(ay)), mask.resize((A, A), Image.LANCZOS))
    else:   # vinyl doodle
        d.rounded_rectangle([ax, ay, ax + A, ay + A], radius=30, fill=t["panel"])
        cx, cy = ax + A / 2, ay + A / 2
        d.ellipse([cx - 120, cy - 120, cx + 120, cy + 120], fill=t["line"])
        for rr in (100, 80, 60):
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=mix(t["line"], t["text"], 0.18), width=2)
        d.ellipse([cx - 38, cy - 38, cx + 38, cy + 38], fill=t["primary"])
        paw(d, cx, cy + 4, 13, t["on_primary"])
    # info
    tx = ax + A + 40
    tw = x1 - tx
    if has:
        app = m.get("app") or "music"
        d.text((tx, y0 + 18), ("playing in " if m.get("playing") else "paused in ") + app,
               font=font("body2", 17), fill=t["sub"])
        ft = font("title", 40)
        lines = wrap(m["title"], ft, tw)[:2]
        if len(wrap(m["title"], ft, tw)) > 2:
            lines[1] = ellipsize(lines[1] + "…", ft, tw)
        for i, ln in enumerate(lines):
            d.text((tx, y0 + 46 + i * 46), ln, font=ft, fill=t["text"])
        ty = y0 + 46 + len(lines) * 46 + 6
        d.text((tx, ty), ellipsize(m.get("artist") or "", font("body", 22), tw), font=font("body", 22), fill=t["primary"])
        if m.get("album"):
            d.text((tx, ty + 32), ellipsize(m["album"], font("body2", 16), tw), font=font("body2", 16), fill=t["sub"])
    else:
        d.text((tx, y0 + 60), "nothing playing rn", font=font("title", 40), fill=t["text"])
        d.text((tx, y0 + 112), "put on some tunes! (spotify, youtube, anything)", font=font("body2", 18),
               fill=t["sub"])
    # progress bar
    py = y0 + 236
    pill(d, [tx, py, x1, py + 14], t["panel2"])
    if m.get("dur"):
        k = min(1.0, max(0.0, (m.get("pos") or 0) / m["dur"]))
        if k > 0.01:
            pill(d, [tx, py, tx + max(14, (x1 - tx) * k), py + 14], t["primary"], outline=False)
        kx = tx + (x1 - tx) * k
        d.ellipse([kx - 10, py - 3, kx + 10, py + 17], fill=t["text"], outline=t["line"], width=2)
        d.text((tx, py + 24), _fmt_t(m.get("pos")), font=font("body2", 15), fill=t["sub"])
        d.text((x1, py + 24), _fmt_t(m["dur"]), font=font("body2", 15), fill=t["sub"], anchor="ra")
    # controls
    cy = y0 + 330
    mid = tx + (x1 - tx) / 2
    icon_button(d, hit, [mid - 150, cy - 30, mid - 90, cy + 30], "prev", t, "music", "prev")
    icon_button(d, hit, [mid - 42, cy - 42, mid + 42, cy + 42], "pause" if m.get("playing") else "play",
                t, "music", "play_pause", primary=True)
    icon_button(d, hit, [mid + 90, cy - 30, mid + 150, cy + 30], "next", t, "music", "next")
    vy = y1 - 30
    icon_button(d, hit, [tx, vy - 22, tx + 44, vy + 22], "vol_down", t, "music", "vol_down")
    icon_button(d, hit, [tx + 54, vy - 22, tx + 98, vy + 22], "mute", t, "music", "mute")
    icon_button(d, hit, [tx + 108, vy - 22, tx + 152, vy + 22], "vol_up", t, "music", "vol_up")
    note = "volume" if m.get("backend") != "keys" else "basic mode - run install.bat for song info + art"
    d.text((tx + 166, vy), note, font=font("body2", 15), fill=t["sub"], anchor="lm")


def _tab_chatbox(d, hit, box, state, t):
    import chatbox as cbx
    x0, y0, x1, y1 = box
    cfg = state.cfg
    cb = cfg["chatbox"]
    on = cfg["modules"].get("chatbox_status", False)
    lw = 456
    # master switch
    panel(d, [x0, y0, x0 + lw, y0 + 72], 22, t)
    d.text((x0 + 22, y0 + 14), "Send to VRChat chatbox", font=font("title", 28), fill=t["text"])
    d.text((x0 + 22, y0 + 48), "stats show up above ur head for everyone", font=font("body2", 14), fill=t["sub"])
    switch(d, x0 + lw - 82, y0 + 21, on, t)
    hit.add([x0, y0, x0 + lw, y0 + 72], "toggle", "chatbox_status")
    # what to show
    d.text((x0 + 4, y0 + 92), "show in chatbox", font=font("head", 20), fill=t["text"])
    cols = 3 if len(cbx.LINE_KEYS) <= 12 else 4
    cw, ch, gy = (lw - 8 * (cols - 1)) / cols, (38 if cols == 3 else 30), (10 if cols == 3 else 6)
    for i, k in enumerate(cbx.LINE_KEYS):
        cx = x0 + (i % cols) * (cw + 8)
        cy = y0 + 120 + (i // cols) * (ch + gy)
        act = cb["lines"].get(k, False)
        pill(d, [cx, cy, cx + cw, cy + ch], t["primary"] if act else t["panel"])
        d.text((cx + cw / 2, cy + ch / 2), cbx.LINE_LABELS[k], font=font("body", 15 if cols == 3 else 13),
               fill=t["on_primary"] if act else t["sub"], anchor="mm")
        hit.add([cx, cy, cx + cw, cy + ch], "cb_line", k)
    # rate + style
    ry = y0 + 120 + (-(-len(cbx.LINE_KEYS) // cols)) * (ch + gy) + 8
    d.text((x0 + 4, ry + 20), "send every", font=font("body2", 16), fill=t["sub"], anchor="lm")
    for i, v in enumerate((2, 3, 5)):
        bx = x0 + 100 + i * 62
        button(d, hit, [bx, ry, bx + 54, ry + 40], f"{v}s", t, "cb_set", "interval_s", v,
               active=cb.get("interval_s") == v, fsize=18)
    for i, (v, lab) in enumerate((("cute", "emoji"), ("simple", "simple"))):
        bx = x0 + 300 + i * 80
        button(d, hit, [bx, ry, bx + 72, ry + 40], lab, t, "cb_set", "style", v,
               active=cb.get("style") == v, fsize=17)
    ty = ry + 50
    button(d, hit, [x0, ty, x0 + 150, ty + 40], "24h clock" if cb.get("time_24h") else "12h clock", t,
           "cb_set", "time_24h", not cb.get("time_24h"), fsize=17)
    if state.extras.get("magicchatbox"):
        d.text((x0 + 164, ty + 20), "MagicChatbox is open - close it so they don't fight!",
               font=font("body2", 14), fill=t["bad"], anchor="lm")

    # live preview: VRChat-style bubble
    px = x0 + lw + 22
    d.text((px, y0 + 2), "preview", font=font("head", 20), fill=t["text"])
    text = cbx.compose(cfg, state.stats, state.extras, state.music) or "(nothing to show yet)"
    lines = rich_wrap(text, 17, x1 - px - 40)
    bh = min(250, 26 + 24 * len(lines))
    bb = [px, y0 + 34, x1, y0 + 34 + bh]
    d.rounded_rectangle(bb, radius=18, fill=(24, 24, 28), outline=t["line_soft"], width=2)
    d.polygon([((bb[0] + bb[2]) / 2 - 10, bb[3]), ((bb[0] + bb[2]) / 2 + 10, bb[3]),
               ((bb[0] + bb[2]) / 2, bb[3] + 12)], fill=(24, 24, 28))
    for i, ln in enumerate(lines[:9]):
        rich_text(d, ((bb[0] + bb[2]) / 2, bb[1] + 12 + i * 24), ln, 17, (255, 255, 255), center=True)
    d.text((x1, bb[3] + 18), f"{len(text)}/144", font=font("body2", 13), fill=t["sub"], anchor="ra")

    # status messages
    sy = y0 + 320
    sts = cb.get("statuses") or [""]
    idx = cb.get("status_index", 0) % len(sts)
    panel(d, [px, sy, x1, y1], 20, t)
    d.text((px + 16, sy + 10), f"status {idx + 1}/{len(sts)}", font=font("head", 18), fill=t["text"])
    d.text((px + 130, sy + 12), ellipsize(sts[idx] or "(empty)", font("body2", 15), x1 - px - 150),
           font=font("body2", 15), fill=t["sub"])
    bw = (x1 - px - 32 - 4 * 6) / 5
    labels = [("<", "cb_status", "prev"), (">", "cb_status", "next"), ("edit", "cb_status", "edit"),
              ("+ new", "cb_status", "add"), ("delete", "cb_status", "delete")]
    for i, (lab, act, arg) in enumerate(labels):
        bx = px + 16 + i * (bw + 6)
        button(d, hit, [bx, sy + 40, bx + bw, sy + 76], lab, t, act, arg, fsize=16)
    rot = cb.get("rotate", True)
    d.text((px + 16, sy + 98), f"rotate statuses every {cb.get('rotate_s', 30)}s", font=font("body2", 14),
           fill=t["sub"], anchor="lm")
    switch(d, x1 - 70, sy + 86, rot, t, scale=0.8)
    hit.add([px, sy + 82, x1, sy + 114], "cb_set", "rotate", not rot)


def _tab_boost(d, hit, box, state, t):
    import tweaks as tw
    x0, y0, x1, y1 = box
    info = state.boost or {}
    status = info.get("status", {})
    lw = 540
    # header
    panel(d, [x0, y0, x0 + lw, y0 + 70], 22, t)
    d.text((x0 + 22, y0 + 14), "FPS Boost", font=font("title", 32), fill=t["text"])
    d.text((x0 + 22, y0 + 50), "safe + undoable, no admin needed", font=font("body2", 14), fill=t["sub"])
    on_n = sum(1 for k, _, _ in tw.TWEAKS if status.get(k))
    button(d, hit, [x0 + lw - 268, y0 + 15, x0 + lw - 108, y0 + 55], f"boost all ({on_n}/{len(tw.TWEAKS)})",
           t, "tw_all", primary=True, fsize=17)
    button(d, hit, [x0 + lw - 100, y0 + 15, x0 + lw - 14, y0 + 55], "undo all", t, "tw_undo_all", fsize=16)
    # tweak cards
    for i, (key, name, desc) in enumerate(tw.TWEAKS):
        cy = y0 + 82 + i * 74
        on = status.get(key)
        panel(d, [x0, cy, x0 + lw, cy + 66], 20, t)
        dot = t["good"] if on else (t["sub"] if on is None else t["warn"])
        d.ellipse([x0 + 18, cy + 26, x0 + 32, cy + 40], fill=dot)
        d.text((x0 + 44, cy + 12), name, font=font("head", 20), fill=t["text"])
        d.text((x0 + 44, cy + 40), desc, font=font("body2", 14), fill=t["sub"])
        if on is None:
            d.text((x0 + lw - 20, cy + 33), "n/a", font=font("body2", 15), fill=t["sub"], anchor="rm")
        else:
            button(d, hit, [x0 + lw - 112, cy + 14, x0 + lw - 14, cy + 52], "undo" if on else "boost",
                   t, "tw_undo" if on else "tw_apply", key, primary=not on, fsize=17)
    if info.get("msg"):
        d.text((x0 + 4, y1 - 4), ellipsize(info["msg"], font("body2", 15), lw), font=font("body2", 15),
               fill=t["warn"], anchor="ls")
    # heavy apps
    px = x0 + lw + 18
    panel(d, [px, y0, x1, y0 + 250], 22, t)
    d.text((px + 18, y0 + 12), "heavy apps rn", font=font("head", 20), fill=t["text"])
    button(d, hit, [x1 - 108, y0 + 10, x1 - 14, y0 + 42], "refresh", t, "tw_heavy", fsize=15)
    heavy = info.get("heavy") or []
    if not heavy:
        d.text((px + 18, y0 + 60), "checking..." if info.get("sampling") else "tap refresh to check",
               font=font("body2", 16), fill=t["sub"])
    for i, r in enumerate(heavy[:5]):
        ry = y0 + 52 + i * 38
        nm = r["name"][:-4] if r["name"].lower().endswith(".exe") else r["name"]
        d.text((px + 18, ry + 16), ellipsize(nm, font("body", 16), 150), font=font("body", 16), fill=t["text"], anchor="lm")
        col = t["bad"] if r["cpu"] > 15 else t["warn"] if r["cpu"] > 5 else t["sub"]
        d.text((px + 210, ry + 16), f"{r['cpu']:.0f}%", font=font("body", 16), fill=col, anchor="rm")
        d.text((px + 278, ry + 16), f"{r['mem'] / 1024:.1f}G" if r["mem"] > 1024 else f"{r['mem']:.0f}M",
               font=font("body2", 14), fill=t["sub"], anchor="rm")
        calmed = r["name"] in info.get("calmed", ())
        button(d, hit, [x1 - 92, ry + 2, x1 - 14, ry + 32], "calmed" if calmed else "calm",
               t, "tw_calm", r["name"], active=calmed, fsize=14)
    d.text((px + 18, y0 + 236), "'calm' lowers priority - nothing closes", font=font("body2", 13), fill=t["sub"], anchor="lm")
    # tips
    ty = y0 + 264
    panel(d, [px, ty, x1, y1], 22, t)
    i = info.get("tip", 0) % len(tw.TIPS)
    title, body = tw.TIPS[i]
    d.text((px + 18, ty + 12), f"tip {i + 1}/{len(tw.TIPS)}", font=font("body2", 14), fill=t["sub"])
    d.text((px + 18, ty + 32), ellipsize(title, font("head", 20), x1 - px - 40), font=font("head", 20), fill=t["primary"])
    for k, ln in enumerate(wrap(body, font("body2", 15), x1 - px - 40)[:3]):
        d.text((px + 18, ty + 64 + k * 21), ln, font=font("body2", 15), fill=t["text"])
    button(d, hit, [x1 - 108, y1 - 44, x1 - 14, y1 - 10], "next tip", t, "tip_next", fsize=15)


def _tab_world(d, hit, box, state, t):
    x0, y0, x1, y1 = box
    w = state.world or {}
    lw = 470
    # --- world card
    panel(d, [x0, y0, x0 + lw, y0 + 214], 22, t)
    if w.get("world"):
        d.text((x0 + 22, y0 + 16), "ur in", font=font("body2", 16), fill=t["sub"])
        ft = font("title", 34)
        lines = wrap(w["world"], ft, lw - 44)[:2]
        for i, ln in enumerate(lines):
            d.text((x0 + 22, y0 + 38 + i * 38), ln, font=ft, fill=t["text"])
        yy = y0 + 46 + len(lines) * 38
        chips = [(w.get("type") or "instance", t["primary"])]
        for i, (lab, col) in enumerate(chips):
            fw = font("head", 18).getlength(lab) + 30
            pill(d, [x0 + 22, yy, x0 + 22 + fw, yy + 34], col)
            d.text((x0 + 22 + fw / 2, yy + 17), lab, font=font("head", 18), fill=t["on_primary"], anchor="mm")
        since = w.get("world_since")
        if since:
            d.text((x0 + 150, yy + 17), "here for " + fmt_dur(time.time() - since), font=font("body2", 17),
                   fill=t["sub"], anchor="lm")
        n = len(w.get("players", []))
        d.text((x0 + lw - 24, y0 + 196), str(n), font=font("title", 64), fill=t["primary"], anchor="rs")
        d.text((x0 + lw - 24 - font("title", 64).getlength(str(n)) - 8, y0 + 190), "ppl here",
               font=font("body2", 16), fill=t["sub"], anchor="rs")
    else:
        d.text((x0 + 22, y0 + 30), "not in VRChat rn", font=font("title", 32), fill=t["text"])
        msg = ("open VRChat and i'll show the world + who's here" if not w.get("found")
               else "join a world and it'll show up here :3")
        for i, ln in enumerate(wrap(msg, font("body2", 17), lw - 44)):
            d.text((x0 + 22, y0 + 80 + i * 24), ln, font=font("body2", 17), fill=t["sub"])
    # --- recent joins/leaves
    ry = y0 + 228
    panel(d, [x0, ry, x0 + lw, y1], 22, t)
    d.text((x0 + 22, ry + 12), "recently", font=font("head", 20), fill=t["text"])
    evs = list(reversed(w.get("events", [])))[:5]
    if not evs:
        d.text((x0 + 22, ry + 50), "no joins or leaves yet", font=font("body2", 16), fill=t["sub"])
    for i, (ts, kind, name) in enumerate(evs):
        yy = ry + 46 + i * 33
        col = t["good"] if kind == "join" else t["sub"]
        d.ellipse([x0 + 24, yy + 7, x0 + 34, yy + 17], fill=col)
        d.text((x0 + 46, yy + 12), ellipsize(name, font("body", 17), lw - 190), font=font("body", 17),
               fill=t["text"], anchor="lm")
        ago = int(time.time() - ts)
        d.text((x0 + lw - 22, yy + 12), ("joined " if kind == "join" else "left ") +
               (f"{ago // 60}m ago" if ago >= 60 else "just now"), font=font("body2", 14), fill=t["sub"], anchor="rm")
    # --- timer
    px = x0 + lw + 18
    tm = state.timer
    panel(d, [px, y0, x1, y0 + 250], 22, t)
    now = time.time()
    if tm["mode"] == "timer":
        left = max(0.0, tm["end"] - now) if tm["running"] else tm["left"]
        big = f"{int(left // 60)}:{int(left % 60):02d}"
        title = "timer"
    else:
        el = tm["elapsed"] + ((now - tm["start"]) if tm["running"] else 0)
        big = f"{int(el // 60)}:{int(el % 60):02d}.{int(el * 10) % 10}"
        title = "stopwatch"
    d.text((px + 22, y0 + 14), title, font=font("head", 20), fill=t["text"])
    button(d, hit, [x1 - 150, y0 + 12, x1 - 18, y0 + 46], "stopwatch" if tm["mode"] == "timer" else "timer", t,
           "timer", "mode", fsize=16)
    d.text(((px + x1) / 2, y0 + 112), big, font=font("title", 72), fill=t["primary"] if tm["running"] else t["text"],
           anchor="mm")
    by = y0 + 160
    if tm["mode"] == "timer":
        for i, (lab, sec) in enumerate((("+1m", 60), ("+5m", 300), ("+15m", 900))):
            bx = px + 18 + i * 66
            button(d, hit, [bx, by, bx + 60, by + 38], lab, t, "timer", "add", sec, fsize=16)
    button(d, hit, [x1 - 196, by, x1 - 102, by + 38], "pause" if tm["running"] else "start", t, "timer", "toggle",
           primary=True, fsize=18)
    button(d, hit, [x1 - 94, by, x1 - 18, by + 38], "reset", t, "timer", "reset", fsize=16)
    d.text((px + 22, y0 + 226), "shows on ur wrist + dings when done", font=font("body2", 14), fill=t["sub"], anchor="lm")
    # --- session recap
    sy = y0 + 264
    panel(d, [px, sy, x1, y1], 22, t)
    d.text((px + 22, sy + 12), "today's recap", font=font("head", 20), fill=t["text"])
    ex = state.extras
    walked = state.walked
    items = [("in VR", fmt_dur(now - ex.get("session_start", now))),
             ("walked", f"{walked / 1000:.2f}km" if walked >= 1000 else f"{walked:.0f}m"),
             ("worlds", str(w.get("worlds_visited", 0))), ("ppl met", str(w.get("people_met", 0))),
             ("headpats", str(ex.get("headpats", 0))), ("floof pats", str(state.cfg.get("floof_pats", 0)))]
    cw = (x1 - px - 44) / 3
    for i, (lab, val) in enumerate(items):
        cx = px + 22 + (i % 3) * cw
        cy = sy + 46 + (i // 3) * 64
        d.text((cx, cy), val, font=font("title", 30), fill=t["text"])
        d.text((cx, cy + 36), lab, font=font("body2", 14), fill=t["sub"])


def _tab_avatar(d, hit, box, state, t):
    x0, y0, x1, y1 = box
    av = state.avatar or {}
    params = av.get("params") or []
    vals = av.get("values") or {}
    panel(d, [x0, y0, x1, y0 + 64], 22, t)
    if av.get("id"):
        d.text((x0 + 22, y0 + 32), ellipsize(av.get("name") or "my avatar", font("title", 30), 520),
               font=font("title", 30), fill=t["text"], anchor="lm")
        d.text((x0 + 560, y0 + 32), f"{len(params)} toggles", font=font("body2", 16), fill=t["sub"], anchor="lm")
    else:
        d.text((x0 + 22, y0 + 32), "no avatar found yet", font=font("title", 30), fill=t["text"], anchor="lm")
    button(d, hit, [x1 - 130, y0 + 12, x1 - 16, y0 + 52], "refresh", t, "av_refresh", fsize=17)
    if not params:
        msg = ["1) in VRChat: Action Menu > Options > OSC > Enabled",
               "2) switch avatars once (or reset OSC config) so VRChat lists its toggles",
               "3) they show up here as buttons :3"]
        for i, ln in enumerate(msg):
            d.text((x0 + 30, y0 + 110 + i * 34), ln, font=font("body", 19), fill=t["sub"])
        if not state.cfg["modules"].get("avatar_toggles"):
            d.text((x0 + 30, y0 + 230), "(turn on 'Avatar toggles' in Mods > VRChat)", font=font("body2", 16),
                   fill=t["warn"])
        return
    per = 12
    pages = max(1, (len(params) + per - 1) // per)
    page = min(state.avatar_page, pages - 1)
    cols, gap, ch = 3, 12, 74
    cw = (x1 - x0 - gap * (cols - 1)) / cols
    for i, p in enumerate(params[page * per:(page + 1) * per]):
        cx = x0 + (i % cols) * (cw + gap)
        cy = y0 + 80 + (i // cols) * (ch + 10)
        v = vals.get(p["name"])
        if p["type"] == "Bool":
            on = bool(v)
            pill(d, [cx, cy, cx + cw, cy + ch], t["primary"] if on else t["panel"])
            d.text((cx + 24, cy + ch / 2), ellipsize(p["name"], font("head", 20), cw - 110), font=font("head", 20),
                   fill=t["on_primary"] if on else t["text"], anchor="lm")
            switch(d, cx + cw - 76, cy + ch / 2 - 15, on, t)
            hit.add([cx, cy, cx + cw, cy + ch], "av_set", p["name"], not on)
        else:
            panel(d, [cx, cy, cx + cw, cy + ch], 24, t)
            d.text((cx + 20, cy + 22), ellipsize(p["name"], font("head", 18), cw - 40), font=font("head", 18),
                   fill=t["text"], anchor="lm")
            if p["type"] == "Int":
                val = int(v or 0)
                shown, step, lo, hi = str(val), 1, 0, 255
            else:
                val = float(v or 0.0)
                shown, step, lo, hi = f"{val * 100:.0f}%", 0.25, -1.0, 1.0
            d.text((cx + cw / 2, cy + 52), shown, font=font("title", 24), fill=t["primary"], anchor="mm")
            button(d, hit, [cx + 14, cy + 38, cx + 64, cy + 66], "-", t, "av_set", p["name"], max(lo, val - step), fsize=20)
            button(d, hit, [cx + cw - 64, cy + 38, cx + cw - 14, cy + 66], "+", t, "av_set", p["name"],
                   min(hi, val + step), fsize=20)
    if pages > 1:
        d.text(((x0 + x1) / 2, y1 - 16), f"page {page + 1}/{pages}", font=font("body2", 16), fill=t["sub"], anchor="mm")
        button(d, hit, [x0, y1 - 36, x0 + 90, y1], "< prev", t, "av_page", -1, fsize=16)
        button(d, hit, [x1 - 90, y1 - 36, x1, y1], "next >", t, "av_page", 1, fsize=16)


def _error_toast(d, hit, box, state, t):
    """Cute error card: derpy cat + what broke + reassurance. Never covers the tabs."""
    x0, y0, x1, y1 = box
    err = state.errors[-1]
    tb = [x0 + 40, y1 - 132, x1 - 40, y1 - 6]
    d.rounded_rectangle([tb[0] - 4, tb[1] - 4, tb[2] + 4, tb[3] + 4], radius=26, fill=t["line"])
    d.rounded_rectangle(tb, radius=22, fill=t["panel2"], outline=t["bad"], width=3)
    state.anim_slots.append(("sticker", 112, (int(tb[0] + 10), int(tb[1] + 7)), ERROR_ART, False))
    tx = tb[0] + 140
    d.text((tx, tb[1] + 14), "oopsie!! something went wrong", font=font("title", 28), fill=t["bad"])
    times = f"  (x{err['count']})" if err.get("count", 1) > 1 else ""
    d.text((tx, tb[1] + 52), ellipsize(err["text"] + times, font("body2", 16), tb[2] - tx - 120),
           font=font("body2", 16), fill=t["text"])
    more = f"  (+{len(state.errors) - 1} more)" if len(state.errors) > 1 else ""
    d.text((tx, tb[1] + 80), "don't worry, i'm still running :3  details are in logs/fluffvr.log" + more,
           font=font("body2", 14), fill=t["sub"])
    button(d, hit, [tb[2] - 100, tb[1] + 40, tb[2] - 16, tb[1] + 84], "ok", t, "dismiss_errors", fsize=22)


def _tab_thanks(d, hit, box, state, t):
    x0, y0, x1, y1 = box
    panel(d, box, 26, t)
    # the cuddly sticker bobs gently (animated by add_logo)
    frames, _ = sticker_frames(330, THANKS_ART)
    sw = frames[0].width if frames else 300
    state.anim_slots.append(("sticker", 330, (int(x0 + 30), int(y1 - 352)), THANKS_ART, True))
    tx = x0 + 60 + sw
    d.text((tx, y0 + 30), "thank u for downloading!!", font=font("title", 40), fill=t["text"])
    d.text((tx, y0 + 80), "Fluff VR Stats", font=font("title", 32), fill=t["primary"])
    doodle_heart(d, tx + font("title", 32).getlength("Fluff VR Stats") + 26, y0 + 98, 9,
                 t["primary"], t["line"])
    body = ("this lil app was made with sooo much love for the fluffy community. "
            "i hope it keeps ur frames smooth and ur tail wagging <3")
    f = font("body", 18)
    for i, ln in enumerate(wrap(body, f, x1 - tx - 30)):
        d.text((tx, y0 + 134 + i * 26), ln, font=f, fill=t["text"])
    tips = ["share it with ur friends :3", "drink water + take breaks", "give someone a headpat today"]
    for i, tip in enumerate(tips):
        ty = y0 + 224 + i * 32
        paw(d, tx + 10, ty + 13, 7, t["primary"])
        d.text((tx + 30, ty + 13), tip, font=font("body2", 17), fill=t["sub"], anchor="lm")
    cfg = state.cfg
    by = y1 - 70
    pats = cfg.get("floof_pats", 0)
    button(d, hit, [tx, by, tx + 210, by + 50], "pat the floof", t, "pat_floof", primary=True, fsize=24)
    d.text((tx + 226, by + 25), f"floof pats: {pats}", font=font("title", 22), fill=t["sub"], anchor="lm")
    # discord: online count + join button
    dc = getattr(state, "discord", {}) or {}
    bx1 = x1 - 24
    button(d, hit, [bx1 - 176, by, bx1, by + 50], "join discord", t, "join_discord", fsize=19)
    line = "our Discord"
    if dc.get("online") is not None:
        line = f"Discord: {dc['online']} online"
    if dc.get("rpc") == "connected":
        line += "  ·  ur status is live"
    d.text((bx1, by - 12), line, font=font("body2", 15), fill=t["sub"], anchor="rs")
    if time.time() - state.last_pat < 1.4:
        state.anim_slots.append(("hearts", state.last_pat, (tx + 105, by), t))
    credit = []
    if cfg.get("made_by"):
        credit.append(f"made by {cfg['made_by']}")
    if cfg.get("support_link"):
        credit.append(f"support me: {cfg['support_link']}")
    credit.append("sticker art by the original artists (signatures kept) · kitty art by a lovely anonymous artist <3")
    d.text((x1 - 24, y0 + 322), "  ·  ".join(credit[:2]), font=font("body2", 14), fill=t["sub"], anchor="ra")
    if len(credit) > 2:
        d.text((x1 - 24, y0 + 342), credit[2], font=font("body2", 14), fill=t["sub"], anchor="ra")


def _stat_tile(d, box, label, value, unit, t, col=None):
    panel(d, box, 20, t)
    x0, y0, x1, y1 = box
    d.text((x0 + 20, y0 + 18), label, font=font("body2", 18), fill=t["sub"])
    d.text((x0 + 20, y1 - 18), value, font=font("title", 44), fill=col or t["text"], anchor="ls")
    vw = font("title", 44).getlength(value)
    d.text((x0 + 26 + vw, y1 - 20), unit, font=font("head", 20), fill=t["sub"], anchor="ls")


def _tab_stats(d, hit, box, state, t):
    s = state.stats
    x0, y0, x1, y1 = box
    if not s.get("vr_ok", True):
        d.text(((x0 + x1) / 2, y0 + 30), "SteamVR isn't sending timing yet…",
               font=font("head", 22), fill=t["warn"], anchor="mm")
    cols, gap = 4, 16
    tw = (x1 - x0 - gap * (cols - 1)) / cols
    fps = s.get("fps")
    tiles = [
        ("VRChat FPS", "--" if fps is None else f"{fps:.0f}",
         f"/ {s['refresh']:.0f}" if s.get("refresh") else "", color_for_fps(fps, s.get("refresh"), t)),
        ("GPU frame", "--" if s.get("gpu_ms") is None else f"{s['gpu_ms']:.1f}", "ms", None),
        ("CPU frame", "--" if s.get("cpu_ms") is None else f"{s['cpu_ms']:.1f}", "ms", None),
        ("Reprojected", "--" if s.get("reproj_pct") is None else f"{s['reproj_pct']:.0f}", "%", None),
    ]
    for i, (lab, val, unit, col) in enumerate(tiles):
        bx = x0 + i * (tw + gap)
        _stat_tile(d, [bx, y0, bx + tw, y0 + 120], lab, val, unit, t, col)

    gy = y0 + 136
    target = 1000.0 / s["refresh"] if s.get("refresh") else 11.1
    graph(d, [x0, gy, x1, gy + 150], s.get("frametimes", []), target, t)
    d.text((x0 + 16, gy + 12), "GPU frametime (dashed line = budget)", font=font("body2", 16), fill=t["sub"])

    by = gy + 166
    half = (x1 - x0 - gap) / 2
    # PC usage
    panel(d, [x0, by, x0 + half, y1], 20, t)
    d.text((x0 + 20, by + 16), "PC", font=font("head", 20), fill=t["text"])
    if s.get("gpu_temp") is not None:
        extra = f"GPU {s['gpu_temp']:.0f}°C"
        if s.get("vram_used") is not None:
            extra += f" · {s['vram_used']:.1f}/{s['vram_total']:.0f} GB"
        d.text((x0 + half - 20, by + 18), extra, font=font("body2", 16), fill=t["sub"], anchor="ra")
    items = [("CPU", s.get("cpu_pct")), ("RAM", s.get("ram_pct")), ("GPU", s.get("gpu_pct"))]
    for i, (lab, val) in enumerate(items):
        ry = by + 52 + i * 34
        d.text((x0 + 20, ry + 10), lab, font=font("body2", 17), fill=t["sub"], anchor="lm")
        bx0, bx1 = x0 + 80, x0 + half - 80
        pill(d, [bx0, ry, bx1, ry + 20], t["panel2"])
        if val is not None:
            pill(d, [bx0, ry, bx0 + max(20, (bx1 - bx0) * min(val, 100) / 100), ry + 20], t["primary"])
        d.text((x0 + half - 20, ry + 10), "--" if val is None else f"{val:.0f}%",
               font=font("body", 17), fill=t["text"], anchor="rm")
    # batteries
    bx = x0 + half + gap
    panel(d, [bx, by, x1, y1], 20, t)
    d.text((bx + 20, by + 16), "Batteries", font=font("head", 20), fill=t["text"])
    bats = s.get("batteries") or []
    if not bats:
        d.text((bx + 20, by + 64), "no battery info yet", font=font("body2", 17), fill=t["sub"])
    for i, (lab, pct, chg) in enumerate(bats[:6]):
        col_i, row_i = i % 2, i // 2
        cx = bx + 20 + col_i * ((x1 - bx - 40) / 2)
        ry = by + 52 + row_i * 34
        colr = t["good"] if pct >= 40 else t["warn"] if pct >= 20 else t["bad"]
        d.rounded_rectangle([cx, ry + 2, cx + 30, ry + 18], radius=4, outline=t["sub"], width=2)
        d.rectangle([cx + 4, ry + 6, cx + 4 + 22 * pct / 100, ry + 14], fill=colr)
        d.text((cx + 40, ry + 10), f"{lab} {pct:.0f}%" + (" +" if chg else ""),
               font=font("body", 17), fill=t["text"], anchor="lm")


def _tab_chat(d, hit, box, state, t):
    x0, y0, x1, y1 = box
    area = [x0, y0, x1, y1 - 70]
    panel(d, area, 22, t)
    f = font("body", 20)
    maxw = (x1 - x0) * 0.68
    # build bubbles bottom-up
    bubbles = []
    for role, text in state.chat:
        lines = wrap(text, f, maxw - 36)
        bubbles.append((role, lines, 26 * len(lines) + 24))
    if state.thinking:
        bubbles.append(("assistant", ["typing…"], 50))
    if not bubbles:
        paw(d, (x0 + x1) / 2, (y0 + y1 - 70) / 2 - 10, 26, t["primary"])
        d.text(((x0 + x1) / 2, (y0 + y1 - 70) / 2 + 40), "say hi to Fluff!",
               font=font("head", 24), fill=t["sub"], anchor="mm")
    else:
        yb = area[3] - 16 + state.chat_scroll
        clip = Image.new("RGBA", d._image.size, (0, 0, 0, 0))
        cd = ImageDraw.Draw(clip)
        for role, lines, bh in reversed(bubbles):
            bw = max(f.getlength(l) for l in lines) + 36
            if role == "user":
                bx1 = area[2] - 18
                bx0 = bx1 - bw
                fill, col = t["primary"], t["on_primary"]
            else:
                bx0 = area[0] + 52
                bx1 = bx0 + bw
                fill, col = t["panel2"], t["text"]
            by0 = yb - bh
            if by0 < area[3] and yb > area[1]:
                cd.rounded_rectangle([bx0, by0, bx1, yb], radius=18, fill=fill)
                if role != "user":
                    paw(cd, area[0] + 30, yb - 18, 9, t["primary"])
                for i, ln in enumerate(lines):
                    cd.text((bx0 + 18, by0 + 12 + i * 26), ln, font=f, fill=col)
            yb = by0 - 12
        # clip to chat area
        m = Image.new("L", clip.size, 0)
        ImageDraw.Draw(m).rounded_rectangle(area, radius=22, fill=255)
        a = Image.composite(clip.getchannel("A"), Image.new("L", clip.size, 0), m)
        clip.putalpha(a)
        d._image.alpha_composite(clip)
        state.chat_content_top = yb  # for scroll clamping

    # scroll arrows
    ax = x1 - 34
    for dirn, ay in ((1, y0 + 14), (-1, y1 - 120)):
        bxx = [ax - 16, ay, ax + 16, ay + 32]
        d.ellipse(bxx, fill=t["panel2"])
        cx, cy = ax, ay + 16
        if dirn == 1:
            d.polygon([(cx - 7, cy + 4), (cx + 7, cy + 4), (cx, cy - 5)], fill=t["text"])
        else:
            d.polygon([(cx - 7, cy - 4), (cx + 7, cy - 4), (cx, cy + 5)], fill=t["text"])
        hit.add(bxx, "scroll", dirn)

    by = y1 - 54
    if state.cfg["modules"].get("ai_look", True):
        button(d, hit, [x0, by, x0 + 400, by + 54], "Type a message…", t, "type", primary=True, fsize=22)
        button(d, hit, [x0 + 410, by, x0 + 560, by + 54], "who's here?", t, "ai_look", fsize=18)
    else:
        button(d, hit, [x0, by, x0 + 560, by + 54], "Type a message…", t, "type", primary=True, fsize=22)
    button(d, hit, [x0 + 576, by, x0 + 700, by + 54], "Clear", t, "clear_chat")
    on = state.cfg["modules"]["ai_to_chatbox"]
    d.text((x0 + 726, by + 27), "to chatbox", font=font("body2", 18), fill=t["sub"], anchor="lm")
    switch(d, x1 - 70, by + 12, on, t)
    hit.add([x0 + 716, by, x1, by + 54], "toggle", "ai_to_chatbox")
    if state.ai_error:
        d.text((x0 + 10, by - 16), ellipsize(state.ai_error, font("body2", 16), x1 - x0 - 20),
               font=font("body2", 16), fill=t["bad"], anchor="ls")


def _tab_mods(d, hit, box, state, t):
    x0, y0, x1, y1 = box
    cat = state.mods_cat
    cx = x0
    labs = []
    for c in MOD_CATS:
        on_count = sum(1 for k, _, _ in MOD_INFO[c] if state.cfg["modules"].get(k))
        labs.append((c, f"{c} {on_count}/{len(MOD_INFO[c])}"))
    fs = 19
    while fs > 13 and sum(font("head", fs).getlength(l) + 28 + 8 for _, l in labs) > x1 - x0:
        fs -= 1
    for c, lab in labs:
        w = font("head", fs).getlength(lab) + 28
        button(d, hit, [cx, y0, cx + w, y0 + 44], lab, t, "mods_cat", c, active=cat == c, fsize=fs)
        cx += w + 8
    gap, ch = 12, (56 if len(MOD_INFO[cat]) <= 8 else 50)
    cw = (x1 - x0 - gap) / 2
    for i, (key, name, desc) in enumerate(MOD_INFO[cat]):
        cx = x0 + (i % 2) * (cw + gap)
        cy = y0 + 56 + (i // 2) * (ch + 6)
        on = state.cfg["modules"].get(key, False)
        panel(d, [cx, cy, cx + cw, cy + ch], 18, t)
        d.text((cx + 20, cy + (10 if ch > 52 else 7)), name, font=font("head", 20), fill=t["text"])
        d.text((cx + 20, cy + (34 if ch > 52 else 29)), ellipsize(desc, font("body2", 15), cw - 110),
               font=font("body2", 15), fill=t["sub"])
        switch(d, cx + cw - 74, cy + (14 if ch > 52 else 11), on, t)
        hit.add([cx, cy, cx + cw, cy + ch], "toggle", key)
    # small settings row for some categories
    rows_used = -(-len(MOD_INFO[cat]) // 2)
    sy = y0 + 56 + rows_used * (ch + 6) + 4
    cfg = state.cfg
    btns = []
    if cat == "Counters":
        x = state.extras
        pat = x.get("pat_param") or "auto"
        btns = [(f"pat param: {pat} ✎", "mod_edit", "headpat_param"),
                (f"boop param: {x.get('boop_param') or 'auto'} ✎", "mod_edit", "boop_param"),
                ("reset counts", "mod_reset_counts", None)]
    elif cat == "Fun":
        cd = cfg.get("countdown", {})
        btns = [(f"countdown: {cd.get('name') or 'name'} ✎", "mod_edit", "countdown_name"),
                (f"date: {cd.get('date') or 'YYYY-MM-DD'} ✎", "mod_edit", "countdown_date")]
    elif cat == "Wrist":
        kt = cfg.get("kitty", {})
        btns = [(f"kitty: {kt.get('name', 'Mochi')} ✎", "mod_edit", "kitty_name"),
                (f"fur: {kt.get('color', 'cream')}", "kitty_color", None),
                (f"trust {min(20, kt.get('trust', 0))}/20 · fed {kt.get('fed', 0)}x", "mods_cat", "Wrist")]
    elif cat == "Comfy":
        btns = [(f"bedtime: {cfg.get('bedtime', '01:00')} ✎", "mod_edit", "bedtime"),
                (f"eye break: {cfg.get('eye_break_min', 20)}m", "mod_cycle", "eye_break_min"),
                (f"posture: {cfg.get('posture_min', 30)}m", "mod_cycle", "posture_min")]
    bx = x0
    for lab, act, arg in btns:
        w = min(font("body", 16).getlength(lab) + 30, 330)
        if sy + 40 <= y1 - 24:
            button(d, hit, [bx, sy, bx + w, sy + 38], ellipsize(lab, font("body", 16), w - 20), t, act, arg, fsize=16)
        bx += w + 8
    note = state.extras.get("note_" + cat.lower())
    if note:
        d.text((x0 + 6, y1 - 8), ellipsize(note, font("body2", 16), x1 - x0 - 12),
               font=font("body2", 16), fill=t["sub"], anchor="ls")


def _swatch(d, hit, cx, cy, r, color, active, t, action, *args, label=None):
    if active:
        d.ellipse([cx - r - 5, cy - r - 5, cx + r + 5, cy + r + 5], outline=t["text"], width=3)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color, outline=t["panel2"], width=2)
    hit.add([cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4], action, *args)


def _tab_style(d, hit, box, state, t):
    x0, y0, x1, y1 = box
    cfg = state.cfg
    style = cfg.setdefault("style", {})
    # preset grid
    cols, gap = 5 if len(PRESETS) > 24 else 4, 8
    rows = -(-len(PRESETS) // cols)
    chh = 38 if rows <= 6 else 32
    cw = (x1 - x0 - gap * (cols - 1)) / cols
    for i, (key, label, *_rest) in enumerate(PRESETS):
        th = preset_preview(key)
        cx = x0 + (i % cols) * (cw + gap)
        cy = y0 + (i // cols) * (chh + 6)
        active = cfg["theme"] == key
        pill(d, [cx, cy, cx + cw, cy + chh], th["bg"][:3] + (255,),
             outline=th["primary"] if active else th["panel2"], width=3 if active else 1)
        stripe(d, cx + 14, cy + chh / 2 - 6, 26 if cols == 4 else 20, 12, th["stripe"])
        d.text((cx + (50 if cols == 4 else 42), cy + chh / 2), label, font=font("head", 16 if cols == 4 else 15),
               fill=th["text"], anchor="lm")
        if active:
            heart(d, cx + cw - 20, cy + chh / 2 + 1, 7, th["primary"])
        hit.add([cx, cy, cx + cw, cy + chh], "theme", key)

    rows_y = y0 + rows * (chh + 6) + 12
    lab_w = 128
    # accent colors
    d.text((x0, rows_y + 22), "Accent", font=font("head", 20), fill=t["text"], anchor="lm")
    sx = x0 + lab_w
    button(d, hit, [sx, rows_y + 4, sx + 74, rows_y + 40], "theme", t, "style_set", "accent", None,
           active=style.get("accent") is None, fsize=15)
    sx += 98
    for name, col in ACCENTS:
        _swatch(d, hit, sx, rows_y + 22, 16, col, style.get("accent") == list(col), t,
                "style_set", "accent", list(col))
        sx += 46
    # backgrounds
    by = rows_y + 54
    d.text((x0, by + 22), "Background", font=font("head", 20), fill=t["text"], anchor="lm")
    sx = x0 + lab_w
    button(d, hit, [sx, by + 4, sx + 74, by + 40], "theme", t, "style_set", "background", None,
           active=style.get("background") is None, fsize=15)
    sx += 98
    for name, col in BACKGROUNDS:
        _swatch(d, hit, sx, by + 22, 16, col, style.get("background") == list(col), t,
                "style_set", "background", list(col))
        sx += 46
    # stripe toggle shares the background row
    d.text((x1 - 84, by + 22), "stripe", font=font("body2", 16), fill=t["sub"], anchor="rm")
    switch(d, x1 - 70, by + 7, style.get("stripe", True), t)
    hit.add([x1 - 150, by, x1, by + 44], "style_set", "stripe", not style.get("stripe", True))
    # ears
    ey = by + 54
    d.text((x0, ey + 22), "Ears", font=font("head", 20), fill=t["text"], anchor="lm")
    sx = x0 + lab_w
    ew = (x1 - sx - 8 * (len(EAR_STYLES) - 1)) / len(EAR_STYLES)
    for e in EAR_STYLES:
        button(d, hit, [sx, ey + 2, sx + ew, ey + 42], e.capitalize(), t, "style_set", "ears", e,
               active=style.get("ears", "cat") == e, fsize=17)
        sx += ew + 8


def _tab_wrist(d, hit, box, state, t):
    x0, y0, x1, y1 = box
    w = state.cfg["wrist"]
    panel(d, [x0, y0, x0 + 420, y1], 22, t)
    d.text((x0 + 24, y0 + 22), "Which wrist?", font=font("head", 22), fill=t["text"])
    button(d, hit, [x0 + 24, y0 + 62, x0 + 194, y0 + 112], "Left", t, "hand", "left",
           active=w["hand"] == "left")
    button(d, hit, [x0 + 206, y0 + 62, x0 + 396, y0 + 112], "Right", t, "hand", "right",
           active=w["hand"] == "right")
    d.text((x0 + 24, y0 + 140), "Size", font=font("head", 22), fill=t["text"])
    d.text((x0 + 396, y0 + 140), f"{w['width_m'] * 100:.0f} cm", font=font("head", 20),
           fill=t["sub"], anchor="ra")
    button(d, hit, [x0 + 24, y0 + 176, x0 + 194, y0 + 226], "smaller", t, "size", -0.01)
    button(d, hit, [x0 + 206, y0 + 176, x0 + 396, y0 + 226], "bigger", t, "size", 0.01)
    d.text((x0 + 24, y0 + 254), "Opacity", font=font("head", 22), fill=t["text"])
    d.text((x0 + 396, y0 + 254), f"{w['opacity'] * 100:.0f}%", font=font("head", 20),
           fill=t["sub"], anchor="ra")
    button(d, hit, [x0 + 24, y0 + 290, x0 + 194, y0 + 340], "fainter", t, "opacity", -0.1)
    button(d, hit, [x0 + 206, y0 + 290, x0 + 396, y0 + 340], "solider", t, "opacity", 0.1)
    button(d, hit, [x0 + 24, y1 - 74, x0 + 396, y1 - 24], "Reset position", t, "reset_wrist")

    px = x0 + 440
    panel(d, [px, y0, x1, y1], 22, t)
    d.text((px + 24, y0 + 22), "Nudge the wrist HUD", font=font("head", 22), fill=t["text"])
    d.text((px + 24, y0 + 52), "look at your wrist while you tap these", font=font("body2", 16),
           fill=t["sub"])
    rows = [("Up / Down", ("down", "move", 1, -0.01), ("up", "move", 1, 0.01)),
            ("Hand / Elbow", ("hand", "move", 2, -0.01), ("elbow", "move", 2, 0.01)),
            ("In / Out", ("in", "move", 0, -0.01), ("out", "move", 0, 0.01)),
            ("Tilt", ("-", "rot", 0, -10), ("+", "rot", 0, 10)),
            ("Turn", ("-", "rot", 2, -10), ("+", "rot", 2, 10)),
            ("Twist", ("-", "rot", 1, -10), ("+", "rot", 1, 10))]
    for i, (lab, a, b) in enumerate(rows):
        ry = y0 + 92 + i * 60
        d.text((px + 24, ry + 24), lab, font=font("body", 19), fill=t["text"], anchor="lm")
        button(d, hit, [x1 - 234, ry, x1 - 134, ry + 48], a[0], t, a[1], *a[2:], fsize=18)
        button(d, hit, [x1 - 124, ry, x1 - 24, ry + 48], b[0], t, b[1], *b[2:], fsize=18)


def _tab_screen(d, hit, box, state, t):
    x0, y0, x1, y1 = box
    sc = state.cfg["screen"]
    info = state.screen_info
    gap = 16
    half = (x1 - x0 - gap) / 2
    top_h = 118
    # left card: desktop on/off
    panel(d, [x0, y0, x0 + half, y0 + top_h], 22, t)
    d.text((x0 + 24, y0 + 20), "Desktop in VR", font=font("title", 28), fill=t["text"])
    d.text((x0 + 24, y0 + 60), "ur PC screen floating", font=font("body2", 16), fill=t["sub"])
    d.text((x0 + 24, y0 + 82), "in front of you", font=font("body2", 16), fill=t["sub"])
    switch(d, x0 + half - 110, y0 + 38, sc["enabled"], t, scale=1.4)
    hit.add([x0, y0, x0 + half, y0 + top_h], "screen_toggle")
    # right card: zoom lens
    zx = x0 + half + gap
    z = state.cfg.get("zoom", {})
    panel(d, [zx, y0, x1, y0 + top_h], 22, t)
    d.text((zx + 24, y0 + 14), "Zoom lens", font=font("title", 26), fill=t["text"])
    gest = z.get("mode", "gesture") == "gesture"
    mw = 128
    button(d, hit, [x1 - 24 - 2 * mw - 6, y0 + 12, x1 - 24 - mw - 6, y0 + 46], "hold to eye", t,
           "zoom_set", "mode", "gesture", active=gest, fsize=15)
    button(d, hit, [x1 - 24 - mw, y0 + 12, x1 - 24, y0 + 46],
           ("on" if z.get("enabled") and not gest else "tap on/off"), t,
           "zoom_toggle", active=not gest and bool(z.get("enabled")), fsize=15)
    lv = [2, 3, 4, 6]
    bw = (x1 - zx - 48 - 8 * (len(lv) - 1)) / len(lv)
    for i, v in enumerate(lv):
        bx = zx + 24 + i * (bw + 8)
        button(d, hit, [bx, y0 + 56, bx + bw, y0 + 92], f"{v}x", t, "zoom_set", "level", v,
               active=z.get("level", 3) == v, fsize=17)
    d.text(((zx + x1) / 2, y0 + 106), "in game: hold a controller up to ur eye like a telescope" if gest
           else "in game: tap the 🔍 on ur wrist", font=font("body2", 14), fill=t["sub"], anchor="mm")

    ly = y0 + top_h + 14
    # left: where + which monitor
    panel(d, [x0, ly, x0 + half, y1], 22, t)
    d.text((x0 + 24, ly + 18), "Monitor", font=font("head", 22), fill=t["text"])
    n = max(1, info.get("monitors", 1))
    bx = x0 + 24
    for i in range(1, min(n, 4) + 1):
        button(d, hit, [bx, ly + 56, bx + 84, ly + 104], str(i), t, "screen_set", "monitor", i,
               active=sc["monitor"] == i)
        bx += 94
    d.text((x0 + 24, ly + 128), "Placement", font=font("head", 22), fill=t["text"])
    w2 = (half - 48 - 10) / 2
    button(d, hit, [x0 + 24, ly + 166, x0 + 24 + w2, ly + 214], "Floating", t,
           "screen_set", "attach", "world", active=sc["attach"] == "world")
    button(d, hit, [x0 + 34 + w2, ly + 166, x0 + half - 24, ly + 214], "Other hand", t,
           "screen_set", "attach", "hand", active=sc["attach"] == "hand")
    button(d, hit, [x0 + 24, y1 - 72, x0 + half - 24, y1 - 22], "Bring it in front of me", t,
           "screen_here", primary=True)

    # right: size + smoothness
    rx = x0 + half + gap
    panel(d, [rx, ly, x1, y1], 22, t)
    d.text((rx + 24, ly + 18), "Size", font=font("head", 22), fill=t["text"])
    d.text((x1 - 24, ly + 18), f"{sc['width_m'] * 100:.0f} cm wide", font=font("head", 20),
           fill=t["sub"], anchor="ra")
    w3 = (x1 - rx - 48 - 10) / 2
    button(d, hit, [rx + 24, ly + 56, rx + 24 + w3, ly + 104], "smaller", t, "screen_size", -0.2)
    button(d, hit, [rx + 34 + w3, ly + 56, x1 - 24, ly + 104], "bigger", t, "screen_size", 0.2)
    d.text((rx + 24, ly + 128), "Smoothness", font=font("head", 22), fill=t["text"])
    d.text((x1 - 24, ly + 130), "lower = more VRChat FPS", font=font("body2", 15),
           fill=t["sub"], anchor="ra")
    opts = [(10, "10 fps"), (15, "15 fps"), (30, "30 fps")]
    w4 = (x1 - rx - 48 - 20) / 3
    for i, (v, lab) in enumerate(opts):
        bx = rx + 24 + i * (w4 + 10)
        button(d, hit, [bx, ly + 166, bx + w4, ly + 214], lab, t, "screen_set", "fps", v,
               active=sc["fps"] == v, fsize=18)
    note = info.get("error") or "view only for now - use your mouse/keyboard as normal"
    d.text((rx + 24, y1 - 46), ellipsize(note, font("body2", 16), x1 - rx - 48),
           font=font("body2", 16), fill=t["bad"] if info.get("error") else t["sub"], anchor="lm")
