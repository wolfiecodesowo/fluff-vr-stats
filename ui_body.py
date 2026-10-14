"""
Fluff VR Stats - v0.5 menu pages: Body (full-body estimation + heart rate + tracking add-ons),
Cam (VRChat camera over OSC) and the YouTube page inside the Music tab.
"""
import math
import time

from PIL import Image

import fbt
import heartrate
import vcam
from ui import button, ellipsize, font, mix, panel, switch, doodle_heart
from lang import ImageDraw, tr  # noqa: F401  (same translating drawer as the rest of the menu)


def _title(d, x, y, text, t, size=24):
    d.text((x, y), text, font=font("title", size), fill=t["text"])


def _sub(d, x, y, text, t, width=None, size=15, col=None, anchor="la"):
    f = font("body2", size)
    if width:
        text = ellipsize(tr(text), f, width)
    d.text((x, y), text, font=f, fill=col or t["sub"], anchor=anchor)


def plain(text):
    """drops emoji our fonts can't draw (YouTube titles love them)"""
    out = "".join(ch for ch in (text or "") if ord(ch) < 0x2190 or 0x3000 <= ord(ch) < 0xD800 or 0xFF00 <= ord(ch) < 0xFFF0)
    return " ".join(out.split())


def _magnifier(d, cx, cy, r, col):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=3)
    d.line([(cx + r * 0.7, cy + r * 0.7), (cx + r * 1.6, cy + r * 1.6)], fill=col, width=4)


def _camera(d, cx, cy, s, col, bg):
    d.rounded_rectangle([cx - s, cy - s * 0.62, cx + s, cy + s * 0.72], radius=s * 0.22, fill=col)
    d.rectangle([cx - s * 0.36, cy - s * 0.86, cx + s * 0.2, cy - s * 0.6], fill=col)
    d.ellipse([cx - s * 0.42, cy - s * 0.36, cx + s * 0.42, cy + s * 0.48], fill=bg)
    d.ellipse([cx - s * 0.24, cy - s * 0.18, cx + s * 0.24, cy + s * 0.3], fill=col)


def _dot(d, x, y, col, r=6):
    d.ellipse([x - r, y - r, x + r, y + r], fill=col)


def _seg(d, hit, x0, y, x1, h, opts, cur, t, action, fsize=16):
    """row of buttons where one is picked: opts = [(value, label)]"""
    gap = 8
    w = (x1 - x0 - gap * (len(opts) - 1)) / len(opts)
    for i, (val, lab) in enumerate(opts):
        bx = x0 + i * (w + gap)
        button(d, hit, [bx, y, bx + w, y + h], lab, t, action, val, active=cur == val, fsize=fsize)


# ============================================================================== Body tab ===
def tab_body(d, hit, box, state, t):
    x0, y0, x1, y1 = box
    gap = 16
    lw = (x1 - x0 - gap) * 0.56
    _fbt_card(d, hit, [x0, y0, x0 + lw, y1], state, t)
    rx = x0 + lw + gap
    mid = y0 + (y1 - y0) * 0.56
    _heart_card(d, hit, [rx, y0, x1, mid - gap / 2], state, t)
    _addons_card(d, hit, [rx, mid + gap / 2, x1, y1], state, t)


