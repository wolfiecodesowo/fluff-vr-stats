"""
Background helpers for the extra mods. Each one runs on its own slow thread and
only does work while its mod is switched on, so they cost basically nothing.

  now playing  - Windows media session (any player, incl. browser/YouTube) if the
                 optional winrt package is installed, else the Spotify window title
  ping         - TCP connect time to a host (default 1.1.1.1)
  weather      - wttr.in, auto-located by IP unless you set weather_location
  VRChat OSC   - listens on 9001 for MuteSelf + your headpat contact parameter
"""
import asyncio
import ctypes
import socket
import struct
import sys
import threading
import time
import urllib.parse
import urllib.request

import psutil


# ----------------------------------------------------------- now playing ---
def _song_winrt():
    try:
        from winrt.windows.media.control import \
            GlobalSystemMediaTransportControlsSessionManager as Manager
    except Exception:
        return None, False

    async def get():
        mgr = await Manager.request_async()
        ses = mgr.get_current_session()
        if not ses:
            return None
        info = ses.get_playback_info()
        if info and int(info.playback_status) != 4:      # 4 = Playing
            return None
        props = await ses.try_get_media_properties_async()
        if not props or not props.title:
            return None
        return f"{props.title} - {props.artist}" if props.artist else props.title
    try:
        return asyncio.run(get()), True
    except Exception:
        return None, True


def _song_spotify():
    if sys.platform != "win32":
        return None
    import ctypes.wintypes as wt
    user32 = ctypes.windll.user32
    pids = {p.pid for p in psutil.process_iter(["name"])
            if (p.info["name"] or "").lower() == "spotify.exe"}
    if not pids:
        return None
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            if n:
                buf = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(hwnd, buf, n + 1)
                title = buf.value
                if " - " in title and not title.startswith("Spotify"):
                    artist, song = title.split(" - ", 1)
                    found.append(f"{song} - {artist}")
        return True
    user32.EnumWindows(cb, 0)
    return found[0] if found else None


# ------------------------------------------------------------- OSC parse ---
def _osc_str(data, i):
    end = data.index(b"\0", i)
    s = data[i:end].decode("utf-8", "ignore")
    return s, (end + 4) & ~3


def parse_osc(data):
    """Yields (address, [args]) from an OSC packet or bundle."""
    if data.startswith(b"#bundle"):
        i = 16
        while i + 4 <= len(data):
            n = struct.unpack(">i", data[i:i + 4])[0]
            yield from parse_osc(data[i + 4:i + 4 + n])
            i += 4 + n
        return
    try:
        addr, i = _osc_str(data, 0)
        tags, i = _osc_str(data, i)
    except ValueError:
        return
    args = []
    for tg in tags[1:]:
        if tg == "i":
            args.append(struct.unpack(">i", data[i:i + 4])[0]); i += 4
        elif tg == "f":
            args.append(struct.unpack(">f", data[i:i + 4])[0]); i += 4
        elif tg == "s":
            v, i = _osc_str(data, i); args.append(v)
        elif tg == "T":
            args.append(True)
        elif tg == "F":
            args.append(False)
    yield addr, args


# ------------------------------------------------------- contact detection ---
import re as _re
PAT_RE = _re.compile(r"(head.?pat|headpat|(^|[_ .-])pat(ted|ting|s)?$|^pat($|s$|ted|ting|[_ .-])|head.?(touch|contact|rub)|(touch|contact|rub).?head|"
                     r"pett?ing|^pets?$|^head$)", _re.I)
BOOP_RE = _re.compile(r"(boop|nose.?(touch|contact|boop)|(touch|contact).?nose|^nose$)", _re.I)
# VRChat's own parameters: never a headpat/boop
BUILTIN = {"VelocityX", "VelocityY", "VelocityZ", "VelocityMagnitude", "AngularY", "Upright", "Grounded", "Seated",
           "AFK", "TrackingType", "VRMode", "MuteSelf", "InStation", "Earmuffs", "IsLocal", "Viseme", "Voice",
           "GestureLeft", "GestureRight", "GestureLeftWeight", "GestureRightWeight", "IsOnFriendsList",
           "AvatarVersion", "ScaleModified", "ScaleFactor", "ScaleFactorInverse", "EyeHeightAsMeters",
           "EyeHeightAsPercent", "IsAnimatorEnabled", "PreviewMode"}


def contact_on(v, was_on):
    """bool / int / float contact value -> on? (floats use hysteresis so proximity contacts don't spam)"""
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return v > 0
    if isinstance(v, float):
        return v > 0.5 if not was_on else v > 0.2
    return False


def wanted_names(cfg_value):
    """'HeadPat, Pat_Contact' -> {'headpat', 'pat_contact'}; '' or 'auto' -> auto-detect only"""
    names = {n.strip().lower() for n in str(cfg_value or "").split(",") if n.strip()}
    names.discard("auto")
    return names


