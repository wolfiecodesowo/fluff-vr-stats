"""
Chatbox stats, MagicChatbox style: builds the text that shows above your head in
VRChat (status, time, song + progress bar, fps, PC stats, headpats...).

VRChat limits: 144 characters, 9 lines, and it rate-limits fast senders, so we
send every few seconds and only when something changed (plus a keep-alive so it
doesn't fade out). Lines are dropped from the bottom if it gets too long.
"""
import time

LINE_KEYS = ["status", "afk", "time", "date", "song", "song_bar", "world", "fps", "pc", "gpu_temp", "session",
             "today", "streak", "distance", "headpats", "boops", "jumps", "yap", "height", "countdown", "quote",
             "kaomoji"]
LINE_LABELS = {
    "status": "Status text", "time": "Time", "song": "Song", "song_bar": "Song progress",
    "fps": "FPS", "pc": "CPU / GPU %", "gpu_temp": "GPU temp", "session": "Time in VR",
    "headpats": "Headpats", "afk": "AFK timer", "world": "World", "distance": "Distance",
    "date": "Date", "today": "VR today", "streak": "VR streak", "boops": "Boops", "jumps": "Jumps",
    "yap": "Yap meter", "height": "Avi height", "countdown": "Countdown", "quote": "Cute quote",
    "kaomoji": "Kaomoji",
}
QUOTES = ["u are so loved <3", "stay hydrated, stay fluffy", "be the headpat u wish to see", "tail wags only",
          "chaos but make it cute", "small steps still count", "u matter more than u know", "nap later, vibe now",
          "everyone deserves a hug", "being silly is a lifestyle", "kindness is free, spread it", "ur doing amazing"]
KAOMOJI = ["(=^･ω･^=)", "(◕ᴗ◕✿)", "(｡•ᴗ•｡)", "ʕ•ᴥ•ʔ", "(≧◡≦)", "(•ω•)", "ฅ^•ﻌ•^ฅ", "(｡♥‿♥｡)"]
DEFAULT = {
    "interval_s": 3,
    "style": "cute",
    "time_24h": False,
    "lines": {"status": True, "time": True, "song": True, "song_bar": True, "fps": False,
              "pc": False, "gpu_temp": False, "session": False, "headpats": False,
              "afk": True, "world": False, "distance": False, "date": False, "today": False,
              "streak": False, "boops": False, "jumps": False, "yap": False, "height": False,
              "countdown": False, "quote": False, "kaomoji": False},
    "statuses": ["fluffy vibes only :3", "pls give headpats", "running on Fluff VR Stats <3"],
    "status_index": 0,
    "rotate": True,
    "rotate_s": 30,
}

ICONS = {
    "cute":   {"status": "✨", "time": "⏰", "song": "🎵", "fps": "🎮", "pc": "🖥️", "gpu_temp": "🌡️",
               "session": "⏱️", "headpats": "🐾", "afk": "💤", "world": "🌍", "distance": "👣",
               "date": "📅", "today": "🥽", "streak": "🔥", "boops": "👃", "jumps": "🐇", "yap": "🗣️",
               "height": "📏", "countdown": "🎉", "quote": "💭"},
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


def _dur(s):
    s = int(s or 0)
    return f"{s // 3600}h {s % 3600 // 60:02d}m" if s >= 3600 else f"{s // 60}m"


def countdown_text(cd, now=None):
    """{'name': 'my birthday', 'date': '2026-12-25'} -> 'my birthday in 12d'"""
    try:
        target = time.mktime(time.strptime(cd.get("date", ""), "%Y-%m-%d"))
    except (ValueError, TypeError):
        return None
    now = time.time() if now is None else now
    days = int((target - now) // 86400) + 1
    name = cd.get("name") or "the big day"
    if days > 1:
        return f"{name} in {days}d"
    if days == 1:
        return f"{name} is tomorrow!!"
    if days == 0:
        return f"{name} is TODAY!!"
    return None


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
    if on.get("date"):
        row.append(tag("date", time.strftime("%b %d", time.localtime(now)).replace(" 0", " ")))
    if on.get("session") and extras.get("session_start"):
        s = int(now - extras["session_start"])
        row.append(tag("session", f"{s // 3600}h {s % 3600 // 60:02d}m" if s >= 3600 else f"{s // 60}m in VR"))
    if on.get("today") and extras.get("vr_today_s"):
        row.append(tag("today", _dur(extras["vr_today_s"]) + " today"))
    if on.get("streak") and extras.get("vr_streak", 0) > 1:
        row.append(tag("streak", f"{extras['vr_streak']} day streak"))
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
    row = []
    if on.get("headpats"):
        row.append(tag("headpats", f"{extras.get('headpats', 0)} pats"))
    if on.get("boops"):
        row.append(tag("boops", f"{extras.get('boops', 0)} boops"))
    if on.get("jumps"):
        row.append(tag("jumps", f"{extras.get('jumps', 0)} jumps"))
    if row:
        lines.append("  ".join(row))
    row = []
    if on.get("yap") and extras.get("talk_s"):
        sess = max(1, now - extras.get("session_start", now))
        row.append(tag("yap", f"yapped {_dur(extras['talk_s'])} ({min(100, extras['talk_s'] * 100 / sess):.0f}%)"))
    if on.get("height") and extras.get("height_m"):
        hm = extras["height_m"]
        ft = hm * 3.28084
        row.append(tag("height", f"{hm:.2f}m ({int(ft)}'{round((ft % 1) * 12)}\")"))
    if row:
        lines.append("  ".join(row))
    if on.get("countdown"):
        c = countdown_text(cfg.get("countdown", {}), now)
        if c:
            lines.append(tag("countdown", _short(c, 40)))
    if on.get("quote"):
        lines.append(tag("quote", QUOTES[int(now // 3600) % len(QUOTES)]))
    if on.get("kaomoji") and lines:
        lines[-1] = lines[-1] + " " + KAOMOJI[int(now // 20) % len(KAOMOJI)]

    # fit VRChat's limits: drop lines from the bottom until it fits
    lines = lines[:MAX_LINES]
    while lines and len("\n".join(lines)) > LIMIT:
        lines.pop()
    return "\n".join(lines)
