"""
Fluff VR Stats :3 - a cute furry SteamVR overlay for VRChat.
  * Wrist HUD: FPS, frametimes, clock, batteries, PC load, music, ping, alerts, AI reply...
  * Dashboard tab (SteamVR menu): stats, AI chat, desktop screen, mods, style, wrist placement

Runs as a separate overlay app (no injection into VRChat), redraws only a
couple of times per second, and lowers its own process priority so it never
steals frames from the game.
"""
import collections
import ctypes
import json
import logging
import logging.handlers
import math
import os
import sys
import tempfile
import threading
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- logging first, so even import problems get written down
os.makedirs(os.path.join(HERE, "logs"), exist_ok=True)
LOG_PATH = os.path.join(HERE, "logs", "fluffvr.log")
log = logging.getLogger("fluffvr")
log.setLevel(logging.INFO)
try:
    _h = logging.handlers.RotatingFileHandler(LOG_PATH, maxBytes=512_000, backupCount=2, encoding="utf-8")
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(_h)
except OSError:
    pass


def _pause():
    if sys.stdin and sys.stdin.isatty():
        try:
            input("Press Enter to close...")
        except Exception:
            pass


try:
    import openvr
    import psutil
    from PIL import Image, ImageDraw
except ImportError as _e:
    log.error("missing package: %s", _e)
    print(f"\n  >w<  missing a package: {_e.name}\n  double-click install.bat first, then try again!\n")
    _pause()
    sys.exit(1)

import ai
import chatbox
import intro
import osc
import ui
from extras import Extras
from gltex import GLUploader
from music import Music
from discord_link import DiscordLink
from vrclog import VRCLog
from avatar import Avatar
from tweaks import Tweaks, TWEAKS
from screen import ScreenMirror
from stats import StatsCollector
from themes import PRESET_MAP

CFG_PATH = os.path.join(HERE, "config.json")
DEFAULT_WRIST = {"offset": [0.0, 0.02, 0.13], "rotation_deg": [-60.0, 0.0, 0.0]}

# anything missing from an older config.json gets filled in from here
DEFAULT_CFG = {
    "theme": "pride_pastel",
    "style": {"accent": None, "background": None, "ears": "cat", "stripe": True},
    "modules": {
        "fps": True, "frametime_graph": True, "gpu_cpu_ms": True, "reprojection": True,
        "pc_usage": True, "gpu_temp": False, "ping": False, "low_fps_alert": True,
        "clock": True, "batteries": True, "session_timer": True, "now_playing": True,
        "weather": False, "break_reminder": False, "last_ai_reply": True, "look_to_show": True,
        "music_controls": True,
        "world_info": True, "join_alerts": True, "avatar_toggles": True, "afk_detect": True,
        "distance": True, "wrist_pet": True, "timer": True,
        "ai_to_chatbox": False, "chatbox_status": False, "chatbox_song": False,
        "typing_indicator": True, "mute_indicator": False, "headpat_counter": False,
        "discord_presence": True,
    },
    "discord": {"app_id": "", "guild_id": "1557135963510280202", "invite": "", "show_song": True},
    "ai": {
        "provider": "anthropic", "api_key": "", "model": "claude-haiku-4-5", "base_url": "",
        "max_tokens": 300,
        "system_prompt": ("You are Fluff, a cute, playful, supportive furry companion living inside a VR "
                          "wrist overlay. The user is hanging out in VRChat. Keep replies short (1-3 "
                          "sentences) since they are read in VR. Be warm, a little silly, use occasional "
                          "cat/paw puns, never cringe-overload."),
    },
    "wrist": {"hand": "left", "width_m": 0.13, "opacity": 0.95,
              "offset": [0.0, 0.02, 0.13], "rotation_deg": [-60.0, 0.0, 0.0]},
    "screen": {"enabled": False, "monitor": 1, "fps": 15, "max_width": 1280, "width_m": 1.4,
               "attach": "world", "distance_m": 1.3},
    "hud_refresh_hz": 2,
    "dashboard_width_m": 2.0,
    "chatbox_text": "{time} | fluffy vibes only",
    "chatbox_interval_s": 6,
    "break_minutes": 45,
    "low_fps_ratio": 0.6,
    "headpat_param": "HeadPat",
    "headpats_total": 0,
    "weather_location": "",
    "weather_units": "F",
    "ping_host": "1.1.1.1",
    "osc_port": 9000,
    "osc_listen_port": 9001,
    "animate_logo": True,
    "intro": True,
    "startup_sound": True,
    "first_run": True,
    "floof_pats": 0,
    "made_by": "wolfiecodesowo",
    "support_link": "",
    "gl_flip": True,
    "gpu_textures": True,
    "sticker_styles": {"logo.gif": "cutout", "error.gif": "card", "thanks.gif": "cutout"},
    "chatbox": json.loads(json.dumps(chatbox.DEFAULT)),
    "touch_offset": [0.0, -0.015, -0.05],
    "touch_depth_m": 0.03,
    "mouse_y": "auto",
    "afk_minutes": 5,
    "walked_total_m": 0,
    "cursor": "paw",
}
CFG_NOTICE = []   # problems found while loading config, shown once the app is up

BREAK_MSGS = [
    "hydrate check! sip some water ~",
    "stretch those paws and wiggle your tail!",
    "take your headset off for a sec, rest your eyes",
    "posture check! sit up, cutie",
    "snack + water break? you've earned it",
]


# ------------------------------------------------------------- helpers ---
def _merge(dst, src):
    for k, v in src.items():
        if k not in dst:
            dst[k] = json.loads(json.dumps(v))
        elif isinstance(v, dict) and isinstance(dst[k], dict):
            _merge(dst[k], v)


def load_cfg():
    """Never fails: a missing or broken config.json is backed up and replaced by defaults."""
    cfg = {}
    try:
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if not isinstance(cfg, dict):
            raise ValueError("config.json isn't a JSON object")
    except FileNotFoundError:
        # first launch: start from the shipped example (no API keys in it), quietly
        try:
            with open(os.path.join(HERE, "config.example.json"), "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
    except Exception as e:
        bad = CFG_PATH.replace(".json", f".broken-{int(time.time())}.json")
        try:
            os.replace(CFG_PATH, bad)
        except OSError:
            pass
        CFG_NOTICE.append(f"config.json had a typo ({e}). Saved it as {os.path.basename(bad)} "
                          "and started with defaults")
        log.error("config load failed: %s", e)
        cfg = {}
    for k, v in DEFAULT_CFG.items():
        if isinstance(v, dict) and not isinstance(cfg.get(k), dict):
            cfg[k] = {}
    _merge(cfg, DEFAULT_CFG)
    w = cfg["wrist"]
    try:
        assert len(w["offset"]) == 3 and len(w["rotation_deg"]) == 3
        float(w["width_m"]), float(w["opacity"])
    except Exception:
        cfg["wrist"] = json.loads(json.dumps(DEFAULT_CFG["wrist"]))
    # repair wrong types (e.g. a module set to "yes")
    for k, v in DEFAULT_CFG["modules"].items():
        if not isinstance(cfg["modules"].get(k), bool):
            cfg["modules"][k] = v
    if cfg.get("theme") not in PRESET_MAP:
        cfg["theme"] = DEFAULT_CFG["theme"]
    if cfg["modules"].get("chatbox_song"):          # old setting -> new chatbox lines
        cfg["chatbox"]["lines"]["song"] = True
        cfg["modules"]["chatbox_status"] = True
        cfg["modules"]["chatbox_song"] = False
    if not isinstance(cfg["chatbox"].get("statuses"), list):
        cfg["chatbox"]["statuses"] = list(chatbox.DEFAULT["statuses"])
    if cfg["style"].get("ears") not in ui.EAR_STYLES:
        cfg["style"]["ears"] = "cat"
    return cfg


def save_cfg(cfg):
    try:
        tmp = CFG_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        os.replace(tmp, CFG_PATH)
    except Exception as e:
        log.error("couldn't save config: %s", e)


def mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def euler_to_rot(rx, ry, rz):
    rx, ry, rz = (math.radians(v) for v in (rx, ry, rz))
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    X = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]
    Y = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
    Z = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]
    return mat_mul(mat_mul(Z, Y), X)


