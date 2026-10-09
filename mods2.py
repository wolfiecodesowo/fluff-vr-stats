"""
Fluff VR Stats - the v0.4.2 mods (quality-of-life + performance).

    tick(app, now)  is called about once a second from main.py

Performance:  power_saver, auto_boost, stutter_alert
Wrist:        second_clock, steps, session_recap
VRChat:       public_alert, avatar_swaps, busy_instance
Counters:     water_log, pat_goal
Fun:          compliments, mood_line, dance_party
Comfy:        quiet_hours, play_limit, charge_reminder
"""
import random
import time

COMPLIMENTS = ["ur avatar looks so good today", "u make every instance cozier", "ur laugh is contagious",
               "u're doing amazing, fr", "ur vibe is immaculate", "someone is glad u're here rn",
               "u deserve all the headpats", "u're a good friend", "ur outfit? 10/10", "proud of u :3",
               "u light up the room", "ur kind and it shows", "u're stronger than u think", "u matter <3"]
MOODS = ["😊 happy", "😴 sleepy", "🥰 cuddly", "😎 chillin", "🤪 chaotic", "🥺 need hugs", "🎉 hyped", "🤫 quiet mode"]

INFO = {  # mod id -> (category, label, description) - read by ui.MOD_INFO
    "power_saver": ("Performance", "Power saver", "Low fps? the overlay slows itself down"),
    "auto_boost": ("Performance", "Auto boost", "Boost tab tweaks on every launch"),
    "stutter_alert": ("Performance", "Stutter alert", "Tells u when frames keep spiking"),
    "second_clock": ("Wrist", "2nd clock", "A friend's time zone on ur wrist"),
    "steps": ("Wrist", "Step counter", "Steps walked this session"),
    "session_recap": ("Wrist", "AFK recap", "Session recap when u go AFK"),
    "public_alert": ("VRChat", "Public alert", "Heads up when u join a public"),
    "avatar_swaps": ("VRChat", "Avatar swaps", "How many avis u tried today"),
    "busy_instance": ("VRChat", "Busy instance", "Warns when 30+ people are here"),
    "water_log": ("Counters", "Water tracker", "Tap 💧 on ur wrist for every sip"),
    "pat_goal": ("Counters", "Headpat goal", "Daily headpat goal (50)"),
    "compliments": ("Fun", "Compliments", "A sweet note on ur wrist every 30 min"),
    "mood_line": ("Fun", "Mood", "Ur mood in the chatbox (Chatbox tab)"),
    "dance_party": ("Fun", "Dance party", "Notices when u're dancing"),
    "quiet_hours": ("Comfy", "Quiet hours", "No pop-ups 11pm-8am (warnings still show)"),
    "play_limit": ("Comfy", "Playtime check", "Gentle nudge after 3h in VR"),
    "charge_reminder": ("Comfy", "Charge reminder", "Plug in low batteries while AFK"),
}
DEFAULTS = {k: False for k in INFO}
DEFAULTS.update(power_saver=True, stutter_alert=False, public_alert=True, quiet_hours=False)
# chatbox lines these mods add (turning the mod on also turns on its line)
MOD_TO_LINE = {"water_log": "water", "mood_line": "mood", "compliments": "compliment", "steps": "steps",
               "avatar_swaps": "avatars"}


def _s(app):
    return app.__dict__.setdefault("_m2", {
        "low_since": None, "ok_since": None, "saving": False, "spikes": [], "spike_t": 0,
        "world_id": None, "players_warned": None, "avatar": None, "swaps_day": None,
        "comp_t": time.time(), "dance_since": None, "dance_t": 0, "play_t": 0, "charge_t": 0,
        "afk_was": False, "pats_goal_day": None, "boosted": False,
    })


def is_quiet(cfg, now=None):
    if not cfg["modules"].get("quiet_hours"):
        return False
    q = cfg.get("quiet", {})
    try:
        a = [int(v) for v in str(q.get("from", "23:00")).split(":")[:2]]
        b = [int(v) for v in str(q.get("to", "08:00")).split(":")[:2]]
    except ValueError:
        a, b = [23, 0], [8, 0]
    lt = time.localtime(now or time.time())
    m, ma, mb = lt.tm_hour * 60 + lt.tm_min, a[0] * 60 + a[1], b[0] * 60 + b[1]
    return (ma <= m < mb) if ma < mb else (m >= ma or m < mb)


