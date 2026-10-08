"""
Fluff VR Stats :3 - a cute furry SteamVR overlay for VRChat.
  * Wrist HUD: FPS, frametimes, clock, batteries, PC load, music, ping, alerts, AI reply...
  * Dashboard tab (SteamVR menu): stats, global chat, desktop screen, mods, style, wrist placement

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
import random
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

import chatbox
import fluffnet
import fun as fun_mod
import intro
import lang
import osc
import ui
from extras import Extras
from gltex import GLUploader
from music import Music
from discord_link import DiscordLink
from zoom import Zoom
from gchat import GlobalChat
import zoom as zoom_mod
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
        "weather": False, "break_reminder": False, "look_to_show": True,
        "music_controls": True,
        "world_info": True, "join_alerts": True, "avatar_toggles": True, "afk_detect": True,
        "distance": True, "wrist_pet": True, "timer": True,
        "chatbox_status": False, "chatbox_song": False,
        "mute_indicator": False, "headpat_counter": True,
        "discord_presence": True,
        "battery_alert": True, "hydration_reminder": False, "vr_milestones": True, "zoom_lens": True,
        "boop_counter": False, "yap_meter": False, "jump_counter": False, "avatar_height": False,
        "mute_reminder": True, "song_toast": False, "kaomoji": False, "countdown": False,
        "vr_streak": True, "quote_of_hour": False, "theme_shuffle": False,
        "eye_break": False, "posture_reminder": False, "bedtime_alert": False, "pat_party": True,
        "wrist_kitty": True, "global_chat": True, "wrist_buttons": True,
        "pat_combo": True, "vibe_meter": False, "daily_goal": False, "world_timer": False, "met_today": False,
        "lucky_paw": False, "night_dim": False, "hot_gpu_alert": True, "ram_alert": True, "hourly_chime": False,
        "fps_drop_log": False, "battery_eta": False, "fluff_friends": True,
    },
    "language": "auto",                # Settings -> Language (auto = ur Windows language)
    "a11y": {"reduced_motion": False, "colorblind": False},
    "start_with_steamvr": False,
    "last_seen_version": "",
    "checklist_done": False,
    "safe_mode": False,
    "vr_goal_min": 60,
    "wrist_actions": ["zoom", "chatbox", "timer", "kitty", "gchat", "pat"],
    "gchat": {"name": "", "muted": [], "hud": True},
    "countdown": {"name": "my birthday", "date": ""},
    "eye_break_min": 20,
    "posture_min": 30,
    "bedtime": "01:00",
    "vr_days": {},
    "zoom": {"enabled": False, "mode": "gesture", "level": 3, "size_m": 0.24, "distance_m": 0.55, "fps": 30, "crosshair": True},
    "discord": {"app_id": "1557140907994910760", "guild_id": "1557135963510280202", "invite": "", "show_song": True,
                "hide_world": True},
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
    "boop_param": "",
    "boops_total": 0,
    "jumps_total": 0,
    "weather_location": "",
    "weather_units": "F",
    "ping_host": "1.1.1.1",
    "osc_port": 9000,
    "osc_listen_port": 9001,
    "animate_logo": True,
    "intro": True,
    "startup_sound": True,
    "first_run": True,
    "launch_mode": "ask",
    "auto_update": True,
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
    "dev_mode": False,                 # unlocks the hidden Dev tab (local toys only, for testing ur own client)
    "dev": {"fake_stats": False, "fps": 90, "gpu_temp": 70, "battery": 80, "fake_world": False,
            "spikes": False, "gold_skin": False},
}
CFG_NOTICE = []   # problems found while loading config, shown once the app is up

LUCKY = ["today's luck: ✨ amazing", "lucky paw says: get headpats", "fortune: someone thinks ur cute",
         "today's luck: big cuddle energy", "fortune: a new friend is near", "lucky paw: wear the cute outfit",
         "today's luck: 100% fluff", "fortune: dance like nobody's watching", "lucky paw: drink water, then vibe",
         "today's luck: tail wags incoming", "fortune: ur gonna laugh so hard", "lucky paw: be silly on purpose"]

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
    # the AI buddy was removed in v0.3.0: drop its wrist button + settings (incl. any saved API key)
    if isinstance(cfg.get("wrist_actions"), list) and "look" in cfg["wrist_actions"]:
        cfg["wrist_actions"] = [a for a in cfg["wrist_actions"] if a != "look"]
        if "pat" not in cfg["wrist_actions"]:
            cfg["wrist_actions"].append("pat")
    cfg.pop("ai", None)
    for k in ("last_ai_reply", "ai_to_chatbox", "typing_indicator", "ai_look"):
        cfg["modules"].pop(k, None)
    if not isinstance(cfg["chatbox"].get("statuses"), list):
        cfg["chatbox"]["statuses"] = list(chatbox.DEFAULT["statuses"])
    if cfg["style"].get("ears") not in ui.EAR_STYLES:
        cfg["style"]["ears"] = "cat"
    if cfg.get("language") not in lang.CODES:
        cfg["language"] = detect_language()
    lang.set_lang(cfg["language"])
    ui.COLORBLIND = bool(cfg.get("a11y", {}).get("colorblind"))
    return cfg


def detect_language():
    """first launch: use the same language as Windows (falls back to English)"""
    code = ""
    try:
        if sys.platform == "win32":
            import locale
            lid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            code = (locale.windows_locale.get(lid) or "")[:2]
        else:
            import locale
            code = (locale.getlocale()[0] or "")[:2]
    except Exception:
        code = ""
    return code.lower() if code.lower() in lang.CODES else "en"


# ---- safe mode: if the app crashes on launch twice in a row, start with every mod off
LAUNCH_FILE = os.path.join(HERE, "logs", "launch_state.json")


def launch_begin(cfg):
    """call at startup. Returns True if we're in safe mode this time."""
    try:
        with open(LAUNCH_FILE, encoding="utf-8") as f:
            stt = json.load(f)
    except (OSError, ValueError):
        stt = {}
    fails = int(stt.get("starting", 0))
    stt["starting"] = fails + 1
    try:
        with open(LAUNCH_FILE, "w", encoding="utf-8") as f:
            json.dump(stt, f)
    except OSError:
        pass
    if fails >= 2 and not cfg.get("safe_mode"):
        cfg["safe_mode_backup"] = dict(cfg["modules"])
        for k in cfg["modules"]:
            cfg["modules"][k] = False
        cfg["safe_mode"] = True
        save_cfg(cfg)
        log.warning("crashed on launch %d times -> safe mode (all mods off)", fails)
        return True
    return bool(cfg.get("safe_mode"))


def launch_ok():
    """the app has been running fine for a bit: reset the crash counter"""
    try:
        with open(LAUNCH_FILE, "w", encoding="utf-8") as f:
            json.dump({"starting": 0, "ok_at": time.time()}, f)
    except OSError:
        pass


def leave_safe_mode(cfg):
    back = cfg.pop("safe_mode_backup", None)
    if isinstance(back, dict):
        cfg["modules"].update({k: v for k, v in back.items() if k in cfg["modules"]})
    cfg["safe_mode"] = False


# ---- profiles: one tap to switch between a light setup and the full fluffy one
PROFILES = {
    "performance": {"label": "Performance", "on": ["fps", "frametime_graph", "gpu_cpu_ms", "reprojection", "pc_usage",
                                                   "low_fps_alert", "battery_alert", "hot_gpu_alert", "ram_alert", "clock",
                                                   "batteries", "look_to_show"], "hz": 1},
    "comfy": {"label": "Comfy", "on": ["fps", "clock", "batteries", "now_playing", "music_controls", "look_to_show",
                                       "wrist_pet", "wrist_kitty", "break_reminder", "hydration_reminder", "eye_break",
                                       "posture_reminder", "bedtime_alert", "night_dim", "battery_alert", "low_fps_alert"],
              "hz": 2},
    "full": {"label": "Full fluff", "on": "__all__", "hz": 2},
}


def apply_profile(cfg, key):
    p = PROFILES.get(key)
    if key == "custom":
        back = cfg.get("profile_custom")
        if isinstance(back, dict):
            cfg["modules"].update({k: v for k, v in back.items() if k in cfg["modules"]})
        cfg["profile"] = "custom"
        return True
    if not p:
        return False
    if cfg.get("profile", "custom") == "custom":
        cfg["profile_custom"] = dict(cfg["modules"])        # remember ur own picks
    on = set(cfg["modules"]) if p["on"] == "__all__" else set(p["on"])
    if p["on"] == "__all__":
        on -= {"theme_shuffle", "gpu_temp", "ping", "weather"}     # these need setup / change ur look
    for k in cfg["modules"]:
        cfg["modules"][k] = k in on
    cfg["hud_refresh_hz"] = p["hz"]
    cfg["profile"] = key
    return True


