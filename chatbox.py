"""
Chatbox stats, MagicChatbox style: builds the text that shows above your head in
VRChat (status, time, song + progress bar, fps, PC stats, headpats...).

VRChat limits: 144 characters, 9 lines, and it rate-limits fast senders, so we
send every few seconds and only when something changed (plus a keep-alive so it
doesn't fade out). Lines are dropped from the bottom if it gets too long.
"""
import time

LINE_KEYS = ["status", "afk", "time", "song", "song_bar", "world", "fps", "pc", "gpu_temp", "session",
             "distance", "headpats"]
LINE_LABELS = {
    "status": "Status text", "time": "Time", "song": "Song", "song_bar": "Song progress",
    "fps": "FPS", "pc": "CPU / GPU %", "gpu_temp": "GPU temp", "session": "Time in VR",
    "headpats": "Headpats", "afk": "AFK timer", "world": "World", "distance": "Distance",
}
DEFAULT = {
    "interval_s": 3,
    "style": "cute",
    "time_24h": False,
    "lines": {"status": True, "time": True, "song": True, "song_bar": True, "fps": False,
              "pc": False, "gpu_temp": False, "session": False, "headpats": False,
              "afk": True, "world": False, "distance": False},
    "statuses": ["fluffy vibes only :3", "pls give headpats", "running on Fluff VR Stats <3"],
    "status_index": 0,
    "rotate": True,
    "rotate_s": 30,
}

ICONS = {
    "cute":   {"status": "✨", "time": "⏰", "song": "🎵", "fps": "🎮", "pc": "🖥️", "gpu_temp": "🌡️",
               "session": "⏱️", "headpats": "🐾", "afk": "💤", "world": "🌍", "distance": "👣"},
    "simple": {"status": "♡", "time": "", "song": "♪", "fps": "", "pc": "", "gpu_temp": "",
               "session": "", "headpats": "", "afk": "zzz", "world": "@", "distance": ""},
}
LIMIT, MAX_LINES = 144, 9


def _fmt_t(sec):
    sec = max(0, int(sec or 0))
    return f"{sec // 60}:{sec % 60:02d}"


def song_bar(pos, dur, width=11):
    if not dur:
        return None
    k = min(1.0, max(0.0, (pos or 0) / dur))
    i = round(k * (width - 1))
    return f"{_fmt_t(pos)} " + "━" * i + "◉" + "─" * (width - 1 - i) + f" {_fmt_t(dur)}"


def current_status(cb, now=None):
    sts = [s for s in cb.get("statuses", []) if s.strip()]
    if not sts:
        return ""
    idx = cb.get("status_index", 0) % len(sts)
    if cb.get("rotate", True) and len(sts) > 1:
        now = time.time() if now is None else now
        idx = (idx + int(now // max(5, cb.get("rotate_s", 30)))) % len(sts)
    return sts[idx]


def _short(text, n):
    return text if len(text) <= n else text[:n - 1].rstrip() + "…"


def compose(cfg, stats, extras, music, now=None):
    """Returns the chatbox text (<=144 chars, <=9 lines)."""
    cb = cfg.get("chatbox", DEFAULT)
    on = cb.get("lines", DEFAULT["lines"])
    ic = ICONS.get(cb.get("style", "cute"), ICONS["cute"])
    now = time.time() if now is None else now

    def tag(k, text):
        return f"{ic[k]} {text}".strip() if ic.get(k) else text

    lines = []
    if on.get("afk") and extras.get("afk_for"):
        s = int(extras["afk_for"])
        lines.append(tag("afk", f"AFK {s // 60}m" if s >= 60 else "AFK"))
    if on.get("status"):
        st = current_status(cb, now)
        if st:
            lines.append(tag("status", _short(st, 60)))
    row = []
    if on.get("time"):
        fmt = "%H:%M" if cb.get("time_24h") else "%I:%M %p"
        row.append(tag("time", time.strftime(fmt, time.localtime(now)).lstrip("0")))
    if on.get("session") and extras.get("session_start"):
        s = int(now - extras["session_start"])
        row.append(tag("session", f"{s // 3600}h {s % 3600 // 60:02d}m" if s >= 3600 else f"{s // 60}m in VR"))
    if row:
        lines.append("  ".join(row))
    m = music or {}
    if on.get("song") and m.get("title") and m.get("playing") is not False:
        song = f"{m['title']} - {m['artist']}" if m.get("artist") else m["title"]
        lines.append(tag("song", _short(song, 48)))
        if on.get("song_bar"):
            bar = song_bar(m.get("pos"), m.get("dur"))
            if bar:
                lines.append(bar)
    elif on.get("song") and extras.get("song"):
        lines.append(tag("song", _short(extras["song"], 48)))
    if on.get("world") and extras.get("world_name"):
        n = extras.get("world_players", 0)
        lines.append(tag("world", _short(extras["world_name"], 34) + (f" ({n})" if n else "")))
    row = []
    if on.get("fps") and stats.get("fps") is not None:
        row.append(tag("fps", f"{stats['fps']:.0f} fps"))
    if on.get("pc"):
        parts = []
        if stats.get("cpu_pct") is not None:
            parts.append(f"CPU {stats['cpu_pct']:.0f}%")
        if stats.get("gpu_pct") is not None:
            parts.append(f"GPU {stats['gpu_pct']:.0f}%")
        if parts:
            row.append(tag("pc", " ".join(parts)))
    if on.get("gpu_temp") and stats.get("gpu_temp") is not None:
        row.append(tag("gpu_temp", f"{stats['gpu_temp']:.0f}°C"))
    if row:
        lines.append("  ".join(row))
    if on.get("distance") and extras.get("walked"):
        wk = extras["walked"]
        lines.append(tag("distance", f"walked {wk / 1000:.2f}km" if wk >= 1000 else f"walked {wk:.0f}m"))
    if on.get("headpats"):
        lines.append(tag("headpats", f"headpats: {extras.get('headpats', 0)}"))

    # fit VRChat's limits: drop lines from the bottom until it fits
    lines = lines[:MAX_LINES]
    while lines and len("\n".join(lines)) > LIMIT:
        lines.pop()
    return "\n".join(lines)
