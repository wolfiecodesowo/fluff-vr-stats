"""Render the HUD + every dashboard tab to PNGs with fake data (no VR needed).
Usage: python preview.py [output_folder]"""
import os, random, sys, time
import ui, themes
from main import State, load_cfg

out = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
cfg = load_cfg()
for k in cfg["modules"]:
    cfg["modules"][k] = True
random.seed(3)
st = State(cfg)
st.stats = {"fps": 86, "refresh": 90, "gpu_ms": 9.4, "cpu_ms": 6.1, "reproj_pct": 4, "vr_ok": True,
            "frametimes": [9 + random.random() * 2 + (5 if i in (20, 21, 44) else 0) for i in range(60)],
            "batteries": [("HMD", 82, False), ("L", 64, False), ("R", 18, False), ("T1", 91, True)],
            "cpu_pct": 37, "ram_pct": 61, "gpu_pct": 88, "gpu_temp": 71, "vram_used": 6.2, "vram_total": 12}
st.extras = {"session_start": time.time() - 5000, "ping": 24, "weather": "64°F Sunny",
             "headpats": 12, "muted": True, "song": "Midnight City - M83"}
st.screen_info = {"monitors": 2}
st.discord = {"rpc": "connected", "online": 23, "server": "Fluff VR Stats :3"}
from PIL import Image as _I, ImageDraw as _D
_art = _I.new("RGBA", (300, 300), (40, 20, 70, 255)); _dd = _D.Draw(_art)
for _i in range(12):
    _dd.ellipse([150 - 140 + _i * 11, 150 - 140 + _i * 11, 150 + 140 - _i * 11, 150 + 140 - _i * 11],
                fill=(255 - _i * 12, 90 + _i * 10, 160 + _i * 6, 255))
st.music = {"title": "Midnight City", "artist": "M83", "album": "Hurry Up, We're Dreaming", "app": "Spotify",
            "playing": True, "pos": 83, "dur": 243, "art": _art, "backend": "windows"}
_unused_chat = [("user", "hiii fluff how's my fps looking"),
           ("assistant", "Purrfect! You're sitting at 86 out of 90, barely any reprojection. Your rig is doing great, go have fun~")]
st.alert = {"text": "Kitsu +2 joined", "kind": "info", "until": time.time() + 60}
st.world = {"world": "The Black Cat", "type": "friends+", "players": ["me", "Kitsu", "Bunbun", "Sable", "Mochi"],
            "world_since": time.time() - 1460, "found": True, "worlds_visited": 3, "people_met": 21,
            "events": [(time.time() - 400, "join", "Sable"), (time.time() - 200, "leave", "Rex"),
                       (time.time() - 30, "join", "Kitsu"), (time.time() - 5, "join", "Bunbun")]}
st.extras.update(world_name="The Black Cat", world_players=5, walked=312)
st.walked = 312
st.speed = 0.4
st.pet_mood = "vibin to Midnight City ~"
st.timer.update(mode="timer", running=True, end=time.time() + 272)
st.boost = {"status": {"power_plan": True, "game_mode": True, "game_dvr": False, "vr_priority": False, "gpu_pref": False},
            "heavy": [{"name": "chrome.exe", "cpu": 18.2, "mem": 2300}, {"name": "Discord.exe", "cpu": 6.1, "mem": 610},
                      {"name": "Spotify.exe", "cpu": 2.4, "mem": 380}, {"name": "obs64.exe", "cpu": 1.1, "mem": 290}],
            "tip": 0, "calmed": {"Discord.exe"}, "msg": ""}
st.avatar = {"id": "avtr_x", "name": "Mayu Goth Kitty", "values": {"Hoodie": True, "HairStyle": 2, "TailFluff": 0.75},
             "params": [{"name": n, "type": ty, "address": "/a/" + n} for n, ty in
                        [("Hoodie", "Bool"), ("Collar", "Bool"), ("EarPiercings", "Bool"), ("Chains", "Bool"),
                         ("HairStyle", "Int"), ("TailFluff", "Float"), ("GoldMetal", "Bool"), ("Glasses", "Bool")]]}

class _FakeChat:
    unread, status, error = 2, "live", ""
    def __init__(self):
        n = time.time()
        self.msgs = [dict(id=str(i), name=nm, text=tx, time=n - 60 + i * 9, sid=nm, client=c, mine=nm == "me")
                     for i, (nm, tx, c) in enumerate([("Kitsu", "anyone in the black cat rn?", "pc"),
                                                     ("me", "omw!! saving u a spot", "pc"),
                                                     ("Bunbun", "hiii from my quest :3", "quest"),
                                                     ("Sable", "the new wrist buttons are so cute", "discord"),
                                                     ("Mochi", "headpat count 40 today lets gooo", "desktop")])]
    def visible(self, n=None):
        return self.msgs[-n:] if n else list(self.msgs)
    def name(self):
        return "me"
st.gchat = _FakeChat()
cfg["gchat"]["name"] = "me"
# v0.4 bits: badges, wrapped, closet, friends, events, key
import fun as _fun, fluffnet as _net, kitty as _kitty
st.fun = _fun.Fun(cfg)
st.fun.f["badges"].update({b[0]: int(time.time()) - i * 3600 for i, b in enumerate(_fun.BADGES[:14])})
st.fun.f["life"].update(pats=420, boops=133, vr_s=200000, walked_m=12000, kitty_pats=380, songs=150, best_streak=9)
m = st.fun.month()
m.update(vr_s=61200, pats=212, boops=48, walked_m=8400, people=96, kitty_pats=151, songs=88, jumps=40, candy=17,
         world_s={"The Black Cat": 30000, "Furry Hideout": 12000, "Midnight Rooftop": 6000},
         song_n={"Midnight City - M83": 14, "Kids - MGMT": 6})
