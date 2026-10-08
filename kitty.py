"""
Lil Kitty: a fluffy cat that lives on ur OTHER wrist (or on ur desktop in desktop mode).

- she's shy at first: pat her 20 times to make friends (a lock + progress bar show until then)
- once she trusts u, u can FEED her (feed button). she gets hungry over a few hours
- pat her head -> she mews + purrs + hearts float up
- boop her nose -> "mrrp!" sneeze
- poke her tail -> she swishes it and gets a lil grumpy
- leave her alone a while -> she naps (zzz)
She's drawn as line-art PNG sprites in assets/kitty/ (made by tools/make_kitty_art.py).
Everything she remembers is saved in config.json -> "kitty".
"""
import math
import os
import random
import sys
import time
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFont
from lang import ImageDraw, tr as _tr  # translates drawn text (Settings -> Language)

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "assets", "kitty")
SIZE = 400                       # texture is SIZE x SIZE
TRUST_NEEDED = 20
HUNGER_HOURS = 4.0               # full -> starving in this long
TAIL_PIVOT = (224, 248)

DEFAULT = {"name": "Mochi", "trust": 0, "unlocked": False, "pats": 0, "boops": 0, "fed": 0,
           "last_fed": 0.0, "color": "white", "style": "custom"}

COLORS = {   # fur tint for the white line art
    "white": (255, 255, 255),
    "cream": (255, 240, 220),
    "pink": (255, 222, 236),
    "grey": (214, 216, 228),
    "ginger": (255, 208, 160),
    "lilac": (228, 214, 255),
    "mint": (214, 246, 228),
}

# where things are on her sprite (image px)
HEAD_BOX = (120, 48, 280, 142)
NOSE_BOX = (184, 138, 216, 164)
TAIL_BOX = (234, 206, 352, 296)
BODY_BOX = (160, 164, 240, 334)

LINES = {
    "pat": ["mew~", "mrrrow <3", "purrrr", "nya~", "more pls", "*happy loaf*"],
    "shy": ["...mew?", "*sniff sniff*", "u seem nice", "*peeks*", "mrrp..."],
    "boop": ["mrrp!", "*sneeze*", "hey!! :<", "boop back"],
    "tail": ["MROW?!", "not the tail!!", "hss... jk", "*swish swish*"],
    "fed": ["nom nom nom", "fishies!!", "*crunch crunch*", "best human ever"],
    "hungry": ["feed me!!", "*stares at u*", "mew mew MEW", "tummy rumbly"],
}


@lru_cache(maxsize=16)
def _font(size):
    for n in ("Fredoka-Bold.ttf", "Nunito-Bold.ttf"):
        p = os.path.join(HERE, "fonts", n)
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


CUSTOM = os.path.join(ART, "custom")


@lru_cache(maxsize=4)
def custom_frames():
    """ur own kitty: every frame_XX.png in assets/kitty/custom (an animated GIF there works too)."""
    if not os.path.isdir(CUSTOM):
        return ()
    names = sorted(n for n in os.listdir(CUSTOM) if n.lower().startswith("frame_") and n.lower().endswith(".png"))
    frames = []
    for n in names:
        try:
            frames.append(Image.open(os.path.join(CUSTOM, n)).convert("RGBA"))
        except Exception:
            pass
    if not frames:
        for n in sorted(os.listdir(CUSTOM)):
            if n.lower().endswith((".gif", ".png", ".webp")):
                try:
                    from PIL import ImageSequence
                    frames = [f.convert("RGBA") for f in ImageSequence.Iterator(Image.open(os.path.join(CUSTOM, n)))]
                    break
                except Exception:
                    pass
    return tuple(frames)


@lru_cache(maxsize=8)
def _fit(i, w, h):
    return custom_frames()[i].resize((w, h), Image.LANCZOS)


@lru_cache(maxsize=64)
def sprite(name, color="white"):
    """assets/kitty/<name>.png tinted to her fur color (lines stay dark)."""
    path = os.path.join(ART, name + ".png")
    if not os.path.exists(path):
        try:
            import subprocess
            subprocess.run([sys.executable, os.path.join(HERE, "tools", "make_kitty_art.py")], timeout=60)
        except Exception:
            pass
    try:
        img = Image.open(path).convert("RGBA")
    except Exception:
        return Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    tint = COLORS.get(color, COLORS["white"])
    if tint != (255, 255, 255):
        r, g, b, a = img.split()
        rgb = ImageChops.multiply(Image.merge("RGB", (r, g, b)), Image.new("RGB", img.size, tint))
        img = Image.merge("RGBA", (*rgb.split(), a))
    return img


