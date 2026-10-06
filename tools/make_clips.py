"""Short feature clips (16:9) for Discord / socials, built from the app's real UI.
Usage: python tools/make_clips.py out_folder [music.wav]
Makes: wrist_hud, menu_tour, themes, chatbox, ai_buddy, fps_boost, discord_status (.mp4)"""
import math
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import make_trailer as base  # noqa: E402  (fake evening VRChat session + helpers)
import chatbox as cbx  # noqa: E402
import logo  # noqa: E402
import ui  # noqa: E402
from themes import PRESET_MAP  # noqa: E402

W, H, FPS = 1280, 720, 30
cfg, st = base.cfg, base.st
INK = (24, 14, 34)
CAP = os.path.join(HERE, "fonts", "LilitaOne-Regular.ttf")
_fc = {}


def capfont(size):
    if size not in _fc:
        _fc[size] = ImageFont.truetype(CAP, size)
    return _fc[size]


def word_img(text, size, fill):
    f = capfont(size)
    sw = max(4, size // 10)
    l, t, r, b = f.getbbox(text, stroke_width=sw)
    img = Image.new("RGBA", (r - l + 20, b - t + 20), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((10 - l, 10 - t), text, font=f, fill=fill, stroke_width=sw, stroke_fill=INK)
    return img


def caption(c, text, t, x, y, size=64, hl=(), start=0.0, align="left", step=0.09):
    """Words pop in one by one; words whose index is in hl are pink."""
    words = text.split()
    imgs = [word_img(w, size, (255, 143, 199) if i in hl else (255, 255, 255)) for i, w in enumerate(words)]
    total = sum(im.width - 6 for im in imgs)
    xx = x - total / 2 if align == "center" else x
    for i, im in enumerate(imgs):
        k = (t - start - i * step) / 0.18
        if k > 0:
            s = base.ease_out_back(k, 2.6)
            base.paste_center(c, im, xx + im.width / 2, y, scale=max(0.05, s),
                              rot=(-2 if i % 2 else 1.5))
        xx += im.width - 6


def bullet(c, text, t, start, x, y, size=34, col=(255, 255, 255)):
    k = (t - start) / 0.25
    if k <= 0:
        return
    s = base.ease_out_back(k, 2.2)
    d = ImageDraw.Draw(c)
    ui.paw(d, x + 14, y, 12 * min(1, s), (255, 143, 199))
    im = word_img(text, size, col)
    base.paste_center(c, im, x + 36 + im.width / 2 - (1 - min(1, k)) * 30, y, alpha=min(1, k * 1.4))


# ------------------------------------------------------------ background ---
rnd = random.Random(4)
PAWS = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(14, 26), rnd.uniform(14, 34)) for _ in range(16)]
STRIPE = [(255, 122, 168), (255, 179, 107), (255, 227, 110), (142, 224, 138), (110, 200, 255), (181, 140, 255)]
STICK, _ = logo.sticker_frames(120)


def background(t, tint=(60, 30, 90)):
    img = Image.new("RGBA", (W, H), (28, 18, 40, 255))
    d = ImageDraw.Draw(img)
    for i in range(0, H, 6):                         # soft vertical gradient
        k = i / H
        col = tuple(int(28 + (tint[j] - 28) * k * 0.7) if j < 3 else 255 for j in range(3))
        d.rectangle([0, i, W, i + 6], fill=col)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    for x, y, r, sp in PAWS:                          # drifting paw doodles (faint)
        yy = (y - t * sp) % (H + 60) - 30
        ui.paw(ld, x, yy, r, (255, 255, 255, 22))
    img.alpha_composite(lay)
    seg = W / len(STRIPE)
    for i, col in enumerate(STRIPE):
        d.rectangle([i * seg, 0, (i + 1) * seg, 7], fill=col)
    return img