st.fun.f["seen_badges"] = list(st.fun.f["badges"])[:-2]
st.fun.f["candy_season"] = {_fun.season_id("halloween"): 17}


class _FakeAccess:
    enabled, linked, status = True, True, "key ok"
    def who(self): return "wolfie"
    def locked(self, now=None): return False
    def grace_left(self, now=None): return 0
    def token(self): return "x"


class _FakeFriends:
    def list(self):
        return [["a1", {"n": "Kitsu", "c": "pc", "seen": time.time()}], ["b2", {"n": "Bunbun", "c": "quest", "seen": time.time()}]]


class _FakeEvents:
    def upcoming(self, now=None):
        return [{"id": "e1", "title": "Spooky Floof Night", "start": time.time() + 7200, "end": time.time() + 14400,
                 "world": "The Black Cat", "desc": "costumes + candy hunt", "cancel": False}]
    def live(self, now=None): return []


st.access, st.friends, st.cevents = _FakeAccess(), _FakeFriends(), _FakeEvents()
st.world["world_id"] = "wrld_x"
_k = _kitty.Kitty(cfg)
_k.outfit = st.fun.closet()
st.kitty_img = _k.render(ui.get_theme(cfg))
ui.render_hud(st).save(os.path.join(out, "preview_hud.png"))
st.extras.update(boops=4, vr_today_s=6200, vr_streak=3)
st.version = "v0.3.0"
for tab in ui.TABS:
    st.tab = tab
    st.logo_frame = None
    img, _ = ui.render_dashboard(st)
    img = ui.add_logo(img, 0, st.anim_slots)
    name = "thanks" if tab == "<3" else tab.lower()
    if tab == "Home":
        st.gchat.unread = 2
    img.save(os.path.join(out, f"preview_dash_{name}.png"))
for page, _ in __import__("ui_fun").FUN_PAGES:
    st.tab, st.fun_page = "Fun", page
    img, _ = ui.render_dashboard(st)
    ui.add_logo(img, 0, st.anim_slots).save(os.path.join(out, f"preview_fun_{page}.png"))
for page, _ in __import__("ui_fun").SET_PAGES:
    st.tab, st.set_page = "Settings", page
    img, _ = ui.render_dashboard(st)
    ui.add_logo(img, 0, st.anim_slots).save(os.path.join(out, f"preview_settings_{page}.png"))
st.tab = "Home"
st.whatsnew = ("v0.4.0: the big safety + fun update", ["🔐 global chat is safe now: Fluff Bot checks every message",
               "🎁 Fluff Wrapped: ur month in VR as a card", "🏅 37 badges", "🌍 12 languages"])
img, _ = ui.render_dashboard(st)
ui.add_logo(img, 0, st.anim_slots).save(os.path.join(out, "preview_whatsnew.png"))
st.whatsnew = None
st.checklist, st.conflicts = True, ["MagicChatbox"]
img, _ = ui.render_dashboard(st)
ui.add_logo(img, 0, st.anim_slots).save(os.path.join(out, "preview_checklist.png"))
st.checklist = None
_FakeAccess.locked = lambda self, now=None: True
_FakeAccess.linked = False
_FakeAccess.status = "no key yet"
img, _ = ui.render_dashboard(st)
ui.add_logo(img, 0, st.anim_slots).save(os.path.join(out, "preview_keylock.png"))
_FakeAccess.locked = lambda self, now=None: False
_FakeAccess.linked = True
_fun.render_wrapped(st.fun, cfg, "wolfie").save(os.path.join(out, "preview_wrapped_card.png"))
# every language, Home + Settings
import lang as _lang
for code in (sys.argv[2].split(",") if len(sys.argv) > 2 else []):
    _lang.set_lang(code)
    for tab in ("Home", "Settings", "Mods", "Fun"):
        st.tab, st.set_page, st.fun_page = tab, "general", "badges"
        img, _ = ui.render_dashboard(st)
        ui.add_logo(img, 0, st.anim_slots).save(os.path.join(out, f"preview_lang_{code}_{tab.lower()}.png"))
    ui.render_hud(st).save(os.path.join(out, f"preview_lang_{code}_hud.png"))
_lang.set_lang("en")
# error card examples
st.tab = "Stats"
st.errors.append({"text": "desktop screen: OSError: monitor 2 unplugged", "time": time.time()})
img, _ = ui.render_dashboard(st)
ui.add_logo(img, 3, st.anim_slots).save(os.path.join(out, "preview_dash_error.png"))
st.alert = {"text": "oops! desktop screen hiccuped, still running :3", "kind": "error", "until": time.time() + 9}
ui.render_hud(st).save(os.path.join(out, "preview_hud_error.png"))
st.alert = None
# a few themes / ears side by side
st.alert = None
for i, (theme, ears) in enumerate([("trans_soft", "fox"), ("cotton_candy", "bunny"),
                                   ("gay_ocean", "wolf"), ("lava_dragon", "dragon"),
                                   ("honey_bear", "bear"), ("neon_rave", "cat")]):
    cfg["theme"], cfg["style"]["ears"] = theme, ears
    ui.render_hud(st).save(os.path.join(out, f"preview_theme_{i}_{theme}.png"))
print("done")
