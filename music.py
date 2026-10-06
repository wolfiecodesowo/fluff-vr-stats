"""
Music controls for any player Windows knows about (Spotify, YouTube in a browser,
Apple Music, VLC, ...).

Primary: Windows media session API (winrt) -> title, artist, album art, progress,
         real play/pause/skip on the exact app that's playing.
Fallback: plain media keys (work everywhere, just no song info).
Everything runs on one background thread with its own asyncio loop; the UI only
reads snapshots and queues commands, so a slow/broken player can't freeze VR.
"""
import asyncio
import ctypes
import io
import queue
import sys
import threading
import time

from PIL import Image

try:
    from winrt.windows.media.control import \
        GlobalSystemMediaTransportControlsSessionManager as _Manager
except Exception:
    _Manager = None
try:
    from winrt.windows.storage.streams import Buffer as _Buffer, InputStreamOptions as _ISO
except Exception:
    _Buffer = _ISO = None

PLAYING, PAUSED = 4, 5
VK = {"play_pause": 0xB3, "next": 0xB0, "prev": 0xB1,
      "vol_up": 0xAF, "vol_down": 0xAE, "mute": 0xAD}


def _press_media_key(name):
    if sys.platform != "win32":
        return
    vk = VK[name]
    user32 = ctypes.windll.user32
    user32.keybd_event(vk, 0, 1, 0)        # KEYEVENTF_EXTENDEDKEY
    user32.keybd_event(vk, 0, 1 | 2, 0)    # + KEYEVENTF_KEYUP


def pretty_app(aumid):
    """'Spotify.exe' / 'Microsoft.ZuneMusic_8wekyb3d8bbwe!Microsoft.ZuneMusic' -> nice name."""
    if not aumid:
        return ""
    s = aumid.split("!")[0].split("_")[0]
    if s.lower().endswith(".exe"):
        s = s[:-4]
    s = s.split("\\")[-1].split(".")[-1] if "." in s else s
    known = {"chrome": "Chrome", "msedge": "Edge", "firefox": "Firefox", "spotify": "Spotify",
             "zunemusic": "Media Player", "opera": "Opera", "brave": "Brave", "vlc": "VLC",
             "applemusic": "Apple Music", "itunes": "iTunes", "discord": "Discord"}
    return known.get(s.lower(), s[:1].upper() + s[1:])


class Music:
    def __init__(self):
        self.lock = threading.Lock()
        self.cmds = queue.Queue()
        self.running = True
        self.backend = "windows" if _Manager else "keys"
        self.state = {"title": "", "artist": "", "album": "", "app": "", "playing": None,
                      "pos": None, "dur": None, "pos_at": time.time(), "art": None, "art_id": 0,
                      "backend": self.backend, "error": None}
        self.changed = True
        self._art_key = None
        threading.Thread(target=self._thread, daemon=True, name="music").start()

    # ---- public (called from the main thread)
    def command(self, name):
        if name in VK:
            self.cmds.put(name)

    def snapshot(self):
        with self.lock:
            s = dict(self.state)
        # smooth progress between polls
        if s["playing"] and s["pos"] is not None:
            s["pos"] = min(s["dur"] or 1e9, s["pos"] + (time.time() - s["pos_at"]))
        return s

    def song_line(self):
        s = self.snapshot()
        if not s["title"] or s["playing"] is False:
            return None
        return f"{s['title']} - {s['artist']}" if s["artist"] else s["title"]

    def stop(self):
        self.running = False

    # ---- background
    def _set(self, **kw):
        with self.lock:
            for k, v in kw.items():
                if self.state.get(k) != v:
                    self.state[k] = v
                    if k not in ("pos", "pos_at"):
                        self.changed = True

    def _thread(self):
        try:
            asyncio.run(self._main())
        except Exception as e:
            self._set(error=str(e), backend="keys")
            self.backend = "keys"
            while self.running:                 # keep media keys working no matter what
                try:
                    _press_media_key(self.cmds.get(timeout=0.5))
                except queue.Empty:
                    pass
                except Exception:
                    pass

    async def _main(self):
        mgr = None
        last_poll = 0
        while self.running:
            # run queued commands right away
            try:
                while True:
                    cmd = self.cmds.get_nowait()
                    await self._do(mgr, cmd)
                    last_poll = 0                # refresh info right after a command
            except queue.Empty:
                pass
            if time.time() - last_poll >= 1.0:
                last_poll = time.time()
                if _Manager is not None:
                    try:
                        if mgr is None:
                            mgr = await _Manager.request_async()
                        await self._poll(mgr)
                    except Exception as e:
                        self._set(error=f"media info: {e}")
                        mgr = None
            await asyncio.sleep(0.1)

    async def _do(self, mgr, cmd):
        ses = None
        if mgr is not None and cmd in ("play_pause", "next", "prev"):
            try:
                ses = mgr.get_current_session()
            except Exception:
                ses = None
        try:
            if ses is not None and cmd == "play_pause":
                await ses.try_toggle_play_pause_async()
            elif ses is not None and cmd == "next":
                await ses.try_skip_next_async()
            elif ses is not None and cmd == "prev":
                await ses.try_skip_previous_async()
            else:
                _press_media_key(cmd)            # volume, or no session -> media keys
        except Exception:
            _press_media_key(cmd)

    async def _poll(self, mgr):
        ses = mgr.get_current_session()
        if ses is None:
            self._set(title="", artist="", album="", app="", playing=None, pos=None, dur=None,
                      art=None, error=None)
            self._art_key = None
            return
        app = pretty_app(ses.source_app_user_model_id)
        info = ses.get_playback_info()
        status = int(info.playback_status) if info is not None else None
        playing = True if status == PLAYING else False if status == PAUSED else None
        pos = dur = None
        try:
            tl = ses.get_timeline_properties()
            dur = tl.end_time.total_seconds()
            pos = tl.position.total_seconds()
            if playing and tl.last_updated_time is not None:
                from datetime import datetime, timezone
                age = (datetime.now(timezone.utc) - tl.last_updated_time).total_seconds()
                if 0 < age < 3600:
                    pos += age
            if not dur or dur <= 0:
                pos = dur = None
        except Exception:
            pass
        props = await ses.try_get_media_properties_async()
        title = (props.title or "") if props else ""
        artist = (props.artist or "") if props else ""
        album = (props.album_title or "") if props else ""
        self._set(title=title, artist=artist, album=album, app=app, playing=playing,
                  pos=pos, dur=dur, pos_at=time.time(), error=None)
        key = (title, artist, album, app)
        if key != self._art_key:
            self._art_key = key
            art = await self._read_art(props)
            with self.lock:
                self.state["art"] = art
                self.state["art_id"] += 1
                self.changed = True

    async def _read_art(self, props):
        if props is None or _Buffer is None:
            return None
        try:
            ref = props.thumbnail
            if ref is None:
                return None
            stream = await ref.open_read_async()
            size = int(stream.size)
            if not 0 < size < 20_000_000:
                return None
            buf = _Buffer(size)
            await stream.read_async(buf, size, _ISO.READ_AHEAD)
            data = bytes(memoryview(buf))[:int(buf.length)]
            img = Image.open(io.BytesIO(data)).convert("RGBA")
            img.thumbnail((512, 512))
            return img
        except Exception:
            return None
