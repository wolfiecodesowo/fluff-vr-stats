"""Zoom lens: a floating magnifier in front of your eyes that zooms into the middle of
your VRChat view (like binoculars / a sniper scope, but cute).

How: VRChat draws what you see into its desktop window. We grab the centre of that
window (or your main monitor if VRChat isn't found), scale it up, and show it in a
round furry lens that follows your head. Only a small area is captured, so it's light.

Toggle it from the Screen tab or the 🔍 button on your wrist (tap with your other hand).
"""
import ctypes
import math
import sys
import threading
import time
from functools import lru_cache

from PIL import Image, ImageDraw

import ui

try:
    import mss
    _MSS = getattr(mss, "MSS", None) or mss.mss
except Exception:
    _MSS = None

LENS = 512              # texture size (square)
DEFAULT = {"enabled": False, "level": 3, "size_m": 0.24, "distance_m": 0.55, "fps": 30, "crosshair": True}


def _window_rect(title):
    """Screen rect (left, top, width, height) of a window's content, or None (missing / minimized)."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes.wintypes as wt
        u = ctypes.windll.user32
        hwnd = u.FindWindowW(None, title)
        if not hwnd or u.IsIconic(hwnd) or not u.IsWindowVisible(hwnd):
            return None
        r = wt.RECT()
        u.GetClientRect(hwnd, ctypes.byref(r))
        pt = wt.POINT(0, 0)
        u.ClientToScreen(hwnd, ctypes.byref(pt))
        w, h = r.right - r.left, r.bottom - r.top
        if w < 50 or h < 50:
            return None
        return pt.x, pt.y, w, h
    except Exception:
        return None


def vrchat_rect():
    return _window_rect("VRChat")


def find_source(sct, pref="auto"):
    """Where to zoom from. auto = VRChat window -> SteamVR 'VR View' -> main monitor.
    Returns (rect, label)."""
    order = {"vrchat": ["vrchat"], "vrview": ["vrview"], "monitor": []}.get(pref, ["vrchat", "vrview"])
    for src in order:
        r = _window_rect("VRChat") if src == "vrchat" else _window_rect("VR View")
        if r:
            return r, "VRChat" if src == "vrchat" else "VR View"
    try:
        mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
        return (mon["left"], mon["top"], mon["width"], mon["height"]), "screen"
    except Exception:
        return None, None


@lru_cache(maxsize=1)
def _lens_mask():
    """Round mask for the lens picture."""
    s = LENS
    mask = Image.new("L", (s * 2, s * 2), 0)
    ImageDraw.Draw(mask).ellipse([40, 40, s * 2 - 40, s * 2 - 40], fill=255)
    mask = mask.resize((s, s), Image.LANCZOS)
    return mask


def draw_ring(img, t, level, found):
    s = LENS
    d = ImageDraw.Draw(img)
    c = s / 2
    r = s / 2 - 22
    # fluffy ring: little bumps all the way round
    for i in range(36):
        a = i / 36 * math.tau
        bx, by = c + math.cos(a) * (r + 6), c + math.sin(a) * (r + 6)
        d.ellipse([bx - 13, by - 13, bx + 13, by + 13], fill=t["primary"])
    d.ellipse([c - r - 2, c - r - 2, c + r + 2, c + r + 2], outline=t["line"], width=6)
    # cat ears on top
    for sx in (-1, 1):
        ex = c + sx * r * 0.55
        ey = c - r * 0.86
        pts = [(ex - 34, ey + 12), (ex + sx * 8, ey - 50), (ex + 34, ey + 12)]
        d.polygon(pts, fill=t["primary"], outline=t["line"])
        inner = [(ex - 16, ey + 6), (ex + sx * 5, ey - 26), (ex + 16, ey + 6)]
        d.polygon(inner, fill=t["accent"] if "accent" in t else t["panel2"])
    # zoom badge
    lab = f"{level}x"
    f = ui.font("title", 34)
    tw = f.getlength(lab)
    bx, by = c, s - 40
    d.rounded_rectangle([bx - tw / 2 - 16, by - 24, bx + tw / 2 + 16, by + 20], radius=20,
                        fill=t["panel"], outline=t["line"], width=3)
    d.text((bx, by - 2), lab, font=f, fill=t["text"], anchor="mm")
    if found and found not in ("VRChat",):
        lab = "zooming ur screen" if found == "screen" else f"zooming {found}"
        f2 = ui.font("body2", 18)
        w2 = f2.getlength(lab)
        d.rounded_rectangle([c - w2 / 2 - 12, 52, c + w2 / 2 + 12, 82], radius=14, fill=t["panel"])
        d.text((c, 67), lab, font=f2, fill=t["sub"], anchor="mm")


def placeholder(t, level, msg):
    """Lens shown while there's no picture yet (or capture is broken), so u always SEE the zoom."""
    s = LENS
    out = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    inner = Image.new("RGBA", (s, s), t["panel"][:3] + (235,))
    out.paste(inner, (0, 0), _lens_mask())
    d = ImageDraw.Draw(out)
    c = s / 2
    ui.paw(d, c, c - 40, 34, t["primary"])
    f = ui.font("head", 26)
    lines = ui.wrap(msg, f, s - 150)[:3]
    for i, ln in enumerate(lines):
        d.text((c, c + 30 + i * 32), ln, font=f, fill=t["text"], anchor="mm")
    draw_ring(out, t, level, None)
    return out


