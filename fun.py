"""
Fluff VR Stats - the fun stuff that isn't a mod:

  - progress: counts ur VR life (per month + forever) from the counters the app already has
  - badges: 30+ achievements that pop up on ur wrist when u earn them
  - Kitty closet: hats + collars for Lil Kitty, unlocked by badges and seasons
  - seasons: Halloween / winter / valentines / pride events that switch on by themselves
    (Halloween: pat ur kitty for candy, collect 31 for a pumpkin hat that's urs forever)
  - theme codes: share ur exact look as a short code (FLUFF-xxxx), paste someone else's
  - Fluff Wrapped: a monthly recap card (PNG) to post anywhere

Everything is saved in config.json -> "fun". Nothing here touches the network
(the Discord link, Fluff Friends + events live in fluffnet.py).
"""
import base64
import math
import os
import random
import time

from PIL import Image

import themes
from lang import ImageDraw, tr

HERE = os.path.dirname(os.path.abspath(__file__))
WRAPPED_DIR = os.path.join(HERE, "wrapped")

COUNTERS = ("pats", "boops", "jumps", "walked_m", "vr_s", "people", "kitty_pats", "kitty_fed",
            "gchat_sent", "waves", "candy", "worlds_new")

DEFAULT = {
    "life": {},               # forever counters
    "months": {},             # "2026-10": counters + "world_s" + "songs"
    "worlds": [],             # world ids u've ever been in (capped)
    "themes_tried": [],
    "badges": {},             # id -> unix time earned
    "seen_badges": [],        # badges u've looked at (for the "new!" dot)
    "closet": {"hat": "none", "neck": "bell"},
    "season": "auto",         # auto / off
    "seasons_joined": [],     # "halloween-2026"...
    "candy_unlocked": [],     # seasonal items earned for keeps
    "flags": {},              # one-off things (night_owl, early_bird, event_joined, linked, wrapped_made...)
    "_last": {},              # last seen totals (to count deltas)
}


# ------------------------------------------------------------------ seasons ---
SEASONS = {
    "halloween": {"name": "Spooky Season", "emoji": "🎃", "theme": "spooky_floof", "hat": "witch",
                  "banner": "spooky season!! pat ur kitty for candy 🍬", "cursor": "pumpkin"},
    "winter": {"name": "Snowy Season", "emoji": "❄", "theme": "frost_wolf", "hat": "santa",
               "banner": "snowy season ~ ur kitty got a lil santa hat", "cursor": "star"},
    "valentine": {"name": "Valentines", "emoji": "💗", "theme": "strawberry_milk", "hat": "heart_bow",
                  "banner": "valentines week! give extra headpats <3", "cursor": "heart"},
    "pride": {"name": "Pride Month", "emoji": "🌈", "theme": "pride_classic", "hat": "none", "neck": "rainbow",
              "banner": "happy pride!! 🏳️‍🌈 ur kitty is wearing her scarf", "cursor": "heart"},
}


def season_key(now=None):
    tm = time.localtime(now or time.time())
    m, d = tm.tm_mon, tm.tm_mday
    if m == 10 or (m == 11 and d <= 2):
        return "halloween"
    if m == 12 or (m == 1 and d <= 6):
        return "winter"
    if m == 2 and 7 <= d <= 15:
        return "valentine"
    if m == 6:
        return "pride"
    return None


def season_id(key, now=None):
    tm = time.localtime(now or time.time())
    y = tm.tm_year - (1 if key == "winter" and tm.tm_mon == 1 else 0)
    return f"{key}-{y}"


# ---------------------------------------------------------------- closet ---
# (id, slot, name, how u unlock it: ("free",) / ("badge", id) / ("season", key) / ("candy", n))
ITEMS = [
    ("none", "hat", "no hat", ("free",)),
    ("bow", "hat", "lil bow", ("free",)),
    ("flower", "hat", "flower crown", ("badge", "streak_7")),
    ("party", "hat", "party hat", ("badge", "wrapped")),
    ("headphones", "hat", "headphones", ("badge", "songs_100")),
    ("crown", "hat", "golden crown", ("badge", "pats_1000")),
    ("halo", "hat", "angel halo", ("badge", "kitty_pats_500")),
    ("beanie", "hat", "beta beanie", ("badge", "beta")),
    ("witch", "hat", "witch hat", ("season", "halloween")),
    ("pumpkin", "hat", "pumpkin hat", ("candy", 31)),
    ("santa", "hat", "santa hat", ("season", "winter")),
    ("heart_bow", "hat", "heart bow", ("season", "valentine")),
    ("none", "neck", "nothing", ("free",)),
    ("bell", "neck", "bell collar", ("free",)),
    ("heart_tag", "neck", "heart tag", ("badge", "kitty_fed_25")),
    ("scarf", "neck", "comfy scarf", ("badge", "vr_10h")),
    ("bandana", "neck", "bandana", ("badge", "worlds_25")),
    ("spiky", "neck", "spiky collar", ("badge", "boops_100")),
    ("bowtie", "neck", "fancy bowtie", ("badge", "people_100")),
    ("rainbow", "neck", "rainbow scarf", ("season", "pride")),
]
ITEM_NAMES = {(i, s): n for i, s, n, _ in ITEMS}


