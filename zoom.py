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


def vrchat_rect():
    """Screen rect (left, top, width, height) of VRChat's window content, or None."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes.wintypes as wt
        u = ctypes.windll.user32
        hwnd = u.FindWindowW(None, "VRChat")
        if not hwnd or u.IsIconic(hwnd):
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
    if not found:
        d.text((c, 70), "VRChat window not found", font=ui.font("body2", 18), fill=t["sub"], anchor="mm")


class Zoom:
    def __init__(self, cfg):
        self.cfg = cfg
        cfg.setdefault("zoom", dict(DEFAULT))
        for k, v in DEFAULT.items():
            cfg["zoom"].setdefault(k, v)
        self.lock = threading.Lock()
        self.frame = None
        self.new = False
        self.error = None if _MSS else "Zoom needs the 'mss' package (run install.bat)"
        self.found = False
        self.running = True
        if _MSS:
            threading.Thread(target=self._loop, daemon=True, name="zoom").start()

    def _on(self):
        return self.cfg["modules"].get("zoom_lens", True) and self.cfg["zoom"].get("enabled")

    def _loop(self):
        try:
            sct = _MSS()
        except Exception as e:
            self.error = f"Zoom capture failed: {e}"
            return
        last_rect_check, rect = 0, None
        while self.running:
            if not self._on():
                time.sleep(0.2)
                continue
            t0 = time.time()
            try:
                z = self.cfg["zoom"]
                if t0 - last_rect_check > 2:          # VRChat window can move / resize
                    last_rect_check = t0
                    rect = vrchat_rect()
                    self.found = rect is not None
                    if rect is None:
                        mon = sct.monitors[1]
                        rect = (mon["left"], mon["top"], mon["width"], mon["height"])
                left, top, w, h = rect
                level = max(1.5, float(z.get("level", 3)))
                side = int(min(w, h) / level)
                cx, cy = left + w // 2, top + h // 2
                box = {"left": cx - side // 2, "top": cy - side // 2, "width": side, "height": side}
                shot = sct.grab(box)
                img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                img = img.resize((LENS, LENS), Image.BILINEAR)
                th = ui.get_theme(self.cfg)
                out = Image.new("RGBA", (LENS, LENS), (0, 0, 0, 0))
                mask = _lens_mask()
                out.paste(img, (0, 0), mask)
                if z.get("crosshair", True):
                    d = ImageDraw.Draw(out)
                    c = LENS / 2
                    ui.paw(d, c, c + 2, 5, th["primary"])
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        d.line([(c + dx * 14, c + dy * 14), (c + dx * 34, c + dy * 34)], fill=th["primary"], width=3)
                draw_ring(out, th, z.get("level", 3), self.found)
                with self.lock:
                    self.frame = (out.tobytes(), LENS, LENS)
                    self.new = True
                self.error = None
            except Exception as e:
                self.error = f"Zoom error: {e}"
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