def _fbt_card(d, hit, box, state, t):
    x0, y0, x1, y1 = box
    fb = getattr(state, "fbt", None)
    cfg = state.cfg.setdefault("fbt", dict(fbt.DEFAULT_CFG))
    panel(d, box, 22, t)
    _title(d, x0 + 22, y0 + 14, "Full-body estimation", t, 24)
    st = fb.status if fb else {"state": "off", "rate": 0, "msg": "", "last": {}}
    state_lab = {"on": f"live · {st.get('rate', 0):.0f}/s", "paused": "resting", "waiting": "waiting",
                 "off": "off"}.get(st.get("state"), "off")
    col = {"on": t["good"], "paused": t["warn"], "waiting": t["warn"]}.get(st.get("state"), t["sub"])
    _dot(d, x1 - 130, y0 + 30, col)
    d.text((x1 - 118, y0 + 30), tr(state_lab), font=font("head", 16), fill=col, anchor="lm")
    _sub(d, x0 + 22, y0 + 48, "no trackers needed ~ ur headset does the legs", t, x1 - x0 - 44)
    mode = cfg.get("mode", "off")
    _seg(d, hit, x0 + 22, y0 + 76, x1 - 22, 40, [("off", "off"), ("standable", "standable"), ("camera", "webcam")],
         mode, t, "fbt_mode")
    _seg(d, hit, x0 + 22, y0 + 124, x1 - 22, 34, [("hips_feet", "hips + feet"), ("full", "+ knees + chest")],
         cfg.get("trackers", "hips_feet"), t, "fbt_trackers", fsize=15)

    # lil stick-figure preview of what VRChat gets (front view)
    px0, py0, px1, py1 = x0 + 22, y0 + 170, x0 + 22 + 170, y1 - 74
    d.rounded_rectangle([px0, py0, px1, py1], radius=16, fill=mix(t["panel"], t["bg"][:3], 0.5))
    _figure(d, [px0, py0, px1, py1], st.get("last") or {}, t, live=st.get("state") == "on")

    # buttons on the right of the preview
    bx0, bx1 = px1 + 14, x1 - 22
    by = py0
    h = state.cfg["fbt"].get("height") or 0
    button(d, hit, [bx0, by, bx1, by + 40], tr("calibrate height") + (f" · {h:.2f}m" if h else ""), t,
           "fbt_calibrate", fsize=15)
    by += 48
    if mode == "camera":
        if not fbt.addon_ready():
            inst = bool(fb and fb.installing)
            button(d, hit, [bx0, by, bx1, by + 40], "installing…" if inst else "install webcam add-on", t,
                   "noop" if inst else "fbt_install", primary=not inst, fsize=15)
        else:
            cy = cfg.get("camera_yaw")
            button(d, hit, [bx0, by, bx1, by + 40], "calibrate webcam" + (" ✓" if cy is not None else ""), t,
                   "fbt_cam_cal", primary=cy is None, fsize=15)
            by += 48
            _seg(d, hit, bx0, by, bx1, 34, [(0, "cam 1"), (1, "cam 2"), (2, "cam 3")], int(cfg.get("camera", 0)), t,
                 "fbt_camera", fsize=14)
        by += 48
    head_on = cfg.get("send_head", True)
    d.text((bx0, by + 15), tr("follow my head"), font=font("head", 16), fill=t["text"], anchor="lm")
    switch(d, bx1 - 56, by, head_on, t)
    hit.add([bx0, by - 4, bx1, by + 34], "fbt_head")
    by += 42
    d.text((bx0, by + 10), tr("step size") + f"  {float(cfg.get('step', 0.22)) * 100:.0f} cm",
           font=font("head", 15), fill=t["text"], anchor="lm")
    button(d, hit, [bx1 - 86, by - 6, bx1 - 46, by + 26], "–", t, "fbt_step", -0.04, fsize=18)
    button(d, hit, [bx1 - 40, by - 6, bx1, by + 26], "+", t, "fbt_step", 0.04, fsize=18)

    msg = st.get("msg") or ("pick standable to start ~ then calibrate FBT in VRChat like normal" if mode == "off" else "")
    _sub(d, x0 + 22, y1 - 60, msg, t, x1 - x0 - 44, size=15,
         col=t["warn"] if st.get("state") in ("paused", "waiting") else None)
    _sub(d, x0 + 22, y1 - 34, "VRChat: turn OSC on, then calibrate FBT. real trackers always win", t, x1 - x0 - 44, size=13)