# ----------------------------------------------------------------- badges ---
# (id, emoji, name, how to get it, check(life, flags, fun) -> bool)
def _c(key, n):
    return lambda L, F, f: L.get(key, 0) >= n


BADGES = [
    ("hello", "🐾", "Hello Fluff", "open the app for the first time", lambda L, F, f: True),
    ("beta", "🧪", "Beta Tester", "link the app to the Fluff Discord while it's in beta", lambda L, F, f: F.get("linked")),
    ("pats_10", "✋", "Pat Me", "get 10 headpats", _c("pats", 10)),
    ("pats_100", "💞", "Pat Magnet", "get 100 headpats", _c("pats", 100)),
    ("pats_1000", "👑", "Headpat Royalty", "get 1,000 headpats", _c("pats", 1000)),
    ("boops_100", "👃", "Boop Champ", "get booped 100 times", _c("boops", 100)),
    ("jumps_100", "🐇", "Bouncy", "jump 100 times", _c("jumps", 100)),
    ("walk_1k", "👣", "Lil Zoomies", "walk 1 km in VR", _c("walked_m", 1000)),
    ("walk_10k", "💨", "ZOOMIES", "walk 10 km in VR", _c("walked_m", 10000)),
    ("vr_1h", "🥽", "First Hour", "spend 1 hour in VR", _c("vr_s", 3600)),
    ("vr_10h", "⏰", "Regular", "spend 10 hours in VR", _c("vr_s", 36000)),
    ("vr_50h", "🌙", "VR Liver", "spend 50 hours in VR", _c("vr_s", 180000)),
    ("vr_100h", "🌌", "Lives Here Now", "spend 100 hours in VR", _c("vr_s", 360000)),
    ("streak_3", "🔥", "On a Roll", "VR 3 days in a row", lambda L, F, f: L.get("best_streak", 0) >= 3),
    ("streak_7", "🌸", "Week Streak", "VR 7 days in a row", lambda L, F, f: L.get("best_streak", 0) >= 7),
    ("streak_30", "💎", "Month Streak", "VR 30 days in a row", lambda L, F, f: L.get("best_streak", 0) >= 30),
    ("worlds_10", "🗺", "Explorer", "visit 10 different worlds", lambda L, F, f: len(f.get("worlds", [])) >= 10),
    ("worlds_25", "🧭", "World Hopper", "visit 25 different worlds", lambda L, F, f: len(f.get("worlds", [])) >= 25),
    ("people_100", "🤝", "Social Fluff", "be in an instance with 100 people", _c("people", 100)),
    ("people_500", "🎉", "Party Animal", "be in an instance with 500 people", _c("people", 500)),
    ("kitty_friend", "🐱", "Kitty's Friend", "make friends with Lil Kitty", lambda L, F, f: F.get("kitty_friend")),
    ("kitty_fed_25", "🐟", "Fish Provider", "feed ur kitty 25 times", _c("kitty_fed", 25)),
    ("kitty_pats_500", "😇", "Kitty Whisperer", "pat ur kitty 500 times", _c("kitty_pats", 500)),
    ("chat_1", "💬", "Said Hi", "send a message in global chat", _c("gchat_sent", 1)),
    ("chat_100", "📣", "Yapper", "send 100 global chat messages", _c("gchat_sent", 100)),
    ("songs_100", "🎧", "DJ Fluff", "vibe to 100 songs in VR", _c("songs", 100)),
    ("themes_10", "🎨", "Drip Check", "try 10 different themes", lambda L, F, f: len(f.get("themes_tried", [])) >= 10),
    ("night_owl", "🦉", "Night Owl", "be in VR at 3am", lambda L, F, f: F.get("night_owl")),
    ("early_bird", "🐤", "Early Bird", "be in VR before 7am", lambda L, F, f: F.get("early_bird")),
    ("wave", "👋", "Hey Friend!", "wave at another Fluff user in ur instance", _c("waves", 1)),
    ("event", "🎪", "Community Night", "be in VR during a Fluff community night", lambda L, F, f: F.get("event_joined")),
    ("wrapped", "🎁", "Wrapped Up", "make ur Fluff Wrapped card", lambda L, F, f: F.get("wrapped_made")),
    ("theme_share", "🔗", "Trendsetter", "copy ur theme code to share it", lambda L, F, f: F.get("theme_shared")),
    ("spooky", "🎃", "Spooky Fluff", "be in VR during spooky season", lambda L, F, f: F.get("season_halloween")),
    ("candy_31", "🍬", "Candy Hoarder", "collect 31 candy in one spooky season", lambda L, F, f: F.get("candy_31")),
    ("snowy", "❄", "Snow Floof", "be in VR during snowy season", lambda L, F, f: F.get("season_winter")),
]
BADGE_MAP = {b[0]: b for b in BADGES}