def _heart(d, x, y, r, fill=None, outline=None, width=3):
    pts = []
    for i in range(40):
        t = i / 40 * math.tau
        hx = 16 * math.sin(t) ** 3
        hy = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((x + hx * r / 16, y + hy * r / 16))
    d.polygon(pts, fill=fill)
    if outline:
        d.line(pts + [pts[0]], fill=outline, width=width, joint="curve")


class Kitty:
    def __init__(self, cfg):
        self.cfg = cfg
        k = cfg.setdefault("kitty", {})
        for key, v in DEFAULT.items():
            k.setdefault(key, v)
        if k.get("color") not in COLORS:
            k["color"] = "white"
        if not k["last_fed"]:
            k["last_fed"] = time.time()
        self.k = k
        self.mood, self.mood_until = "idle", 0.0
        self.say, self.say_until = "", 0.0
        self.hearts = []            # (x, y, t0)
        self.last_touch = time.time()
        self.last_hungry_mew = 0.0
        self.tail_kick = 0.0
        self.changed = True
        self.hits = []              # [(x0, y0, x1, y1), action] in image px
        self.sound = None           # name of a sound to play (main loop picks it up)
        self.outfit = ("none", "none")  # (hat, collar) from the Fun tab closet (fun.py)

    # ---- state
    def hunger(self, now=None):
        now = time.time() if now is None else now
        return max(0.0, min(1.0, (now - self.k["last_fed"]) / (HUNGER_HOURS * 3600)))

    def _set(self, mood, secs, line_key=None, sound=None):
        now = time.time()
        self.mood, self.mood_until = mood, now + secs
        if line_key:
            self.say, self.say_until = random.choice(LINES[line_key]), now + 2.5
        if sound:
            self.sound = sound
        self.last_touch = now
        self.changed = True

    def act(self, action):
        """action: pat / boop / tail / feed. Returns an alert string or None."""
        now = time.time()
        k = self.k
        if action == "pat":
            k["pats"] += 1
            self.hearts.append((SIZE * random.choice((0.74, 0.8, 0.86)), SIZE * (0.4 + random.random() * 0.08), now))
            del self.hearts[:-8]
            if not k["unlocked"]:
                k["trust"] = min(TRUST_NEEDED, k["trust"] + 1)
                if k["trust"] >= TRUST_NEEDED:
                    k["unlocked"] = True
                    self._set("love", 4, "pat", "meow")
                    self.say, self.say_until = "i trust u now!! <3", now + 4
                    return k['name'] + " " + _tr("trusts u now!! u can feed her :3")
                self._set("shy", 1.6, "shy", "meow")
            else:
                self._set("happy", 2.2, "pat", random.choice(["meow", "meow", "purr"]))
        elif action == "boop":
            k["boops"] += 1
            self._set("boop", 1.2, "boop", "mrrp")
        elif action == "tail":
            self.tail_kick = now
            self._set("grumpy", 1.5, "tail", "mrrp")
        elif action == "feed":
            if not k["unlocked"]:
                self.say, self.say_until = _tr("too shy... pat her") + f" ({k['trust']}/{TRUST_NEEDED})", now + 3
                self.changed = True
                return None
            k["fed"] += 1
            k["last_fed"] = now
            self._set("eat", 3.0, "fed", "nom")
        return None

    def tick(self, now=None):
        """Call often. Returns True when she needs a redraw."""
        now = time.time() if now is None else now
        if self.mood != "idle" and now > self.mood_until:
            self.mood = "idle"
            self.changed = True
        if self.k["unlocked"] and self.hunger(now) > 0.7 and now - self.last_hungry_mew > 600:
            self.last_hungry_mew = now
            self.say, self.say_until = random.choice(LINES["hungry"]), now + 4
            self.sound = "meow"
            self.changed = True
        self.hearts = [h for h in self.hearts if now - h[2] < 1.4]
        # fast redraws while something's happening, slow ones (breathing + blinking) otherwise
        self.fast = bool(self.hearts) or now < self.say_until or self.mood != "idle" or now - self.tail_kick < 1.5
        self.changed = True
        return self.changed

    def face(self, now):
        if self.mood == "shy":
            return "shy"
        if self.mood != "idle":
            return self.mood
        if self.k["unlocked"] and self.hunger(now) > 0.7:
            return "hungry"
        if now - self.last_touch > 180:
            return "sleepy"
        if (now % 4.2) < 0.14:
            return "blink"
        return "idle" if self.k["unlocked"] else "shy"

    # ---- drawing
    def render(self, theme=None, now=None):
        now = time.time() if now is None else now
        self.changed = False
        if custom_frames() and self.k.get("style", "custom") == "custom":
            return self.render_custom(theme, now)
        return self.render_lineart(theme, now)

    def render_custom(self, theme, now):
        """ur own kitty picture (animated), on a soft white card"""
        S = SIZE
        frames = custom_frames()
        face = self.face(now)
        img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        ink = (58, 52, 66)
        accent = tuple(theme["primary"][:3]) if theme else (255, 143, 199)
        paper = (254, 252, 254)
        d.rounded_rectangle([6, 6, S - 6, S - 6], 46, fill=paper + (255,), outline=accent + (255,), width=5)
        # pick the frame: wags faster when happy, slow + still-ish when sleepy
        speed = {"happy": 0.06, "love": 0.05, "eat": 0.07, "grumpy": 0.04, "sleepy": 0.35}.get(face, 0.1)
        i = 0 if face == "blink" else int(now / speed) % len(frames)
        fw, fh = frames[0].size
        box_h = 286
        sc = box_h / fh
        w, h = int(fw * sc), box_h
        # lil squish when patted / booped
        squish = 0.0
        if self.mood in ("happy", "shy", "love", "boop") and self.mood_until - now > 0:
            squish = max(0.0, math.sin((now % 0.5) / 0.5 * math.pi)) * 0.04
        hh = int(h * (1 - squish))
        pic = _fit(i, w, h) if not squish else _fit(i, w, h).resize((w, hh), Image.LANCZOS)
        ox, oy = (S - w) // 2, 48 + (h - hh)
        img.alpha_composite(pic, (ox, oy))
        X = lambda x: ox + x * sc
        Y = lambda y: 48 + y * sc
        self._wear(img, X(108), Y(30) + (h - hh), 110 * sc, Y(106) + (h - hh))
        d = ImageDraw.Draw(img)
        hits = [((X(110 - 26), Y(70), X(110 + 26), Y(100)), "boop"),
                ((X(40), Y(10), X(180), Y(108)), "pat"),
                ((X(75), Y(100), X(150), Y(290)), "pat"),
                ((X(0), Y(150), X(75), Y(290)), "tail"),
                ((X(150), Y(150), X(fw), Y(290)), "tail")]
        if face == "eat":
            d.ellipse([150, 330, 250, 356], fill=(170, 210, 255), outline=ink, width=3)
            d.ellipse([176, 322, 214, 338], fill=(255, 180, 130), outline=ink, width=2)
        if face == "sleepy":
            f = _font(28)
            for k in range(3):
                ph = (now * 0.5 + k / 3) % 1
                d.text((270 + ph * 34, 100 - ph * 60), "z", font=f, fill=ink + (int(255 * (1 - ph)),))
        for (x, y, t0) in self.hearts:
            k = (now - t0) / 1.4
            a = int(255 * (1 - k))
            _heart(d, x, y - k * 80, 12 + 6 * k, fill=(255, 150, 190, a), outline=(255, 90, 150, a), width=3)
        self._ui(d, img, now, hits, ink, accent, ink)
        return img

    def _wear(self, img, cx, top, w, neck_y):
        hat, neck = self.outfit or ("none", "none")
        if hat == "none" and neck == "none":
            return
        try:
            import fun
            fun.draw_outfit(img, hat, neck, cx, top, w, neck_y)
        except Exception:
            pass

    def _ui(self, d, img, now, hits, ink, accent, txt):
        """name, tummy / trust bar, feed button (cached, text is slow to draw) + speech bubble"""
        S = SIZE
        hg = round(self.hunger(now), 2)
        import lang
        key = (self.k["name"], self.k["unlocked"], self.k["trust"], hg, ink, accent, txt, lang.current(),
               bool(custom_frames()) and self.k.get("style", "custom") == "custom")
        if getattr(self, "_ui_key", None) != key:
            layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
            self._ui_hits = self._ui_static(ImageDraw.Draw(layer), now, ink, accent, txt, key[-1])
            self._ui_layer, self._ui_key = layer, key
        img.alpha_composite(self._ui_layer)
        hits[:0] = self._ui_hits
        if now < self.say_until and self.say:
            fs = 20
            while fs > 12 and d.textlength(self.say, font=_font(fs)) > 140:
                fs -= 1
            f3 = _font(fs)
            w = d.textlength(self.say, font=f3) + 24
            bx, by = 16, 184
            bub = (255, 236, 246, 250)
            d.rounded_rectangle([bx, by, bx + w, by + 36], 16, fill=bub, outline=ink, width=2)
            d.text((bx + w / 2, by + 18), self.say, font=f3, fill=ink, anchor="mm")
        self.hits = hits

    def _ui_static(self, d, now, ink, accent, txt, credit):
        S = SIZE
        hits = []
        if credit:      # artist credit (used with permission)
            d.text((S - 22, 70), "art: anon artist <3", font=_font(11), fill=(150, 140, 160), anchor="ra")
        d.text((24, 18), self.k["name"], font=_font(22), fill=txt)
        if self.k["unlocked"]:
            hg = self.hunger(now)
            bw = 110
            d.rounded_rectangle([S - 24 - bw, 22, S - 24, 40], 9, fill=(60, 48, 72))
            fill = (1 - hg) * (bw - 4)
            col = (123, 224, 181) if hg < 0.5 else (255, 200, 90) if hg < 0.75 else (255, 110, 120)
            if fill > 2:
                d.rounded_rectangle([S - 22 - bw, 24, S - 22 - bw + fill, 38], 7, fill=col)
            d.text((S - 24 - bw, 46), "tummy", font=_font(14), fill=txt, anchor="lt")
            fb = (S - 118, S - 62, S - 22, S - 20)
            d.rounded_rectangle(fb, 20, fill=accent, outline=ink, width=2)
            d.text(((fb[0] + fb[2]) / 2, (fb[1] + fb[3]) / 2), "feed", font=_font(22), fill=(30, 20, 40), anchor="mm")
            hits.append((fb, "feed"))
        else:
            lx, ly = S - 54, 42
            d.rounded_rectangle([lx - 16, ly - 4, lx + 16, ly + 22], 5, fill=(255, 210, 90), outline=ink, width=2)
            d.arc([lx - 11, ly - 20, lx + 11, ly + 4], 180, 360, fill=ink, width=4)
            tr = self.k["trust"]
            d.text((S / 2, S - 44), _tr("pat me to make friends!") + f" {tr}/{TRUST_NEEDED}", font=_font(17), fill=txt, anchor="mm")
            bw2 = S - 80
            d.rounded_rectangle([40, S - 30, 40 + bw2, S - 17], 7, fill=(60, 48, 72))
            if tr:
                d.rounded_rectangle([42, S - 28, 42 + (bw2 - 4) * tr / TRUST_NEEDED, S - 19], 5, fill=accent)
        return hits

    def render_lineart(self, theme=None, now=None):
        now = time.time() if now is None else now
        S = SIZE
        img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        ink = (58, 52, 66)
        accent = tuple(theme["primary"][:3]) if theme else (255, 143, 199)
        panel = tuple(theme["panel"][:3]) if theme else (46, 32, 61)
        txt = tuple(theme["text"][:3]) if theme else (246, 238, 252)
        face = self.face(now)
        color = self.k.get("color", "white")
        # soft round card behind her
        d.rounded_rectangle([6, 6, S - 6, S - 6], 46, fill=panel + (235,), outline=accent + (255,), width=4)
        # tail (swishes, faster when poked)
        kick = max(0.0, 1.5 - (now - self.tail_kick))
        ang = math.sin(now * (1.6 + 9 * kick)) * (6 + 14 * kick)
        tail = sprite("tail", color).rotate(ang, resample=Image.BICUBIC, center=TAIL_PIVOT)
        img.alpha_composite(tail)
        # body (gentle breathing bob)
        bob = int(round(math.sin(now * (1.0 if face == "sleepy" else 2.0)) * 2))
        img.alpha_composite(sprite("body_" + face, color), (0, bob))
        self._wear(img, 200, 48 + bob, 160, 160 + bob)
        d = ImageDraw.Draw(img)
        # food bowl when eating
        if face == "eat":
            d.ellipse([150, 316, 250, 346], fill=(170, 210, 255), outline=ink, width=3)
            d.ellipse([176, 308, 214, 324], fill=(255, 180, 130), outline=ink, width=2)
            d.polygon([(212, 316), (226, 306), (226, 326)], fill=(255, 180, 130), outline=ink)
        # zzz
        if face == "sleepy":
            f = _font(28)
            for i in range(3):
                ph = (now * 0.5 + i / 3) % 1
                d.text((262 + ph * 34, 96 - ph * 60), "z", font=f, fill=txt + (int(255 * (1 - ph)),))
        # hearts (line-art style, float up)
        for (x, y, t0) in self.hearts:
            k = (now - t0) / 1.4
            a = int(255 * (1 - k))
            _heart(d, x, y - k * 80, 12 + 6 * k, fill=(255, 150, 190, a), outline=(255, 90, 150, a), width=3)
        # name + needs
        d.text((24, 18), self.k["name"], font=_font(22), fill=txt)
        hits = [(HEAD_BOX, "pat"), (NOSE_BOX, "boop"), (TAIL_BOX, "tail"), (BODY_BOX, "pat")]
        if self.k["unlocked"]:
            hg = self.hunger(now)
            bw = 110
            d.rounded_rectangle([S - 24 - bw, 22, S - 24, 40], 9, fill=(30, 20, 40))
            fill = (1 - hg) * (bw - 4)
            col = (123, 224, 181) if hg < 0.5 else (255, 200, 90) if hg < 0.75 else (255, 110, 120)
            if fill > 2:
                d.rounded_rectangle([S - 22 - bw, 24, S - 22 - bw + fill, 38], 7, fill=col)
            d.text((S - 24 - bw, 46), "tummy", font=_font(14), fill=txt, anchor="lt")
            fb = (S - 118, S - 62, S - 22, S - 20)
            d.rounded_rectangle(fb, 20, fill=accent, outline=ink, width=2)
            d.text(((fb[0] + fb[2]) / 2, (fb[1] + fb[3]) / 2), "feed", font=_font(22), fill=(30, 20, 40), anchor="mm")
            hits.append((fb, "feed"))
        else:
            # lock + trust bar
            lx, ly = S - 54, 42
            d.rounded_rectangle([lx - 16, ly - 4, lx + 16, ly + 22], 5, fill=(255, 210, 90), outline=ink, width=2)
            d.arc([lx - 11, ly - 20, lx + 11, ly + 4], 180, 360, fill=ink, width=4)
            tr = self.k["trust"]
            d.text((S / 2, S - 48), _tr("pat me to make friends!") + f" {tr}/{TRUST_NEEDED}", font=_font(18), fill=txt, anchor="mm")
            bw2 = S - 80
            d.rounded_rectangle([40, S - 32, 40 + bw2, S - 18], 7, fill=(30, 20, 40))
            if tr:
                d.rounded_rectangle([42, S - 30, 42 + (bw2 - 4) * tr / TRUST_NEEDED, S - 20], 5, fill=accent)
        # speech bubble
        if now < self.say_until and self.say:
            fs = 20
            while fs > 12 and d.textlength(self.say, font=_font(fs)) > 140:
                fs -= 1
            f3 = _font(fs)
            w = d.textlength(self.say, font=f3) + 24
            bx, by = 16, 184
            d.rounded_rectangle([bx, by, bx + w, by + 36], 16, fill=(255, 255, 255, 245), outline=ink, width=2)
            d.polygon([(bx + w - 4, by + 12), (bx + w + 12, by + 20), (bx + w - 4, by + 26)], fill=(255, 255, 255, 245), outline=ink)
            d.rectangle([bx + w - 6, by + 13, bx + w - 2, by + 25], fill=(255, 255, 255, 245))
            d.text((bx + w / 2, by + 18), self.say, font=f3, fill=ink, anchor="mm")
        self.hits = hits
        return img

    def hit(self, x, y):
        """image px -> action (feed first, then nose, head, tail, body)"""
        order = {"feed": 0, "boop": 1, "pat": 2, "tail": 3}
        for (x0, y0, x1, y1), a in sorted(self.hits, key=lambda h: order[h[1]]):
            if x0 <= x <= x1 and y0 <= y <= y1:
                return a
        return None


def play(name):
    """meow / purr / mrrp / nom (async, Windows only - silent elsewhere)"""
    if sys.platform != "win32" or not name:
        return
    files = {"meow": ["meow1.wav", "meow2.wav", "meow3.wav"], "purr": ["purr.wav"], "mrrp": ["mrrp.wav"], "nom": ["nom.wav"]}
    path = os.path.join(HERE, "assets", random.choice(files.get(name, ["meow1.wav"])))
    if not os.path.exists(path):
        return
    try:
        import winsound
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except Exception:
        pass