def _figure(d, box, parts, t, live=False):
    """front view stick figure from the tracker positions (relative to the hip)"""
    x0, y0, x1, y1 = box
    cx, base = (x0 + x1) / 2, y1 - 14
    sc = (y1 - y0 - 30) / 1.9
    if not parts or "hip" not in parts:
        parts = {"hip": ((0, 0.95, 0), (0, 0, 0)), "foot_l": ((-0.12, 0.07, 0), 0), "foot_r": ((0.12, 0.07, 0), 0),
                 "knee_l": ((-0.11, 0.5, 0), 0), "knee_r": ((0.11, 0.5, 0), 0), "chest": ((0, 1.3, 0), 0)}
    hip, hip_rot = parts["hip"]
    yaw = math.radians(hip_rot[1] if isinstance(hip_rot, tuple) else 0)

    def P(p):   # body-relative x (sideways) so the figure always faces u
        dx, dz = p[0] - hip[0], p[2] - hip[2]
        side = dx * math.cos(yaw) - dz * math.sin(yaw)
        return cx + side * sc, base - p[1] * sc

    col = t["primary"] if live else mix(t["sub"], t["panel"], 0.3)
    hp = P(hip)
    chest = P(parts["chest"][0]) if "chest" in parts else (hp[0], hp[1] - 0.38 * sc)
    head = (chest[0], chest[1] - 0.32 * sc)
    d.line([hp, chest], fill=col, width=5)
    d.ellipse([head[0] - 13, head[1] - 13, head[0] + 13, head[1] + 13], outline=col, width=4)
    for side in "lr":
        foot = P(parts["foot_" + side][0])
        knee = P(parts["knee_" + side][0]) if "knee_" + side in parts else ((hp[0] + foot[0]) / 2, (hp[1] + foot[1]) / 2)
        d.line([hp, knee, foot], fill=col, width=5, joint="curve")
        d.ellipse([foot[0] - 6, foot[1] - 4, foot[0] + 6, foot[1] + 4], fill=col)
        hand_x = chest[0] + (-1 if side == "l" else 1) * 0.28 * sc
        d.line([chest, (hand_x, chest[1] + 0.36 * sc)], fill=col, width=4)
    d.ellipse([hp[0] - 7, hp[1] - 7, hp[0] + 7, hp[1] + 7], fill=t["text"] if live else col)


def _heart_card(d, hit, box, state, t):
    x0, y0, x1, y1 = box
    hr = getattr(state, "heart", None)
    cfg = state.cfg.setdefault("heart", dict(heartrate.DEFAULT_CFG))
    panel(d, box, 22, t)
    _title(d, x0 + 20, y0 + 12, "Heart rate", t, 22)
    on = bool(hr and hr.connected)
    bpm = hr.bpm if on else None
    beat = 1 + 0.12 * (math.sin(time.time() * math.pi * 2 * (bpm or 60) / 60) > 0.6) if on else 1
    doodle_heart(d, x1 - 108, y0 + 34, 12 * beat, t["bad"] if on else t["panel2"], t["line"])
    d.text((x1 - 20, y0 + 36), f"{bpm}" if on else "--", font=font("title", 34), fill=t["text"], anchor="rm")
    _seg(d, hit, x0 + 20, y0 + 56, x1 - 20, 34, [("off", "off"), ("pulsoid", "pulsoid"), ("ble", "bluetooth")],
         cfg.get("source", "off"), t, "hr_source", fsize=15)
    src = cfg.get("source", "off")
    by = y0 + 98
    half = (x1 - x0 - 48) / 2
    if src == "pulsoid":
        has = bool(cfg.get("pulsoid_token"))
        button(d, hit, [x0 + 20, by, x0 + 20 + half, by + 34], "token ✓" if has else "paste token", t,
               "mod_edit", "pulsoid_token", primary=not has, fsize=14)
        button(d, hit, [x0 + 28 + half, by, x1 - 20, by + 34], "get a token", t, "open_url",
               "https://pulsoid.net/ui/keys", fsize=14)
    elif src == "ble":
        if not heartrate.ble_ready():
            inst = bool(hr and hr.installing)
            button(d, hit, [x0 + 20, by, x1 - 20, by + 34], "installing…" if inst else "install Bluetooth add-on", t,
                   "noop" if inst else "hr_install", primary=not inst, fsize=14)
        else:
            button(d, hit, [x0 + 20, by, x0 + 20 + half, by + 34], "find my strap", t, "hr_scan", fsize=14)
            found = (hr.found if hr else [])[:1]
            if found:
                nm, addr = found[0]
                cur = cfg.get("ble_device") == addr
                button(d, hit, [x0 + 28 + half, by, x1 - 20, by + 34], ("✓ " if cur else "") + nm[:14], t,
                       "hr_pick", addr, active=cur, fsize=13)
    else:
        _sub(d, x0 + 20, by + 8, "watch / strap / phone ~ ur wrist, chatbox + avatar", t, x1 - x0 - 40, size=14)
    # status + session stats + lil graph
    s = hr.session if hr else {}
    avg = hr.avg() if hr else None
    stats = f"min {s.get('min') or '-'} · avg {avg or '-'} · max {s.get('max') or '-'}"
    _sub(d, x0 + 20, by + 44, (hr.status if hr else "off"), t, x1 - x0 - 40, size=13,
         col=t["good"] if on else None)
    if y1 - (by + 66) > 30:
        gx0, gy0, gx1, gy1 = x0 + 20, by + 66, x1 - 20, y1 - 30
        hist = [b for _t, b in (hr.history if hr else [])][-60:]
        if len(hist) > 2:
            lo, hi = min(hist) - 5, max(hist) + 5
            pts = [(gx0 + i * (gx1 - gx0) / (len(hist) - 1), gy1 - (b - lo) / max(1, hi - lo) * (gy1 - gy0))
                   for i, b in enumerate(hist)]
            d.line(pts, fill=t["bad"], width=3, joint="curve")
        else:
            d.line([(gx0, (gy0 + gy1) / 2), (gx1, (gy0 + gy1) / 2)], fill=t["panel2"], width=2)
    _sub(d, x0 + 20, y1 - 24, stats, t, x1 - x0 - 40, size=13)