# ------------------------------------------------------------- theme codes ---
_CURSORS = ["paw", "heart", "star", "pumpkin"]


def _rgb_idx(val, table):
    if not val:
        return 255
    for i, (_, c) in enumerate(table):
        if tuple(c) == tuple(val):
            return i
    return None


def theme_code(cfg):
    """ur exact look as a short code: FLUFF-XXXXXXXXXX"""
    st = cfg.get("style", {})
    names = [p[0] for p in themes.PRESETS]
    b = bytearray([1, names.index(cfg.get("theme")) if cfg.get("theme") in names else 0,
                   themes.EAR_STYLES.index(st.get("ears", "cat")) if st.get("ears") in themes.EAR_STYLES else 0,
                   (1 if st.get("stripe", True) else 0) | (_CURSORS.index(cfg.get("cursor", "paw")) << 1
                                                          if cfg.get("cursor", "paw") in _CURSORS else 0)])
    for key, table in (("accent", themes.ACCENTS), ("background", themes.BACKGROUNDS)):
        v = st.get(key)
        i = _rgb_idx(v, table)
        if i is None:                  # custom color from config.json -> raw rgb
            b += bytes([254]) + bytes(int(x) & 255 for x in list(v)[:3])
        else:
            b.append(i)
    b.append(sum(b) & 255)             # tiny checksum so typos get caught
    return "FLUFF-" + base64.b32encode(bytes(b)).decode().rstrip("=")


def read_theme_code(code):
    """code -> dict of settings to apply, or None if it's not a real code"""
    try:
        s = "".join(str(code).upper().split()).replace("FLUFF-", "").replace("FLUFF", "")
        s = s.replace("0", "O").replace("1", "I").replace("8", "B")     # people mistype these
        raw = base64.b32decode(s + "=" * (-len(s) % 8))
        if len(raw) < 6 or raw[0] != 1 or raw[-1] != sum(raw[:-1]) & 255:
            return None
        names = [p[0] for p in themes.PRESETS]
        out = {"theme": names[raw[1] % len(names)],
               "ears": themes.EAR_STYLES[raw[2] % len(themes.EAR_STYLES)],
               "stripe": bool(raw[3] & 1), "cursor": _CURSORS[(raw[3] >> 1) % len(_CURSORS)]}
        i = 4
        for key, table in (("accent", themes.ACCENTS), ("background", themes.BACKGROUNDS)):
            v = raw[i]
            if v == 254:
                out[key] = list(raw[i + 1:i + 4])
                i += 4
            else:
                out[key] = None if v == 255 else list(table[v % len(table)][1])
                i += 1
        return out
    except Exception:
        return None


def apply_theme_code(cfg, code):
    got = read_theme_code(code)
    if not got:
        return False
    cfg["theme"] = got["theme"]
    st = cfg.setdefault("style", {})
    st.update(ears=got["ears"], stripe=got["stripe"], accent=got["accent"], background=got["background"])
    if got["cursor"] != "pumpkin" or season_key() == "halloween":
        cfg["cursor"] = got["cursor"]
    return True


# ---------------------------------------------------------------- tracker ---
def _month(now=None):
    return time.strftime("%Y-%m", time.localtime(now or time.time()))