def watermark(c, t):
    fr = STICK[int(t * 10) % len(STICK)]
    base.paste_center(c, fr, W - 78, H - 74, scale=0.75)
    im = word_img("Fluff VR Stats :3", 26, (255, 255, 255))
    base.paste_center(c, im, W - 150 - im.width / 2, H - 50)


def end_card(c, t, start):
    k = (t - start) / 0.35
    if k <= 0:
        return
    ov = Image.new("RGBA", (W, H), (20, 12, 30, int(min(1, k) * 225)))
    c.alpha_composite(ov)
    big = STICK[int(t * 10) % len(STICK)]
    base.paste_center(c, big, W / 2, 250, scale=2.0 * base.ease_out_back(k, 2.0))
    caption(c, "Fluff VR Stats :3", t, W / 2, 430, 74, hl=(3,), start=start + 0.1, align="center")
    caption(c, "free + open source", t, W / 2, 515, 40, start=start + 0.4, align="center")
    caption(c, "grab it in #download", t, W / 2, 575, 40, hl=(3,), start=start + 0.6, align="center")


def fit(img, max_w, max_h):
    s = min(max_w / img.width, max_h / img.height)
    return s


# ------------------------------------------------------------------ clips ---
def clip_wrist(t):
    c = background(t, (90, 40, 110))
    base.tick_stats(t)
    cfg["theme"], cfg["style"]["ears"] = "pride_pastel", "cat"
    st.alert = {"text": "Kitsu joined", "kind": "info", "until": base.CLOCK.t + 99} if 5.5 < t < 8.5 else None
    st.pet_mood = "vibin to Pawsitive Vibes ~"
    hud = ui.render_hud(st)
    s = fit(hud, 560, 600)
    k = base.ease_out_back(t / 0.5)
    base.paste_center(c, hud, 900, 380 + math.sin(t * 1.6) * 8, scale=s * (0.8 + 0.2 * k),
                      rot=-3 + math.sin(t * 1.2) * 1.5, alpha=min(1, k * 1.5))
    caption(c, "ur stats on ur WRIST", t, 60, 120, 68, hl=(3,))
    for i, txt in enumerate(["FPS + frametimes", "headset + controller battery", "tap-able music controls",
                             "join alerts", "a lil pet who vibes w/ u"]):
        bullet(c, txt, t, 1.2 + i * 0.9, 70, 240 + i * 62)
    caption(c, "it fades in when u look at it", t, 60, 600, 36, start=6.2, step=0.05)
    watermark(c, t)
    end_card(c, t, 10.2)
    return c


MENU_PLAN = ["Stats", "Boost", "Chat", "Music", "Chatbox", "Avatar", "World", "Mods", "Style", "<3"]


def clip_menu(t):
    c = background(t, (60, 40, 120))
    base.tick_stats(t)
    cfg["theme"] = "pride_pastel"
    seg = 0.95
    i = min(len(MENU_PLAN) - 1, int(max(0, t - 0.6) / seg))
    st.tab = MENU_PLAN[i]
    st.chat = [(r, m) for _, r, m in CHAT]
    st.thinking = False
    st.logo_frame = int(t * 10)
    img0, hit = ui.render_dashboard(st)
    th = ui.get_theme(cfg)
    img = ui.add_logo(img0, int(t * 10), st.anim_slots)
    nxt = MENU_PLAN[min(len(MENU_PLAN) - 1, i + 1)]
    a = base._hit_center(hit, "tab", st.tab)
    b = base._hit_center(hit, "tab", nxt)
    local = (max(0, t - 0.6) % seg) / seg
    kk = base.ease(min(1, local / 0.8))
    cur = (a[0] + (b[0] - a[0]) * kk, a[1] + (b[1] - a[1]) * kk + math.sin(local * 3.14) * -30)
    clicks = [(a[0], a[1], local * seg)] if local * seg < 0.5 and t > 0.6 else []
    img = ui.draw_hover(img, hit.find_box(*cur), th)
    img = ui.draw_cursor(img, cur, [], clicks, th, "paw")
    s = fit(img, 1060, 520)
    k = base.ease_out_back(t / 0.5)
    base.paste_center(c, img, W / 2, 400, scale=s * (0.85 + 0.15 * k), alpha=min(1, k * 1.5))
    caption(c, "12 tabs in ur SteamVR menu", t, W / 2, 70, 56, hl=(0, 1), align="center")
    tab_name = {"<3": "thank-u page"}.get(st.tab, st.tab)
    caption(c, f"→ {tab_name}", t, W / 2, 690 - 20, 34, align="center", start=0.6 + i * seg, step=0.0)
    end_card(c, t, 10.4)
    return c


