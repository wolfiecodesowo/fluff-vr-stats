"""Turns assets/logo.gif into die-cut sticker frames (white border + lineart outline).
Swap in any gif/png with a plain light background and it just works."""
import os
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(HERE, "assets", "logo.gif")
ERROR_ART = os.path.join(HERE, "assets", "error.gif")
THANKS_ART = os.path.join(HERE, "assets", "thanks.gif")

# "cutout" = die-cut around the drawing (needs closed outlines)
# "card"   = whole picture on a rounded sticker card (for art whose lines run off the edge)
# Overridable from config.json -> "sticker_styles"
STYLES = {"logo.gif": "cutout", "error.gif": "card", "thanks.gif": "cutout"}


def _silhouette(frames, bg_tol=24, grow=7):
    """Union of everything that isn't background, dilated and hole-filled = sticker shape."""
    w, h = frames[0].size
    ink = Image.new("L", (w, h), 0)
    for f in frames:
        rgb = f.convert("RGB")
        bgc = rgb.getpixel((0, 0))
        diff = ImageChops.difference(rgb, Image.new("RGB", (w, h), bgc)).convert("L")
        ink = ImageChops.lighter(ink, diff.point(lambda v: 255 if v > bg_tol else 0))
    pad = grow * 3
    big = Image.new("L", (w + pad * 2, h + pad * 2), 0)
    big.paste(ink, (pad, pad))
    big = big.filter(ImageFilter.MaxFilter(grow * 2 + 1))
    # fill holes: flood the outside, everything else is inside
    outside = big.copy()
    ImageDraw.floodfill(outside, (0, 0), 128)
    sil = outside.point(lambda v: 0 if v == 128 else 255)
    sil = sil.filter(ImageFilter.GaussianBlur(2)).point(lambda v: 255 if v > 110 else 0)
    return sil, pad


@lru_cache(maxsize=12)
def sticker_frames(height, path=LOGO, line=(40, 30, 58), border=(255, 255, 255)):
    """Returns ([RGBA frames], duration_ms) scaled so each frame is `height` px tall.
    Never raises: a missing/broken image just gives an empty list."""
    try:
        return _sticker_frames(height, path, line, border)
    except Exception:
        return [], 100


def _card_frames(frames, line, border):
    """Whole picture on a rounded die-cut card (keeps every pixel of the art)."""
    w, h = frames[0].size
    pad, ol = max(8, w // 22), max(4, w // 45)
    W, H = w + pad * 2 + ol * 2, h + pad * 2 + ol * 2
    r = int(min(W, H) * 0.2)
    shape = Image.new("L", (W * 2, H * 2), 0)
    ImageDraw.Draw(shape).rounded_rectangle([0, 0, W * 2 - 1, H * 2 - 1], radius=r * 2, fill=255)
    shape = shape.resize((W, H), Image.LANCZOS)
    inner = Image.new("L", (W * 2, H * 2), 0)
    ImageDraw.Draw(inner).rounded_rectangle([ol * 2, ol * 2, (W - ol) * 2 - 1, (H - ol) * 2 - 1],
                                            radius=(r - ol) * 2, fill=255)
    inner = inner.resize((W, H), Image.LANCZOS)
    art_mask = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(art_mask).rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1],
                                               radius=max(4, r - ol - pad // 2) * 2, fill=255)
    art_mask = art_mask.resize((w, h), Image.LANCZOS)
    out = []
    for f in frames:
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        img.paste(Image.new("RGBA", (W, H), line + (255,)), (0, 0), shape)
        img.paste(Image.new("RGBA", (W, H), border + (255,)), (0, 0), inner)
        img.paste(f, (pad + ol, pad + ol), art_mask)
        out.append(img)
    return out


def _sticker_frames(height, path, line, border):
    if not os.path.exists(path):
        return [], 100
    src = Image.open(path)
    frames, durs = [], []
    for i in range(getattr(src, "n_frames", 1)):
        src.seek(i)
        frames.append(src.convert("RGBA"))
        durs.append(src.info.get("duration", 100) or 100)
    if STYLES.get(os.path.basename(path), "cutout") == "card":
        out = _card_frames(frames, line, border)
        scale = height / out[0].height
        out = [o.resize((max(1, round(o.width * scale)), height), Image.LANCZOS) for o in out]
        return out, max(60, sum(durs) // len(durs))
    # each frame gets its own sticker shape so the tail wag isn't boxed in
    grow = max(7, round(max(frames[0].size) / 32))
    sils = [_silhouette([f], grow=grow) for f in frames]
    pad = sils[0][1]
    ow = 7 if max(frames[0].size) < 300 else 11
    outlines = [s.filter(ImageFilter.MaxFilter(ow)) for s, _ in sils]
    union = outlines[0]
    for o in outlines[1:]:
        union = ImageChops.lighter(union, o)
    bbox = union.getbbox()
    out = []
    for f, (sil, _), outline in zip(frames, sils, outlines):
        W, H = sil.size
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        img.paste(Image.new("RGBA", (W, H), line + (255,)), (0, 0), outline)
        img.paste(Image.new("RGBA", (W, H), border + (255,)), (0, 0), sil)
        art = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        art.paste(f, (pad, pad))
        img.paste(art, (0, 0), sil)          # art only inside the sticker shape
        img = img.crop(bbox)
        scale = height / img.height
        out.append(img.resize((max(1, round(img.width * scale)), height), Image.LANCZOS))
    return out, max(60, sum(durs) // len(durs))