class Fun:
    """Owned by the App. tick() once a second-ish; it returns a list of alerts to show."""

    def __init__(self, cfg):
        self.cfg = cfg
        f = cfg.setdefault("fun", {})
        for k, v in DEFAULT.items():
            if k not in f or type(f[k]) is not type(v):
                f[k] = json_copy(v)
        self.f = f
        self.new_alerts = []
        self.last_tick = 0
        self.last_song = None
        self.last_world = None
        self.last_people = None
        self.world_t = time.time()
        self.candy_cd = 0

    # ---- helpers
    def month(self, key=None):
        m = self.f["months"].setdefault(key or _month(), {})
        return m

    def add(self, key, n=1):
        if not n:
            return
        L = self.f["life"]
        L[key] = L.get(key, 0) + n
        m = self.month()
        m[key] = m.get(key, 0) + n

    def life(self, key):
        return self.f["life"].get(key, 0)

    def has(self, badge):
        return badge in self.f["badges"]

    def unlocked(self, item_id, slot):
        for i, s, _, how in ITEMS:
            if i == item_id and s == slot:
                kind = how[0]
                if kind == "free":
                    return True
                if kind == "badge":
                    return self.has(how[1])
                if kind == "season":
                    return season_key() == how[1] or item_id in self.f["candy_unlocked"] \
                        or any(x.startswith(how[1]) for x in self.f["seasons_joined"])
                if kind == "candy":
                    return item_id in self.f["candy_unlocked"]
        return False

    def closet(self):
        """what kitty is wearing right now (season items show up by themselves unless u picked something)"""
        c = self.f["closet"]
        hat, neck = c.get("hat", "none"), c.get("neck", "bell")
        if not self.unlocked(hat, "hat"):
            hat = "none"
        if not self.unlocked(neck, "neck"):
            neck = "bell"
        s = self.season()
        if s and not c.get("picked"):
            hat = SEASONS[s].get("hat", hat) if SEASONS[s].get("hat", "none") != "none" else hat
            neck = SEASONS[s].get("neck", neck)
        return hat, neck

    def season(self):
        if self.f.get("season") == "off":
            return None
        return season_key()

    def new_badges(self):
        return [b for b in self.f["badges"] if b not in self.f["seen_badges"]]

    # ---- the main tick
    def tick(self, app_state, kitty_cfg, music=None, world=None, desktop=False, now=None):
        now = now or time.time()
        if now - self.last_tick < 1.0:
            return []
        dt = min(5.0, now - self.last_tick) if self.last_tick else 0
        self.last_tick = now
        cfg, F, last = self.cfg, self.f["flags"], self.f["_last"]

        # deltas from the counters the app already keeps
        for key, total in (("pats", cfg.get("headpats_total", 0)), ("boops", cfg.get("boops_total", 0)),
                           ("jumps", cfg.get("jumps_total", 0)), ("walked_m", int(cfg.get("walked_total_m", 0))),
                           ("kitty_pats", kitty_cfg.get("pats", 0)), ("kitty_fed", kitty_cfg.get("fed", 0))):
            was = last.get(key)
            last[key] = total
            if was is not None and total > was:
                self.add(key, min(total - was, 10000))
        if kitty_cfg.get("unlocked"):
            F["kitty_friend"] = True

        # time in VR (desktop mode counts too, it's still VRChat time)
        if dt:
            self.add("vr_s", dt)
        vd = cfg.get("vr_days", {})
        L = self.f["life"]
        L["best_streak"] = max(L.get("best_streak", 0), vd.get("best", 0), vd.get("streak", 0))
        hr = time.localtime(now).tm_hour
        if hr == 3:
            F["night_owl"] = True
        if 4 <= hr < 7:
            F["early_bird"] = True

        # themes u've tried
        th = cfg.get("theme")
        if th and th not in self.f["themes_tried"]:
            self.f["themes_tried"].append(th)

        # songs
        if music and music.get("title"):
            key = f"{music.get('title')} - {music.get('artist', '')}".strip(" -")
            if key != self.last_song:
                self.last_song = key
                self.add("songs")
                songs = self.month().setdefault("song_n", {})
                songs[key] = songs.get(key, 0) + 1
                if len(songs) > 60:
                    for k in sorted(songs, key=songs.get)[:20]:
                        songs.pop(k, None)

        # worlds + people
        if world and world.get("found"):
            wid, wname = world.get("world_id") or world.get("world"), world.get("world") or "?"
            if wid and wid not in self.f["worlds"]:
                self.f["worlds"].append(wid)
                del self.f["worlds"][:-3000]
                self.add("worlds_new")
            if dt and wname:
                ws = self.month().setdefault("world_s", {})
                ws[wname] = ws.get(wname, 0) + dt
                if len(ws) > 60:
                    for k in sorted(ws, key=ws.get)[:20]:
                        ws.pop(k, None)
            pm = world.get("people_met")
            if isinstance(pm, int):
                if self.last_people is not None and pm > self.last_people:
                    self.add("people", pm - self.last_people)
                self.last_people = pm

        # seasons
        s = self.season()
        if s:
            sid = season_id(s, now)
            if sid not in self.f["seasons_joined"]:
                self.f["seasons_joined"].append(sid)
                self.new_alerts.append(f"{SEASONS[s]['emoji']} {tr(SEASONS[s]['banner'])}")
            F["season_" + s] = True

        self.check_badges()
        out, self.new_alerts = self.new_alerts, []
        return out

    def on_kitty_pat(self):
        """Halloween: pats give candy (one every ~20s so it's a vibe, not a grind)"""
        if self.season() != "halloween":
            return None
        now = time.time()
        if now < self.candy_cd or random.random() > 0.55:
            return None
        self.candy_cd = now + 20
        sid = season_id("halloween", now)
        c = self.f.setdefault("candy_season", {})
        c[sid] = c.get(sid, 0) + 1
        self.add("candy")
        n = c[sid]
        if n >= 31 and "pumpkin" not in self.f["candy_unlocked"]:
            self.f["candy_unlocked"].append("pumpkin")
            self.f["flags"]["candy_31"] = True
            self.check_badges()
            return "🎃 31 candy!! u unlocked the pumpkin hat forever (Fun > closet)"
        return f"🍬 +1 candy ({n}/31)"

    def candy(self):
        return self.f.get("candy_season", {}).get(season_id("halloween"), 0)

    def check_badges(self):
        L, F = dict(self.f["life"]), self.f["flags"]
        for bid, emo, name, how, chk in BADGES:
            if bid in self.f["badges"]:
                continue
            try:
                ok = chk(L, F, self.f)
            except Exception:
                ok = False
            if ok:
                self.f["badges"][bid] = int(time.time())
                self.earned.append(bid)
                self.new_alerts.append(f"{emo} {tr('new badge')}: {tr(name)}!!")

    @property
    def earned(self):
        q = self.__dict__.setdefault("_earned", [])
        return q

    def pop_earned(self):
        q, self._earned = self.earned, []
        return q

    def flag(self, key):
        if not self.f["flags"].get(key):
            self.f["flags"][key] = True
            self.check_badges()

    # ---- wrapped
    def wrapped_data(self, month=None):
        month = month or _month()
        m = self.f["months"].get(month, {})
        ws = m.get("world_s", {})
        songs = m.get("song_n", {})
        top_world = max(ws, key=ws.get) if ws else None
        top_song = max(songs, key=songs.get) if songs else None
        earned = [b for b, ts in self.f["badges"].items() if time.strftime("%Y-%m", time.localtime(ts)) == month]
        return {
            "month": month, "vr_h": m.get("vr_s", 0) / 3600, "pats": m.get("pats", 0), "boops": m.get("boops", 0),
            "km": m.get("walked_m", 0) / 1000, "worlds": len(ws), "people": m.get("people", 0),
            "kitty_pats": m.get("kitty_pats", 0), "jumps": m.get("jumps", 0), "songs": m.get("songs", 0),
            "top_world": top_world, "top_world_h": (ws.get(top_world, 0) / 3600) if top_world else 0,
            "top_song": top_song, "badges": earned, "streak": self.f["life"].get("best_streak", 0),
            "candy": m.get("candy", 0),
        }