# ---- export / import / reset settings
EXPORT_DIR = os.path.join(HERE, "exports")
PRIVATE_KEYS = ("access", "gchat", "link")       # never exported (ur key + chat id stay on this PC)


def export_cfg(cfg):
    os.makedirs(EXPORT_DIR, exist_ok=True)
    out = {k: v for k, v in cfg.items() if k not in PRIVATE_KEYS and not k.startswith("_")}
    path = os.path.join(EXPORT_DIR, time.strftime("fluff-settings-%Y%m%d-%H%M%S.json"))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    return path


def latest_export():
    try:
        files = sorted(f for f in os.listdir(EXPORT_DIR) if f.endswith(".json"))
        return os.path.join(EXPORT_DIR, files[-1]) if files else None
    except OSError:
        return None


def import_cfg(cfg, path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or "modules" not in data:
        raise ValueError("that file isn't Fluff VR Stats settings")
    for k, v in data.items():
        if k in PRIVATE_KEYS or k.startswith("_"):
            continue
        cfg[k] = v
    _merge(cfg, DEFAULT_CFG)
    return cfg


def reset_cfg(cfg):
    """back to defaults, but keep ur key, chat name, kitty + badges (u'd be sad to lose those)"""
    export_cfg(cfg)                                   # backup first, just in case
    keep = {k: cfg.get(k) for k in ("access", "gchat", "kitty", "fun", "headpats_total", "boops_total",
                                     "jumps_total", "walked_total_m", "vr_days", "language", "first_run") if k in cfg}
    cfg.clear()
    cfg.update(json.loads(json.dumps(DEFAULT_CFG)))
    cfg.update({k: v for k, v in keep.items() if v is not None})
    cfg["checklist_done"] = True
    return cfg


def copy_to_clipboard(text):
    if sys.platform != "win32":
        return False
    try:
        import subprocess
        subprocess.run(["clip"], input=text.encode("utf-16le"), check=True, timeout=5,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return True
    except Exception:
        return False


def recent_logs(n=300):
    try:
        with open(LOG_PATH, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-n:]
    except OSError:
        lines = ["(no log yet)\n"]
    head = f"Fluff VR Stats {_version()} · {sys.platform} · python {sys.version.split()[0]}\n"
    return head + "".join(lines)


def conflicting_apps():
    """apps that fight with us over the chatbox / wrist"""
    names = {"magicchatbox.exe": "MagicChatbox", "xsoverlay.exe": "XSOverlay", "ovr toolkit.exe": "OVR Toolkit",
             "ovrtoolkit.exe": "OVR Toolkit", "vrchatosctools.exe": "OSC Tools"}
    found = set()
    try:
        for pr in psutil.process_iter(["name"]):
            nm = (pr.info.get("name") or "").lower()
            if nm in names:
                found.add(names[nm])
    except Exception:
        pass
    return sorted(found)


def whats_new(version):
    """the top section of CHANGELOG.md (for the 'what's new' card after an update)"""
    try:
        with open(os.path.join(HERE, "CHANGELOG.md"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return "", []
    parts = text.split("\n## ")
    if len(parts) < 2:
        return "", []
    sec = parts[1].split("\n")
    title = sec[0].strip()
    bullets = [ln.strip()[2:].replace("**", "") for ln in sec[1:] if ln.strip().startswith("- ")]
    return title, bullets


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


def _get_path(cfg, key):
    cur = cfg
    for k in key.split("."):
        cur = cur.get(k) if isinstance(cur, dict) else None
    return cur


def _set_path(cfg, key, val):
    parts = key.split(".")
    cur = cfg
    for k in parts[:-1]:
        cur = cur.setdefault(k, {})
    cur[parts[-1]] = val


# --------------------------------------------------------------- state ---
class State:
    def __init__(self, cfg):
        self.cfg = cfg
        self.stats = {}
        self.tab = "Home"
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
        self.gchat_scroll = 0
        self.desktop = False
        self.version = _version()
        self.dev_msg = ""
        self.fun_page = "badges"
        self.fun = None
        self.access = None
        self.friends = None
        self.cevents = None
        self.whatsnew = None          # (title, bullets) shown once after an update
        self.checklist = None         # first-run checklist card
        self.confirm = None           # (action, until) for "tap again to confirm"
        self.app_usage = {}
        self.safe_mode = False


def _version():
    try:
        with open(os.path.join(HERE, "VERSION"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "dev"


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

        # lil kitty on the other wrist
        import kitty as _kitty
        self.kitty_mod = _kitty
        self.kitty = _kitty.Kitty(self.cfg)
        self.kitty_ov = self.ov.createOverlay("fluffvr.stats.kitty", "Fluff VR Stats Kitty")
        self.ov.setOverlaySortOrder(self.kitty_ov, 11)
        self.ov.setOverlayWidthInMeters(self.kitty_ov, self.cfg.get("kitty_width_m", 0.11))
        self.kitty_idx = None
        self.kitty_shown = False
        self.kitty_t = 0
        self.kitty_touch = None          # (time, finger pos) while touching
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
        # zoom lens (magnifier that follows your head)
        self.zoom = Zoom(self.cfg)
        self.zoom_ov = self.ov.createOverlay("fluffvr.stats.zoom", "Fluff VR Stats Zoom")
        self.ov.setOverlaySortOrder(self.zoom_ov, 6)
        self.zoom_shown = False
        self.zoom_placed = None
        self.gesture_since = None
        self.scr_shown = False

        self.safe("icon", self.refresh_icon)

        # animated sticker logo
        self.dash_base = None
        self.logo_i = 0
        self.logo_ms = ui.sticker_frames(ui.LOGO_H)[1]

        # music + extra mods (ping, weather, VRChat OSC)
        self.music = Music()
        if not self.cfg.get("_pats_v2"):          # show the headpat counter on ur wrist by default now
            self.cfg["_pats_v2"] = True
            self.cfg["modules"]["headpat_counter"] = True
        self.extras = Extras(self.cfg)
        self.extras.music = self.music
        self.discord = DiscordLink(self.cfg)
        self.last_discord_feed = 0
        self.vrclog = VRCLog()
        self.tweaks = Tweaks(self.cfg)
        self.last_prio = 0
        self.avatar = Avatar()
        self.extras.avatar = self.avatar
        self.access = fluffnet.Access(self.cfg, self.state.version, client="pc", on_linked=self.on_linked)
        self.gchat = GlobalChat(self.cfg, client="pc", on_message=self.on_gchat, access=self.access)
        self.state.gchat = self.gchat
        self.fun = fun_mod.Fun(self.cfg)
        self.friends = fluffnet.Friends(self.cfg, client="pc", on_wave=self.on_wave, access=self.access)
        self.cevents = fluffnet.Events()
        st0 = self.state
        st0.fun, st0.access, st0.friends, st0.cevents = self.fun, self.access, self.friends, self.cevents
        st0.safe_mode = bool(self.cfg.get("safe_mode"))
        self.last_fun = 0
        self.started_at = time.time()
        self.launch_marked = False
        self.my_proc = psutil.Process()
        try:
            self.my_proc.cpu_percent(None)
        except Exception:
            pass
        self.last_usage = 0
        ver = self.state.version
        if self.cfg.get("last_seen_version") and self.cfg["last_seen_version"] != ver:
            st0.whatsnew = whats_new(ver)
        self.cfg["last_seen_version"] = ver
        if not self.cfg.get("checklist_done"):
            st0.checklist = True
        self.safe("SteamVR startup list", self.register_manifest)
        try:                   # a new version came out while u were playing -> tell u (installs next launch)
            import updater
            def _found(tag):
                self.state.extras["update_available"] = tag
                self.state.dash_dirty = True
                self.show_alert(f"update {tag} is out!! restart the app to get it :3", secs=12)
            updater.check_in_background(_found)
        except Exception:
            pass
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
        self.last_water = time.time()
        self.low_batt_warned = set()
        self.milestone_hours = 0
        self.last_eye = self.last_posture = time.time()
        self.bedtime_day = None
        self.mute_warned = False
        self.last_song_key = None
        self.last_vr_tick = time.time()
        self.contact_note_for = None
        self.pat_times = []
        self.update_vr_days(0)
        if self.cfg["modules"].get("theme_shuffle"):
            import random as _r
            self.cfg["theme"] = _r.choice([p[0] for p in ui.PRESETS])
        self.low_fps_since = None
        self.last_low_alert = 0
        self.last_chatbox = 0
        self.last_chatbox_text = None
        self.last_chatbox_sent = 0

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
        if getattr(self, "kitty_ov", None) is not None:
            try:
                self.ov.destroyOverlay(self.kitty_ov)
            except Exception:
                pass
        for part in (getattr(self, "friends", None), getattr(self, "cevents", None),
                     getattr(self, "extras", None), getattr(self, "mirror", None), getattr(self, "discord", None), getattr(self, "zoom", None), getattr(self, "gchat", None),
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

    def zoom_gesture(self):
        """True while either controller is held up to your face, like a telescope."""
        poses = (openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount)()
        self.vr.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseStanding, 0, poses)
        hp = poses[openvr.k_unTrackedDeviceIndex_Hmd]
        if not hp.bPoseIsValid:
            return False
        H = hp.mDeviceToAbsoluteTracking.m
        for role in (openvr.TrackedControllerRole_LeftHand, openvr.TrackedControllerRole_RightHand):
            idx = self.vr.getTrackedDeviceIndexForControllerRole(role)
            if idx == openvr.k_unTrackedDeviceIndexInvalid or not poses[idx].bPoseIsValid:
                continue
            C = poses[idx].mDeviceToAbsoluteTracking.m
            rel = [C[i][3] - H[i][3] for i in range(3)]
            loc = [sum(H[k][i] * rel[k] for k in range(3)) for i in range(3)]   # into headset space
            # in front of the face (z is backwards in SteamVR), near the eyes, not far off to the side
            if -0.20 < loc[2] < -0.02 and abs(loc[0]) < 0.11 and -0.10 < loc[1] < 0.07:
                return True
        return False

    def zoom_wanted(self):
        """Lens is up while: u tapped it on (wrist button / menu / F10), or (gesture mode) a controller is held to ur eye."""
        z = self.cfg["zoom"]
        if not self.cfg["modules"].get("zoom_lens", True):
            return False
        on = bool(getattr(self, "zoom_manual", False))
        if z.get("mode", "gesture") == "gesture" and not on:
            now = time.time()
            if self.zoom_gesture():
                self.gesture_since = self.gesture_since or now
            else:
                self.gesture_since = None
            on = self.gesture_since is not None and now - self.gesture_since > 0.25
        return on

    def update_zoom(self):
        z = self.cfg["zoom"]
        on = self.zoom_wanted()
        self.zoom.active = on
        if bool(z.get("enabled")) != on:          # live state (drawn on the buttons), not a saved setting
            z["enabled"] = on
            self.state.hud_dirty = self.state.dash_dirty = True
        if not on:
            if self.zoom_shown:
                self.ov.hideOverlay(self.zoom_ov)
                self.zoom_shown = False
                self.zoom_placed = None
            return
        place = (z.get("size_m", 0.24), z.get("distance_m", 0.55))
        if place != self.zoom_placed:          # stick it to the headset, straight ahead
            self.zoom_placed = place
            self.ov.setOverlayWidthInMeters(self.zoom_ov, place[0])
            self.ov.setOverlayTransformTrackedDeviceRelative(
                self.zoom_ov, openvr.k_unTrackedDeviceIndex_Hmd, to_hmd34(euler_to_rot(0, 0, 0), [0.0, -0.02, -place[1]]))
        frame = self.zoom.take()
        if frame is None and not self.zoom_shown:
            frame = getattr(self, "_zoom_hello", None)
            if frame is None:                  # instant "here i am" lens while the first picture loads
                img = zoom_mod.placeholder(ui.get_theme(self.cfg), z.get("level", 3), "zooming in…")
                frame = self._zoom_hello = (img.tobytes(), img.width, img.height)
        if frame:
            self.push(self.zoom_ov, frame=frame)
            if not self.zoom_shown:
                self.ov.showOverlay(self.zoom_ov)
                self.zoom_shown = True

    def toggle_zoom(self, on=None):
        z = self.cfg["zoom"]
        self.zoom_manual = (not getattr(self, "zoom_manual", False)) if on is None else bool(on)
        self.cfg["modules"]["zoom_lens"] = True
        self.state.dirty_cfg = self.state.dash_dirty = self.state.hud_dirty = True
        if self.zoom_manual:
            self.show_alert(f"zoom {z.get('level', 3)}x on 🔍 (tap again to close)", secs=3)
        else:
            self.show_alert("zoom off", secs=2)

    def on_linked(self, who, beta):
        self.fun.flag("linked")
        self.show_alert(f"🧪 {lang.tr('key ok!! linked to')} {who} ~ {lang.tr('u got the Beta Tester badge')} <3", secs=10)
        self.state.dirty_cfg = self.state.dash_dirty = True

    def on_wave(self, name, sid):
        self.show_alert(f"👋 {name} {lang.tr('waved at u!')}", secs=6)
        self.state.dash_dirty = True

    def register_manifest(self):
        """shows us in SteamVR's 'startup overlay apps' list (Settings -> Startup / Shutdown)"""
        if type(self.ov).__name__ == "NullOverlay" or not hasattr(openvr, "VRApplications"):
            return                                   # desktop mode: no SteamVR
        apps = openvr.VRApplications()
        path = os.path.join(HERE, "fluffvr_stats.vrmanifest")
        pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pyw):
            pyw = sys.executable
        man = {"source": "builtin", "applications": [{
            "app_key": "fluffvr.stats", "launch_type": "binary", "binary_path_windows": pyw,
            "arguments": f'"{os.path.join(HERE, "main.py")}" --vr', "working_directory": HERE,
            "is_dashboard_overlay": True,
            "strings": {"en_us": {"name": "Fluff VR Stats", "description": "Cute furry wrist HUD for VRChat"}}}]}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(man, f, indent=2)
        apps.addApplicationManifest(path, False)
        if not self.cfg.get("_autolaunch_synced"):        # people who used autostart_with_steamvr.py before
            self.cfg["_autolaunch_synced"] = True
            try:
                if apps.getApplicationAutoLaunch("fluffvr.stats"):
                    self.cfg["start_with_steamvr"] = True
            except Exception:
                pass
        apps.setApplicationAutoLaunch("fluffvr.stats", bool(self.cfg.get("start_with_steamvr")))

    def tick_fun(self, now):
        """badges, Wrapped stats, seasons, kitty outfit, Fluff Friends, events, app key, safe-mode timer"""
        st = self.state
        if now - self.last_fun < 1.0:
            return
        self.last_fun = now
        if not self.launch_marked and now - self.started_at > 60:
            self.launch_marked = True
            launch_ok()
        w = st.world or {}
        before = self.cfg.get("kitty", {}).get("pats", 0)
        for msg in self.fun.tick(st, self.cfg.get("kitty", {}), st.music, w, st.desktop, now):
            self.show_alert(msg, secs=8)
            st.dash_dirty = True
        # Halloween: kitty pats can drop candy
        kp = self.cfg.get("kitty", {}).get("pats", 0)
        if kp > self.__dict__.setdefault("_kp", kp):
            got = self.fun.on_kitty_pat()
            if got:
                self.show_alert(got, secs=4)
        self._kp = kp
        earned = self.fun.pop_earned()
        if earned:
            st.dirty_cfg = st.dash_dirty = True
            self.access.sync_badges(list(self.fun.f["badges"]))
        outfit = self.fun.closet()
        if outfit != self.kitty.outfit:
            self.kitty.outfit = outfit
            self.kitty.changed = True
        # same-instance friends
        if w.get("found") and w.get("world_id"):
            self.friends.set_instance(w.get("world_id"), w.get("instance", ""))
        else:
            self.friends.set_instance(None, None)
        self.friends.tick()
        if self.friends.changed:
            self.friends.changed = False
            st.dash_dirty = True
        if self.cevents.changed:
            self.cevents.changed = False
            st.dash_dirty = True
        if self.cevents.live(now):
            self.fun.flag("event_joined")
        # overlay's own cost (Stats tab)
        if now - self.last_usage > 3:
            self.last_usage = now
            try:
                with self.my_proc.oneshot():
                    st.app_usage = {"cpu": self.my_proc.cpu_percent(None) / max(1, psutil.cpu_count() or 1),
                                    "ram_mb": self.my_proc.memory_info().rss / 1048576,
                                    "threads": self.my_proc.num_threads()}
            except Exception:
                pass
        if st.checklist and now - self.__dict__.get("_conf_t", 0) > 10:
            self._conf_t = now
            st.conflicts = conflicting_apps()
            st.dash_dirty = True
        if st.tab == "Fun" and getattr(st, "fun_page", "") == "closet" and now - self.__dict__.get("_kimg_t", 0) > 2:
            self._kimg_t = now
            st.kitty_img = self.kitty.render(ui.get_theme(self.cfg), now)
            self.kitty.changed = True
            st.dash_dirty = True
        if st.confirm and now > st.confirm[1]:
            st.confirm = None
            st.dash_dirty = True

    def on_gchat(self, msg):
        st = self.state
        st.dash_dirty = True
        if not msg.get("mine") and self.cfg["gchat"].get("hud", True):
            st.hud_dirty = True

    def hud_command(self, cmd):
        """A button on the wrist (VR: tap with ur other hand, desktop: click the floating menu)."""
        cfg, st = self.cfg, self.state
        if cmd in ("next", "prev", "play_pause", "play", "pause", "vol_up", "vol_down", "mute"):
            self.music.command(cmd)
        elif cmd == "zoom":
            self.toggle_zoom()
        elif cmd == "chatbox":
            on = not cfg["modules"].get("chatbox_status")
            cfg["modules"]["chatbox_status"] = on
            if not on:
                try:
                    osc.chatbox("", cfg.get("osc_port", 9000))
                except Exception:
                    pass
            self.show_alert("chatbox ON ~ ur stats are showing" if on else "chatbox off", secs=3)
            st.dirty_cfg = True
        elif cmd == "timer":
            tm = st.timer
            if tm["running"]:
                self.timer_action("toggle")
                self.timer_action("reset")
                self.show_alert("timer stopped", secs=2)
            else:
                tm.update(mode="timer", left=300.0)
                self.timer_action("toggle")
                self.show_alert("5 min timer started ⏱", secs=3)
            cfg["modules"]["timer"] = True
        elif cmd == "kitty":
            cfg["modules"]["wrist_kitty"] = not cfg["modules"].get("wrist_kitty", True)
            self.show_alert("kitty says hiii :3" if cfg["modules"]["wrist_kitty"] else "kitty is napping", secs=3)
            st.dirty_cfg = True
        elif cmd == "gchat":
            st.tab = "Global"
            self.gchat.unread = 0
            if st.desktop:
                self.raise_window = True
            else:
                try:
                    self.ov.showDashboard("fluffvr.stats.dash")
                except Exception:
                    pass
        elif cmd == "menu":
            st.tab = "Home"
            if st.desktop:
                self.raise_window = True
            try:
                self.ov.showDashboard("fluffvr.stats.dash")
            except Exception:
                pass
        elif cmd == "screen":
            cfg["screen"]["enabled"] = not cfg["screen"]["enabled"]
            self.scr_placed = False
            st.dirty_cfg = True
        elif cmd == "pat":
            cfg["floof_pats"] = cfg.get("floof_pats", 0) + 1
            st.last_pat = time.time()
            self.show_alert(random.choice(["purrr~", "hehe thank u <3", "*happy tail wag*", "mrrp! :3"]), secs=2)
            st.dirty_cfg = True
        st.hud_pressed, st.hud_pressed_t = cmd, time.time()
        st.hud_dirty = st.dash_dirty = True

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
        if self.cfg["modules"].get("night_dim"):
            hr = time.localtime().tm_hour
            if hr >= 22 or hr < 6:
                target *= 0.6                     # softer at night so it's not blinding in a dark room
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
        if self.do_more(action, args):
            st.dash_dirty = True
            return
        if action == "tab":
            st.tab = args[0]
            st.chat_scroll = st.gchat_scroll = 0
            if st.tab == "Boost":
                self.safe("boost status", self.refresh_boost)
        elif action == "toggle":
            cfg["modules"][args[0]] = not cfg["modules"].get(args[0], False)
            line = ui.MOD_TO_LINE.get(args[0])
            if line:
                cfg["chatbox"].setdefault("lines", {})[line] = cfg["modules"][args[0]]
            st.dirty_cfg = st.hud_dirty = True
            self.hud_alpha = None
        elif action == "mod_edit":
            key = args[0]
            cur = {"kitty_name": cfg.get("kitty", {}).get("name", "Mochi"),
                   "gchat_name": cfg.get("gchat", {}).get("name", ""),
                   "countdown_name": cfg.get("countdown", {}).get("name", ""),
                   "countdown_date": cfg.get("countdown", {}).get("date", "")}.get(key, str(cfg.get(key, "")))
            desc = {"headpat_param": "Headpat parameter name (blank = auto)", "boop_param": "Boop parameter name (blank = auto)",
                    "countdown_name": "Countdown to what?", "countdown_date": "Date (YYYY-MM-DD)",
                    "bedtime": "Bedtime (HH:MM, 24h)", "kitty_name": "Name ur kitty",
                    "gchat_name": "Ur name in global chat", "weather_location": "Weather city (blank = auto)"}.get(key, key)
            self.open_keyboard(desc, cur, ("cfg", key))
        elif action == "kitty_color":
            cols = list(self.kitty_mod.COLORS)
            kt = cfg.setdefault("kitty", {})
            kt["color"] = cols[(cols.index(kt.get("color", "cream")) + 1) % len(cols)] if kt.get("color") in cols else "cream"
            self.kitty.changed = True
            st.dirty_cfg = st.dash_dirty = True
        elif action == "mod_cycle":
            opts = [10, 15, 20, 30, 45, 60]
            cur = cfg.get(args[0], 20)
            cfg[args[0]] = opts[(opts.index(cur) + 1) % len(opts)] if cur in opts else 20
            st.dirty_cfg = st.dash_dirty = True
        elif action == "learn_contact":
            kind = args[0]
            self.extras.start_learn(kind)
            what = "pat ur own head (or get a friend to)" if kind == "headpats" else "boop ur own nose (or get a friend to)"
            self.show_alert(f"learning... {what} in the next 25s!", secs=8)
            st.dash_dirty = True
        elif action == "mod_reset_counts":
            for k, tot in (("headpats", "headpats_total"), ("boops", "boops_total"), ("jumps", "jumps_total")):
                cfg[tot] = 0
                self.extras._set(k, 0)
            self.extras.data["talk_s"] = 0
            st.dirty_cfg = st.dash_dirty = True
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
        elif action == "zoom_toggle":
            self.toggle_zoom()
        elif action == "zoom_set":
            cfg["zoom"][args[0]] = args[1]
            if args[0] == "mode":
                self.zoom_manual = False
            self.zoom_placed = None
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
        elif action == "hud_cmd":
            self.hud_command(args[0])
        elif action == "gchat_send":
            if not cfg["gchat"].get("name"):
                self.open_keyboard("Pick a name for global chat first :3", "", ("cfg", "gchat_name"))
            else:
                self.open_keyboard("Say something to everyone (no links, be nice <3)", "", "gchat")
        elif action == "gchat_mute":
            self.gchat.mute(args[0])
            st.dirty_cfg = True
            self.show_alert("muted them (only for u) ~ unmute in Settings", secs=5)
        elif action == "gchat_unmute_all":
            cfg["gchat"]["muted"] = []
            st.dirty_cfg = True
        elif action == "gchat_scroll":
            st.gchat_scroll = max(0, st.gchat_scroll + args[0])
        elif action == "wrist_action":            # Wrist tab: add / remove a button on ur wrist
            acts = cfg.setdefault("wrist_actions", [])
            if args[0] in acts:
                acts.remove(args[0])
            elif len(acts) < 6:
                acts.append(args[0])
            else:
                self.show_alert("max 6 wrist buttons ~ remove one first", "warn", 4)
            st.dirty_cfg = st.hud_dirty = True
        elif action == "dev":
            self.dev_action(args)
        elif action == "set":                     # Settings tab: set / cycle simple options
            key, val = args[0], args[1]
            if val == "__cycle__":
                opts = args[2]
                cur = _get_path(cfg, key)
                val = opts[(opts.index(cur) + 1) % len(opts)] if cur in opts else opts[0]
            _set_path(cfg, key, val)
            st.dirty_cfg = st.hud_dirty = True
            if key.startswith("wrist."):
                self.apply_wrist()
                self.hud_alpha = None
        elif action == "open_link":
            import webbrowser
            webbrowser.open(args[0])
            self.show_alert("opened on ur desktop :3", secs=4)
        st.dash_dirty = True

    def confirmed(self, action):
        """'tap again to confirm' for things that can't be undone easily"""
        st = self.state
        if st.confirm and st.confirm[0] == action and time.time() < st.confirm[1]:
            st.confirm = None
            return True
        st.confirm = (action, time.time() + 5)
        self.show_alert(lang.tr("tap again to confirm"), "warn", 5)
        return False

    def do_more(self, action, args):
        """v0.4 actions: Fun tab, app key, language, privacy, comfy settings, profiles, backups, logs"""
        st, cfg, f = self.state, self.cfg, self.fun
        a0 = args[0] if args else None
        if action == "noop":
            return True
        if action == "set_page":
            st.set_page = a0
        elif action == "tab_fun":
            st.tab, st.fun_page = "Fun", a0 or "badges"
            if st.fun_page == "badges":
                f.f["seen_badges"] = list(f.f["badges"])
        elif action == "fun_page":
            st.fun_page = a0
            if a0 == "badges":
                f.f["seen_badges"] = list(f.f["badges"])
                st.dirty_cfg = True
        elif action == "wrapped":
            path = fun_mod.save_wrapped(f, cfg, cfg.get("gchat", {}).get("name", ""), a0)
            st.dirty_cfg = True
            try:
                if sys.platform == "win32":
                    os.startfile(path)
            except Exception:
                pass
            self.show_alert(lang.tr("ur Fluff Wrapped card is saved in the wrapped folder ~ post it!!"), secs=8)
        elif action == "wear":
            slot, item = args[0], args[1]
            if f.unlocked(item, slot):
                f.f["closet"][slot] = item
                f.f["closet"]["picked"] = True
                st.dirty_cfg = True
            else:
                self.show_alert(lang.tr("still locked ~ check how to get it below"), "warn", 4)
        elif action == "season":
            f.f["season"] = "off" if f.f.get("season") != "off" else "auto"
            st.dirty_cfg = True
        elif action == "season_theme":
            s = f.season()
            if s:
                cfg["theme"] = fun_mod.SEASONS[s]["theme"]
                cfg["cursor"] = fun_mod.SEASONS[s].get("cursor", cfg.get("cursor", "paw"))
                st.dirty_cfg = st.hud_dirty = True
                self.safe("icon", self.refresh_icon)
        elif action == "theme_copy":
            code = fun_mod.theme_code(cfg)
            ok = copy_to_clipboard(code)
            f.flag("theme_shared")
            st.dirty_cfg = True
            self.show_alert((lang.tr("copied!! paste it in #theme-share:") if ok else lang.tr("ur code:")) + " " + code, secs=10)
        elif action == "theme_enter":
            self.open_keyboard(lang.tr("Paste a theme code (FLUFF-...)"), "", ("cfg", "theme_code"))
        elif action == "wave":
            if self.friends.wave(a0):
                f.add("waves")
                f.check_badges()
                st.dirty_cfg = True
                self.show_alert("👋 " + lang.tr("waved!"), secs=3)
        elif action == "key_enter":
            self.open_keyboard(lang.tr("Ur app key from the Fluff Discord (/key)"), "", ("cfg", "app_key"))
        elif action == "key_forget":
            if self.confirmed("key_forget"):
                self.access.forget()
                st.dirty_cfg = True
        elif action == "lang":
            cfg["language"] = a0 if a0 in lang.CODES else lang.next_lang(cfg.get("language", "en"))
            lang.set_lang(cfg["language"])
            self.kitty.changed = True
            st.dirty_cfg = st.hud_dirty = True
            self.show_alert(lang.tr("language") + ": " + lang.NAMES[cfg["language"]], secs=3)
        elif action == "a11y":
            ax = cfg.setdefault("a11y", {})
            ax[a0] = not ax.get(a0)
            if a0 == "reduced_motion":
                cfg["animate_logo"] = not ax[a0]
                cfg["intro"] = not ax[a0]
            ui.COLORBLIND = bool(ax.get("colorblind"))
            st.dirty_cfg = st.hud_dirty = True
        elif action == "left_handed":
            cfg["wrist"]["hand"] = "right" if cfg["wrist"]["hand"] == "left" else "left"
            self.apply_wrist()
            self.kitty_idx = -1                      # re-attach kitty to the other wrist
            st.dirty_cfg = st.hud_dirty = True
        elif action == "menu_size":
            sizes = [1.6, 2.0, 2.4, 2.8]
            cur = float(cfg.get("dashboard_width_m", 2.0))
            cfg["dashboard_width_m"] = sizes[(min(range(4), key=lambda i: abs(sizes[i] - cur)) + 1) % 4]
            try:
                self.ov.setOverlayWidthInMeters(self.dash, cfg["dashboard_width_m"])
            except Exception:
                pass
            st.dirty_cfg = True
        elif action == "wrist_size":
            sizes = [0.11, 0.13, 0.16, 0.19]
            cur = float(cfg["wrist"].get("width_m", 0.13))
            cfg["wrist"]["width_m"] = sizes[(min(range(4), key=lambda i: abs(sizes[i] - cur)) + 1) % 4]
            self.apply_wrist()
            st.dirty_cfg = True
        elif action == "privacy":
            cfg["discord"][a0] = not cfg["discord"].get(a0, a0 == "hide_world")
            st.dirty_cfg = True
        elif action == "start_with_steamvr":
            cfg["start_with_steamvr"] = not cfg.get("start_with_steamvr")
            self.safe("SteamVR startup list", self.register_manifest)
            st.dirty_cfg = True
        elif action == "profile":
            if apply_profile(cfg, a0):
                st.dirty_cfg = st.hud_dirty = True
                self.hud_alpha = None
                self.show_alert(lang.tr("profile") + ": " + lang.tr(PROFILES.get(a0, {}).get("label", "my own picks")), secs=4)
        elif action == "export_cfg":
            path = export_cfg(cfg)
            self.show_alert(lang.tr("saved ur settings to") + " exports/" + os.path.basename(path), secs=6)
        elif action == "import_cfg":
            path = latest_export()
            if not path:
                self.show_alert(lang.tr("no settings file in the exports folder yet"), "warn", 6)
            elif self.confirmed("import_cfg"):
                import_cfg(cfg, path)
                lang.set_lang(cfg.get("language", "en"))
                st.dirty_cfg = st.hud_dirty = True
                self.apply_wrist()
                self.show_alert(lang.tr("loaded") + " " + os.path.basename(path), secs=6)
        elif action == "reset_cfg":
            if self.confirmed("reset_cfg"):
                reset_cfg(cfg)
                lang.set_lang(cfg.get("language", "en"))
                st.dirty_cfg = st.hud_dirty = True
                self.apply_wrist()
                self.show_alert(lang.tr("settings reset ~ a backup is in the exports folder"), secs=6)
        elif action == "copy_logs":
            ok = copy_to_clipboard(recent_logs())
            try:
                if sys.platform == "win32":
                    os.startfile(os.path.dirname(LOG_PATH))
            except Exception:
                pass
            self.show_alert(lang.tr("logs copied ~ paste them in ur Discord ticket") if ok
                            else lang.tr("opened the logs folder ~ send fluffvr.log in ur ticket"), secs=8)
        elif action == "safe_off":
            leave_safe_mode(cfg)
            st.safe_mode = False
            st.dirty_cfg = st.hud_dirty = True
            self.show_alert(lang.tr("mods are back on :3"), secs=4)
        elif action == "whatsnew_close":
            st.whatsnew = None
        elif action == "checklist":
            if a0 == "done":
                st.checklist = None
                cfg["checklist_done"] = True
                st.dirty_cfg = True
            else:
                st.checklist = True
                st.tab = "Home"
        elif action == "gchat_report":
            why = self.gchat.report(a0)
            self.show_alert(why or lang.tr("reported to staff, thank u <3"), "warn" if why else "info", 5)
        else:
            return False
        return True

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

    def dev_action(self, args):
        """Dev tab: local-only toys for messing with ur OWN client (testing, screenshots, fun)."""
        st, cfg = self.state, self.cfg
        dev = cfg.setdefault("dev", {})
        what = args[0]
        a = args[1] if len(args) > 1 else None
        if what == "toggle":
            dev[a] = not dev.get(a)
            self.dev_msg = f"{a} = {dev.get(a)}"
        elif what == "fps":
            dev["fps"] = a; dev["fake_stats"] = True
        elif what == "temp":
            dev["gpu_temp"] = a; dev["fake_stats"] = True
        elif what == "battery":
            dev["battery"] = a; dev["fake_stats"] = True
        elif what == "pats":
            for _ in range(a):
                self.extras._set("headpats", self.extras.get("headpats", 0) + 1)
            self.dev_msg = f"+{a} pats"
        elif what == "boops":
            for _ in range(a):
                self.extras._set("boops", self.extras.get("boops", 0) + 1)
        elif what == "combo":
            nm = self.__dict__.setdefault("_nm", {})
            nm["pat_t"] = [time.time()] * a
            self.extras._set("headpats", self.extras.get("headpats", 0) + a)
            self.dev_msg = f"combo x{a} primed"
        elif what == "zoomies":
            st.zoomies = not getattr(st, "zoomies", False)
        elif what == "alert":
            self.show_alert(a or "dev test alert :3", "info", 6)
        elif what == "warn":
            self.show_alert("dev test warning!!", "warn", 6)
        elif what == "error":
            self.report("dev test", msg="dev test error cat :3")
        elif what == "theme_roll":
            import random as _r
            cfg["theme"] = _r.choice([p[0] for p in ui.PRESETS])
            self.dev_msg = f"theme: {cfg['theme']}"
            self.safe("icon", self.refresh_icon)
        elif what == "ears_roll":
            import random as _r
            cfg["style"]["ears"] = _r.choice(ui.EAR_STYLES)
        elif what == "all_mods":
            for k in cfg["modules"]:
                cfg["modules"][k] = bool(a)
            self.dev_msg = "all mods " + ("ON" if a else "off")
        elif what == "reload_ui":
            for fn in (ui.hud_bg, ui.dash_bg, ui.furry_frame, ui.fluff_shape, getattr(ui, "_velvet", None),
                       getattr(ui, "_card_ears", None), getattr(ui, "_glow", None)):
                try:
                    fn.cache_clear()
                except Exception:
                    pass
            self.dev_msg = "UI caches cleared, redrawing"
        elif what == "dump_cfg":
            safe = {k: v for k, v in cfg.items() if k not in ("ai",)}
            log.info("DEV config dump: %s", json.dumps(safe)[:4000])
            self.dev_msg = "config dumped to logs/ :3"
        elif what == "tab":
            st.tab = a
        st.dirty_cfg = st.dash_dirty = st.hud_dirty = True

    def apply_dev_stats(self, stats):
        """Overlay the Dev tab's fake values onto real stats (only when fake_stats is on)."""
        dev = self.cfg.get("dev", {})
        if dev.get("fake_stats"):
            ref = stats.get("refresh") or 90
            stats["fps"] = float(dev.get("fps", 90))
            stats["refresh"] = ref
            stats["gpu_temp"] = float(dev.get("gpu_temp", 70))
            stats["gpu_ms"] = 1000.0 / max(1, stats["fps"]) * 0.6
            stats["cpu_ms"] = 1000.0 / max(1, stats["fps"]) * 0.4
            b = float(dev.get("battery", 80))
            stats["batteries"] = [("HMD", b, False), ("L", b, False), ("R", max(0, b - 20), False)]
        if dev.get("spikes"):
            ft = list(stats.get("frametimes") or [11.0] * 60)
            import random as _r
            for _ in range(3):
                ft[_r.randint(0, len(ft) - 1)] = _r.uniform(25, 45)
            stats["frametimes"] = ft
        return stats

    def apply_dev_extras(self):
        """Fake world + players for testing the World tab / chatbox, local only."""
        if self.cfg.get("dev", {}).get("fake_world"):
            x = self.state.extras
            x["world_name"] = "DEV Test World"
            x["world_players"] = 7
            x.setdefault("world_since", time.time() - 600)

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
            return
        if target == "gchat":
            why = self.gchat.send(text)
            if why:
                self.show_alert(why, "warn", 5)
            st.dash_dirty = True
            return
        if isinstance(target, tuple) and target[0] == "cfg":
            key, text = target[1], text.strip()
            if key == "app_key":
                why = self.access.start(text)
                self.show_alert(why or lang.tr("checking ur key…"), "warn" if why else "info", 6)
                st.dash_dirty = True
                return
            if key == "theme_code":
                if fun_mod.apply_theme_code(self.cfg, text):
                    self.show_alert(lang.tr("new look applied!! :3"), secs=4)
                    st.hud_dirty = True
                    self.safe("icon", self.refresh_icon)
                else:
                    self.show_alert(lang.tr("that's not a theme code ~ they look like FLUFF-ABCD..."), "warn", 6)
                st.dirty_cfg = st.dash_dirty = True
                return
            if key == "gchat_name":
                from gchat import clean_name
                name = clean_name(text)
                if name:
                    self.cfg["gchat"]["name"] = name
                    self.show_alert(f"hiii {name}! ur global chat name is set :3", secs=5)
            elif key == "kitty_name":
                if text:
                    self.cfg.setdefault("kitty", {})["name"] = text[:16]
                    self.kitty.changed = True
            elif key in ("countdown_name", "countdown_date"):
                cd = self.cfg.setdefault("countdown", {})
                if key == "countdown_date":
                    try:
                        time.strptime(text, "%Y-%m-%d")
                    except ValueError:
                        self.show_alert("date needs to look like 2026-12-25", "warn", 6)
                        return
                cd[key.split("_")[1]] = text[:30]
            elif key == "bedtime":
                try:
                    hh, mm = [int(v) for v in text.split(":")[:2]]
                    assert 0 <= hh < 24 and 0 <= mm < 60
                    self.cfg["bedtime"] = f"{hh:02d}:{mm:02d}"
                except Exception:
                    self.show_alert("bedtime needs to look like 23:30", "warn", 6)
                    return
            else:
                self.cfg[key] = text[:60]
            st.dirty_cfg = st.dash_dirty = True
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
        if st.tab == "Global":
            st.gchat_scroll = max(0, min(len(self.gchat.msgs) - 1, st.gchat_scroll + (1 if amount > 0 else -1)))
            st.dash_dirty = True
            return
        top_room = max(0, (ui.DASH_H * 0.25) - st.chat_content_top) + st.chat_scroll
        st.chat_scroll = max(0, min(st.chat_scroll + amount, top_room))
        st.dash_dirty = True

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
            elif t == openvr.VREvent_ScrollSmooth and self.state.tab == "Global":
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
    def update_vr_days(self, add_s):
        """today's VR time + how many days in a row u've been in VR (saved in config)"""
        vd = self.cfg.setdefault("vr_days", {})
        today = time.strftime("%Y-%m-%d")
        if vd.get("date") != today:
            yday = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
            vd["streak"] = vd.get("streak", 0) + 1 if vd.get("date") == yday else 1
            vd["date"], vd["today_s"] = today, 0
            vd["best"] = max(vd.get("best", 0), vd["streak"])
        vd["today_s"] = vd.get("today_s", 0) + add_s
        self.extras._set("vr_today_s", int(vd["today_s"]))
        self.extras._set("vr_streak", vd.get("streak", 1))

    def tick_new_mods(self, now):
        """v0.3 mods: pat combo, vibe meter, daily goal, world timer, people met, lucky paw, chime, PC alerts."""
        st, m, x, s = self.state, self.cfg["modules"], self.state.extras, self.state.stats
        nm = self.__dict__.setdefault("_nm", {"pats": None, "pat_t": [], "combo_best": 0, "vibe": 0.0, "goal_day": None,
                                             "gpu_t": 0, "ram_t": 0, "chime_h": None, "low_t": 0, "drops": []})
        # pat combo: pats in the last 20s
        pats = x.get("headpats", 0) + x.get("boops", 0)
        if nm["pats"] is not None and pats > nm["pats"]:
            nm["pat_t"] += [now] * min(5, pats - nm["pats"])
        nm["pats"] = pats
        nm["pat_t"] = [t for t in nm["pat_t"] if now - t < 20]
        combo = len(nm["pat_t"])
        if m.get("pat_combo"):
            if combo != x.get("combo", 0):
                x["combo"] = combo
                st.hud_dirty = True
                if combo in (5, 10, 20, 50):
                    self.show_alert({5: "pat combo x5!! :3", 10: "PAT COMBO x10!!! ur so loved", 20: "x20 COMBO?! headpat frenzy",
                                     50: "x50!!! LEGENDARY PATS"}[combo], secs=4)
        # vibe meter: how much u're moving (irl walking/dancing + in-game) as 0-100
        mv = min(1.0, (self.speed or 0) / 1.6 + (getattr(self.extras, "vel_h", 0) or 0) / 6)
        nm["vibe"] = nm["vibe"] * 0.9 + mv * 100 * 0.1
        x["vibe"] = int(nm["vibe"])
        # daily goal
        goal = max(10, int(self.cfg.get("vr_goal_min", 60)))
        x["goal_pct"] = min(100, int((x.get("vr_today_s", 0) or 0) / 60 * 100 / goal))
        today = time.strftime("%Y-%m-%d")
        if m.get("daily_goal") and x["goal_pct"] >= 100 and nm["goal_day"] != today:
            nm["goal_day"] = today
            self.show_alert(f"daily goal done!! {goal} min in VR today 🎯", secs=8)
        # world timer + people met (from VRChat's log)
        w = st.world or {}
        x["world_s"] = (now - w["world_since"]) if w.get("world_since") else None
        x["met"] = w.get("people_met")
        # lucky paw: one fortune a day
        x["fortune"] = LUCKY[sum(map(ord, today)) % len(LUCKY)]
        # PC alerts
        if m.get("hot_gpu_alert") and (s.get("gpu_temp") or 0) >= 84 and now - nm["gpu_t"] > 600:
            nm["gpu_t"] = now
            self.show_alert(f"ur GPU is toasty ({s['gpu_temp']:.0f}°C)! check ur fans / lower settings", "warn", 8)
        if m.get("ram_alert") and (s.get("ram_pct") or 0) >= 92 and now - nm["ram_t"] > 600:
            nm["ram_t"] = now
            self.show_alert(f"RAM is almost full ({s['ram_pct']:.0f}%)! close some apps so VRChat doesn't hitch", "warn", 8)
        # fps drop log: remember the last few big drops (shown in Stats)
        fps, ref = s.get("fps"), s.get("refresh")
        if m.get("fps_drop_log") and fps and ref and fps < ref * 0.5 and now - nm["low_t"] > 30:
            nm["low_t"] = now
            nm["drops"] = (nm["drops"] + [(now, int(fps), x.get("world_name") or "?")])[-5:]
            x["fps_drops"] = list(nm["drops"])
        # hourly chime
        lt = time.localtime(now)
        if m.get("hourly_chime") and lt.tm_min == 0 and nm["chime_h"] != lt.tm_hour:
            nm["chime_h"] = lt.tm_hour
            self.safe("ding", self.play_ding)
            self.show_alert(f"it's {time.strftime('%I %p', lt).lstrip('0')} ~ ding!", secs=5)

    def tick_more_mods(self, now):
        st, m = self.state, self.cfg["modules"]
        x = st.extras
        self.safe("new mods", self.tick_new_mods, now)
        # VR time today + streak (every minute)
        if now - self.last_vr_tick >= 60:
            self.update_vr_days(now - self.last_vr_tick)
            self.last_vr_tick = now
            st.dirty_cfg = True
        # 20-20-20 eye break
        if m.get("eye_break"):
            if now - self.last_eye > max(5, self.cfg.get("eye_break_min", 20)) * 60:
                self.last_eye = now
                self.show_alert("eye break! look at something far away for 20 secs 👀", secs=20)
        else:
            self.last_eye = now
        # posture
        if m.get("posture_reminder"):
            if now - self.last_posture > max(5, self.cfg.get("posture_min", 30)) * 60:
                self.last_posture = now
                self.show_alert("posture check!! sit up / stand tall, roll ur shoulders :3", secs=10)
        else:
            self.last_posture = now
        # bedtime
        if m.get("bedtime_alert"):
            try:
                hh, mm = [int(v) for v in str(self.cfg.get("bedtime", "01:00")).split(":")[:2]]
            except ValueError:
                hh, mm = 1, 0
            lt = time.localtime(now)
            since_bed = (lt.tm_hour * 60 + lt.tm_min - (hh * 60 + mm)) % 1440
            night = time.strftime("%Y-%m-%d", time.localtime(now - 12 * 3600))
            if since_bed < 240 and self.bedtime_day != night:
                self.bedtime_day = night
                self.show_alert(f"it's {time.strftime('%I:%M %p', lt).lstrip('0')}... bedtime soon? sleepy fluffs need rest 💤", "warn", 15)
        # still muted?
        if m.get("mute_reminder"):
            since = x.get("muted_since")
            if x.get("muted") and since and now - since > 10 * 60:
                if not self.mute_warned:
                    self.mute_warned = True
                    self.show_alert("ur still muted! (10+ min) just a heads up :3", "warn", 8)
            else:
                self.mute_warned = False
        # new song toast
        mu = st.music or {}
        key = (mu.get("title"), mu.get("artist")) if mu.get("title") else None
        if key != self.last_song_key:
            if m.get("song_toast") and key and self.last_song_key is not None and mu.get("playing") is not False:
                self.show_alert(f"now playing: {mu['title']}" + (f" - {mu['artist']}" if mu.get("artist") else ""), secs=5)
            self.last_song_key = key
        # learn mode finished?
        res = x.get("learn_result")
        if res and res != getattr(self, "_last_learn", None):
            self._last_learn = res
            ok, kind, name = res
            if ok == "ok":
                self.show_alert(f"got it!! {kind} = '{name}' :3", secs=8)
            else:
                self.show_alert(f"didn't see a contact turn on. is OSC on, and is the contact in ur Expression Parameters?", "warn", 10)
            st.dirty_cfg = st.dash_dirty = True
        if self.extras.learn and now > self.extras.learn["until"]:
            self.extras._learn_step("", 0, now)
        # headpat/boop help: avatar loaded but no contact param found
        av = st.avatar or {}
        if (m.get("headpat_counter") or m.get("boop_counter")) and av.get("id") and av.get("params") and self.contact_note_for != av["id"]:
            self.contact_note_for = av["id"]
            from extras import PAT_RE, is_contact
            names = [p["name"] for p in av["params"]]
            found = next((n for n in names if is_contact(n, self.cfg.get("headpat_param", ""), PAT_RE)), None)
            if found:
                self.extras.notes["note_vrchat"] = f"headpats: watching '{found}' on this avatar ✓"
            else:
                self.extras.notes["note_vrchat"] = ("no headpat parameter on this avatar. add ur contact receiver's parameter "
                                                    "to Expression Parameters, then VRChat OSC → Reset Config")
            self.extras.changed = True

    def show_alert(self, text, kind="info", secs=8):
        text = lang.tr(text)
        self.state.alert = {"text": text, "kind": kind, "until": time.time() + secs}
        self.state.hud_dirty = True
        self.hud_alpha = None

    def tick_extras(self, now):
        st, m = self.state, self.cfg["modules"]
        # pull fresh data from the helper threads
        if self.extras.changed:
            self.extras.changed = False
            old_pats = st.extras.get("headpats")
            old_boops, old_jumps = st.extras.get("boops"), st.extras.get("jumps")
            st.extras = self.extras.snapshot()
            if old_pats is not None and st.extras.get("headpats") != old_pats:
                st.dirty_cfg = True
                self.pat_times = [x for x in self.pat_times if now - x < 30] + [now]
                if m.get("pat_party") and len(self.pat_times) >= 5:
                    self.pat_times = []
                    self.show_alert(f"PAT PARTY!! 5 pats in 30s 🎉 ({st.extras['headpats']} total)", secs=5)
                else:
                    self.show_alert(f"headpat #{st.extras['headpats']}! good fluff~", secs=3)
            if old_boops is not None and st.extras.get("boops") != old_boops:
                st.dirty_cfg = True
                if m.get("boop_counter"):
                    self.show_alert(f"boop #{st.extras['boops']}! *sneeze*", secs=3)
            if old_jumps is not None and st.extras.get("jumps") != old_jumps:
                st.dirty_cfg = True
            st.hud_dirty = st.dash_dirty = True
        # feed Discord rich presence (it only sends every 15s itself)
        if now - self.last_discord_feed > 5:
            self.last_discord_feed = now
            mu = st.music or {}
            song = None
            if mu.get("title") and mu.get("playing") is not False:
                song = f"{mu['title']} - {mu['artist']}" if mu.get("artist") else mu["title"]
            self.discord.status = {
                "fps": st.stats.get("fps"),
                "world": None if self.cfg["discord"].get("hide_world", True) else (st.extras.get("world_name") or None),
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
        # low battery alert: once per device until it's charged back up
        if m.get("battery_alert"):
            for b in st.stats.get("batteries") or []:
                name, pct, charging = (list(b) + [None, None, None])[:3]
                if pct is None:
                    continue
                if pct <= 15 and not charging and name not in self.low_batt_warned:
                    self.low_batt_warned.add(name)
                    nice = {"HMD": "headset", "L": "left controller", "R": "right controller"}.get(name, name)
                    self.show_alert(f"ur {nice} is at {pct:.0f}%! plug it in soon >w<", "warn", 10)
                elif pct > 25 or charging:
                    self.low_batt_warned.discard(name)
        # hydration nudge every 30 min
        if m.get("hydration_reminder"):
            if now - self.last_water > 30 * 60:
                self.last_water = now
                self.show_alert("water break!! sip sip :3 Lil Fluff is drinking too", secs=8)
        else:
            self.last_water = now
        # VR time milestones: 1h, 2h, 3h...
        if m.get("vr_milestones"):
            hrs = int((now - st.extras.get("session_start", now)) // 3600)
            if hrs > self.milestone_hours:
                self.milestone_hours = hrs
                self.show_alert(f"{hrs} hour{'s' if hrs > 1 else ''} in VR!! 🎉 proud of u (stretch a lil?)", secs=10)
        self.tick_more_mods(now)
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
            self.safe("game motion", self.step_game_motion, now)
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
        if m.get("chatbox_status"):
            cb = self.cfg["chatbox"]
            if now - self.last_chatbox >= max(2, float(cb.get("interval_s", 3))):
                self.last_chatbox = now
                text = chatbox.compose(self.cfg, st.stats, st.extras, st.music, now)
                if text and (text != self.last_chatbox_text or now - self.last_chatbox_sent > 20):
                    self.last_chatbox_text, self.last_chatbox_sent = text, now
                    osc.chatbox(text, self.cfg.get("osc_port", 9000))

    def step_game_motion(self, now):
        """Zoomies from VRChat itself (thumbstick walking/running), not just walking around ur room."""
        st = self.state
        last = getattr(self, "_game_motion_t", None)
        self._game_motion_t = now
        if last is None:
            return
        dt = min(now - last, 1.0)
        v = 0.0 if self.extras.data.get("seated") else getattr(self.extras, "vel_h", 0.0)
        if 0.3 < v < 15:                              # ignore tiny drift + teleports / flying worlds
            st.walked += v * dt
            self.cfg["walked_total_m"] = self.cfg.get("walked_total_m", 0) + v * dt
            self.last_active = now
        self.game_speed = v
        zoom = self.speed > 1.3 or v > 3.2            # running irl, or sprinting in VRChat
        if zoom != getattr(st, "zoomies", False):
            st.zoomies = zoom
            st.hud_dirty = True
        st.speed = max(self.speed, v)

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
        if self.speed > 1.3 or getattr(self, "game_speed", 0) > 3.2:
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

    # ---- lil kitty on the other wrist
    def kitty_role(self):
        return openvr.TrackedControllerRole_RightHand if self.cfg["wrist"]["hand"] == "left" \
            else openvr.TrackedControllerRole_LeftHand

    def step_kitty(self, now):
        on = self.cfg["modules"].get("wrist_kitty", True)
        idx = self.vr.getTrackedDeviceIndexForControllerRole(self.kitty_role()) if on else openvr.k_unTrackedDeviceIndexInvalid
        idx = None if idx == openvr.k_unTrackedDeviceIndexInvalid else idx
        if idx != self.kitty_idx:
            self.kitty_idx = idx
            if idx is not None:
                rot, pos = wrist_transform(self.cfg["wrist"])
                pos = [-pos[0], pos[1], pos[2]]
                self.ov.setOverlayTransformTrackedDeviceRelative(self.kitty_ov, idx, to_hmd34(rot, pos))
        want = idx is not None
        if want != self.kitty_shown:
            (self.ov.showOverlay if want else self.ov.hideOverlay)(self.kitty_ov)
            self.kitty_shown = want
            self.kitty.changed = True
        if not want:
            return
        self.kitty.tick(now)
        if self.kitty.changed and now - self.kitty_t > (1 / 12 if getattr(self.kitty, "fast", True) else 1 / 4):
            self.kitty_t = now
            self.push(self.kitty_ov, self.kitty.render(ui.get_theme(self.cfg), now), "kitty")
        if self.kitty.sound:
            self.kitty_mod.play(self.kitty.sound)
            self.kitty.sound = None
        self.safe("kitty touch", self.kitty_check_touch, now)

    def kitty_check_touch(self, now):
        """pat her with ur other hand (the one wearing the stats HUD)"""
        if self.ctrl_index is None or self.kitty_idx is None:
            return
        poses = (openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount)()
        self.vr.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseStanding, 0, poses)
        kp, fp = poses[self.kitty_idx], poses[self.ctrl_index]
        if not (kp.bPoseIsValid and fp.bPoseIsValid):
            return
        F = fp.mDeviceToAbsoluteTracking.m
        off = self.cfg.get("touch_offset", [0.0, -0.015, -0.05])
        tip = [sum(F[i][k] * off[k] for k in range(3)) + F[i][3] for i in range(3)]
        K = kp.mDeviceToAbsoluteTracking.m
        krot = [[K[i][j] for j in range(3)] for i in range(3)]
        rot, pos = wrist_transform(self.cfg["wrist"])
        pos = [-pos[0], pos[1], pos[2]]
        wrot = mat_mul(krot, rot)
        wpos = [sum(krot[i][k] * pos[k] for k in range(3)) + K[i][3] for i in range(3)]
        rel = [tip[i] - wpos[i] for i in range(3)]
        local = [sum(wrot[k][i] * rel[k] for k in range(3)) for i in range(3)]
        wm = self.cfg.get("kitty_width_m", 0.11)
        inside = abs(local[0]) <= wm / 2 and abs(local[1]) <= wm / 2 and abs(local[2]) <= 0.04
        if not inside:
            self.kitty_touch = None
            return
        S = self.kitty_mod.SIZE
        px, py = (local[0] / wm + 0.5) * S, (0.5 - local[1] / wm) * S
        act = self.kitty.hit(px, py)
        if act is None:
            return
        fire = False
        if self.kitty_touch is None:
            fire = True                                  # new touch
        elif act == "pat":
            t0, p0 = self.kitty_touch                    # stroking = more pats
            moved = math.dist(p0, tip)
            if now - t0 > 0.7 and moved > 0.015:
                fire = True
        if fire:
            self.kitty_touch = (now, tip)
            msg = self.kitty.act(act)
            if msg:
                self.show_alert(msg, secs=6)
            self.state.dirty_cfg = True
            for dev in (self.ctrl_index, self.kitty_idx):
                try:
                    self.vr.triggerHapticPulse(dev, 0, 900 if act == "pat" else 1800)
                except Exception:
                    pass
        elif self.kitty_touch is None:
            self.kitty_touch = (now, tip)

    # ---- tap your wrist with the other controller
    def check_touch(self):
        if not (self.cfg["modules"].get("music_controls") or self.cfg["modules"].get("wrist_buttons")) \
                or self.ctrl_index is None \
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
                self.hud_command(cmd)
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
            self.safe("zoom", self.update_zoom)
            self.safe("kitty", self.step_kitty, now)
            self.safe("fun", self.tick_fun, now)
            if st.dirty_cfg and now - self.t["save"] > 1:
                st.dirty_cfg = False
                self.t["save"] = now
                save_cfg(self.cfg)
            if self.vr_errors >= 4:      # SteamVR itself is gone or broken -> reconnect
                raise ConnectionError("lost connection to SteamVR")
            # 20 Hz loop is plenty for the HUD; speed up only while the desktop mirror needs it
            sc = self.cfg["screen"]
            fast = (sc.get("enabled") and sc.get("fps", 15) > 15) or self.cfg["zoom"].get("enabled") or self.kitty_touch is not None
            time.sleep(0.02 if fast else 0.05)

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
            st.stats = self.apply_dev_stats(self.stats.collect())
            self.apply_dev_extras()
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
        if st.dash_dirty:
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
                calm = self.cfg.get("a11y", {}).get("reduced_motion")
                trail = [] if calm else [(x, y, now - t0) for x, y, t0 in st.trail]
                clicks = [] if calm else [(x, y, now - t0) for x, y, t0 in st.click_fx]
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


def choose_mode(cfg):
    """VR or Desktop? --vr / --desktop win, then a remembered choice, else ask with a lil window."""
    args = [a.lower() for a in sys.argv[1:]]
    if "--desktop" in args:
        return "desktop"
    if "--vr" in args:
        return "vr"
    if "--pick" not in args and cfg.get("launch_mode") in ("vr", "desktop"):
        return cfg["launch_mode"]
    try:
        import desktop
        mode = desktop.pick_mode(cfg)
        save_cfg(cfg)
        return mode
    except Exception as e:
        log.warning("mode picker failed, going VR: %s", e)
        return "vr"


def main():
    lower_priority()
    try:                       # new release on GitHub? download it, swap the files, restart (keeps ur settings)
        import updater
        updater.check_and_update(load_cfg(), log=log)
    except Exception as e:
        log.warning("updater: %s", e)
    _c = load_cfg()
    if launch_begin(_c):
        print("  safe mode: started with every mod off (it crashed on launch twice). Settings -> mods back on")
    mode = choose_mode(_c)
    if mode is None:          # closed the picker
        return
    if mode == "desktop":
        try:
            ensure_music_packages(load_cfg())
        except Exception as e:
            log.warning("music package check failed: %s", e)
        import desktop
        desktop.run()
        return
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
