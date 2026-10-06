"""
Discord connection for the client.

1. Rich Presence: your Discord profile shows "Fluff VR Stats :3" with your fps, world and
   time in VR, the logo, and Download / Join Discord buttons (free advertising <3).
   Uses the local Discord app (pypresence), so no login or token is needed - just the
   public application id of the Fluff VR Stats Discord app.
2. Server info: how many people are online in the Fluff VR Stats Discord, read from the
   server's public widget, shown on the <3 page with a join button.

Everything here runs in a background thread and never throws into the app.
"""
import json
import threading
import time
import urllib.request

LOGO_URL = "https://raw.githubusercontent.com/wolfiecodesowo/fluff-vr-stats/main/docs/images/logo.png"
GITHUB_URL = "https://github.com/wolfiecodesowo/fluff-vr-stats"
UA = {"User-Agent": "FluffVRStats/0.1 (+https://github.com/wolfiecodesowo/fluff-vr-stats)"}

try:
    from pypresence import Presence
except Exception:          # not installed yet -> presence just stays off
    Presence = None


def _fmt_dur(sec):
    sec = int(sec)
    return f"{sec // 3600}h {sec % 3600 // 60:02d}m" if sec >= 3600 else f"{sec // 60}m"


class DiscordLink:
    def __init__(self, cfg):
        self.cfg = cfg
        self.running = True
        self.info = {"rpc": "off", "online": None, "server": None}
        self.changed = False
        self.status = {}             # filled in by the app: fps, world, song, session_start
        self._rpc = None
        self._last_payload = None
        threading.Thread(target=self._guard, args=(self._rpc_loop,), daemon=True, name="discord_rpc").start()
        threading.Thread(target=self._guard, args=(self._widget_loop,), daemon=True, name="discord_widget").start()

    # ---- helpers
    def _guard(self, fn):
        while self.running:
            try:
                fn()
                return
            except Exception:
                time.sleep(10)

    def _set(self, k, v):
        if self.info.get(k) != v:
            self.info[k] = v
            self.changed = True

    def stop(self):
        self.running = False
        self._close_rpc()

    def snapshot(self):
        return dict(self.info)

    def invite(self):
        return (self.cfg.get("discord") or {}).get("invite") or ""

    # ---- rich presence
    def _close_rpc(self):
        if self._rpc:
            try:
                self._rpc.clear()
                self._rpc.close()
            except Exception:
                pass
        self._rpc = None
        self._last_payload = None

    def _payload(self):
        s = self.status
        dc = self.cfg.get("discord") or {}
        fps = s.get("fps")
        world = s.get("world")
        details = "chillin in VR :3"
        if fps is not None and world:
            details = f"{fps:.0f} fps in {world}"[:120]
        elif fps is not None:
            details = f"{fps:.0f} fps in VR"
        elif world:
            details = f"in {world}"[:120]
        state = None
        if dc.get("show_song", True) and s.get("song"):
            state = f"listening to {s['song']}"[:120]
        p = {"details": details, "large_image": LOGO_URL, "large_text": "Fluff VR Stats :3",
             "start": int(s.get("session_start") or time.time())}
        if state:
            p["state"] = state
        btns = [{"label": "Get Fluff VR Stats", "url": GITHUB_URL}]
        if self.invite():
            btns.append({"label": "Join the Discord", "url": self.invite()})
        p["buttons"] = btns
        return p

    def _rpc_loop(self):
        while self.running:
            dc = self.cfg.get("discord") or {}
            app_id = str(dc.get("app_id") or "").strip()
            want = self.cfg["modules"].get("discord_presence", True) and app_id.isdigit()
            global Presence
            if Presence is None:
                try:
                    from pypresence import Presence as _P
                    Presence = _P
                except Exception:
                    pass
            if not want or Presence is None:
                self._close_rpc()
                self._set("rpc", "off" if Presence else "missing pypresence")
                time.sleep(5)
                continue
            if self._rpc is None:
                try:
                    rpc = Presence(app_id)
                    rpc.connect()
                    self._rpc = rpc
                    self._set("rpc", "connected")
                except Exception:
                    self._set("rpc", "discord not open")
                    time.sleep(20)
                    continue
            p = self._payload()
            if p != self._last_payload:
                try:
                    self._rpc.update(**p)
                    self._last_payload = p
                except Exception:
                    self._close_rpc()
                    self._set("rpc", "discord not open")
                    time.sleep(10)
                    continue
            time.sleep(15)       # Discord allows one presence update every 15s

    # ---- server widget (online count)
    def _widget_loop(self):
        while self.running:
            gid = str((self.cfg.get("discord") or {}).get("guild_id") or "").strip()
            if gid.isdigit():
                try:
                    req = urllib.request.Request(f"https://discord.com/api/guilds/{gid}/widget.json", headers=UA)
                    with urllib.request.urlopen(req, timeout=8) as r:
                        data = json.loads(r.read().decode("utf-8"))
                    self._set("online", int(data.get("presence_count", 0)))
                    self._set("server", data.get("name"))
                    if data.get("instant_invite") and not self.invite():
                        self.cfg.setdefault("discord", {})["invite"] = data["instant_invite"]
                except Exception:
                    pass
            for _ in range(300):              # every 5 minutes
                if not self.running:
                    return
                time.sleep(1)