def json_copy(v):
    import json
    return json.loads(json.dumps(v))


# ------------------------------------------------------- kitty accessories ---
INK = (58, 52, 66)


def draw_outfit(img, hat, neck, cx, top, w, neck_y, ink=INK):
    """Draws kitty's hat + collar onto img. cx/top/w = her head (center x, top y, width),
    neck_y = where her collar sits. Hand-drawn-ish shapes w/ the same ink as her lineart."""
    if (not hat or hat == "none") and (not neck or neck == "none"):
        return img
    d = ImageDraw.Draw(img)
    s = w / 160.0
    lw = max(2, int(3 * s))
    if neck and neck != "none":
        _neck(d, neck, cx, neck_y, w, s, lw, ink)
    if hat and hat != "none":
        _hat(d, hat, cx, top, w, s, lw, ink)
    return img


def _neck(d, kind, cx, y, w, s, lw, ink):
    hw = w * 0.36
    col = {"bell": (255, 110, 150), "heart_tag": (255, 140, 190), "scarf": (120, 170, 255), "bandana": (230, 60, 70),
           "spiky": (40, 34, 50), "bowtie": (150, 90, 230), "rainbow": (255, 100, 100)}.get(kind, (255, 110, 150))
    if kind in ("scarf", "rainbow"):
        band = [cx - hw, y - 9 * s, cx + hw, y + 9 * s]
        if kind == "rainbow":
            cols = [(240, 70, 70), (255, 160, 60), (255, 225, 80), (90, 200, 110), (80, 150, 255), (160, 100, 230)]
            bw = (band[2] - band[0]) / len(cols)
            for i, c in enumerate(cols):
                d.rectangle([band[0] + i * bw, band[1], band[0] + (i + 1) * bw, band[3]], fill=c)
            d.rounded_rectangle(band, radius=8 * s, outline=ink, width=lw)
            tail_c = cols[2]
        else:
            d.rounded_rectangle(band, radius=8 * s, fill=col, outline=ink, width=lw)
            for k in range(3):
                x = band[0] + (k + 1) * (band[2] - band[0]) / 4
                d.line([(x, band[1] + 3 * s), (x, band[3] - 3 * s)], fill=(255, 255, 255), width=max(1, lw - 1))
            tail_c = col
        d.polygon([(cx + hw * 0.4, y), (cx + hw * 0.75, y + 40 * s), (cx + hw * 0.2, y + 36 * s)],
                  fill=tail_c, outline=ink)
        return
    if kind == "bandana":
        d.polygon([(cx - hw, y - 6 * s), (cx + hw, y - 6 * s), (cx, y + 30 * s)], fill=col, outline=ink)
        d.line([(cx - hw, y - 6 * s), (cx + hw, y - 6 * s), (cx, y + 30 * s), (cx - hw, y - 6 * s)], fill=ink, width=lw)
        for k in range(4):
            px = cx - hw * 0.5 + k * hw * 0.33
            d.ellipse([px - 2 * s, y + 2 * s, px + 2 * s, y + 6 * s], fill=(255, 255, 255))
        return
    # thin collar band
    d.rounded_rectangle([cx - hw, y - 5 * s, cx + hw, y + 5 * s], radius=5 * s, fill=col, outline=ink, width=lw)
    if kind == "spiky":
        for k in range(5):
            x = cx - hw * 0.8 + k * hw * 0.4
            d.polygon([(x - 5 * s, y - 4 * s), (x + 5 * s, y - 4 * s), (x, y - 15 * s)], fill=(220, 220, 230), outline=ink)
    elif kind == "bell":
        r = 9 * s
        d.ellipse([cx - r, y, cx + r, y + 2 * r], fill=(255, 210, 80), outline=ink, width=lw)
        d.line([(cx - r * 0.6, y + r), (cx + r * 0.6, y + r)], fill=ink, width=max(1, lw - 1))
        d.ellipse([cx - 2 * s, y + r * 1.3, cx + 2 * s, y + r * 1.7], fill=ink)
    elif kind == "heart_tag":
        _heart(d, cx, y + 12 * s, 11 * s, (255, 200, 220), ink, lw)
    elif kind == "bowtie":
        r = 12 * s
        d.polygon([(cx, y), (cx - 2 * r, y - r), (cx - 2 * r, y + r)], fill=col, outline=ink)
        d.polygon([(cx, y), (cx + 2 * r, y - r), (cx + 2 * r, y + r)], fill=col, outline=ink)
        d.ellipse([cx - r * 0.5, y - r * 0.5, cx + r * 0.5, y + r * 0.5], fill=col, outline=ink, width=lw)