def is_contact(name, cfg_value, regex):
    n = name.lower()
    return n in wanted_names(cfg_value) or bool(regex.search(name))


# ----------------------------------------------------------------- main ---
class Extras:
    def __init__(self, cfg):
        self.cfg = cfg
        self.data = {"session_start": time.time(), "headpats": cfg.get("headpats_total", 0),
                     "boops": cfg.get("boops_total", 0), "jumps": cfg.get("jumps_total", 0),
                     "talk_s": 0.0, "height_m": None, "pat_param": None, "boop_param": None,
                     "song": None, "ping": None, "weather": None, "muted": None}
        self._contact = {}          # param name -> (on?, last count time)
        self.learn = None           # {"kind": "headpats"/"boops", "until": t, "seen": {name: was_on}}
        self.recent = []            # last few avatar params VRChat sent (for the status line)
        self._talk_since = None
        self._grounded = None
        self.notes = {}
        self.changed = True
        self.running = True
        self._pat_on = False
        self._last_pat = 0
        for fn in (self._music_loop, self._ping_loop, self._weather_loop, self._osc_loop):
            threading.Thread(target=self._guard, args=(fn,), daemon=True, name=fn.__name__).start()

    def _guard(self, fn):
        """Restart a helper loop if it ever throws, with a small backoff."""
        while self.running:
            try:
                fn()
                return
            except Exception as e:
                self.notes["note_error"] = f"{fn.__name__.strip('_')} hiccup: {e}"
                time.sleep(5)

    def stop(self):
        self.running = False

    def on(self, key):
        return self.cfg["modules"].get(key, False)

    def _set(self, k, v):
        if self.data.get(k) != v:
            self.data[k] = v
            self.changed = True

    def snapshot(self):
        d = dict(self.data)
        d["talk_s"] = self.talk_seconds()
        d.update(self.notes)
        return d

    # ---- VRChat parameters -> headpats, boops, yap meter, jumps, height
    def on_param(self, addr, v, now=None):
        now = time.time() if now is None else now
        if addr == "/avatar/change":
            self._contact.clear(); self._grounded = None
            self._set("pat_param", None); self._set("boop_param", None); self._set("height_m", None)
            return
        if not addr.startswith("/avatar/parameters/"):
            return
        name = addr[len("/avatar/parameters/"):]
        self.data["osc_msgs"] = self.data.get("osc_msgs", 0) + 1
        self.data["osc_last"] = now
        if now - self.data.get("_osc_flag", 0) > 1:      # refresh the status line ~1x/s
            self.data["_osc_flag"] = now
            self.changed = True
        if name not in BUILTIN and (not self.recent or self.recent[-1] != name):
            self.recent = (self.recent + [name])[-4:]
            self.data["osc_recent"] = list(self.recent)
        if self.learn and name not in BUILTIN:
            self._learn_step(name, v, now)
        if name == "MuteSelf":
            self._set("muted", bool(v))
            if v:
                self.data.setdefault("muted_since", now)
            else:
                self.data.pop("muted_since", None)
            return
        if name == "Voice" and isinstance(v, (int, float)):
            talking = float(v) > 0.05
            if talking and self._talk_since is None:
                self._talk_since = now
            elif not talking and self._talk_since is not None:
                self.data["talk_s"] = self.data.get("talk_s", 0) + (now - self._talk_since)
                self._talk_since = None
                self.changed = True
            return
        if name == "Grounded":
            g = bool(v)
            if self._grounded is True and g is False and not self.data.get("seated"):
                self._set("jumps", self.data["jumps"] + 1)
                self.cfg["jumps_total"] = self.data["jumps"]
            self._grounded = g
            return
        if name in ("Seated", "InStation"):
            self.data["seated"] = bool(v)
            return
        if name == "EyeHeightAsMeters" and isinstance(v, (int, float)):
            self._set("height_m", round(float(v), 2))
            return
        # VRChat sends hundreds of these a second: work out once per name what it is
        ck = (self.cfg.get("headpat_param", ""), self.cfg.get("boop_param", ""))
        if getattr(self, "_kind_key", None) != ck:
            self._kind_key, self._kind = ck, {}
        kind_of = self._kind.get(name)
        if kind_of is None:
            kind_of = ("headpats" if is_contact(name, ck[0], PAT_RE) else
                       "boops" if is_contact(name, ck[1], BOOP_RE) else "")
            self._kind[name] = kind_of
        if not kind_of:
            return
        for kind, cfg_key, rx, total in (("headpats", "headpat_param", PAT_RE, "headpats_total"),
                                         ("boops", "boop_param", BOOP_RE, "boops_total")):
            if kind == kind_of:
                was, last = self._contact.get(name, (False, 0))
                on = contact_on(v, was)
                if on and not was and now - last > 0.8:
                    self._set(kind, self.data[kind] + 1)
                    self.cfg[total] = self.data[kind]
                    last = now
                self._contact[name] = (on, last)
                self._set(kind[:-1].replace("headpat", "pat") + "_param", name)
                return

    # ---- learn mode: "pat me now" -> whatever avatar param turns ON becomes the headpat/boop param
    def start_learn(self, kind, secs=25):
        self.learn = {"kind": kind, "until": time.time() + secs, "seen": {}}
        self._set("learn", kind)

    def _learn_step(self, name, v, now):
        L = self.learn
        if now > L["until"]:
            self.learn = None
            self._set("learn", None)
            self._set("learn_result", ("timeout", L["kind"], None))
            return
        was = L["seen"].get(name)
        on = contact_on(v, bool(was))
        L["seen"][name] = on
        if on and not was:                     # VRChat only sends changes, so "on" now = it just turned on
            key = "headpat_param" if L["kind"] == "headpats" else "boop_param"
            self.cfg[key] = name
            self._kind_key = None              # re-classify params with the new name
            self.learn = None
            self._set("learn", None)
            self._set("learn_result", ("ok", L["kind"], name))

    def talk_seconds(self, now=None):
        now = time.time() if now is None else now
        t = self.data.get("talk_s", 0)
        if self._talk_since is not None:
            t += now - self._talk_since
        return t

    # ---- threads
    def _music_loop(self):
        use_winrt = True
        while self.running:
            want = self.on("now_playing") or self.on("chatbox_status") or self.on("music_controls")
            if not want:
                self._set("song", None)
                time.sleep(1)
                continue
            music = getattr(self, "music", None)
            song = None
            if music is not None and music.backend == "windows":
                song = music.song_line()            # shared with the Music tab
            else:
                if use_winrt:
                    song, ok = _song_winrt()
                    use_winrt = ok
                if not song and not use_winrt:
                    try:
                        song = _song_spotify()
                    except Exception:
                        song = None
            self._set("song", song)
            time.sleep(2)

    def _ping_loop(self):
        while self.running:
            if self.on("ping"):
                host = self.cfg.get("ping_host", "1.1.1.1")
                try:
                    t0 = time.perf_counter()
                    with socket.create_connection((host, 443), timeout=2):
                        pass
                    self._set("ping", (time.perf_counter() - t0) * 1000)
                except OSError:
                    self._set("ping", None)
                time.sleep(5)
            else:
                time.sleep(1)

    def _weather_loop(self):
        last = 0
        while self.running:
            if self.on("weather") and time.time() - last > 20 * 60:
                last = time.time()
                loc = urllib.parse.quote(self.cfg.get("weather_location", ""))
                unit = "u" if self.cfg.get("weather_units", "F").upper() == "F" else "m"
                try:
                    req = urllib.request.Request(f"https://wttr.in/{loc}?format=%t+%C&{unit}",
                                                 headers={"User-Agent": "curl/8"})
                    with urllib.request.urlopen(req, timeout=10) as r:
                        txt = r.read().decode("utf-8", "ignore").strip().replace("+", "")
                    if txt and "<" not in txt and len(txt) < 40:
                        self._set("weather", txt)
                except Exception:
                    last = time.time() - 18 * 60      # retry in ~2 min
            elif not self.on("weather"):
                last = 0
            time.sleep(2)

    def _osc_loop(self):
        port = self.cfg.get("osc_listen_port", 9001)
        sock = None
        while self.running:
            want = any(self.on(k) for k in ("mute_indicator", "headpat_counter", "avatar_toggles", "boop_counter",
                                            "yap_meter", "jump_counter", "avatar_height", "mute_reminder"))
            if not want:
                if sock:
                    sock.close()
                    sock = None
                    self._set("muted", None)
                self.notes.pop("note_vrchat", None)
                time.sleep(1)
                continue
            if sock is None:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.bind(("127.0.0.1", port))
                    sock.settimeout(1.0)
                    self.notes["note_vrchat"] = (f"Listening to VRChat OSC on port {port}. "
                                                 "Turn on OSC in VRChat's Action Menu.")
                except OSError:
                    if sock:
                        sock.close()
                    sock = None
                    self.notes["note_vrchat"] = (f"Port {port} is busy (another OSC app?). "
                                                 "Close it or change osc_listen_port.")
                    self.changed = True
                    time.sleep(5)
                    continue
            try:
                data, _ = sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                sock = None
                continue
            if not self.running:
                break
            for addr, args in parse_osc(data):
                if not args:
                    continue
                av = getattr(self, "avatar", None)
                if av is not None:
                    try:
                        av.on_osc(addr, args)
                    except Exception:
                        pass
                self.on_param(addr, args[0])
        if sock:
            sock.close()