def _addons_card(d, hit, box, state, t):
    x0, y0, x1, y1 = box
    fb = getattr(state, "fbt", None)
    panel(d, box, 22, t)
    _title(d, x0 + 20, y0 + 12, "Tracking add-ons", t, 22)
    apps = set(fb.status.get("apps", [])) if fb else set()
    real = fb.status.get("real_trackers", 0) if fb else 0
    rows = [
        ("Kinect One", "Kinect One" in apps or "Amethyst" in apps, "via Amethyst (free)", "open_url", fbt.LINKS["amethyst"]),
        ("SlimeVR", "SlimeVR" in apps, "cheap DIY / bought trackers", "open_url", fbt.LINKS["slimevr"]),
        ("SteamVR trackers", real > 0, f"{real} on" if real else "Vive, Tundra…", None, None),
    ]
    rh = (y1 - y0 - 52) / len(rows)
    for i, (name, live, desc, act, arg) in enumerate(rows):
        ry = y0 + 46 + i * rh
        _dot(d, x0 + 28, ry + rh / 2, t["good"] if live else t["panel2"])
        d.text((x0 + 44, ry + rh / 2 - 9), name, font=font("head", 16), fill=t["text"], anchor="lm")
        _sub(d, x0 + 44, ry + rh / 2 + 10, desc, t, x1 - x0 - 170, size=13, anchor="lm")
        if act and not live:
            button(d, hit, [x1 - 92, ry + rh / 2 - 15, x1 - 18, ry + rh / 2 + 15], "get", t, act, arg, fsize=14)
        elif live:
            d.text((x1 - 22, ry + rh / 2), tr("live"), font=font("head", 15), fill=t["good"], anchor="rm")