def _heart(d, cx, cy, r, fill, ink, lw):
    pts = []
    for i in range(32):
        a = i / 32 * 2 * math.pi
        x = 16 * math.sin(a) ** 3
        y = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
        pts.append((cx + x * r / 16, cy + y * r / 16))
    d.polygon(pts, fill=fill)
    d.line(pts + [pts[0]], fill=ink, width=lw, joint="curve")


def _hat(d, kind, cx, top, w, s, lw, ink):
    if kind == "bow":
        r = 14 * s
        x, y = cx + w * 0.26, top + 10 * s
        col = (255, 130, 180)
        d.polygon([(x, y), (x - 2 * r, y - r), (x - 2 * r, y + r)], fill=col, outline=ink)
        d.polygon([(x, y), (x + 2 * r, y - r), (x + 2 * r, y + r)], fill=col, outline=ink)
        d.ellipse([x - r * 0.55, y - r * 0.55, x + r * 0.55, y + r * 0.55], fill=col, outline=ink, width=lw)
    elif kind == "heart_bow":
        _heart(d, cx + w * 0.26, top + 8 * s, 16 * s, (255, 90, 140), ink, lw)
        _heart(d, cx - w * 0.2, top + 2 * s, 10 * s, (255, 170, 200), ink, lw)
    elif kind == "flower":
        for k in range(7):
            x = cx - w * 0.42 + k * w * 0.14
            y = top + 8 * s + abs(k - 3) * 3 * s
            col = [(255, 170, 200), (255, 230, 120), (190, 160, 255), (160, 230, 190)][k % 4]
            for a in range(5):
                ang = a / 5 * 2 * math.pi
                px, py = x + math.cos(ang) * 6 * s, y + math.sin(ang) * 6 * s
                d.ellipse([px - 5 * s, py - 5 * s, px + 5 * s, py + 5 * s], fill=col, outline=ink, width=1)
            d.ellipse([x - 3 * s, y - 3 * s, x + 3 * s, y + 3 * s], fill=(255, 200, 80))
    elif kind in ("party", "witch", "santa", "beanie"):
        base_y = top + 14 * s
        if kind == "party":
            pts = [(cx - 28 * s, base_y), (cx + 28 * s, base_y), (cx + 4 * s, top - 58 * s)]
            d.polygon(pts, fill=(120, 200, 255), outline=ink)
            for k in range(3):
                yy = base_y - (k + 1) * 15 * s
                x_off = 28 * s * (1 - (k + 1) * 15 * s / (72 * s))
                d.line([(cx - x_off + 4 * s, yy), (cx + x_off, yy)], fill=(255, 140, 190), width=lw + 1)
            d.line(pts + [pts[0]], fill=ink, width=lw)
            d.ellipse([cx - 4 * s, top - 68 * s, cx + 12 * s, top - 52 * s], fill=(255, 220, 80), outline=ink, width=lw)
        elif kind == "witch":
            d.ellipse([cx - 62 * s, base_y - 10 * s, cx + 62 * s, base_y + 10 * s], fill=(50, 34, 70), outline=ink, width=lw)
            pts = [(cx - 32 * s, base_y - 2 * s), (cx + 32 * s, base_y - 2 * s), (cx + 22 * s, top - 40 * s),
                   (cx + 48 * s, top - 62 * s), (cx + 6 * s, top - 46 * s)]
            d.polygon(pts, fill=(60, 40, 84), outline=ink)
            d.line(pts + [pts[0]], fill=ink, width=lw)
            d.rectangle([cx - 31 * s, base_y - 14 * s, cx + 29 * s, base_y - 4 * s], fill=(255, 140, 40))
            sx, sy, r = cx + 2 * s, base_y - 26 * s, 7 * s
            d.polygon([(sx, sy - r), (sx + r * 0.3, sy - r * 0.3), (sx + r, sy), (sx + r * 0.3, sy + r * 0.3),
                       (sx, sy + r), (sx - r * 0.3, sy + r * 0.3), (sx - r, sy), (sx - r * 0.3, sy - r * 0.3)],
                      fill=(255, 220, 120))
        elif kind == "santa":
            pts = [(cx - 40 * s, base_y), (cx + 40 * s, base_y), (cx + 30 * s, top - 30 * s), (cx + 58 * s, top - 10 * s)]
            d.polygon([pts[0], pts[1], pts[3], pts[2]], fill=(220, 40, 50), outline=ink)
            d.rounded_rectangle([cx - 46 * s, base_y - 8 * s, cx + 46 * s, base_y + 8 * s], radius=8 * s,
                                fill=(255, 255, 255), outline=ink, width=lw)
            d.ellipse([cx + 50 * s, top - 18 * s, cx + 68 * s, top], fill=(255, 255, 255), outline=ink, width=lw)
        else:   # beanie
            d.chord([cx - 44 * s, top - 34 * s, cx + 44 * s, base_y + 30 * s], 180, 360, fill=(140, 110, 230),
                    outline=ink, width=lw)
            d.rounded_rectangle([cx - 46 * s, base_y - 6 * s, cx + 46 * s, base_y + 8 * s], radius=6 * s,
                                fill=(110, 230, 190), outline=ink, width=lw)
            d.ellipse([cx - 9 * s, top - 46 * s, cx + 9 * s, top - 28 * s], fill=(255, 255, 255), outline=ink, width=lw)
    elif kind == "pumpkin":
        y = top - 6 * s
        for k, dx in enumerate((-22, 0, 22)):
            d.ellipse([cx + dx * s - 22 * s, y - 20 * s, cx + dx * s + 22 * s, y + 20 * s],
                      fill=(255, 140 - k * 6, 40), outline=ink, width=lw)
        d.rounded_rectangle([cx - 4 * s, y - 34 * s, cx + 4 * s, y - 16 * s], radius=3 * s, fill=(90, 160, 70), outline=ink)
        d.polygon([(cx - 16 * s, y - 4 * s), (cx - 8 * s, y - 4 * s), (cx - 12 * s, y - 12 * s)], fill=ink)
        d.polygon([(cx + 8 * s, y - 4 * s), (cx + 16 * s, y - 4 * s), (cx + 12 * s, y - 12 * s)], fill=ink)
        d.arc([cx - 14 * s, y - 2 * s, cx + 14 * s, y + 12 * s], 10, 170, fill=ink, width=lw)
    elif kind == "crown":
        y = top + 4 * s
        pts = [(cx - 34 * s, y + 6 * s), (cx - 34 * s, y - 24 * s), (cx - 17 * s, y - 8 * s), (cx, y - 32 * s),
               (cx + 17 * s, y - 8 * s), (cx + 34 * s, y - 24 * s), (cx + 34 * s, y + 6 * s)]
        d.polygon(pts, fill=(255, 210, 70))
        d.line(pts + [pts[0]], fill=ink, width=lw)
        for x in (-17, 0, 17):
            d.ellipse([cx + x * s - 4 * s, y - 4 * s, cx + x * s + 4 * s, y + 4 * s], fill=(255, 100, 150), outline=ink)
    elif kind == "halo":
        y = top - 22 * s
        d.ellipse([cx - 36 * s, y - 9 * s, cx + 36 * s, y + 9 * s], outline=ink, width=lw + 6)
        d.ellipse([cx - 36 * s, y - 9 * s, cx + 36 * s, y + 9 * s], outline=(255, 230, 120), width=lw + 2)
    elif kind == "headphones":
        d.arc([cx - w * 0.5, top - 20 * s, cx + w * 0.5, top + w * 0.7], 190, 350, fill=ink, width=lw + 6)
        d.arc([cx - w * 0.5, top - 20 * s, cx + w * 0.5, top + w * 0.7], 190, 350, fill=(255, 130, 190), width=lw + 2)
        for side in (-1, 1):
            x = cx + side * w * 0.48
            d.rounded_rectangle([x - 14 * s, top + 36 * s, x + 14 * s, top + 74 * s], radius=10 * s,
                                fill=(255, 130, 190), outline=ink, width=lw)


