"""Renders a vertical (9:16) promo trailer straight from the app's real UI code.
Usage: python tools/make_trailer.py out.mp4 music.wav"""
import math
import os
import random
import subprocess
import sys
import time as _time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

import intro  # noqa: E402
import logo  # noqa: E402
import ui  # noqa: E402
from main import State, load_cfg  # noqa: E402
from themes import theme_key, mix  # noqa: E402

W, H, FPS = 1080, 1920, 30
TOTAL = 32.5
FAKE_NOW = _time.mktime((2026, 10, 6, 21, 12, 0, 0, 0, -1))   # a cozy 9:12 PM VRChat night

# ------------------------------------------------------------ fake world ---
random.seed(7)
cfg = load_cfg()
cfg["theme"] = "pride_pastel"
cfg["style"] = {"accent": None, "background": None, "ears": "cat", "stripe": True}
for k in cfg["modules"]:
    cfg["modules"][k] = k not in ("weather", "break_reminder", "ping", "headpat_counter")
cfg["modules"]["chatbox_status"] = True
cfg["chatbox"]["style"] = "simple"          # emoji fonts differ per PC; keep the video clean
cfg["chatbox"]["lines"].update(fps=True, session=True)
st = State(cfg)
art = Image.new("RGBA", (300, 300), (40, 20, 70, 255))
ad = ImageDraw.Draw(art)
for i in range(14):
    ad.ellipse([10 + i * 10, 10 + i * 10, 290 - i * 10, 290 - i * 10],
               fill=(255 - i * 9, 120 + i * 8, 170 + i * 5, 255))
ui.paw(ad, 150, 160, 40, (255, 255, 255, 230))
MUSIC = {"title": "Pawsitive Vibes", "artist": "DJ Floof", "album": "Midnight Zoomies", "app": "Spotify",
         "playing": True, "pos": 64, "dur": 201, "art": art, "backend": "windows"}
st.music = dict(MUSIC)
st.extras = {"session_start": FAKE_NOW - 4980, "headpats": 12, "muted": False, "song": "Pawsitive Vibes - DJ Floof"}
st.screen_info = {"monitors": 1}
FT = [9.2 + random.random() * 1.4 for _ in range(60)]

ui_time = ui.time
_real_time = _time.time


class _FakeClock:
    """ui.py reads the clock for the HUD; pin it so the video shows an evening VRChat session."""
    def __init__(self):
        self.t = FAKE_NOW

    def time(self):
        return self.t

    def localtime(self, *a):
        return _time.localtime(self.t if not a else a[0])

    def strftime(self, fmt, tt=None):
        return _time.strftime(fmt, tt if tt is not None else _time.localtime(self.t))

    def __getattr__(self, k):
        return getattr(_time, k)


CLOCK = _FakeClock()
ui.time = CLOCK
import chatbox as _cbx  # noqa: E402
_cbx.time = CLOCK


def tick_stats(t):
    FT.append(9.0 + 1.2 * math.sin(t * 3.1) + random.random() * 1.1 + (4 if random.random() < 0.02 else 0))
    del FT[:-60]
    fps = 88 + 1.6 * math.sin(t * 1.7)
    st.stats = {"fps": fps, "refresh": 90, "gpu_ms": 9.6 + math.sin(t) * 0.6, "cpu_ms": 6.2 + math.cos(t) * 0.4,
                "reproj_pct": 2 + abs(math.sin(t * 0.7)) * 2, "vr_ok": True, "frametimes": list(FT),
                "batteries": [("HMD", 84, False), ("L", 66, False), ("R", 71, False), ("T1", 93, True)],
                "cpu_pct": 34 + 6 * math.sin(t * 0.9), "ram_pct": 58, "gpu_pct": 86 + 5 * math.sin(t * 1.3),
                "gpu_temp": 70, "vram_used": 6.1, "vram_total": 12}
    st.music["pos"] = MUSIC["pos"] + t
    CLOCK.t = FAKE_NOW + t