class Zoom:
    """Capture thread. Turn it on with .active = True (main.py does that while the lens is up).
    While active it ALWAYS makes frames: the real zoom, or a placeholder lens saying what's wrong."""

    def __init__(self, cfg, size=LENS, ring=True):
        self.cfg = cfg
        cfg.setdefault("zoom", dict(DEFAULT))
        for k, v in DEFAULT.items():
            cfg["zoom"].setdefault(k, v)
        self.size, self.ring = size, ring
        self.lock = threading.Lock()
        self.frame = None
        self.image = None             # last PIL frame (desktop magnifier uses this)
        self.new = False
        self.error = None if _MSS else "zoom needs the 'mss' package ~ run install.bat"
        self.found = None             # "VRChat" / "VR View" / "screen"
        self.active = False
        self.running = True
        threading.Thread(target=self._loop, daemon=True, name="zoom").start()

    def _publish(self, img):
        if img.size != (LENS, LENS) and self.size == LENS:
            img = img.resize((LENS, LENS))
        with self.lock:
            self.image = img
            self.frame = (img.tobytes(), img.width, img.height)
            self.new = True

    def _loop(self):
        sct = None
        last_rect_check, rect = 0, None
        while self.running:
            if not self.active:
                time.sleep(0.15)
                continue
            t0 = time.time()
            z = self.cfg["zoom"]
            th = ui.get_theme(self.cfg)
            try:
                if sct is None:
                    if not _MSS:
                        raise RuntimeError(self.error)
                    sct = _MSS()
                if t0 - last_rect_check > 2 or rect is None:     # windows can move / resize / minimize
                    last_rect_check = t0
                    rect, self.found = find_source(sct, z.get("source", "auto"))
                if rect is None:
                    raise RuntimeError("couldn't find a screen to zoom")
                left, top, w, h = rect
                level = max(1.5, float(z.get("level", 3)))
                side = max(16, int(min(w, h) / level))
                cx, cy = left + w // 2, top + h // 2
                box = {"left": cx - side // 2, "top": cy - side // 2, "width": side, "height": side}
                shot = sct.grab(box)
                img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                img = img.resize((LENS, LENS), Image.BILINEAR)
                out = Image.new("RGBA", (LENS, LENS), (0, 0, 0, 0))
                out.paste(img, (0, 0), _lens_mask())
                if z.get("crosshair", True):
                    d = ImageDraw.Draw(out)
                    c = LENS / 2
                    ui.paw(d, c, c + 2, 5, th["primary"])
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        d.line([(c + dx * 14, c + dy * 14), (c + dx * 34, c + dy * 34)], fill=th["primary"], width=3)
                if self.ring:
                    draw_ring(out, th, z.get("level", 3), self.found)
                self._publish(out)
                self.error = None
            except Exception as e:
                self.error = str(e) or e.__class__.__name__
                sct, rect = None, None                          # start fresh next time
                try:
                    self._publish(placeholder(th, z.get("level", 3), "zoom hiccup: " + self.error[:60]))
                except Exception:
                    pass
                time.sleep(1)
            fps = max(5, int(self.cfg["zoom"].get("fps", 30)))
            time.sleep(max(0.0, 1.0 / fps - (time.time() - t0)))

    def stop(self):
        self.running = False

    def take(self):
        with self.lock:
            if not self.new:
                return None
            self.new = False
            return self.frame