def to_hmd34(rot, pos):
    m = openvr.HmdMatrix34_t()
    for i in range(3):
        for j in range(3):
            m.m[i][j] = rot[i][j]
        m.m[i][3] = pos[i]
    return m


def wrist_transform(w):
    ox, oy, oz = w["offset"]
    rx, ry, rz = w["rotation_deg"]
    if w["hand"] == "right":         # mirror for the other hand
        ox, ry, rz = -ox, -ry, -rz
    return euler_to_rot(rx, ry, rz), [ox, oy, oz]


def push_image(overlay, handle, img, state_key, cache):
    """Upload a PIL RGBA image. Falls back to a temp PNG if raw upload is refused."""
    w, h = img.size
    data = img.tobytes()
    buf = (ctypes.c_char * len(data)).from_buffer_copy(data)
    try:
        overlay.setOverlayRaw(handle, buf, w, h, 4)
    except Exception:
        path = cache.get(state_key)
        if not path:
            path = os.path.join(tempfile.gettempdir(), f"fluffvr_{state_key}.png")
            cache[state_key] = path
        img.save(path)
        overlay.setOverlayFromFile(handle, path)


def push_raw(overlay, handle, frame, cache):
    data, w, h = frame
    buf = (ctypes.c_char * len(data)).from_buffer_copy(data)
    try:
        overlay.setOverlayRaw(handle, buf, w, h, 4)
    except Exception:
        push_image(overlay, handle, Image.frombytes("RGBA", (w, h), data), "screen", cache)


def keyboard_text(overlay):
    fn = overlay.function_table.getKeyboardText
    buf = ctypes.create_string_buffer(2048)
    fn(buf, 2048)
    return buf.value.decode("utf-8", "ignore").strip()