def second_clock_text(cfg, now=None):
    c = cfg.get("second_clock", {}) or {}
    try:
        off = float(c.get("offset", 9))
    except (TypeError, ValueError):
        off = 9.0
    t = time.gmtime((now or time.time()) + off * 3600)
    fmt = "%H:%M" if cfg.get("chatbox", {}).get("time_24h") else "%I:%M %p"
    return (c.get("name") or "Tokyo"), time.strftime(fmt, t).lstrip("0")


def tick(app, now):
    st, cfg, m = app.state, app.cfg, app.cfg["modules"]
    x, s = st.extras, st.stats
    S = _s(app)
    today = time.strftime("%Y-%m-%d", time.localtime(now))

    # ---------------------------------------------------------- performance
    fps, ref = s.get("fps"), s.get("refresh")
    if m.get("power_saver") and fps and ref and not st.desktop:
        low = fps < ref * 0.75
        if low:
            S["ok_since"] = None
            S["low_since"] = S["low_since"] or now
            if not S["saving"] and now - S["low_since"] > 15:
                S["saving"] = True
                st.power_saving = True
                app.show_alert("fps is low ~ power saver on: the overlay is going easy on ur PC", "warn", 5)
        else:
            S["low_since"] = None
            S["ok_since"] = S["ok_since"] or now
            if S["saving"] and now - S["ok_since"] > 30:
                S["saving"] = False
                st.power_saving = False
    elif S["saving"]:
        S["saving"] = False
        st.power_saving = False
    if m.get("auto_boost") and not S["boosted"] and getattr(app, "tweaks", None) is not None:
        S["boosted"] = True
        done = 0
        for key in ("power_plan", "game_mode", "game_dvr", "vr_priority", "gpu_pref"):
            try:
                if app.tweaks.apply(key):
                    done += 1
            except Exception:
                pass
        if done:
            app.show_alert(f"auto boost: {done} fps tweaks on ⚡ (undo any in the Boost tab)", secs=5)
    if m.get("stutter_alert") and ref:
        ft = s.get("frametimes") or []
        budget = 1000.0 / ref
        if ft and ft[-1] > budget * 2.2:
            S["spikes"].append(now)
        S["spikes"] = [t for t in S["spikes"] if now - t < 10]
        if len(S["spikes"]) >= 6 and now - S["spike_t"] > 300:
            S["spike_t"] = now
            S["spikes"] = []
            app.show_alert("lots of stutters rn ~ probably new avatars / shaders loading. it usually settles", "warn", 7)

    # ---------------------------------------------------------- wrist
    if m.get("second_clock"):
        x["clock2"] = second_clock_text(cfg, now)
    if m.get("steps"):
        x["steps"] = int((st.walked or 0) / 0.72)
    afk = bool(st.afk)
    if m.get("session_recap") and afk and not S["afk_was"]:
        ss = x.get("session_start") or now
        mins = int((now - ss) // 60)
        w = st.world or {}
        app.show_alert(f"recap: {mins // 60}h {mins % 60:02d}m in VR · {x.get('headpats', 0)} pats · "
                       f"{w.get('worlds_visited', 0) or 0} worlds · {w.get('people_met', 0) or 0} people", secs=12)
    S["afk_was"] = afk

    # ---------------------------------------------------------- vrchat
    w = st.world or {}
    wid = (w.get("world_id") or "") + ":" + (w.get("instance") or "") if w.get("found") else None
    if wid != S["world_id"]:
        S["world_id"] = wid
        S["players_warned"] = None
        if wid and m.get("public_alert") and str(w.get("type", "")).lower().startswith("public"):
            app.show_alert("u're in a PUBLIC instance ~ mind ur mic + personal info :3", "warn", 6)
    n = len(w.get("players") or [])
    if m.get("busy_instance") and n >= 30 and S["players_warned"] != wid:
        S["players_warned"] = wid
        app.show_alert(f"busy instance ({n} people) ~ fps might dip, Boost tab can help", "warn", 6)
    av = (st.avatar or {}).get("id")
    if S["swaps_day"] != today:
        S["swaps_day"] = today
        cfg["avatar_swaps"] = {"date": today, "n": 0}
    if av and av != S["avatar"]:
        if S["avatar"] is not None:
            sw = cfg.setdefault("avatar_swaps", {"date": today, "n": 0})
            sw["n"] = sw.get("n", 0) + 1
            st.dirty_cfg = True
        S["avatar"] = av
    x["avatar_swaps"] = (cfg.get("avatar_swaps") or {}).get("n", 0)

    # ---------------------------------------------------------- counters
    wl = cfg.setdefault("water", {"date": today, "sips": 0})
    if wl.get("date") != today:
        wl.update(date=today, sips=0)
    x["water"] = wl.get("sips", 0)
    if m.get("pat_goal"):
        goal = max(5, int(cfg.get("pat_goal_n", 50)))
        pd = cfg.setdefault("pats_today", {"date": today, "start": x.get("headpats", 0)})
        if pd.get("date") != today:
            pd.update(date=today, start=x.get("headpats", 0))
        got = max(0, x.get("headpats", 0) - pd.get("start", 0))
        x["pat_goal"] = (got, goal)
        if got >= goal and S["pats_goal_day"] != today:
            S["pats_goal_day"] = today
            app.show_alert(f"headpat goal reached!! {got}/{goal} today 🐾💖", secs=8)

    # ---------------------------------------------------------- fun
    if m.get("compliments"):
        x["compliment"] = COMPLIMENTS[int(now // 600) % len(COMPLIMENTS)]
        if now - S["comp_t"] > 1800:
            S["comp_t"] = now
            app.show_alert("💖 " + random.choice(COMPLIMENTS), secs=6)
    else:
        S["comp_t"] = now
    x["mood"] = cfg.get("mood", MOODS[0]) if m.get("mood_line") else None
    if m.get("dance_party"):
        if (x.get("vibe") or 0) > 65:
            S["dance_since"] = S["dance_since"] or now
            if now - S["dance_since"] > 20 and now - S["dance_t"] > 900:
                S["dance_t"] = now
                app.show_alert("DANCE PARTY DETECTED 💃🕺 go off!!", secs=5)
        else:
            S["dance_since"] = None

    # ---------------------------------------------------------- comfy
    if m.get("play_limit"):
        lim = max(1, float(cfg.get("play_limit_h", 3)))
        sess = now - (x.get("session_start") or now)
        if sess > lim * 3600 and now - S["play_t"] > 1800:
            S["play_t"] = now
            app.show_alert(f"u've been in VR for {sess / 3600:.1f}h ~ water, snack, stretch? :3", "warn", 10)
    if m.get("charge_reminder") and afk and now - S["charge_t"] > 1800:
        low = [b for b in (s.get("batteries") or []) if b[1] is not None and b[1] < 30 and not b[2]]
        if low:
            S["charge_t"] = now
            app.show_alert("u're AFK ~ good time to charge: " + ", ".join(f"{b[0]} {b[1]:.0f}%" for b in low), "warn", 12)


def sip(app):
    today = time.strftime("%Y-%m-%d")
    wl = app.cfg.setdefault("water", {"date": today, "sips": 0})
    if wl.get("date") != today:
        wl.update(date=today, sips=0)
    wl["sips"] = wl.get("sips", 0) + 1
    app.state.extras["water"] = wl["sips"]
    app.state.dirty_cfg = app.state.hud_dirty = True
    app.show_alert(f"💧 sip #{wl['sips']} today ~ good job!", secs=3)


def next_mood(cfg):
    cur = cfg.get("mood", MOODS[0])
    cfg["mood"] = MOODS[(MOODS.index(cur) + 1) % len(MOODS)] if cur in MOODS else MOODS[0]
    return cfg["mood"]
