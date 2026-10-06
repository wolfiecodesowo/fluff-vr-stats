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


# ----------------------------------------------------------------- main ---
class Extras:
    def __init__(self, cfg):
        self.cfg = cfg
        self.data = {"session_start": time.time(), "headpats": cfg.get("headpats_total", 0),
                     "song": None, "ping": None, "weather": None, "muted": None}
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
        d.update(self.notes)
        return d

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
            want = self.on("mute_indicator") or self.on("headpat_counter") or self.on("avatar_toggles")
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
            pat_addr = "/avatar/parameters/" + self.cfg.get("headpat_param", "HeadPat")
            for addr, args in parse_osc(data):
                if not args:
                    continue
                av = getattr(self, "avatar", None)
                if av is not None:
                    try:
                        av.on_osc(addr, args)
                    except Exception:
                        pass
                v = args[0]
                if addr == "/avatar/parameters/MuteSelf":
                    self._set("muted", bool(v))
                elif addr == pat_addr:
                    on = (v is True) or (isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0.5)
                    now = time.time()
                    if on and not self._pat_on and now - self._last_pat > 0.8:
                        self._last_pat = now
                        self._set("headpats", self.data["headpats"] + 1)
                        self.cfg["headpats_total"] = self.data["headpats"]
                    self._pat_on = on
        if sock:
            sock.close()