def make_icon(path, cfg):
    """SteamVR dashboard icon: your sticker on a little furry card."""
    t = ui.get_theme(cfg)
    s = 256
    img = ui.furry_frame(ui.theme_key(cfg), s, s, (14, 40, s - 14, s - 16), 40, 40).copy()
    frames, _ = ui.sticker_frames(176)
    if frames:
        fr = frames[0]
        img.alpha_composite(fr, ((s - fr.width) // 2, s - 22 - fr.height))
    else:
        ui.paw(ImageDraw.Draw(img), s / 2, s / 2 + 20, 46, t["primary"])
    img.save(path)


# --------------------------------------------------------------- state ---
class State:
    def __init__(self, cfg):
        self.cfg = cfg
        self.stats = {}
        self.chat = []           # (role, text)
        self.thinking = False
        self.ai_error = None
        self.tab = "Stats"
        self.chat_scroll = 0
        self.chat_content_top = 0
        self.dirty_cfg = False
        self.dash_dirty = True
        self.hud_dirty = True
        self.screen_info = {}
        self.extras = {"session_start": time.time()}
        self.alert = None           # {"text", "kind", "until"}
        self.mods_cat = "Performance"
        self.logo_frame = 0
        self.anim_slots = []
        self.errors = collections.deque(maxlen=6)    # {"text", "time"}
        self.errors_dismissed = False
        self.last_pat = 0
        self.music = {}
        self.discord = {}
        self.hud_hits = []
        self.hud_size = (1, 1)
        self.hud_pressed = None
        self.hud_pressed_t = 0
        self.kb_target = "chat"
        self.world = {}
        self.avatar = {}
        self.avatar_page = 0
        self.timer = {"mode": "timer", "running": False, "end": 0.0, "start": 0.0,
                      "left": 300.0, "elapsed": 0.0, "done_at": 0.0}
        self.afk = False
        self.afk_since = None
        self.walked = 0.0
        self.speed = 0.0
        self.pet_mood = "hiii :3"
        self.boost = {"status": {}, "heavy": [], "tip": 0, "calmed": set(), "msg": ""}
        self.hover_box = None
        self.cursor = None
        self.trail = []
        self.click_fx = []

    def last_reply(self):
        for role, text in reversed(self.chat):
            if role == "assistant":
                return text
        return ""


# ----------------------------------------------------------------- app ---
class QuitApp(Exception):
    """SteamVR is shutting down: exit cleanly, don't restart."""


class App:
    def __init__(self, cfg, vr):
        self.cfg = cfg
        try:
            import logo
            logo.STYLES.update({k: v for k, v in cfg.get("sticker_styles", {}).items()
                                if v in ("cutout", "card")})
            logo.sticker_frames.cache_clear()
        except Exception:
            pass
        self.state = State(self.cfg)
        self.vr = vr
        self.ov = openvr.IVROverlay()
        self._last_err = {}
        self.vr_errors = 0
        # flicker-free GPU textures (falls back to raw uploads if OpenGL can't start)
        self.gl = None
        self.gl_error = None
        try:
            if not cfg.get("gpu_textures", True):
                raise RuntimeError("turned off in config.json (gpu_textures)")
            self.gl = GLUploader(flip=cfg.get("gl_flip", True))
            log.info("GPU textures on: %s", self.gl.info)
        except Exception as e:
            self.gl_error = str(e)
            log.warning("GPU textures off, using raw uploads: %s", e)
        self.stats = StatsCollector(self.vr)
        self.file_cache = {}
        self.hit = ui.Hit()
        self.ctrl_index = None
        self.last_ctrl_check = 0
        self.hud_alpha = None

        # wrist HUD
        self.hud = self.ov.createOverlay("fluffvr.stats.hud", "Fluff VR Stats HUD")
        self.ov.setOverlaySortOrder(self.hud, 10)
        self.apply_wrist()

        # dashboard tab
        self.dash, self.thumb = self.ov.createDashboardOverlay("fluffvr.stats.dash", "Fluff VR Stats :3")
        self.ov.setOverlayWidthInMeters(self.dash, self.cfg.get("dashboard_width_m", 2.0))
        self.ov.setOverlayInputMethod(self.dash, openvr.VROverlayInputMethod_Mouse)
        scale = openvr.HmdVector2_t()
        scale.v[0], scale.v[1] = ui.DASH_W, ui.DASH_H
        self.ov.setOverlayMouseScale(self.dash, scale)
        flags = [openvr.VROverlayFlags_SendVRSmoothScrollEvents]
        if self.cfg.get("cursor", "paw") != "steamvr":
            flags.append(openvr.VROverlayFlags_HideLaserIntersection)   # we draw a cute one
        for flag in flags:
            try:
                self.ov.setOverlayFlag(self.dash, flag, True)
            except Exception:
                pass
        # desktop mirror
        self.mirror = ScreenMirror(self.cfg)
        self.scr = self.ov.createOverlay("fluffvr.stats.screen", "Fluff VR Stats Screen")
        self.ov.setOverlaySortOrder(self.scr, 5)
        self.scr_placed = False
        self.scr_shown = False

        self.safe("icon", self.refresh_icon)

        # animated sticker logo
        self.dash_base = None
        self.logo_i = 0
        self.logo_ms = ui.sticker_frames(ui.LOGO_H)[1]

        # music + extra mods (ping, weather, VRChat OSC)
        self.music = Music()
        self.extras = Extras(self.cfg)
        self.extras.music = self.music
        self.discord = DiscordLink(self.cfg)
        self.last_discord_feed = 0
        self.vrclog = VRCLog()
        self.tweaks = Tweaks(self.cfg)
        self.last_prio = 0
        self.avatar = Avatar()
        self.extras.avatar = self.avatar
        self.last_motion = 0
        self.last_pos = None
        self.last_rot = None
        self.last_active = time.time()
        self.zoom_since = None
        self.speed = 0.0
        self.last_pet = 0
        self.join_batch = []
        self.join_batch_t = 0
        self.touch_armed = True
        self.last_touch = 0
        self.mouse_learned = None
        self.cursor_moved = False
        self.last_trail = 0
        self.miss_streak = 0
        self.clicks_logged = 0
        self.last_magic_check = 0
        self.last_break = time.time()
        self.low_fps_since = None
        self.last_low_alert = 0
        self.last_chatbox = 0
        self.last_chatbox_text = None
        self.last_chatbox_sent = 0
        self.last_ai_chatbox = 0

    # ---- error proofing
    def report(self, where, exc=None, msg=None, show=True):
        """Log an error, show the derpy error cat, keep running.
        A repeating error is logged in full once, then just counted (no log spam),
        and the popup only shows the first time (again after 10 min if it's still happening)."""
        text = msg or f"{where}: {type(exc).__name__}: {exc}"
        now = time.time()
        rec = self._last_err.get(text)
        if rec is None:
            rec = self._last_err[text] = {"first": now, "logged": 0, "shown": 0, "count": 0}
        rec["count"] += 1
        if now - rec["logged"] > 600:
            extra = f" (happened {rec['count']}x so far)" if rec["count"] > 1 else ""
            if exc is not None:
                log.error("%s%s\n%s", text, extra,
                          "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
            else:
                log.warning("%s%s", text, extra)
            rec["logged"] = now
        st = self.state
        for e in st.errors:
            if e["text"] == text:
                e["count"] = rec["count"]
                break
        else:
            st.errors.append({"text": text, "time": now, "count": 1})
        if now - rec["shown"] < 600:
            return
        rec["shown"] = now
        st.errors_dismissed = False
        st.dash_dirty = True
        if show:
            self.show_alert("oops! " + (msg or f"{where} hiccuped, still running :3"), "error", 6)

    def safe(self, where, fn, *args):
        try:
            return fn(*args)
        except (QuitApp, KeyboardInterrupt, SystemExit):
            raise
        except openvr.OpenVRError as e:
            self.vr_errors += 1
            self.report(where, e)
        except Exception as e:
            self.report(where, e)
        return None

    def push(self, handle, img=None, key="img", frame=None):
        """Send an image to an overlay. GPU texture path = no flashing."""
        if self.gl is not None:
            try:
                if frame is not None:
                    self.gl.push(self.ov, handle, None, data=frame[0], size=(frame[1], frame[2]))
                else:
                    self.gl.push(self.ov, handle, img)
                return
            except Exception as e:
                self.report("GPU texture", e, msg=f"GPU textures failed ({e}), switched to backup mode")
                try:
                    self.gl.close()
                except Exception:
                    pass
                self.gl = None
        if frame is not None:
            push_raw(self.ov, handle, frame, self.file_cache)
        else:
            push_image(self.ov, handle, img, key, self.file_cache)

    def close(self):
        """Stop helper threads (used before a reconnect so nothing doubles up)."""
        if self.gl is not None:
            self.gl.close()
            self.gl = None
        for part in (getattr(self, "extras", None), getattr(self, "mirror", None), getattr(self, "discord", None),
                     getattr(self, "music", None), getattr(self, "vrclog", None)):
            try:
                part.stop()
            except Exception:
                pass

    def refresh_icon(self):
        icon = os.path.join(HERE, "icon.png")
        make_icon(icon, self.cfg)
        self.ov.setOverlayFromFile(self.thumb, icon)

    # ---- startup intro + sound
    def play_sound(self):
        path = os.path.join(HERE, "assets", "startup.wav")
        if not (self.cfg.get("startup_sound", True) and os.path.exists(path)):
            return
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)

    def play_intro(self):
        if not self.cfg.get("intro", True):
            self.safe("startup sound", self.play_sound)
            return
        key = ui.theme_key(self.cfg)
        intro.prewarm(key)                       # bake the frames' heavy parts first
        ov = self.ov.createOverlay("fluffvr.stats.intro", "Fluff VR Stats Intro")
        try:
            self.ov.setOverlayWidthInMeters(ov, 1.25)
            self.ov.setOverlaySortOrder(ov, 50)
            self.ov.setOverlayTransformTrackedDeviceRelative(
                ov, openvr.k_unTrackedDeviceIndex_Hmd, to_hmd34(euler_to_rot(0, 0, 0), [0.0, -0.05, -1.35]))
            self.safe("startup sound", self.play_sound)
            start = time.perf_counter()
            shown = False
            while True:
                t = time.perf_counter() - start
                if t > intro.DURATION:
                    break
                self.poll_events()
                img = intro.frame(key, t, int(t * 10))
                self.push(ov, img, "intro")
                fade = 1.0 if t < intro.FADE_START else \
                    max(0.0, 1 - (t - intro.FADE_START) / (intro.DURATION - intro.FADE_START))
                self.ov.setOverlayAlpha(ov, fade)
                if not shown:
                    self.ov.showOverlay(ov)
                    shown = True
                time.sleep(max(0.0, 1 / 30 - (time.perf_counter() - start - t)))
        finally:
            try:
                if self.gl is not None:
                    self.gl.forget(ov)
                self.ov.destroyOverlay(ov)
            except Exception:
                pass

    # ---- wrist placement
    def apply_wrist(self):
        w = self.cfg["wrist"]
        self.ov.setOverlayWidthInMeters(self.hud, w["width_m"])
        if self.ctrl_index is not None:
            rot, pos = wrist_transform(w)
            self.ov.setOverlayTransformTrackedDeviceRelative(self.hud, self.ctrl_index, to_hmd34(rot, pos))
        self.hud_alpha = None

    # ---- desktop screen placement
    def place_screen(self):
        sc = self.cfg["screen"]
        if sc["attach"] == "hand":
            role = openvr.TrackedControllerRole_RightHand if self.cfg["wrist"]["hand"] == "left" \
                else openvr.TrackedControllerRole_LeftHand
            idx = self.vr.getTrackedDeviceIndexForControllerRole(role)
            if idx == openvr.k_unTrackedDeviceIndexInvalid:
                return False
            self.ov.setOverlayWidthInMeters(self.scr, min(sc["width_m"], 0.5))
            rot = euler_to_rot(-45, 0, 0)            # held like a tablet above the hand
            self.ov.setOverlayTransformTrackedDeviceRelative(
                self.scr, idx, to_hmd34(rot, [0.0, 0.12, -0.08]))
            return True
        poses = (openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount)()
        self.vr.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseStanding, 0, poses)
        hp = poses[openvr.k_unTrackedDeviceIndex_Hmd]
        if not hp.bPoseIsValid:
            return False
        H = hp.mDeviceToAbsoluteTracking.m
        fx, fz = -H[0][2], -H[2][2]                  # headset forward, flattened
        ln = math.hypot(fx, fz) or 1
        fx, fz = fx / ln, fz / ln
        d = sc.get("distance_m", 1.3)
        pos = [H[0][3] + fx * d, H[1][3] - 0.1, H[2][3] + fz * d]
        yaw = math.degrees(math.atan2(-fx, -fz))     # face back toward you
        self.ov.setOverlayWidthInMeters(self.scr, sc["width_m"])
        self.ov.setOverlayTransformAbsolute(self.scr, openvr.TrackingUniverseStanding,
                                            to_hmd34(euler_to_rot(0, yaw, 0), pos))
        return True

    def update_screen(self):
        sc = self.cfg["screen"]
        if not sc["enabled"]:
            if self.scr_shown:
                self.ov.hideOverlay(self.scr)
                self.scr_shown = False
            return
        if not self.scr_placed:
            self.scr_placed = self.place_screen()
        frame = self.mirror.take()
        if frame:
            self.push(self.scr, frame=frame)
            if not self.scr_shown and self.scr_placed:
                self.ov.showOverlay(self.scr)
                self.scr_shown = True

    def find_controller(self):
        role = openvr.TrackedControllerRole_LeftHand if self.cfg["wrist"]["hand"] == "left" \
            else openvr.TrackedControllerRole_RightHand
        idx = self.vr.getTrackedDeviceIndexForControllerRole(role)
        if idx == openvr.k_unTrackedDeviceIndexInvalid:
            idx = None
        if idx != self.ctrl_index:
            self.ctrl_index = idx
            if idx is None:
                self.ov.hideOverlay(self.hud)
            else:
                self.apply_wrist()
                self.ov.showOverlay(self.hud)

    def update_alpha(self):
        target = self.cfg["wrist"]["opacity"]
        alerting = self.state.alert and time.time() < self.state.alert["until"]
        if self.cfg["modules"]["look_to_show"] and self.ctrl_index is not None and not alerting:
            poses = (openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount)()
            self.vr.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseStanding, 0, poses)
            hp, cp = poses[openvr.k_unTrackedDeviceIndex_Hmd], poses[self.ctrl_index]
            if hp.bPoseIsValid and cp.bPoseIsValid:
                C = cp.mDeviceToAbsoluteTracking.m
                crot = [[C[i][j] for j in range(3)] for i in range(3)]
                rot, pos = wrist_transform(self.cfg["wrist"])
                wrot = mat_mul(crot, rot)
                wpos = [sum(crot[i][k] * pos[k] for k in range(3)) + C[i][3] for i in range(3)]
                normal = [wrot[i][2] for i in range(3)]          # overlay faces +Z
                H = hp.mDeviceToAbsoluteTracking.m
                to_eye = [H[i][3] - wpos[i] for i in range(3)]
                ln = math.sqrt(sum(v * v for v in to_eye)) or 1
                facing = sum(normal[i] * to_eye[i] / ln for i in range(3))
                k = max(0.0, min(1.0, (facing - 0.45) / 0.3))   # fade between ~63° and ~40°
                target *= k * k * (3 - 2 * k)
        if self.hud_alpha is None or abs(target - self.hud_alpha) > 0.02:
            # ease toward target so it fades instead of popping
            a = target if self.hud_alpha is None else self.hud_alpha + (target - self.hud_alpha) * 0.35
            self.hud_alpha = a
            self.ov.setOverlayAlpha(self.hud, max(0.0, min(1.0, a)))

    # ---- actions from dashboard clicks
    def do(self, action, args):
        st, cfg = self.state, self.cfg
        if action == "tab":
            st.tab = args[0]
            st.chat_scroll = 0
            if st.tab == "Boost":
                self.safe("boost status", self.refresh_boost)
        elif action == "toggle":
            cfg["modules"][args[0]] = not cfg["modules"][args[0]]
            st.dirty_cfg = st.hud_dirty = True
            self.hud_alpha = None
        elif action in ("theme", "style_set"):
            if action == "theme":
                cfg["theme"] = args[0]
            else:
                cfg["style"][args[0]] = args[1]
            st.dirty_cfg = st.hud_dirty = True
            self.safe("icon", self.refresh_icon)
        elif action == "mods_cat":
            st.mods_cat = args[0]
        elif action == "hand":
            cfg["wrist"]["hand"] = args[0]
            self.ctrl_index = -1          # force re-attach
            self.find_controller()
            st.dirty_cfg = True
        elif action == "size":
            cfg["wrist"]["width_m"] = round(min(0.4, max(0.06, cfg["wrist"]["width_m"] + args[0])), 3)
            self.apply_wrist()
            st.dirty_cfg = True
        elif action == "opacity":
            cfg["wrist"]["opacity"] = round(min(1.0, max(0.2, cfg["wrist"]["opacity"] + args[0])), 2)
            self.hud_alpha = None
            st.dirty_cfg = True
        elif action == "move":
            cfg["wrist"]["offset"][args[0]] = round(cfg["wrist"]["offset"][args[0]] + args[1], 3)
            self.apply_wrist()
            st.dirty_cfg = True
        elif action == "rot":
            cfg["wrist"]["rotation_deg"][args[0]] = (cfg["wrist"]["rotation_deg"][args[0]] + args[1]) % 360
            self.apply_wrist()
            st.dirty_cfg = True
        elif action == "reset_wrist":
            cfg["wrist"].update(json.loads(json.dumps(DEFAULT_WRIST)))
            self.apply_wrist()
            st.dirty_cfg = True
        elif action == "type":
            if self.open_keyboard("Talk to Fluff", "", "chat") and cfg["modules"].get("typing_indicator"):
                osc.typing(True, cfg.get("osc_port", 9000))
        elif action == "music":
            self.music.command(args[0])
        elif action in ("tw_apply", "tw_undo", "tw_all", "tw_undo_all"):
            keys = [args[0]] if args else [k for k, _, _ in TWEAKS]
            fails = []
            for k in keys:
                try:
                    (self.tweaks.apply if action in ("tw_apply", "tw_all") else self.tweaks.undo)(k)
                except Exception as e:
                    fails.append(f"{k}: {e}")
                    log.warning("tweak %s %s failed: %s", action, k, e)
            st.boost["msg"] = "; ".join(fails)[:140]
            st.boost["status"] = self.tweaks.status(force=True)
            st.dirty_cfg = True
            if not fails and action == "tw_all":
                self.show_alert("BOOSTED!! ur PC is in VR mode now :3", secs=5)
        elif action == "tw_heavy":
            self.tweaks.sample_heavy()
            st.boost["sampling"] = True
        elif action == "tw_calm":
            if self.tweaks.calm(args[0]):
                st.boost["calmed"].add(args[0])
        elif action == "tip_next":
            st.boost["tip"] = st.boost.get("tip", 0) + 1
        elif action == "timer":
            self.timer_action(*args)
        elif action == "av_set":
            self.avatar.set(args[0], args[1], cfg.get("osc_port", 9000))
        elif action == "av_page":
            st.avatar_page = max(0, st.avatar_page + args[0])
        elif action == "av_refresh":
            self.avatar.load_latest()
        elif action == "cb_line":
            ln = cfg["chatbox"]["lines"]
            ln[args[0]] = not ln.get(args[0], False)
            st.dirty_cfg = True
        elif action == "cb_set":
            cfg["chatbox"][args[0]] = args[1]
            st.dirty_cfg = True
        elif action == "cb_status":
            cb = cfg["chatbox"]
            sts = cb.setdefault("statuses", [])
            n = max(1, len(sts))
            i = cb.get("status_index", 0) % n
            if args[0] == "prev":
                cb["status_index"] = (i - 1) % n
            elif args[0] == "next":
                cb["status_index"] = (i + 1) % n
            elif args[0] == "edit":
                self.open_keyboard("Edit status", sts[i] if sts else "", ("status", i))
            elif args[0] == "add":
                self.open_keyboard("New status", "", ("status", None))
            elif args[0] == "delete" and sts:
                sts.pop(i)
                cb["status_index"] = max(0, i - 1)
            st.dirty_cfg = True
        elif action == "clear_chat":
            st.chat.clear()
            st.ai_error = None
            st.hud_dirty = True
        elif action == "screen_toggle":
            cfg["screen"]["enabled"] = not cfg["screen"]["enabled"]
            self.scr_placed = False
            st.dirty_cfg = True
        elif action == "screen_set":
            cfg["screen"][args[0]] = args[1]
            if args[0] == "attach":
                self.scr_placed = False
            st.dirty_cfg = True
        elif action == "screen_size":
            cfg["screen"]["width_m"] = round(min(4.0, max(0.4, cfg["screen"]["width_m"] + args[0])), 2)
            self.scr_placed = False
            st.dirty_cfg = True
        elif action == "screen_here":
            if not cfg["screen"]["enabled"]:
                cfg["screen"]["enabled"] = True
                st.dirty_cfg = True
            self.scr_placed = False
        elif action == "dismiss_errors":
            st.errors_dismissed = True
        elif action == "pat_floof":
            cfg["floof_pats"] = cfg.get("floof_pats", 0) + 1
            st.last_pat = time.time()
            st.dirty_cfg = True
        elif action == "join_discord":
            link = self.discord.invite()
            if link:
                import webbrowser
                webbrowser.open(link)
                self.show_alert("opened the Discord invite on ur desktop :3", secs=5)
            else:
                self.show_alert("no Discord invite set yet", "warn", 5)
        elif action == "scroll":
            self.scroll(args[0] * 120)
        st.dash_dirty = True

    def mouse_flipped(self):
        """SteamVR reports laser y from the bottom for raw textures but from the top for
        OpenGL textures. 'auto' picks by texture mode and self-corrects if clicks keep missing."""
        mode = self.cfg.get("mouse_y", "auto")
        if mode == "flip":
            return True
        if mode == "noflip":
            return False
        if self.mouse_learned is not None:
            return self.mouse_learned
        return self.gl is None

    def on_hover(self, mx, my):
        y = ui.DASH_H - my if self.mouse_flipped() else my
        now = time.time()
        st = self.state
        if st.cursor is not None and (now - self.last_trail > 0.03):
            self.last_trail = now
            st.trail.append((st.cursor[0], st.cursor[1], now))
            del st.trail[:-10]
        st.cursor = (mx, y)
        self.cursor_moved = True
        box = self.hit.find_box(mx, y)
        if box != self.state.hover_box:
            self.state.hover_box = box
            self.t["logo"] = 0          # repaint right away (cheap: only the overlay pass)

    def on_click(self, mx, my):
        H = ui.DASH_H
        flip = self.mouse_flipped()
        y_main, y_alt = (H - my, my) if flip else (my, H - my)
        self.state.click_fx.append((mx, y_main, time.time()))
        del self.state.click_fx[:-4]
        self.cursor_moved = True
        action, args = self.hit.find(mx, y_main)
        if self.clicks_logged < 8:
            self.clicks_logged += 1
            log.info("click raw=(%.0f,%.0f) flip=%s -> %s", mx, my, flip, action)
        if action:
            self.miss_streak = 0
            self.safe(f"button '{action}'", self.do, action, args)
            return
        alt, alt_args = self.hit.find(mx, y_alt)
        if alt and self.cfg.get("mouse_y", "auto") == "auto":
            # clicked empty space, but the mirrored spot is a button -> probably flipped
            self.miss_streak += 1
            if self.miss_streak >= 2:
                self.mouse_learned = not flip
                self.miss_streak = 0
                log.info("laser looked upside down, switched mouse flip to %s", self.mouse_learned)
                self.show_alert("fixed ur laser aim :3 click again!", secs=4)

    def refresh_boost(self):
        st = self.state
        st.boost["status"] = self.tweaks.status(force=True)
        if not st.boost.get("heavy"):
            self.tweaks.sample_heavy()
            st.boost["sampling"] = True

    def timer_action(self, what, val=None):
        tm, now = self.state.timer, time.time()
        if what == "mode":
            tm.update(mode="stopwatch" if tm["mode"] == "timer" else "timer", running=False,
                      elapsed=0.0, left=300.0)
        elif what == "add":
            if tm["mode"] == "timer":
                if tm["running"]:
                    tm["end"] += val
                else:
                    tm["left"] = max(0.0, tm["left"] + val)
        elif what == "toggle":
            if tm["running"]:
                if tm["mode"] == "timer":
                    tm["left"] = max(0.0, tm["end"] - now)
                else:
                    tm["elapsed"] += now - tm["start"]
                tm["running"] = False
            else:
                if tm["mode"] == "timer":
                    if tm["left"] <= 0:
                        tm["left"] = 300.0
                    tm["end"] = now + tm["left"]
                else:
                    tm["start"] = now
                tm["running"] = True
        elif what == "reset":
            tm.update(running=False, elapsed=0.0, left=300.0 if tm["mode"] == "timer" else 0.0)
        self.state.hud_dirty = True

    def play_ding(self):
        path = os.path.join(HERE, "assets", "ding.wav")
        if sys.platform == "win32" and os.path.exists(path):
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)

    def open_keyboard(self, desc, existing, target):
        try:
            self.ov.showKeyboardForOverlay(
                self.dash, openvr.k_EGamepadTextInputModeNormal,
                openvr.k_EGamepadTextInputLineModeSingleLine,
                openvr.KeyboardFlag_Modal, desc, 120 if target != "chat" else 500, existing or "", 0)
            self.state.kb_target = target
            return True
        except Exception as e:
            self.report("keyboard", e, msg=f"couldn't open the SteamVR keyboard ({e})")
            return False

    def keyboard_done(self, text):
        st = self.state
        target, st.kb_target = st.kb_target, "chat"
        if target == "chat":
            self.send_chat(text)
            return
        if isinstance(target, tuple) and target[0] == "status":
            text = text.strip()[:60]
            sts = self.cfg["chatbox"].setdefault("statuses", [])
            if target[1] is None:
                if text:
                    sts.append(text)
                    self.cfg["chatbox"]["status_index"] = len(sts) - 1
            elif target[1] < len(sts):
                if text:
                    sts[target[1]] = text
                else:
                    sts.pop(target[1])
            st.dirty_cfg = st.dash_dirty = True

    def scroll(self, amount):
        st = self.state
        top_room = max(0, (ui.DASH_H * 0.25) - st.chat_content_top) + st.chat_scroll
        st.chat_scroll = max(0, min(st.chat_scroll + amount, top_room))
        st.dash_dirty = True

    def send_chat(self, text):
        st = self.state
        if not text or st.thinking:
            return
        st.chat.append(("user", text))
        st.thinking, st.ai_error, st.chat_scroll = True, None, 0
        st.dash_dirty = True

        def done(reply, err):
            st.thinking = False
            if err:
                st.ai_error = err
                self.report("AI", msg=err, show=False)
            else:
                st.chat.append(("assistant", reply))
                if self.cfg["modules"]["ai_to_chatbox"]:
                    osc.chatbox(reply, self.cfg.get("osc_port", 9000))
                    self.last_ai_chatbox = time.time()
            st.dash_dirty = st.hud_dirty = True
        ai.ask_async(self.cfg, list(st.chat), done)

    # ---- events
    def poll_events(self):
        ev = openvr.VREvent_t()
        while self.vr.pollNextEvent(ev):
            if ev.eventType == openvr.VREvent_Quit:
                try:
                    self.vr.acknowledgeQuit_Exiting()
                finally:
                    raise QuitApp()
            if ev.eventType in (openvr.VREvent_TrackedDeviceActivated,
                                openvr.VREvent_TrackedDeviceDeactivated,
                                openvr.VREvent_TrackedDeviceRoleChanged):
                self.last_ctrl_check = 0
        while True:
            ok, ev = self.ov.pollNextOverlayEvent(self.dash, ev)
            if not ok:
                break
            t = ev.eventType
            if t == openvr.VREvent_MouseButtonDown:
                self.safe("click", self.on_click, ev.data.mouse.x, ev.data.mouse.y)
            elif t == openvr.VREvent_MouseMove:
                self.safe("hover", self.on_hover, ev.data.mouse.x, ev.data.mouse.y)
            elif t == openvr.VREvent_ScrollSmooth and self.state.tab == "Chat":
                self.scroll(ev.data.scroll.ydelta * 60)
            elif t == openvr.VREvent_KeyboardDone:
                self.safe("typing", self.stop_typing)
                self.safe("keyboard", self.keyboard_done, keyboard_text(self.ov))
            elif t == openvr.VREvent_KeyboardClosed:
                self.stop_typing()
            elif t in (getattr(openvr, "VREvent_FocusLeave", -1), openvr.VREvent_OverlayHidden):
                self.state.cursor = None
                self.state.hover_box = None
                self.t["logo"] = 0
            elif t in (openvr.VREvent_OverlayShown, openvr.VREvent_DashboardActivated):
                self.state.dash_dirty = True

    def stop_typing(self):
        if self.cfg["modules"].get("typing_indicator"):
            osc.typing(False, self.cfg.get("osc_port", 9000))

    # ---- extra mods
    def show_alert(self, text, kind="info", secs=8):
        self.state.alert = {"text": text, "kind": kind, "until": time.time() + secs}
        self.state.hud_dirty = True
        self.hud_alpha = None

    def tick_extras(self, now):
        st, m = self.state, self.cfg["modules"]
        # pull fresh data from the helper threads
        if self.extras.changed:
            self.extras.changed = False
            old_pats = st.extras.get("headpats")
            st.extras = self.extras.snapshot()
            if old_pats is not None and st.extras.get("headpats") != old_pats:
                st.dirty_cfg = True
                self.show_alert(f"headpat #{st.extras['headpats']}! good fluff~", secs=3)
            st.hud_dirty = st.dash_dirty = True
        # feed Discord rich presence (it only sends every 15s itself)
        if now - self.last_discord_feed > 5:
            self.last_discord_feed = now
            mu = st.music or {}
            song = None
            if mu.get("title") and mu.get("playing") is not False:
                song = f"{mu['title']} - {mu['artist']}" if mu.get("artist") else mu["title"]
            self.discord.status = {
                "fps": st.stats.get("fps"), "world": st.extras.get("world_name") or None,
                "song": song, "session_start": st.extras.get("session_start")}
            if self.discord.changed:
                self.discord.changed = False
                st.discord = self.discord.snapshot()
                st.dash_dirty = True
        # alert expired -> redraw so the banner goes away
        if st.alert and now > st.alert["until"]:
            st.alert = None
            st.hud_dirty = True
        # break reminder
        if m.get("break_reminder"):
            if now - self.last_break > self.cfg.get("break_minutes", 45) * 60:
                self.last_break = now
                self.show_alert(BREAK_MSGS[int(now) % len(BREAK_MSGS)], secs=12)
        else:
            self.last_break = now
        # low fps alert (sustained for 5s, then cool down 2 min)
        fps, ref = st.stats.get("fps"), st.stats.get("refresh")
        if m.get("low_fps_alert") and fps is not None and ref:
            if fps < ref * self.cfg.get("low_fps_ratio", 0.6):
                self.low_fps_since = self.low_fps_since or now
                if now - self.low_fps_since > 5 and now - self.last_low_alert > 120:
                    self.last_low_alert = now
                    self.show_alert(f"fps dipped to {fps:.0f}! try hiding some avatars", "warn", 8)
            else:
                self.low_fps_since = None
        # music snapshot (smoothly moving progress for the UI)
        new_music = self.music.snapshot()
        if self.music.changed:
            self.music.changed = False
            st.hud_dirty = True
            st.dash_dirty = True
        st.music = new_music
        # MagicChatbox running? (both apps would fight over the chatbox)
        if now - self.last_magic_check > 15:
            self.last_magic_check = now
            try:
                running = any("magicchatbox" in (p.info["name"] or "").lower()
                              for p in psutil.process_iter(["name"]))
            except Exception:
                running = False
            if self.extras.notes.get("magicchatbox") != running:
                self.extras.notes["magicchatbox"] = running
                self.extras.changed = True
        # VRChat world / players (from VRChat's log file)
        if self.vrclog.changed:
            self.vrclog.changed = False
            st.world = self.vrclog.snapshot()
            st.hud_dirty = True
            if st.tab == "World":
                st.dash_dirty = True
        evs = self.vrclog.pop_events()
        if evs and m.get("join_alerts"):
            self.join_batch += evs
            self.join_batch_t = self.join_batch_t or now
        if self.join_batch and now - self.join_batch_t > 1.5:
            joins = [n for k, n in self.join_batch if k == "join"]
            lefts = [n for k, n in self.join_batch if k == "leave"]
            parts = []
            if joins:
                parts.append(joins[0] + (f" +{len(joins) - 1}" if len(joins) > 1 else "") + " joined")
            if lefts:
                parts.append(lefts[0] + (f" +{len(lefts) - 1}" if len(lefts) > 1 else "") + " left")
            self.show_alert("  ·  ".join(parts), secs=4)
            self.join_batch, self.join_batch_t = [], 0
        # avatar toggles
        if self.avatar.changed:
            self.avatar.changed = False
            st.avatar = self.avatar.snapshot()
            if st.tab == "Avatar":
                st.dash_dirty = True
        # boost: keep VR at High priority, pull in heavy-apps results
        if now - self.last_prio > 8:
            self.last_prio = now
            self.safe("vr priority", self.tweaks.enforce_priority)
        if st.boost.get("sampling") and not self.tweaks.sampling:
            st.boost["sampling"] = False
            st.boost["heavy"] = list(self.tweaks.heavy)
            st.dash_dirty = True
        # motion: distance walked, zoomies, AFK
        if now - self.last_motion > 0.2:
            self.safe("motion", self.step_motion, now)
        # timer
        tm = st.timer
        if tm["running"] and tm["mode"] == "timer" and now >= tm["end"]:
            tm.update(running=False, left=0.0, done_at=now)
            self.show_alert("ding!! ur timer is done :3", secs=8)
            self.safe("ding", self.play_ding)
        if tm["running"] and int(now * 2) != int((now - 0.05) * 2):
            st.hud_dirty = True
        # pet mood
        if m.get("wrist_pet") and now - self.last_pet > 1:
            self.last_pet = now
            mood = self.pet_mood_text(now)
            if mood != st.pet_mood:
                st.pet_mood = mood
                st.hud_dirty = True
        # live values the chatbox + HUD can use
        w = st.world or {}
        st.extras.update(world_name=w.get("world", ""), world_players=len(w.get("players", [])),
                         world_type=w.get("type", ""), walked=st.walked,
                         afk_for=(now - st.afk_since) if st.afk and st.afk_since else 0)

        # VRChat chatbox stats (MagicChatbox-style)
        if m.get("chatbox_status") and now - self.last_ai_chatbox > 20:
            cb = self.cfg["chatbox"]
            if now - self.last_chatbox >= max(2, float(cb.get("interval_s", 3))):
                self.last_chatbox = now
                text = chatbox.compose(self.cfg, st.stats, st.extras, st.music, now)
                if text and (text != self.last_chatbox_text or now - self.last_chatbox_sent > 20):
                    self.last_chatbox_text, self.last_chatbox_sent = text, now
                    osc.chatbox(text, self.cfg.get("osc_port", 9000))

    def step_motion(self, now):
        st, m = self.state, self.cfg["modules"]
        dt = now - self.last_motion if self.last_motion else 0.2
        self.last_motion = now
        poses = (openvr.TrackedDevicePose_t * 1)()
        self.vr.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseStanding, 0, poses)
        hp = poses[0]
        if not hp.bPoseIsValid:
            return
        H_ = hp.mDeviceToAbsoluteTracking.m
        pos = (H_[0][3], H_[1][3], H_[2][3])
        fwd = (-H_[0][2], -H_[1][2], -H_[2][2])
        if self.last_pos is not None:
            d = math.hypot(pos[0] - self.last_pos[0], pos[2] - self.last_pos[2])
            if 0.004 < d < 1.0:                      # ignore jitter + teleport glitches
                st.walked += d
                self.cfg["walked_total_m"] = self.cfg.get("walked_total_m", 0) + d
            self.speed = 0.7 * self.speed + 0.3 * (d / max(dt, 1e-3))
            st.speed = self.speed
            turn = 1 - sum(a * b for a, b in zip(fwd, self.last_rot))
            if d > 0.01 or turn > 0.0008:
                self.last_active = now
        self.last_pos, self.last_rot = pos, fwd
        # zoomies!!
        if self.speed > 1.3:
            self.zoom_since = self.zoom_since or now
        else:
            self.zoom_since = None
        # AFK: headset off your head, or not moving for a while
        afk = False
        if m.get("afk_detect"):
            try:
                lvl = self.vr.getTrackedDeviceActivityLevel(openvr.k_unTrackedDeviceIndex_Hmd)
                if lvl in (getattr(openvr, "k_EDeviceActivityLevel_Standby", 3),
                           getattr(openvr, "k_EDeviceActivityLevel_Idle_Timeout", 4)):
                    afk = True
            except Exception:
                pass
            if now - self.last_active > float(self.cfg.get("afk_minutes", 5)) * 60:
                afk = True
        if afk != st.afk:
            if afk:
                st.afk_since = now - (0 if self.last_active > now - 5 else now - self.last_active)
            else:
                gone = now - (st.afk_since or now)
                if gone > 60:
                    self.show_alert(f"welcome back!! u were afk {ui.fmt_dur(gone)} :3", secs=6)
                st.afk_since = None
            st.afk = afk
            st.hud_dirty = True

    PET_IDLE = ["hiii :3", "u look cute today", "*wags tail*", "mrrp?", "stay hydrated ok",
                "headpats pls", "*happy floof noises*", "ur doing great!!", "zzz... jk im awake"]

    def pet_mood_text(self, now):
        st = self.state
        if st.afk:
            return "zzz... *curled up asleep*"
        if st.timer.get("done_at") and now - st.timer["done_at"] < 8:
            return "DING DING DING!!"
        if self.zoom_since and now - self.zoom_since > 0.8:
            return "ZOOMIES!!! *runs in circles*"
        fps, ref = st.stats.get("fps"), st.stats.get("refresh")
        if fps and ref and fps < ref * 0.6:
            return "it's so laggy in here >_<"
        if st.alert and "headpat" in st.alert.get("text", "") and now < st.alert["until"]:
            return "hehe PATS!! <3"
        if st.alert and "joined" in st.alert.get("text", "") and now < st.alert["until"]:
            return "ooh a new friend!!"
        mu = st.music or {}
        if mu.get("playing") and mu.get("title") and int(now / 12) % 2 == 0:
            return f"vibin to {mu['title']} ~"
        if st.extras.get("muted"):
            return "shhh ur muted :x"
        return self.PET_IDLE[int(now / 20) % len(self.PET_IDLE)]

    # ---- tap your wrist with the other controller
    def check_touch(self):
        if not self.cfg["modules"].get("music_controls") or self.ctrl_index is None \
                or (self.hud_alpha or 0) < 0.3 or not self.state.hud_hits:
            return
        other_role = openvr.TrackedControllerRole_RightHand if self.cfg["wrist"]["hand"] == "left" \
            else openvr.TrackedControllerRole_LeftHand
        oi = self.vr.getTrackedDeviceIndexForControllerRole(other_role)
        if oi == openvr.k_unTrackedDeviceIndexInvalid:
            return
        poses = (openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount)()
        self.vr.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseStanding, 0, poses)
        hp, op = poses[self.ctrl_index], poses[oi]
        if not (hp.bPoseIsValid and op.bPoseIsValid):
            return
        # fingertip = point a little in front of the other controller
        O = op.mDeviceToAbsoluteTracking.m
        off = self.cfg.get("touch_offset", [0.0, -0.015, -0.05])
        tip = [sum(O[i][k] * off[k] for k in range(3)) + O[i][3] for i in range(3)]
        # HUD panel pose in the world
        C = hp.mDeviceToAbsoluteTracking.m
        crot = [[C[i][j] for j in range(3)] for i in range(3)]
        rot, pos = wrist_transform(self.cfg["wrist"])
        wrot = mat_mul(crot, rot)
        wpos = [sum(crot[i][k] * pos[k] for k in range(3)) + C[i][3] for i in range(3)]
        rel = [tip[i] - wpos[i] for i in range(3)]
        local = [sum(wrot[k][i] * rel[k] for k in range(3)) for i in range(3)]   # R^T * rel
        iw, ih = self.state.hud_size
        wm = self.cfg["wrist"]["width_m"]
        hm = wm * ih / max(1, iw)
        depth = self.cfg.get("touch_depth_m", 0.03)
        inside = abs(local[0]) <= wm / 2 and abs(local[1]) <= hm / 2
        if not inside or abs(local[2]) > depth * 1.6:
            self.touch_armed = True             # finger left -> next touch can fire
            return
        if abs(local[2]) > depth or not self.touch_armed or time.time() - self.last_touch < 0.4:
            return
        px = (local[0] / wm + 0.5) * iw
        py = (0.5 - local[1] / hm) * ih
        for (x0, y0, x1, y1), cmd in self.state.hud_hits:
            if x0 <= px <= x1 and y0 <= py <= y1:
                self.touch_armed = False
                self.last_touch = time.time()
                self.music.command(cmd)
                self.state.hud_pressed, self.state.hud_pressed_t = cmd, time.time()
                self.state.hud_dirty = True
                try:
                    self.vr.triggerHapticPulse(oi, 0, 1500)    # little buzz (if supported)
                except Exception:
                    pass
                break

    # ---- main loop
    def run(self):
        st = self.state
        self.vr_errors = 0
        self.t = {"hud": 0, "stats": 0, "dash": 0, "save": 0, "logo": 0}
        for note in CFG_NOTICE:
            self.report("config", msg=note)
        CFG_NOTICE.clear()
        if self.cfg.get("first_run", True):
            self.cfg["first_run"] = False
            st.tab = "<3"
            st.dirty_cfg = True
            self.show_alert("thanks for downloading!! open the SteamVR menu for a lil surprise <3", secs=14)
        while True:
            now = time.time()
            self.vr_errors = 0
            # every step is isolated: if one breaks, the rest keep going
            self.safe("events", self.poll_events)
            self.safe("controllers", self.step_controllers, now)
            self.safe("stats", self.step_stats, now)
            self.safe("wrist HUD", self.step_hud, now)
            self.safe("dashboard", self.step_dash, now)
            self.safe("extras", self.tick_extras, now)
            self.safe("fade", self.update_alpha)
            self.safe("wrist touch", self.check_touch)
            self.safe("desktop screen", self.update_screen)
            if st.dirty_cfg and now - self.t["save"] > 1:
                st.dirty_cfg = False
                self.t["save"] = now
                save_cfg(self.cfg)
            if self.vr_errors >= 4:      # SteamVR itself is gone or broken -> reconnect
                raise ConnectionError("lost connection to SteamVR")
            # 20 Hz loop is plenty for the HUD; speed up only while the desktop mirror needs it
            sc = self.cfg["screen"]
            time.sleep(0.02 if sc.get("enabled") and sc.get("fps", 15) > 15 else 0.05)

    def step_controllers(self, now):
        if now - self.last_ctrl_check > 3:
            self.last_ctrl_check = now
            self.find_controller()
            if self.cfg["screen"]["attach"] == "hand":
                self.scr_placed = False          # follow controller reconnects

    def step_stats(self, now):
        st = self.state
        hud_period = 1.0 / max(0.5, float(self.cfg.get("hud_refresh_hz", 2)))
        if now - self.t["stats"] > hud_period:
            self.t["stats"] = now
            st.stats = self.stats.collect()
            st.hud_dirty = True
            info = {"monitors": self.mirror.monitor_count, "error": self.mirror.error}
            if info != st.screen_info:
                st.screen_info = info
                st.dash_dirty = True
            if st.tab in ("Stats", "Music", "Chatbox"):
                st.dash_dirty = True

    def step_hud(self, now):
        st = self.state
        if st.hud_dirty and self.ctrl_index is not None and (self.hud_alpha or 0) > 0.01 \
                or (st.hud_dirty and now - self.t["hud"] > 5):
            st.hud_dirty = False
            self.t["hud"] = now
            self.push(self.hud, ui.render_hud(st), "hud")

    def step_dash(self, now):
        st = self.state
        if not self.ov.isOverlayVisible(self.dash):
            return
        if st.dash_dirty or (st.thinking and now - self.t["dash"] > 0.5):
            st.dash_dirty = False
            self.t["dash"] = now
            st.logo_frame = None                     # logo is pasted on separately
            self.dash_base, self.hit = ui.render_dashboard(st)
            self.t["logo"] = 0
        anim_ok = self.gl is not None or self.t["logo"] == 0
        fx_live = st.cursor is not None and (self.cursor_moved or any(now - c[2] < 0.6 for c in st.click_fx)
                                              or any(now - tr[2] < 0.45 for tr in st.trail))
        due = now - self.t["logo"] >= (1 / 30 if fx_live else self.logo_ms / 1000)
        if self.dash_base and anim_ok and due:
            self.cursor_moved = False
            # only the little stickers animate: cheap paste, no full redraw
            self.t["logo"] = now
            if self.cfg.get("animate_logo", True):
                self.logo_i += 1
            th = ui.get_theme(self.cfg)
            frame = ui.draw_hover(ui.add_logo(self.dash_base, self.logo_i, st.anim_slots), st.hover_box, th)
            if self.cfg.get("cursor", "paw") != "steamvr":
                trail = [(x, y, now - t0) for x, y, t0 in st.trail]
                clicks = [(x, y, now - t0) for x, y, t0 in st.click_fx]
                frame = ui.draw_cursor(frame, st.cursor, trail, clicks, th, self.cfg.get("cursor", "paw"))
            self.push(self.dash, frame, "dash")


