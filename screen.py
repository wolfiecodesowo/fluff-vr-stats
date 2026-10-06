"""Desktop mirror: shows one of your monitors as a floating screen in VR.

Capturing runs on its own thread at a capped FPS (default 15) and the image is
downscaled before upload, so it stays light enough to run next to VRChat.
"""
import ctypes
import sys
import threading
import time
from functools import lru_cache

from PIL import Image, ImageDraw

import ui

try:
    import mss
    _MSS = getattr(mss, "MSS", None) or mss.mss
except Exception:          # mss missing -> feature just reports it
    _MSS = None

PAD, EAR = 12, 48


def cursor_pos():
    if sys.platform != "win32":
        return None
    try:
        import ctypes.wintypes as wt
        pt = wt.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y
    except Exception:
        return None


FUR = 18   # room around the picture for fur tufts


@lru_cache(maxsize=8)
def _frame(key, w, h):
    """Furry hand-drawn frame with ears around the screen + rounded mask for the picture."""
    W, H = w + 2 * (PAD + FUR), h + 2 * PAD + EAR + FUR
    frame = ui.furry_frame(key, W, H, (FUR, EAR, W - FUR, H - FUR), 30, EAR)
    m = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], radius=36, fill=255)
    return frame, m.resize((w, h), Image.LANCZOS)


class ScreenMirror:
    def __init__(self, cfg):
        self.cfg = cfg
        self.lock = threading.Lock()
        self.frame = None          # (bytes, w, h)
        self.new = False
        self.error = None if _MSS else "Screen mirror needs the 'mss' package (run install.bat)"
        self.monitor_count = 1
        self.running = True
        if _MSS:
            threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        try:
            sct = _MSS()
        except Exception as e:
            self.error = f"Screen capture failed: {e}"
            return
        while self.running:
            sc = self.cfg["screen"]
            if not sc["enabled"]:
                time.sleep(0.25)
                continue
            t0 = time.time()
            try:
                mons = sct.monitors[1:]
                self.monitor_count = len(mons)
                mon = mons[min(max(sc["monitor"], 1), len(mons)) - 1]
                shot = sct.grab(mon)
                img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                maxw = sc.get("max_width", 1280)
                if img.width > maxw:
                    img = img.resize((maxw, round(img.height * maxw / img.width)), Image.BILINEAR,
                                     reducing_gap=2.0)
                cp = cursor_pos()
                if cp:   # draw a little pink cursor so you can see where the mouse is
                    sx = (cp[0] - mon["left"]) * img.width / mon["width"]
                    sy = (cp[1] - mon["top"]) * img.height / mon["height"]
                    if 0 <= sx < img.width and 0 <= sy < img.height:
                        d = ImageDraw.Draw(img)
                        col = ui.get_theme(self.cfg)["primary"]
                        d.polygon([(sx, sy), (sx, sy + 18), (sx + 5, sy + 14), (sx + 12, sy + 14)],
                                  fill=col, outline=(255, 255, 255))
                frame, mask = _frame(ui.theme_key(self.cfg), img.width, img.height)
                out = frame.copy()
                out.paste(img, (FUR + PAD, EAR + PAD), mask)
                data = out.tobytes()
                with self.lock:
                    self.frame = (data, out.width, out.height)
                    self.new = True
                self.error = None
            except Exception as e:
                self.error = f"Screen capture error: {e}"
                time.sleep(1)
            fps = max(1, sc.get("fps", 15))
            time.sleep(max(0.0, 1.0 / fps - (time.time() - t0)))

    def stop(self):
        self.running = False

    def take(self):
        with self.lock:
            if not self.new:
                return None
            self.new = False
            return self.frame