# =============================================================================== Cam tab ===
def tab_cam(d, hit, box, state, t):
    x0, y0, x1, y1 = box
    v = vcam.ensure(state.cfg)
    gap = 16
    top_h = 132
    panel(d, [x0, y0, x1, y0 + top_h], 22, t)
    _title(d, x0 + 22, y0 + 14, "VCam", t, 26)
    _sub(d, x0 + 112, y0 + 24, "VRChat's camera from here ~ open it in VRChat once first", t, x1 - x0 - 380)
    bw = 128
    button(d, hit, [x1 - 22 - bw, y0 + 12, x1 - 22, y0 + 50], "close cam", t, "vcam", "close", fsize=15)
    _seg(d, hit, x0 + 22, y0 + 62, x1 - 22, 36, [(m, lab) for m, lab in vcam.MODES], v.get("mode", 1), t,
         "vcam_mode", fsize=15)
    _sub(d, x0 + 22, y0 + 108, "needs VRChat 2025.3 or newer + OSC on", t, x1 - x0 - 44, size=13)

    ly = y0 + top_h + gap
    lw = (x1 - x0 - gap) * 0.36
    # shutter
    panel(d, [x0, ly, x0 + lw, y1], 22, t)
    cxm = x0 + lw / 2
    sy = ly + (y1 - ly) * 0.36
    r = min(62, (y1 - ly) * 0.2)
    d.ellipse([cxm - r - 8, sy - r - 8, cxm + r + 8, sy + r + 8], fill=t["line"])
    d.ellipse([cxm - r, sy - r, cxm + r, sy + r], fill=t["primary"])
    _camera(d, cxm, sy, r * 0.5, t["on_primary"], t["primary"])
    hit.add([cxm - r - 8, sy - r - 8, cxm + r + 8, sy + r + 8], "vcam", "capture")
    button(d, hit, [x0 + 22, y1 - 108, x0 + lw - 22, y1 - 66],
           tr("timer photo") + f" · {v['sliders'].get('Duration', 2):g}s", t, "vcam", "timer", fsize=16)
    button(d, hit, [x0 + 22, y1 - 58, x0 + lw - 22, y1 - 20], "reset settings", t, "vcam", "reset", fsize=14)

    # toggles + sliders
    rx = x0 + lw + gap
    panel(d, [rx, ly, x1, y1], 22, t)
    cols = 3
    tw = (x1 - rx - 44 - 8 * (cols - 1)) / cols
    for i, (name, lab) in enumerate(vcam.TOGGLES):
        r_, c_ = divmod(i, cols)
        bx, by = rx + 22 + c_ * (tw + 8), ly + 16 + r_ * 40
        button(d, hit, [bx, by, bx + tw, by + 34], lab, t, "vcam_toggle", name,
               active=bool(v["toggles"].get(name)), fsize=14)
    sy0 = ly + 16 + ((len(vcam.TOGGLES) + cols - 1) // cols) * 40 + 6
    n = len(vcam.SLIDERS)
    sw = (x1 - rx - 44 - 10) / 2
    rows = (n + 1) // 2
    rh = max(30, min(40, (y1 - 14 - sy0) / rows))
    for i, (name, lab, dflt, lo, hi, step, unit) in enumerate(vcam.SLIDERS):
        r_, c_ = divmod(i, 2)
        bx, by = rx + 22 + c_ * (sw + 10), sy0 + r_ * rh
        val = v["sliders"].get(name, dflt)
        d.text((bx, by + rh / 2 - 2), f"{tr(lab)} {val:g}{unit}", font=font("head", 15), fill=t["text"], anchor="lm")
        button(d, hit, [bx + sw - 74, by + 2, bx + sw - 40, by + rh - 6], "–", t, "vcam_slide", name, -1, fsize=17)
        button(d, hit, [bx + sw - 34, by + 2, bx + sw, by + rh - 6], "+", t, "vcam_slide", name, 1, fsize=17)


# ======================================================================= Music -> YouTube ===
PER_PAGE = 4

def music_switch(d, hit, box, state, t):
    """the lil 'player | youtube' switch in the Music tab's top right"""
    x0, y0, x1, _ = box
    page = getattr(state, "music_page", "player")
    w = 112
    for i, (val, lab) in enumerate((("player", "player"), ("youtube", "youtube"))):
        bx = x1 - (2 - i) * (w + 6)
        button(d, hit, [bx, y0, bx + w, y0 + 32], lab, t, "music_page", val, active=page == val, fsize=14)


def tab_youtube(d, hit, box, state, t):
    x0, y0, x1, y1 = box
    yt = getattr(state, "yt", None)
    music_switch(d, hit, box, state, t)
    _title(d, x0 + 4, y0 - 2, "YouTube", t, 26)
    # search bar
    sy = y0 + 40
    q = yt.query if yt else ""
    d.rounded_rectangle([x0, sy, x1 - 140, sy + 44], radius=22, fill=t["panel2"], outline=t["line"], width=3)
    _magnifier(d, x0 + 30, sy + 20, 8, t["sub"])
    d.text((x0 + 52, sy + 22), plain(q) if q else tr("search youtube…"), font=font("head", 17),
           fill=t["text"] if q else t["sub"], anchor="lm")
    hit.add([x0, sy, x1 - 140, sy + 44], "yt_search")
    button(d, hit, [x1 - 130, sy, x1, sy + 44], "search", t, "yt_search", primary=True, fsize=17)
    # recent searches
    hy = sy + 54
    hx = x0
    for h in (yt.history if yt else [])[:5]:
        f = font("body", 13)
        w = min(170, f.getlength(h) + 28)
        if hx + w > x1:
            break
        button(d, hit, [hx, hy, hx + w, hy + 26], ellipsize(plain(h), f, w - 16), t, "yt_again", h, fsize=13)
        hx += w + 6
    status = yt.status if yt else ""
    if not (yt and yt.results):
        d.text(((x0 + x1) / 2, (y0 + y1) / 2 + 30),
               tr(status or "search for a song or video ~ copy the link, then paste it into a world's video player"),
               font=font("head", 17), fill=t["sub"], anchor="mm")
        return
    # results: 2 x 2 per page
    per = PER_PAGE
    res = yt.results
    pages = max(1, (len(res) + per - 1) // per)
    page = min(yt.page, pages - 1)
    gy0 = hy + 36
    cols, rows = 2, 2
    gap = 12
    cw = (x1 - x0 - gap) / cols
    ch = (y1 - 40 - gy0 - gap * (rows - 1)) / rows
    for i, r in enumerate(res[page * per:(page + 1) * per]):
        rr, cc = divmod(i, cols)
        bx, by = x0 + cc * (cw + gap), gy0 + rr * (ch + gap)
        panel(d, [bx, by, bx + cw, by + ch], 16, t)
        th_h = ch - 16
        th_w = th_h * 16 / 9
        img = yt.thumbs.get(r["id"])
        tx, ty = bx + 8, by + 8
        if img is not None:
            im = img.resize((int(th_w), int(th_h)), Image.LANCZOS)
            mask = Image.new("L", im.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, im.size[0] - 1, im.size[1] - 1], radius=10, fill=255)
            d._image.paste(im, (int(tx), int(ty)), mask)
        else:
            d.rounded_rectangle([tx, ty, tx + th_w, ty + th_h], radius=10, fill=t["panel2"])
        ln = r.get("length", "")
        if ln:
            f = font("body", 11)
            lw_ = f.getlength(ln) + 10
            d.rounded_rectangle([tx + th_w - lw_ - 4, ty + th_h - 20, tx + th_w - 4, ty + th_h - 4], radius=6,
                                fill=(200, 30, 40) if ln == "LIVE" else (0, 0, 0))
            d.text((tx + th_w - 4 - lw_ / 2, ty + th_h - 12), ln, font=f, fill=(255, 255, 255), anchor="mm")
        ix = tx + th_w + 10
        iw = bx + cw - 10 - ix
        ft = font("head", 14)
        words, lines, cur = plain(r["title"]).split(), [], ""
        for w in words:
            if ft.getlength(cur + " " + w) > iw and cur:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        lines.append(cur)
        if len(lines) > 2:
            lines = [lines[0], " ".join(lines[1:])]
        for k, ln_ in enumerate(lines[:2]):
            d.text((ix, by + 10 + k * 20), ellipsize(ln_, ft, iw), font=ft, fill=t["text"])
        _sub(d, ix, by + 54, plain(f"{r['channel']} · {r.get('views', '')}"), t, iw, size=13)
        byy = by + ch - 40
        wc, wo = (iw - 12) * 0.42, (iw - 12) * 0.25
        button(d, hit, [ix, byy, ix + wc, byy + 30], "copy link", t, "yt_copy", r["id"], fsize=13, primary=True)
        button(d, hit, [ix + wc + 6, byy, ix + wc + 6 + wo, byy + 30], "open", t, "yt_open", r["id"], fsize=13)
        button(d, hit, [ix + wc + wo + 12, byy, ix + iw, byy + 30], "chatbox", t, "yt_chat", r["id"], fsize=13)
    # pager
    py = y1 - 32
    d.text((x0, py + 14), tr(status), font=font("body2", 14), fill=t["sub"], anchor="lm")
    if pages > 1:
        button(d, hit, [x1 - 210, py, x1 - 120, py + 30], "‹ prev", t, "yt_page", -1, fsize=14)
        d.text((x1 - 104, py + 15), f"{page + 1}/{pages}", font=font("head", 14), fill=t["text"], anchor="mm")
        button(d, hit, [x1 - 88, py, x1, py + 30], "next ›", t, "yt_page", 1, fsize=14)