def lower_priority():
    try:
        p = psutil.Process()
        if sys.platform == "win32":
            p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        else:
            p.nice(10)
    except Exception:
        pass


def connect_steamvr():
    """Waits for SteamVR instead of failing, so you can start this first."""
    waited = False
    while True:
        try:
            return openvr.init(openvr.VRApplication_Overlay)
        except openvr.OpenVRError as e:
            if not waited:
                print("  waiting for SteamVR to start... (close this window to cancel)")
                log.info("waiting for SteamVR: %s", e)
                waited = True
            time.sleep(5)


def ensure_gl_packages():
    """One-time self-install of the GPU texture packages if they're missing."""
    import importlib.util
    need = [p for p, mod in (("glfw", "glfw"), ("PyOpenGL", "OpenGL"), ("numpy", "numpy"), ("pypresence", "pypresence"))
            if importlib.util.find_spec(mod) is None]
    if not need:
        return
    import importlib
    import subprocess
    import gltex
    print("  installing GPU + Discord support (one time, ~20s)...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", *need],
                       timeout=180, check=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        importlib.invalidate_caches()
        importlib.reload(gltex)
        globals()["GLUploader"] = gltex.GLUploader
        log.info("installed glfw + PyOpenGL")
    except Exception as e:
        log.warning("couldn't auto-install GL packages: %s", e)
        print("  couldn't install it automatically - run install.bat later (works fine without it, "
              "just might flicker)")