# ------------------------------------------------------------- helpers ---
def ease_out_back(x, s=1.7):
    x = min(max(x, 0.0), 1.0) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def paste_center(canvas, img, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    if scale != 1.0:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BICUBIC)
    if rot:
        img = img.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1.0:
        img = img.copy()
        img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
    x, y = int(cx - img.width / 2), int(cy - img.height / 2)
    intro._paste(canvas, img, x, y)


def caption(canvas, lines, t_local, y=250, size=96, color=None, accent_idx=None):
    """Big hand-lettered caption that pops in word block by word block."""
    th = ui.get_theme(cfg)
    d = ImageDraw.Draw(canvas)
    f = ui.font("title", size)
    for i, ln in enumerate(lines):
        k = ease_out_back((t_local - i * 0.18) / 0.35)
        if k <= 0.01:
            continue
        col = th["primary"] if accent_idx == i else (color or (255, 255, 255))
        lay = Image.new("RGBA", (W, size + 60), (0, 0, 0, 0))
        ImageDraw.Draw(lay).text((W / 2, (size + 60) / 2), ln, font=f, fill=col, anchor="mm",
                                 stroke_width=max(5, size // 14), stroke_fill=(36, 24, 52))
        paste_center(canvas, lay, W / 2, y + i * (size + 8), scale=0.6 + 0.4 * k, alpha=min(1, k * 1.3))


# ---------------------------------------------------------- background ---
def make_bg():
    bg = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(bg)
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=(int(30 + 30 * k), int(18 + 14 * k), int(48 + 30 * k)))
    blobs = Image.new("RGBA", (W // 4, H // 4), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blobs)
    for cx, cy, r, c in ((60, 90, 90, (255, 140, 200, 70)), (230, 300, 110, (140, 190, 255, 60)),
                         (120, 430, 100, (190, 150, 255, 60))):
        bd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
    blobs = blobs.filter(ImageFilter.GaussianBlur(28)).resize((W, H), Image.BICUBIC)
    bg = bg.convert("RGBA")
    bg.alpha_composite(blobs)
    return bg


BG = make_bg()
PARTS = [(random.uniform(0, W), random.uniform(0, H), random.uniform(10, 26), random.uniform(18, 50),
          random.choice(("paw", "heart", "star")), random.uniform(0, 6.28)) for _ in range(26)]


def background(t):
    img = BG.copy()
    d = ImageDraw.Draw(img)
    th = ui.get_theme(cfg)
    for x, y, r, spd, kind, ph in PARTS:
        yy = (y - t * spd) % (H + 100) - 50
        xx = x + math.sin(t * 0.8 + ph) * 18
        c = mix((44, 30, 64), th["primary"] if kind != "star" else th["warn"], 0.35)
        if kind == "paw":
            ui.paw(d, xx, yy, r * 0.6, c)
        elif kind == "heart":
            ui.heart(d, xx, yy, r * 0.6, c)
        else:
            ui.sparkle(d, xx, yy, r * 0.5, c)
    # pride stripe band at the very top + watermark at the bottom
    ui.stripe(d, 0, 0, W, 14, th["stripe"])
    d.text((W / 2, H - 120), "Fluff VR Stats :3", font=ui.font("title", 46), fill=(255, 255, 255, 150),
           anchor="mm", stroke_width=3, stroke_fill=(36, 24, 52))
    return img


# -------------------------------------------------------------- scenes ---
STICKERS, _ = logo.sticker_frames(560)
ERRS, _ = logo.sticker_frames(520, logo.ERROR_ART)
THANKS, _ = logo.sticker_frames(420, logo.THANKS_ART)
KEY = theme_key(cfg)
intro.prewarm(KEY)


def s_intro(c, tl):
    img = intro.frame(KEY, min(tl, intro.DURATION - 0.01), int(tl * 10), glow=False)
    fade = 1.0 if tl < 3.35 else max(0.0, 1 - (tl - 3.35) / 0.35)
    paste_center(c, img, W / 2, H / 2 - 40, scale=1.12, alpha=fade)


def s_title(c, tl):
    k = ease_out_back(tl / 0.5, 2.2)
    fr = STICKERS[int(tl * 10) % len(STICKERS)]
    paste_center(c, fr, W / 2, 820 + math.sin(tl * 3) * 10, scale=max(0.05, k), rot=math.sin(tl * 2.2) * 3)
    caption(c, ["Fluff VR Stats", ":3"], tl - 0.25, y=1260, size=130, accent_idx=1)
    caption(c, ["a cute furry overlay", "for SteamVR + VRChat"], tl - 0.8, y=1560, size=58)


def s_wrist(c, tl):
    caption(c, ["all ur stats", "right on ur wrist"], tl, y=260, size=100, accent_idx=1)
    hud = ui.render_hud(st)
    k = ease_out_back(tl / 0.45)
    paste_center(c, hud, W / 2 + 20, 1080 + math.sin(tl * 1.6) * 14, scale=1.55 * (0.7 + 0.3 * k),
                 alpha=min(1, k * 1.5), rot=math.sin(tl * 1.1) * 2.5)


THEME_SEQ = [("trans_soft", "fox"), ("cotton_candy", "bunny"), ("gay_ocean", "wolf"), ("lava_dragon", "dragon"),
             ("honey_bear", "bear"), ("neon_rave", "cat"), ("bi_night", "fox"), ("mayu_goth", "cat"),
             ("lesbian_sunset", "bunny"), ("frost_wolf", "wolf")]


def s_themes(c, tl):
    i = min(len(THEME_SEQ) - 1, int(tl / 0.34))
    name, ears = THEME_SEQ[i]
    cfg["theme"], cfg["style"]["ears"] = name, ears
    caption(c, ["24 themes", "7 ear styles"], tl, y=260, size=110, accent_idx=1)
    hud = ui.render_hud(st)
    pop = 1 + 0.06 * max(0, 1 - ((tl % 0.34) / 0.12))
    paste_center(c, hud, W / 2 + 20, 1080, scale=1.5 * pop)
    th = ui.get_theme(cfg)
    chip = Image.new("RGBA", (700, 90), (0, 0, 0, 0))
    cd = ImageDraw.Draw(chip)
    cd.rounded_rectangle([0, 0, 699, 89], radius=45, fill=th["bg"][:3] + (255,), outline=th["primary"], width=4)
    cd.text((350, 45), f"{th['label']}  ·  {ears} ears", font=ui.font("title", 46), fill=th["text"], anchor="mm")
    paste_center(c, chip, W / 2, 1640)


def _hit_center(hit, action, arg=None):
    for box, a, args in hit.areas:
        if a == action and (arg is None or (args and args[0] == arg)):
            return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
    return (500, 300)


MENU_STATE = {"tab": "Stats", "clicks": [], "trail": []}


def s_menu(c, tl):
    cfg["theme"], cfg["style"]["ears"] = "pride_pastel", "cat"
    caption(c, ["a whole menu", "in ur SteamVR dash"], tl, y=260, size=100, accent_idx=1)
    plan = [(0.0, "Stats"), (1.3, "Music"), (2.7, "Style")]
    tab = [p[1] for p in plan if tl >= p[0]][-1]
    st.tab = tab
    if tl < 1.9:
        cfg["theme"] = "pride_pastel"
    st.logo_frame = int(tl * 10)
    base, hit = ui.render_dashboard(st)
    th = ui.get_theme(cfg)
    img = ui.add_logo(base, int(tl * 10), st.anim_slots)
    # cursor path: -> Music tab (click 1.2) -> play button (click 2.1) -> Style tab (click 2.6) -> theme (3.4)
    pts = [(0.0, (520, 420)), (1.1, _hit_center(hit, "tab", "Music") if tab == "Stats" else (0, 0))]
    if tab == "Stats":
        a, b = pts[0][1], pts[1][1]
        k = ease(tl / 1.1)
        cur = (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
        clicks = [(b[0], b[1], tl - 1.15)] if tl > 1.15 else []
    elif tab == "Music":
        play = _hit_center(hit, "music", "play_pause")
        styl = _hit_center(hit, "tab", "Style")
        start = _hit_center(hit, "tab", "Music")
        if tl < 2.0:
            k = ease((tl - 1.3) / 0.6)
            cur = (start[0] + (play[0] - start[0]) * k, start[1] + (play[1] - start[1]) * k)
        else:
            k = ease((tl - 2.1) / 0.55)
            cur = (play[0] + (styl[0] - play[0]) * k, play[1] + (styl[1] - play[1]) * k)
        clicks = [(play[0], play[1], tl - 2.0)] if tl > 2.0 else []
        st.music["playing"] = not (2.0 < tl)
    else:
        st.music["playing"] = True
        styl = _hit_center(hit, "tab", "Style")
        target = _hit_center(hit, "theme", "trans_soft")
        k = ease((tl - 2.75) / 0.6)
        cur = (styl[0] + (target[0] - styl[0]) * k, styl[1] + (target[1] - styl[1]) * k)
        clicks = [(target[0], target[1], tl - 3.4)] if tl > 3.4 else []
        if tl > 3.4:
            cfg["theme"] = "trans_soft"
            base, hit = ui.render_dashboard(st)
            th = ui.get_theme(cfg)
            img = ui.add_logo(base, int(tl * 10), st.anim_slots)
    box = hit.find_box(*cur)
    img = ui.draw_hover(img, box, th)
    MENU_STATE["trail"].append((cur[0], cur[1], tl))
    MENU_STATE["trail"] = MENU_STATE["trail"][-8:]
    trail = [(x, y, (tl - t0) * 2.2) for x, y, t0 in MENU_STATE["trail"][:-1]]
    img = ui.draw_cursor(img, cur, trail, [cl for cl in clicks if cl[2] < 0.6], th)
    k = ease_out_back(tl / 0.45)
    paste_center(c, img, W / 2, 1060, scale=1.02 * (0.75 + 0.25 * k), alpha=min(1, k * 1.5))


def s_chatbox(c, tl):
    cfg["theme"] = "pride_pastel"
    caption(c, ["ur stats in the", "VRChat chatbox"], tl, y=250, size=100, accent_idx=1)
    import chatbox as cbx
    text = cbx.compose(cfg, st.stats, st.extras, st.music, CLOCK.t)
    # big VRChat-style bubble, typing in line by line
    lines = text.split("\n")
    shown = max(1, min(len(lines), int((tl - 0.3) / 0.35) + 1))
    f = ui.font("body", 46)
    bw = 880
    bh = 60 + 62 * len(lines)
    bub = Image.new("RGBA", (bw + 20, bh + 50), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bub)
    bd.rounded_rectangle([10, 10, bw + 10, bh + 10], radius=40, fill=(20, 20, 26, 235), outline=(255, 255, 255, 40), width=3)
    bd.polygon([(bw / 2 - 20, bh + 10), (bw / 2 + 40, bh + 10), (bw / 2 + 10, bh + 46)], fill=(20, 20, 26, 235))
    for i, ln in enumerate(lines[:shown]):
        ui.rich_text(bd, (bw / 2 + 10, 40 + i * 62), ln, 46, (255, 255, 255), center=True)
    k = ease_out_back(tl / 0.4)
    paste_center(c, bub, W / 2, 800, scale=0.7 + 0.3 * k, alpha=min(1, k * 1.5))
    # the Chatbox tab it comes from
    st.tab = "Chatbox"
    st.logo_frame = int(tl * 10)
    base, hit = ui.render_dashboard(st)
    img = ui.add_logo(base, int(tl * 10), st.anim_slots)
    k2 = ease_out_back((tl - 0.6) / 0.45)
    if k2 > 0:
        paste_center(c, img, W / 2, 1420, scale=0.9 * (0.75 + 0.25 * k2), alpha=min(1, k2 * 1.5))


CHAT_SCRIPT = [(0.3, "user", "fluff am i lagging rn??"),
               (1.4, "assistant", "nope!! 88 fps, smooth as ur tail fur :3 go have fun"),
               (2.6, "user", "ily fluff"),
               (3.2, "assistant", "ily too!! *headpats* drink some water ok?")]


def s_ai(c, tl):
    caption(c, ["chat with Fluff", "ur AI buddy <3"], tl, y=260, size=100, accent_idx=1)
    st.tab = "Chat"
    st.chat = [(r, m) for t0, r, m in CHAT_SCRIPT if tl >= t0]
    st.thinking = any(t0 - 0.7 < tl < t0 for t0, r, m in CHAT_SCRIPT if r == "assistant")
    st.logo_frame = int(tl * 10)
    base, hit = ui.render_dashboard(st)
    img = ui.add_logo(base, int(tl * 10), st.anim_slots)
    k = ease_out_back(tl / 0.45)
    paste_center(c, img, W / 2, 1060, scale=1.02 * (0.75 + 0.25 * k), alpha=min(1, k * 1.5))


def s_error(c, tl):
    k = ease_out_back(tl / 0.35, 2.5)
    fr = ERRS[int(tl * 10) % len(ERRS)]
    shake = 10 * max(0, 1 - tl / 0.5) * math.sin(tl * 70)
    paste_center(c, fr, W / 2 + shake, 960, scale=max(0.05, k), rot=math.sin(tl * 9) * 2)
    caption(c, ["even the errors", "are cute"], tl - 0.2, y=330, size=104, accent_idx=1)
    caption(c, ["(and it never crashes)"], tl - 1.1, y=1450, size=56)


def s_outro(c, tl):
    k = ease_out_back(tl / 0.5, 2.2)
    fr = STICKERS[int(tl * 10) % len(STICKERS)]
    paste_center(c, fr, W / 2, 760 + math.sin(tl * 3) * 10, scale=max(0.05, k * 0.85))
    caption(c, ["Fluff VR Stats", ":3"], tl - 0.2, y=1150, size=130, accent_idx=1)
    caption(c, ["coming soon <3"], tl - 0.7, y=1440, size=84)
    caption(c, ["made with love for the fluffy community"], tl - 1.1, y=1580, size=44)
    # heart burst
    if tl > 0.25:
        th = ui.get_theme(cfg)
        d = ImageDraw.Draw(c)
        kk = tl - 0.25
        rnd = random.Random(4)
        for i in range(30):
            ang = rnd.uniform(0, 6.28)
            spd = rnd.uniform(300, 750)
            x = W / 2 + math.cos(ang) * spd * kk
            y = 760 + math.sin(ang) * spd * kk + 420 * kk * kk
            a = max(0.0, 1 - kk / 1.6)
            if a > 0:
                col = mix((44, 30, 64), th["primary"] if i % 3 else th["warn"], a)
                if i % 3:
                    ui.heart(d, x, y, 16, mix((44, 30, 64), th["line"], a))
                    ui.heart(d, x, y, 13, col)
                else:
                    ui.sparkle(d, x, y, 16, col)


SCENES = [(0.0, 3.7, s_intro), (3.7, 6.0, s_title), (6.0, 10.5, s_wrist), (10.5, 14.0, s_themes),
          (14.0, 18.0, s_menu), (18.0, 22.0, s_chatbox), (22.0, 26.0, s_ai), (26.0, 28.5, s_error),
          (28.5, TOTAL, s_outro)]


def frame(t):
    tick_stats(t)
    c = background(t)
    for a, b, fn in SCENES:
        if a <= t < b:
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            fn(layer, t - a)
            out_k = 1.0 if (b - t) > 0.18 or fn is s_outro else (b - t) / 0.18
            if out_k < 1:
                layer.putalpha(layer.getchannel("A").point(lambda v: int(v * out_k)))
            c.alpha_composite(layer)
            break
    return c.convert("RGB")


if __name__ == "__main__":
    out = sys.argv[1]
    music = sys.argv[2] if len(sys.argv) > 2 else None
    n = int(TOTAL * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-"]
    if music:
        cmd += ["-i", music, "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = _real_time()
    for i in range(n):
        p.stdin.write(frame(i / FPS).tobytes())
        if i % 150 == 0:
            print(f"  frame {i}/{n}  ({_real_time() - t0:.0f}s)", flush=True)
    p.stdin.close()
    p.wait()
    print("done", out, p.returncode)