THEME_LIST = list(PRESET_MAP.keys())
EARS = ["cat", "fox", "wolf", "bunny", "bear", "dragon", "cat"]


def clip_themes(t):
    c = background(t, (100, 40, 90))
    base.tick_stats(t)
    n = int(t / 0.38)
    cfg["theme"] = THEME_LIST[n % len(THEME_LIST)]
    cfg["style"]["ears"] = EARS[(n // 3) % len(EARS)]
    st.alert = None
    hud = ui.render_hud(st)
    s = fit(hud, 520, 560)
    pulse = 1 + 0.04 * math.exp(-((t % 0.38) * 14))
    base.paste_center(c, hud, 880, 380, scale=s * pulse, rot=-3 + math.sin(t * 2) * 2)
    caption(c, "24 themes", t, 70, 170, 84, hl=(0,))
    caption(c, "7 ear styles", t, 70, 280, 64, hl=(0,), start=0.8)
    caption(c, "accents, backgrounds", t, 70, 380, 40, start=1.6, step=0.05)
    caption(c, "+ a paw laser cursor", t, 70, 440, 40, hl=(2,), start=2.0, step=0.05)
    name = PRESET_MAP[cfg["theme"]].get("name", cfg["theme"]) if isinstance(PRESET_MAP[cfg["theme"]], dict) \
        else cfg["theme"]
    im = word_img(str(name).replace("_", " "), 30, (255, 227, 110))
    base.paste_center(c, im, 70 + im.width / 2, 520)
    watermark(c, t)
    end_card(c, t, 10.2)
    return c


def bubble(text, shown):
    lines = text.split("\n")
    f = 30
    bw = 520
    bh = 40 + 42 * len(lines)
    bub = Image.new("RGBA", (bw + 20, bh + 40), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bub)
    bd.rounded_rectangle([10, 10, bw + 10, bh + 10], radius=28, fill=(20, 20, 26, 235),
                         outline=(255, 255, 255, 50), width=3)
    bd.polygon([(bw / 2 - 14, bh + 10), (bw / 2 + 30, bh + 10), (bw / 2 + 6, bh + 36)], fill=(20, 20, 26, 235))
    for i, ln in enumerate(lines[:shown]):
        ui.rich_text(bd, (bw / 2 + 10, 28 + i * 42), ln, f, (255, 255, 255), center=True)
    return bub


def clip_chatbox(t):
    c = background(t, (40, 50, 110))
    base.tick_stats(t * 3)
    cfg["theme"] = "pride_pastel"
    text = cbx.compose(cfg, st.stats, st.extras, st.music, base.CLOCK.t)
    shown = max(1, int((t - 0.8) / 0.3) + 1)
    k = base.ease_out_back((t - 0.6) / 0.4)
    if k > 0:
        base.paste_center(c, bubble(text, shown), 330, 330 + math.sin(t * 1.5) * 6, scale=0.7 + 0.3 * k,
                          alpha=min(1, k * 1.5))
    caption(c, "over ur head in VRChat", t, 330, 600, 40, hl=(3,), align="center", start=1.2, step=0.06)
    st.tab = "Chatbox"
    st.logo_frame = int(t * 10)
    img0, hit = ui.render_dashboard(st)
    img = ui.add_logo(img0, int(t * 10), st.anim_slots)
    s = fit(img, 640, 420)
    k2 = base.ease_out_back((t - 0.3) / 0.45)
    if k2 > 0:
        base.paste_center(c, img, 950, 390, scale=s * (0.8 + 0.2 * k2), rot=2, alpha=min(1, k2 * 1.5))
    caption(c, "MagicChatbox-style stats", t, W / 2, 70, 54, hl=(0,), align="center")
    end_card(c, t, 10.2)
    return c


CHAT = [(0.8, "user", "fluff am i lagging rn??"),
        (2.4, "assistant", "nope!! 88 fps, smooth as ur tail fur :3 go have fun"),
        (4.6, "user", "what should i do tonight"),
        (6.4, "assistant", "world hop w/ friends, then a cozy mirror chill. and drink water ok?")]


def clip_ai(t):
    c = background(t, (90, 40, 120))
    base.tick_stats(t)
    st.tab = "Chat"
    st.chat = [(r, m) for t0, r, m in CHAT if t >= t0]
    st.thinking = any(t0 - 0.9 < t < t0 for t0, r, m in CHAT if r == "assistant")
    st.logo_frame = int(t * 10)
    img0, hit = ui.render_dashboard(st)
    img = ui.add_logo(img0, int(t * 10), st.anim_slots)
    s = fit(img, 1060, 520)
    k = base.ease_out_back(t / 0.5)
    base.paste_center(c, img, W / 2, 410, scale=s * (0.85 + 0.15 * k), alpha=min(1, k * 1.5))
    caption(c, "talk to Fluff, ur AI buddy", t, W / 2, 70, 54, hl=(2,), align="center")
    caption(c, "free with Groq · works in VR", t, W / 2, 680, 32, align="center", start=1.5, step=0.05)
    end_card(c, t, 10.2)
    return c


BOOST_KEYS = ["power_plan", "game_mode", "game_dvr", "vr_priority", "gpu_pref"]


def clip_boost(t):
    c = background(t, (110, 70, 40))
    base.tick_stats(t)
    on = sum(1 for i in range(5) if t > 1.4 + i * 0.8)
    st.boost = {"status": {k: (i < on) if k != "game_dvr" else not (i < on) for i, k in enumerate(BOOST_KEYS)},
                "heavy": [{"name": "chrome.exe", "cpu": 18.2, "mem": 2300}, {"name": "Discord.exe", "cpu": 6.1, "mem": 610},
                          {"name": "Spotify.exe", "cpu": 2.4, "mem": 380}, {"name": "obs64.exe", "cpu": 1.1, "mem": 290}],
                "tip": int(t / 3) % 4, "calmed": set(), "msg": ""}
    st.tab = "Boost"
    st.logo_frame = int(t * 10)
    img0, hit = ui.render_dashboard(st)
    img = ui.add_logo(img0, int(t * 10), st.anim_slots)
    s = fit(img, 1060, 520)
    k = base.ease_out_back(t / 0.5)
    base.paste_center(c, img, W / 2, 410, scale=s * (0.85 + 0.15 * k), alpha=min(1, k * 1.5))
    caption(c, "one-tap FPS boost", t, W / 2, 70, 60, hl=(1, 2), align="center")
    for i in range(on):
        tt = t - (1.4 + i * 0.8)
        if tt < 0.7:
            im = word_img("+fps!", 40, (255, 227, 110))
            base.paste_center(c, im, 1120, 300 - tt * 120, alpha=max(0, 1 - tt / 0.7), rot=8)
    caption(c, "no admin · undo anytime", t, W / 2, 680, 34, align="center", start=5.8, step=0.05)
    end_card(c, t, 10.2)
    return c


def discord_card(t):
    """A stylized profile card (not Discord's real UI) showing the rich presence idea."""
    cw, ch = 560, 350
    card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=26, fill=(36, 30, 48, 255), outline=(255, 255, 255, 30), width=2)
    d.rounded_rectangle([0, 0, cw - 1, 90], radius=26, fill=(255, 143, 199, 255))
    d.rectangle([0, 60, cw - 1, 90], fill=(255, 143, 199, 255))
    d.ellipse([28, 46, 128, 146], fill=(36, 30, 48, 255))
    d.ellipse([36, 54, 120, 138], fill=(181, 140, 255, 255))
    ui.paw(d, 78, 98, 22, (255, 255, 255))
    d.ellipse([100, 118, 124, 142], fill=(36, 30, 48, 255))
    d.ellipse([104, 122, 120, 138], fill=(123, 224, 181, 255))
    d.text((146, 100), "you :3", font=ui.font("title", 30), fill=(255, 255, 255))
    d.text((28, 160), "PLAYING", font=ui.font("head", 16), fill=(201, 182, 218))
    lg = STICK[int(t * 10) % len(STICK)].resize((84, 84))
    card.alpha_composite(lg, (28, 188))
    d.text((126, 190), "Fluff VR Stats :3", font=ui.font("head", 24), fill=(255, 255, 255))
    fps = 88 + 1.5 * math.sin(t * 1.7)
    d.text((126, 222), f"{fps:.0f} fps in The Black Cat", font=ui.font("body", 19), fill=(230, 220, 240))
    d.text((126, 248), "listening to Pawsitive Vibes", font=ui.font("body", 19), fill=(201, 182, 218))
    el = int(4980 + t)
    d.text((126, 274), f"{el // 3600:02d}:{el % 3600 // 60:02d}:{el % 60:02d} elapsed", font=ui.font("body2", 16),
           fill=(201, 182, 218))
    for i, lab in enumerate(["Get Fluff VR Stats", "Join the Discord"]):
        x0 = 28 + i * 258
        d.rounded_rectangle([x0, 296 - 2, x0 + 246, 296 + 30], radius=10, fill=(70, 60, 90, 255))
        d.text((x0 + 123, 311), lab, font=ui.font("head", 16), fill=(255, 255, 255), anchor="mm")
    return card


def clip_discord(t):
    c = background(t, (70, 40, 120))
    k = base.ease_out_back((t - 0.3) / 0.5)
    if k > 0:
        base.paste_center(c, discord_card(t), 860, 380 + math.sin(t * 1.4) * 6, scale=0.8 + 0.2 * k,
                          rot=-2, alpha=min(1, k * 1.5))
    caption(c, "ur Discord shows", t, 60, 150, 62)
    caption(c, "ur fps + world", t, 60, 230, 62, hl=(1, 3), start=0.6)
    for i, txt in enumerate(["live while u play", "buttons so friends can grab it",
                             "🥽 In VR Now role in our server", "just keep Discord open"]):
        bullet(c, txt.replace("🥽 ", ""), t, 2.0 + i * 0.9, 70, 340 + i * 62)
    watermark(c, t)
    end_card(c, t, 10.2)
    return c


CLIPS = {"wrist_hud": clip_wrist, "menu_tour": clip_menu, "themes": clip_themes, "chatbox": clip_chatbox,
         "ai_buddy": clip_ai, "fps_boost": clip_boost, "discord_status": clip_discord}
DUR = 12.0


def render(name, fn, out, music=None, music_off=0.0):
    n = int(DUR * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-"]
    if music:
        cmd += ["-ss", f"{music_off:.2f}", "-i", music, "-af",
                f"afade=t=in:d=0.4,afade=t=out:st={DUR - 1.2}:d=1.2,volume=0.85", "-c:a", "aac", "-b:a", "128k",
                "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            os.path.join(out, name + ".mp4")]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(fn(i / FPS).convert("RGB").tobytes())
    p.stdin.close()
    p.wait()


if __name__ == "__main__":
    out = sys.argv[1]
    music = sys.argv[2] if len(sys.argv) > 2 else None
    only = sys.argv[3:] or list(CLIPS)
    os.makedirs(out, exist_ok=True)
    for j, name in enumerate(only):
        render(name, CLIPS[name], out, music, (j * 7.3) % 20)
        print("made", name)