def ensure_music_packages(cfg):
    """One-time install of the Windows media packages (song info + album art + controls)."""
    if sys.platform != "win32" or cfg.get("tried_music_install"):
        return
    import importlib
    try:
        import winrt.windows.media.control  # noqa: F401
        import winrt.windows.storage.streams  # noqa: F401
        return
    except Exception:
        pass
    import subprocess
    print("  installing music support (one time)...")
    cfg["tried_music_install"] = True
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "winrt-runtime",
                        "winrt-Windows.Foundation", "winrt-Windows.Media.Control",
                        "winrt-Windows.Storage.Streams"], timeout=240, check=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        importlib.invalidate_caches()
        import music as _music
        importlib.reload(_music)
        globals()["Music"] = _music.Music
        log.info("installed winrt media packages")
    except Exception as e:
        log.warning("couldn't install music packages: %s", e)


def main():
    lower_priority()
    try:
        ensure_gl_packages()
    except Exception as e:
        log.warning("GL package check failed: %s", e)
    cfg = load_cfg()
    try:
        ensure_music_packages(cfg)
    except Exception as e:
        log.warning("music package check failed: %s", e)
    restarts = collections.deque(maxlen=5)
    first = True
    while True:
        vr = connect_steamvr()
        app = None
        try:
            app = App(cfg, vr)
            threading.excepthook = lambda a: app.report(f"background task ({a.thread.name})", a.exc_value)
            if first:
                print("  Fluff VR Stats :3 is running! look at ur wrist, or open the SteamVR menu.")
                app.safe("intro", app.play_intro)
                first = False
            app.run()
        except (QuitApp, KeyboardInterrupt):
            log.info("SteamVR closed - bye!")
            break
        except openvr.error_code.OverlayError_KeyInUse:
            print("  Fluff VR Stats is already running! (only one at a time pls :3)")
            log.warning("already running")
            _pause()
            break
        except Exception as e:
            log.error("crashed, restarting: %s\n%s", e, traceback.format_exc())
            print(f"  >w< hiccup ({e}), restarting in 3s...")
            restarts.append(time.time())
            if len(restarts) == restarts.maxlen and restarts[-1] - restarts[0] < 120:
                print("  too many crashes in a row, giving up. check logs/fluffvr.log")
                _pause()
                break
            time.sleep(3)
        finally:
            save_cfg(cfg)
            if app:
                app.close()
            try:
                openvr.shutdown()
            except Exception:
                pass


if __name__ == "__main__":
    main()