# ----------------------------------------------------------- wrapped card ---
def _fmt_n(v):
    return f"{v:,.0f}" if v >= 10 or float(v).is_integer() else f"{v:.1f}"


def render_wrapped(fun, cfg, name="", month=None):
    """1080x1350 recap card (Instagram/TikTok/Twitter friendly). Returns a PIL image."""
    import ui
    W, H = 1080, 1350
    t = themes.get_theme(cfg)
    data = fun.wrapped_data(month)
    bg = t["bg"][:3]
    img = Image.new("RGBA", (W, H), bg + (255,))
    d = ImageDraw.Draw(img)
    # soft glow + doodles
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([-260, -200, 700, 640], fill=t["primary"][:3] + (60,))
    gd.ellipse([520, 820, 1380, 1600], fill=t["stripe"][-1][:3] + (50,))
    from PIL import ImageFilter
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(90)))
    d = ImageDraw.Draw(img)
    rnd = random.Random(data["month"])
    for _ in range(26):
        x, y = rnd.randint(30, W - 30), rnd.randint(30, H - 30)
        k = rnd.random()
        if k < 0.45:
            ui.doodle_heart(d, x, y, rnd.randint(6, 11), ui.mix(t["panel"][:3], t["primary"], 0.35), ui.mix(t["panel"][:3], t["line"], 0.4))
        elif k < 0.8:
            ui.sparkle(d, x, y, rnd.randint(5, 10), ui.mix(bg, t["warn"], 0.5))
        else:
            ui.paw(d, x, y, rnd.randint(8, 13), ui.mix(bg, t["primary"], 0.25))
    # big furry card
    ui._CUR = t
    ui.fluff_card(d, [60, 150, W - 60, H - 120], t, radius=46, ears_on=True, ear_size=60)
    d = ImageDraw.Draw(img)
    stripe = t.get("stripe") or [t["primary"]]
    ui.stripe(d, 100, 196, W - 200, 12, stripe, radius=6)
    try:
        yr, mo = data["month"].split("-")
        mname = time.strftime("%B", time.strptime(mo, "%m"))
    except Exception:
        yr, mname = "", data["month"]
    d.text((W / 2, 92), "Fluff Wrapped", font=ui.font("title", 78), fill=t["text"], anchor="mm")
    d.text((W / 2, 262), f"{tr(mname)} {yr}", font=ui.font("head", 46), fill=t["primary"], anchor="mm")
    who = name or tr("a very fluffy someone")
    d.text((W / 2, 318), who, font=ui.font("body", 30), fill=t["sub"], anchor="mm")

    tiles = [
        ("hours in VR", _fmt_n(data["vr_h"]), "🥽"),
        ("headpats", _fmt_n(data["pats"]), "✋"),
        ("boops", _fmt_n(data["boops"]), "👃"),
        ("km walked", f"{data['km']:.1f}", "👣"),
        ("worlds", _fmt_n(data["worlds"]), "🗺"),
        ("people met", _fmt_n(data["people"]), "🤝"),
        ("kitty pats", _fmt_n(data["kitty_pats"]), "🐱"),
        ("songs vibed", _fmt_n(data["songs"]), "🎧"),
        ("best streak", f"{data['streak']}d", "🔥"),
    ]
    cols, gx, gy = 3, 110, 370
    tw, th, gap = (W - 2 * gx - 2 * 22) / 3, 150, 22
    for i, (lab, val, emo) in enumerate(tiles):
        r, c = divmod(i, cols)
        x0 = gx + c * (tw + gap)
        y0 = gy + r * (th + gap)
        ui.panel(d, [x0, y0, x0 + tw, y0 + th], 28, t)
        col = t["primary"] if i in (1, 6) else t["text"]
        fv = ui.font("title", 64 if len(val) < 6 else 50)
        d.text((x0 + tw / 2, y0 + 70), val, font=fv, fill=col, anchor="mm")
        d.text((x0 + tw / 2, y0 + 124), lab, font=ui.font("body2", 24), fill=t["sub"], anchor="mm")
    y = gy + 3 * (th + gap) + 14
    rows = []
    if data["top_world"]:
        rows.append(("top world", f"{data['top_world']}  ·  {data['top_world_h']:.1f}h"))
    if data["top_song"]:
        rows.append(("on repeat", data["top_song"]))
    if data["candy"]:
        rows.append(("candy collected", f"🍬 {data['candy']}"))
    b = data["badges"]
    max_rows = 3 if not b else 2
    for lab, val in rows[:max_rows]:
        ui.panel(d, [gx, y, W - gx, y + 76], 24, t)
        d.text((gx + 26, y + 38), tr(lab), font=ui.font("body2", 24), fill=t["sub"], anchor="lm")
        f = ui.font("head", 32)
        lw = f.getlength(tr(lab)) if False else ui.font("body2", 24).getlength(tr(lab))
        d.text((W - gx - 26, y + 38), ui.ellipsize(val, f, W - 2 * gx - lw - 90), font=f, fill=t["text"], anchor="rm")
        y += 90
    # badges earned this month
    if b:
        d.text((W / 2, y + 18), f"{len(b)} " + tr("new badges"), font=ui.font("head", 30), fill=t["text"], anchor="mm")
        icons = " ".join(BADGE_MAP[x][1] for x in b[:12] if x in BADGE_MAP)
        ui.rich_text(d, (W / 2, y + 40), icons, 30, t["text"], center=True)
    # footer
    d.text((W / 2, H - 78), "made with Fluff VR Stats :3", font=ui.font("head", 34), fill=t["text"], anchor="mm")
    d.text((W / 2, H - 38), "github.com/wolfiecodesowo/fluff-vr-stats", font=ui.font("body2", 22),
           fill=t["sub"], anchor="mm")
    return img


def save_wrapped(fun, cfg, name="", month=None):
    os.makedirs(WRAPPED_DIR, exist_ok=True)
    img = render_wrapped(fun, cfg, name, month)
    path = os.path.join(WRAPPED_DIR, f"fluff-wrapped-{month or _month()}.png")
    img.convert("RGB").save(path, quality=95)
    fun.flag("wrapped_made")
    return path
