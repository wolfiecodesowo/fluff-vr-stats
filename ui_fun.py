"""
Fluff VR Stats - UI for the v0.4 stuff: the Fun tab (badges, Wrapped, kitty closet, theme codes,
Fluff Friends, community nights), the paged Settings tab, and the cards that pop over the menu
(app key, what's new, first-run checklist, safe mode).
Drawn with the same helpers as ui.py so it all looks hand-made + furry.
"""
import time

import fluffnet
import fun as F
import lang
import ui
from lang import tr
from ui import (button, ellipsize, font, mix, panel, paw, pill, rich_text, switch, wrap, doodle_heart,
                fluff_card, _setting_row)

FUN_PAGES = [("badges", "badges"), ("wrapped", "wrapped"), ("closet", "kitty closet"), ("themes", "theme codes"),
             ("friends", "fluff friends"), ("events", "community nights")]
SET_PAGES = [("general", "general"), ("comfy", "comfy + access"), ("osc", "osc + chatbox"), ("privacy", "privacy"),
             ("key", "app key"), ("backup", "backup + help")]


def _pills(d, hit, x0, y0, x1, pages, cur, t, action):
    f = font("head", 16)
    total = sum(ui.tw(lab, f) + 42 for _, lab in pages)
    if total > x1 - x0:                          # long languages: shrink the pills to fit
        f = font("head", max(11, int(16 * (x1 - x0) / total)))
    x = x0
    for key, lab in pages:
        w = ui.tw(lab, f) + 34
        box = [x, y0, x + w, y0 + 36]
        active = cur == key
        pill(d, box, t["primary"] if active else t["panel2"])
        d.text(((box[0] + box[2]) / 2, y0 + 18), lab, font=f, fill=t["on_primary"] if active else t["text"], anchor="mm")
        hit.add(box, action, key)
        x += w + 8
    return x


# ------------------------------------------------------------------ fun tab ---
def tab_fun(d, hit, box, state, t):
    x0, y0, x1, y1 = box
    fun = state.fun
    if fun is None:
        d.text(((x0 + x1) / 2, (y0 + y1) / 2), "loading the fun stuff…", font=font("head", 22), fill=t["sub"], anchor="mm")
        return
    page = getattr(state, "fun_page", "badges")
    state._pill_end = _pills(d, hit, x0, y0, x1, FUN_PAGES, page, t, "fun_page")
    nb = len(fun.new_badges())
    if nb and page != "badges":
        d.ellipse([x0 + 74, y0 - 6, x0 + 92, y0 + 12], fill=t["bad"])
        d.text((x0 + 83, y0 + 3), str(min(nb, 9)), font=font("body", 11), fill=(255, 255, 255), anchor="mm")
    body = [x0, y0 + 50, x1, y1]
    {"badges": _fun_badges, "wrapped": _fun_wrapped, "closet": _fun_closet, "themes": _fun_themes,
     "friends": _fun_friends, "events": _fun_events}.get(page, _fun_badges)(d, hit, body, state, t, fun)


def _fun_badges(d, hit, box, state, t, fun):
    x0, y0, x1, y1 = box
    got = fun.f["badges"]
    lab = f"{len(got)}/{len(F.BADGES)} " + tr("earned")
    if getattr(state, "_pill_end", x1) + ui.tw(lab, font("head", 18)) + 16 < x1:
        d.text((x1, y0 - 34), lab, font=font("head", 18), fill=t["primary"], anchor="ra")
    cols = 6
    n = len(F.BADGES)
    rows = (n + cols - 1) // cols
    gap = 7
    tw = (x1 - x0 - gap * (cols - 1)) / cols
    th = min(64, (y1 - y0 - gap * (rows - 1)) / rows)
    new = set(fun.new_badges())
    for i, (bid, emo, name, how, _) in enumerate(F.BADGES):
        r, c = divmod(i, cols)
        bx, by = x0 + c * (tw + gap), y0 + r * (th + gap)
        have = bid in got
        fill = mix(t["panel"], t["primary"], 0.22) if have else mix(t["panel"], t["bg"][:3], 0.4)
        d.rounded_rectangle([bx, by, bx + tw, by + th], radius=14, fill=fill,
                            outline=t["primary"] if bid in new else t["line_soft"], width=3 if bid in new else 2)
        if have:
            rich_text(d, (bx + 8, by + th / 2 - 13), emo, 20, t["text"])
        else:
            d.text((bx + 19, by + th / 2), "?", font=font("head", 20), fill=t["sub"], anchor="mm")
        fn = font("body", 13)
        d.text((bx + 38, by + th / 2 - 9), ellipsize(name, fn, tw - 44), font=fn,
               fill=t["text"] if have else t["sub"], anchor="lm")
        d.text((bx + 38, by + th / 2 + 10), ellipsize(how, font("body2", 10), tw - 44), font=font("body2", 10),
               fill=t["sub"], anchor="lm")


_THUMB = {}


def _fun_wrapped(d, hit, box, state, t, fun):
    x0, y0, x1, y1 = box
    data = fun.wrapped_data()
    # mini card preview (re-rendered at most every 30s, it's a big image)
    th = y1 - y0
    tw = th * 1080 / 1350
    k = (ui.theme_key(state.cfg), lang.current(), int(time.time() // 30))
    if _THUMB.get("k") != k:
        try:
            img = F.render_wrapped(fun, state.cfg, state.cfg.get("gchat", {}).get("name", ""))
            _THUMB["img"] = img.resize((int(tw), int(th)))
        except Exception:
            _THUMB["img"] = None
        _THUMB["k"] = k
    if _THUMB.get("img") is not None:
        d._image.alpha_composite(_THUMB["img"], (int(x0), int(y0)))
        d.rounded_rectangle([x0, y0, x0 + tw, y0 + th], radius=14, outline=t["line"], width=3)
    rx = x0 + tw + 24
    panel(d, [rx, y0, x1, y1], 22, t, ears_on=True)
    d.text((rx + 24, y0 + 22), "Fluff Wrapped", font=font("title", 32), fill=t["text"])
    for i, ln in enumerate(wrap("ur month in VR as one cute card. it saves as a picture, post it anywhere "
                                "(TikTok, Twitter, Discord...) and tag us!", font("body2", 16), x1 - rx - 48)[:3]):
        d.text((rx + 24, y0 + 72 + i * 22), ln, font=font("body2", 16), fill=t["sub"])
    stats = [("hours in VR", f"{data['vr_h']:.1f}"), ("headpats", str(data["pats"])),
             ("worlds", str(data["worlds"])), ("people met", str(data["people"])),
             ("km walked", f"{data['km']:.1f}"), ("kitty pats", str(data["kitty_pats"]))]
    cw = (x1 - rx - 48 - 20) / 3
    for i, (lab, val) in enumerate(stats):
        r, c = divmod(i, 3)
        bx, by = rx + 24 + c * (cw + 10), y0 + 150 + r * 82
        d.rounded_rectangle([bx, by, bx + cw, by + 72], radius=16, fill=t["panel2"])
        d.text((bx + cw / 2, by + 30), val, font=font("title", 28), fill=t["text"], anchor="mm")
        d.text((bx + cw / 2, by + 56), lab, font=font("body2", 13), fill=t["sub"], anchor="mm")
    by = y1 - 66
    bw = (x1 - rx - 58) / 2
    button(d, hit, [rx + 24, by, rx + 24 + bw, by + 44], "make my card ✨", t, "wrapped", None, primary=True, fsize=18)
    first = time.mktime(time.strptime(time.strftime("%Y-%m-01"), "%Y-%m-%d"))
    last = time.strftime("%Y-%m", time.localtime(first - 86400))
    button(d, hit, [rx + 34 + bw, by, x1 - 24, by + 44], "last month", t, "wrapped", last, fsize=18)


def _fun_closet(d, hit, box, state, t, fun):
    x0, y0, x1, y1 = box
    kimg = getattr(state, "kitty_img", None)
    kw = y1 - y0 - 120
    panel(d, [x0, y0, x0 + kw, y1], 22, t, ears_on=True)
    if kimg is not None:
        try:
            d._image.alpha_composite(kimg.resize((int(kw - 20), int(kw - 20))), (int(x0 + 10), int(y0 + 10)))
        except Exception:
            pass
    hat, neck = fun.closet()
    d.text((x0 + kw / 2, y1 - 92), "wearing", font=font("body2", 14), fill=t["sub"], anchor="mm")
    d.text((x0 + kw / 2, y1 - 66), tr(F.ITEM_NAMES.get((hat, "hat"), hat)) + " + " + tr(F.ITEM_NAMES.get((neck, "neck"), neck)),
           font=font("head", 18), fill=t["text"], anchor="mm")
    d.text((x0 + kw / 2, y1 - 34), "she wears it on ur wrist too :3", font=font("body2", 13), fill=t["sub"], anchor="mm")
    rx = x0 + kw + 18
    yy = y0
    for slot, title in (("hat", "hats"), ("neck", "collars + scarves")):
        d.text((rx, yy + 4), title, font=font("head", 19), fill=t["text"])
        yy += 34
        items = [it for it in F.ITEMS if it[1] == slot]
        x = rx
        cur = hat if slot == "hat" else neck
        for iid, _, name, how in items:
            ok = fun.unlocked(iid, slot)
            lab = tr(name) if ok else "🔒 " + tr(name)
            f = font("body", 14)
            w = f.getlength(lab) + 26
            if x + w > x1:
                x, yy = rx, yy + 40
            b = [x, yy, x + w, yy + 32]
            fill = t["primary"] if cur == iid else (t["panel2"] if ok else mix(t["panel"], t["bg"][:3], 0.4))
            pill(d, b, fill)
            rich_text(d, (b[0] + 13, yy + 7), lab, 14, t["on_primary"] if cur == iid else (t["text"] if ok else t["sub"]),
                      kind="body")
            hit.add(b, "wear", slot, iid)
            x += w + 6
        yy += 46
    # season card
    s = fun.season()
    sb = [rx, y1 - 128, x1, y1]
    panel(d, sb, 20, t)
    if s:
        info = F.SEASONS[s]
        rich_text(d, (sb[0] + 18, sb[1] + 14), f"{info['emoji']} " + tr(info["name"]), 20, t["text"], kind="head")
        line = tr(info["banner"])
        if s == "halloween":
            line = f"🍬 {fun.candy()}/31 " + tr("candy ~ pat ur kitty to find more. 31 = pumpkin hat forever!")
        for i, ln in enumerate(wrap(line, font("body2", 14), sb[2] - sb[0] - 36)[:2]):
            rich_text(d, (sb[0] + 18, sb[1] + 46 + i * 20), ln, 14, t["sub"], kind="body2")
        button(d, hit, [sb[0] + 18, sb[3] - 44, sb[0] + 210, sb[3] - 12], "use the season look", t, "season_theme", fsize=15)
    else:
        d.text((sb[0] + 18, sb[1] + 18), "no season event right now", font=font("head", 19), fill=t["text"])
        d.text((sb[0] + 18, sb[1] + 50), "spooky season (Oct), snowy season (Dec), valentines + pride come back every year",
               font=font("body2", 13), fill=t["sub"])
    on = fun.f.get("season") != "off"
    d.text((sb[2] - 150, sb[3] - 28), "season events", font=font("body2", 13), fill=t["sub"], anchor="rm")
    switch(d, sb[2] - 80, sb[3] - 42, on, t, scale=0.8)
    hit.add([sb[2] - 150, sb[3] - 46, sb[2] - 10, sb[3] - 10], "season")


def _fun_themes(d, hit, box, state, t, fun):
    x0, y0, x1, y1 = box
    code = F.theme_code(state.cfg)
    panel(d, [x0, y0, x1, y0 + 200], 22, t, ears_on=True)
    d.text((x0 + 24, y0 + 20), "ur look as a code", font=font("head", 22), fill=t["text"])
    d.text((x0 + 24, y0 + 54), "theme + accent + background + ears + cursor, all in one short code",
           font=font("body2", 15), fill=t["sub"])
    cb = [x0 + 24, y0 + 90, x1 - 24, y0 + 146]
    d.rounded_rectangle(cb, radius=18, fill=t["panel2"], outline=t["primary"], width=3)
    d.text(((cb[0] + cb[2]) / 2, (cb[1] + cb[3]) / 2), code, font=font("title", 34), fill=t["primary"], anchor="mm")
    bw = (x1 - x0 - 58) / 2
    button(d, hit, [x0 + 24, y0 + 154, x0 + 24 + bw, y0 + 190], "copy my code", t, "theme_copy", primary=True, fsize=17)
    button(d, hit, [x0 + 34 + bw, y0 + 154, x1 - 24, y0 + 190], "use someone's code", t, "theme_enter", fsize=17)
    hb = [x0, y0 + 216, x1, y1]
    panel(d, hb, 22, t)
    d.text((hb[0] + 24, hb[1] + 18), "share it!", font=font("head", 20), fill=t["text"])
    tips = ["post it in the Discord: /sharetheme + ur code (it shows a preview in #theme-share)",
            "someone's look u love? ask for their code and paste it here",
            "codes work on PC + desktop mode. ur kitty's outfit isn't in the code, that's just urs"]
    for i, tip in enumerate(tips):
        paw(d, hb[0] + 32, hb[1] + 66 + i * 34, 6, t["primary"])
        d.text((hb[0] + 48, hb[1] + 66 + i * 34), ellipsize(tip, font("body2", 15), hb[2] - hb[0] - 70),
               font=font("body2", 15), fill=t["sub"], anchor="lm")


def _fun_friends(d, hit, box, state, t, fun):
    x0, y0, x1, y1 = box
    fr = state.friends
    on = state.cfg["modules"].get("fluff_friends", True)
    lw = (x1 - x0) * 0.6
    panel(d, [x0, y0, x0 + lw, y1], 22, t, ears_on=True)
    d.text((x0 + 24, y0 + 20), "fluffs in ur instance", font=font("head", 22), fill=t["text"])
    lst = fr.list() if fr and on else []
    world = (state.world or {}).get("world")
    if not on:
        msg = "Fluff Friends is off ~ turn it on to see other Fluff users near u"
    elif not world:
        msg = "join a world in VRChat and other Fluff users there show up here"
    elif not lst:
        msg = "no other Fluff users here yet ~ invite ur friends to the app!"
    else:
        msg = None
    if msg:
        for i, ln in enumerate(wrap(msg, font("body2", 16), lw - 48)[:3]):
            d.text((x0 + 24, y0 + 70 + i * 24), ln, font=font("body2", 16), fill=t["sub"])
    for i, (sid, info) in enumerate(lst[:7]):
        ry = y0 + 64 + i * 50
        d.rounded_rectangle([x0 + 18, ry, x0 + lw - 18, ry + 42], radius=14, fill=t["panel2"])
        paw(d, x0 + 40, ry + 22, 8, t["primary"])
        d.text((x0 + 58, ry + 21), info["n"], font=font("body", 17), fill=t["text"], anchor="lm")
        tag = {"quest": "quest", "desktop": "desktop"}.get(info.get("c"), "")
        if tag:
            d.text((x0 + 66 + font("body", 17).getlength(info["n"]), ry + 22), tag, font=font("body2", 12), fill=t["sub"], anchor="lm")
        button(d, hit, [x0 + lw - 118, ry + 5, x0 + lw - 26, ry + 37], "wave", t, "wave", sid, fsize=15)
    if world:
        d.text((x0 + 24, y1 - 24), ellipsize(tr("in") + " " + world, font("body2", 13), lw - 48), font=font("body2", 13),
               fill=t["sub"], anchor="lm")
    rx = x0 + lw + 16
    panel(d, [rx, y0, x1, y1], 22, t)
    d.text((rx + 20, y0 + 20), "how it works", font=font("head", 20), fill=t["text"])
    info = ["shows other people running Fluff VR Stats in the SAME instance as u",
            "tap wave and it pops up on their wrist",
            "only ur chat name is shared, + only with people in that instance",
            "needs ur free app key (Settings > app key)"]
    yy = y0 + 58
    for tip in info:
        for j, ln in enumerate(wrap(tip, font("body2", 14), x1 - rx - 56)[:3]):
            if j == 0:
                paw(d, rx + 26, yy + 9, 5, t["primary"])
            d.text((rx + 40, yy), ln, font=font("body2", 14), fill=t["sub"])
            yy += 19
        yy += 8
    d.text((rx + 20, y1 - 32), "Fluff Friends", font=font("body", 15), fill=t["text"], anchor="lm")
    switch(d, x1 - 74, y1 - 46, on, t, scale=0.85)
    hit.add([rx, y1 - 52, x1, y1 - 10], "toggle", "fluff_friends")


def _fun_events(d, hit, box, state, t, fun):
    x0, y0, x1, y1 = box
    ev = state.cevents.upcoming() if state.cevents else []
    lw = (x1 - x0) * 0.62
    panel(d, [x0, y0, x0 + lw, y1], 22, t, ears_on=True)
    d.text((x0 + 24, y0 + 20), "community nights", font=font("head", 22), fill=t["text"])
    if not ev:
        for i, ln in enumerate(wrap("nothing planned right now ~ events get posted in the Discord and show up here + on "
                                    "ur Home tab by themselves", font("body2", 16), lw - 48)[:3]):
            d.text((x0 + 24, y0 + 70 + i * 24), ln, font=font("body2", 16), fill=t["sub"])
    for i, e in enumerate(ev[:4]):
        ry = y0 + 64 + i * 92
        live = e["start"] <= time.time()
        d.rounded_rectangle([x0 + 18, ry, x0 + lw - 18, ry + 82], radius=16,
                            fill=mix(t["panel2"], t["primary"], 0.3) if live else t["panel2"])
        d.text((x0 + 36, ry + 20), ellipsize(e["title"], font("head", 20), lw - 260), font=font("head", 20), fill=t["text"], anchor="lm")
        d.text((x0 + lw - 36, ry + 20), tr(fluffnet.fmt_when(e["start"])), font=font("body", 15),
               fill=t["good"] if live else t["primary"], anchor="rm")
        sub = " · ".join(x for x in (e.get("world"), e.get("desc")) if x)
        d.text((x0 + 36, ry + 52), ellipsize(sub or tr("hang out with the Fluff community :3"), font("body2", 14), lw - 72),
               font=font("body2", 14), fill=t["sub"], anchor="lm")
    rx = x0 + lw + 16
    panel(d, [rx, y0, x1, y1], 22, t)
    d.text((rx + 20, y0 + 20), "be there!", font=font("head", 20), fill=t["text"])
    yy = y0 + 58
    for tip in ("be in VR with the app open during an event for the 🎪 Community Night badge",
                "events are planned in the Discord (#announcements), grab 📢 Update Pings to get pinged"):
        for ln in wrap(tip, font("body2", 14), x1 - rx - 44)[:4]:
            rich_text(d, (rx + 20, yy), ln, 14, t["sub"], kind="body2")
            yy += 20
        yy += 10
    button(d, hit, [rx + 20, y1 - 58, x1 - 20, y1 - 18], "open the Discord", t, "join_discord", primary=True, fsize=17)


# ---------------------------------------------------------------- settings ---
def tab_settings(d, hit, box, state, t):
    x0, y0, x1, y1 = box
    cfg = state.cfg
    page = getattr(state, "set_page", "general")
    _pills(d, hit, x0, y0, x1, SET_PAGES, page, t, "set_page")
    g = cfg.get("gchat", {})
    ax = cfg.get("a11y", {})
    acc = state.access
    disc = cfg.get("discord", {})
    rows_l, rows_r, note = [], [], None
    if page == "general":
        rows_l = [
            ("Language", lang.NAMES.get(cfg.get("language", "en"), "English"), ("lang",), None, "tap to switch · 12 languages"),
            ("Start in", {"ask": "ask me", "vr": "VR", "desktop": "desktop"}.get(cfg.get("launch_mode", "ask"), "ask me"),
             ("set", "launch_mode", "__cycle__", ["ask", "vr", "desktop"]), None, "VR or desktop when u open the app"),
            ("Start with SteamVR", None, ("start_with_steamvr",), cfg.get("start_with_steamvr", False),
             "opens by itself when SteamVR starts"),
            ("Auto updates", None, ("set", "auto_update", not cfg.get("auto_update", True)), cfg.get("auto_update", True),
             "signed updates install by themselves"),
            ("Menu cursor", cfg.get("cursor", "paw"), ("set", "cursor", "__cycle__", ["paw", "heart", "star", "pumpkin"]), None, None),
            ("Wrist refresh", f"{cfg.get('hud_refresh_hz', 2)}x / sec", ("set", "hud_refresh_hz", "__cycle__", [1, 2, 4]), None,
             "lower = a tiny bit more fps"),
            ("Setup checklist", "open", ("checklist", "open"), None, "OSC, conflicts, wrist, key"),
        ]
        rows_r = [
            ("Profile", {"performance": "Performance", "comfy": "Comfy", "full": "Full fluff"}.get(cfg.get("profile"), "my own picks"),
             ("profile", {"custom": "performance", "performance": "comfy", "comfy": "full", "full": "custom"}.get(cfg.get("profile", "custom"), "performance")),
             None, "one tap: light ~ comfy ~ everything ~ ur own picks"),
            ("Startup sound", None, ("set", "startup_sound", not cfg.get("startup_sound", True)), cfg.get("startup_sound", True), None),
            ("Intro animation", None, ("set", "intro", not cfg.get("intro", True)), cfg.get("intro", True), None),
            ("Animated logo", None, ("set", "animate_logo", not cfg.get("animate_logo", True)), cfg.get("animate_logo", True), None),
            ("Clock", "24h" if cfg["chatbox"].get("time_24h") else "12h", ("cb_set", "time_24h", not cfg["chatbox"].get("time_24h")), None, None),
            ("Weather units", "°" + cfg.get("weather_units", "F"), ("set", "weather_units", "__cycle__", ["F", "C"]), None, None),
            ("Version", getattr(state, "version", "") or "dev", ("open_link", "https://github.com/wolfiecodesowo/fluff-vr-stats/releases"),
             None, "click to see what's new"),
        ]
    elif page == "comfy":
        rows_l = [
            ("Left-handed mode", None, ("left_handed",), cfg["wrist"]["hand"] == "right",
             "stats go on ur right wrist, kitty on the left"),
            ("Menu size", f"{cfg.get('dashboard_width_m', 2.0):.1f} m", ("menu_size",), None, "bigger menu = bigger text"),
            ("Wrist size", f"{cfg['wrist'].get('width_m', 0.13) * 100:.0f} cm", ("wrist_size",), None, "bigger wrist = bigger text"),
            ("Wrist layout", {"full": "full", "compact": "compact", "minimal": "minimal"}.get(cfg.get("hud_style", "full"), "full"),
             ("set", "hud_style", "__cycle__", ["full", "compact", "minimal"]), None, "minimal = fps, clock, batteries only"),
            ("Reduced motion", None, ("a11y", "reduced_motion"), ax.get("reduced_motion", False),
             "no intro, no animated logo, calmer cursor"),
            ("Colorblind-safe colors", None, ("a11y", "colorblind"), ax.get("colorblind", False),
             "fps uses blue / orange / pink + a label, not red vs green"),
        ]
        rows_r = [
            ("Daily VR goal", f"{cfg.get('vr_goal_min', 60)} min", ("set", "vr_goal_min", "__cycle__", [30, 60, 90, 120, 180]), None,
             "turn on Daily VR goal in Mods > Counters"),
            ("Wrist buttons", f"{len(cfg.get('wrist_actions', []))} " + tr("picked"), ("tab", "Wrist"), None, "choose them in the Wrist tab"),
            ("Break reminder", None, ("toggle", "break_reminder"), cfg["modules"].get("break_reminder", False), "water + stretch nudges"),
            ("Night dim", None, ("toggle", "night_dim"), cfg["modules"].get("night_dim", False), "softer wrist after 10pm"),
        ]
    elif page == "osc":
        oc = cfg.get("osc") or {}
        rt = oc.get("router") or {}
        mode = oc.get("mode", "auto")
        cbm = rt.get("chatbox", "yield")
        fw = rt.get("forward_to") or []
        rows_l = [
            ("OSC connection", {"auto": "auto (OSCQuery)", "classic": "classic ports"}.get(mode, mode),
             ("osc_set", "mode", "classic" if mode == "auto" else "auto"), None,
             "auto finds VRChat by itself · classic = 9000/9001"),
            ("Another app uses the chatbox", {"yield": "let them", "own": "Fluff wins", "merge": "share it"}.get(cbm, cbm),
             ("osc_set", "chatbox", {"yield": "merge", "merge": "own", "own": "yield"}.get(cbm, "yield")), None,
             "let them = Fluff waits · share = both show · Fluff wins"),
            ("Pass OSC to other apps", None, ("osc_set", "router", not rt.get("enabled", False)), rt.get("enabled", False),
             "for apps that need port 9001 too (classic mode)"),
            ("Forward to ports", ", ".join(str(p) for p in fw) or "none", ("mod_edit", "osc_forward"), None,
             "like 9002, 9003"),
        ]
        rows_r = [
            ("Chatbox on/off", None, ("toggle", "chatbox_status"), cfg["modules"].get("chatbox_status", False),
             "what to show: Chatbox tab"),
            ("Chatbox every", f"{cfg['chatbox'].get('interval_s', 3)}s",
             ("cb_set", "interval_s", {2: 3, 3: 5, 5: 2}.get(cfg["chatbox"].get("interval_s", 3), 3)), None,
             "VRChat allows about one msg every 2s"),
            ("Rotate statuses", None, ("cb_set", "rotate", not cfg["chatbox"].get("rotate", True)),
             cfg["chatbox"].get("rotate", True), "the status line changes by itself"),
            ("Open Chatbox tab", "open", ("tab", "Chatbox"), None, "pick lines + edit ur status"),
        ]
        note = state.extras.get("note_osc_router") or (
            "auto works for almost everyone: VRChat finds Fluff by itself, and other OSC apps (MagicChatbox, VRCOSC...) "
            "keep working. if VRChat doesn't see Fluff, try classic. 'let them' = when another app writes ur chatbox, "
            "Fluff waits until it's done instead of fighting it.")
    elif page == "privacy":
        rows_l = [
            ("Hide world on Discord", None, ("privacy", "hide_world"), disc.get("hide_world", True),
             "ur Discord status won't say which world u're in"),
            ("Song on Discord", None, ("privacy", "show_song"), disc.get("show_song", True), None),
            ("Discord status", None, ("toggle", "discord_presence"), cfg["modules"].get("discord_presence", True),
             "the whole 'playing Fluff VR Stats' thing"),
            ("Fluff Friends", None, ("toggle", "fluff_friends"), cfg["modules"].get("fluff_friends", True),
             "shares ur chat name w/ Fluff users in ur instance"),
        ]
        rows_r = [
            ("Global chat", None, ("toggle", "global_chat"), cfg["modules"].get("global_chat", True), "chat w/ every Fluff user"),
            ("Global chat name", g.get("name") or "pick one", ("mod_edit", "gchat_name"), None, None),
            ("Muted in chat", f"{len(g.get('muted', []))} · unmute all" if g.get("muted") else "nobody",
             ("gchat_unmute_all",) if g.get("muted") else (None,), None, None),
            ("Auto updates", None, ("set", "auto_update", not cfg.get("auto_update", True)), cfg.get("auto_update", True),
             "checks GitHub for new versions"),
        ]
        note = ("what leaves ur PC: global chat msgs + ur chat name (to ntfy.sh + our Discord) · Fluff Friends: ur chat name, "
                "only to Fluff users in ur instance · app key: key, chat name, app version, badge names (to Fluff Bot) · "
                "Discord status: fps, song, world if u allow it (to ur own Discord app) · update check: asks GitHub for the "
                "newest version. that's it. no tracking, no ads, nothing about ur PC or VRChat account.")
    elif page == "key":
        rows_l = [
            ("App key", tr("ok, linked") if acc and acc.linked else (tr("not set") if acc and acc.enabled else tr("not needed yet")),
             ("key_enter",) if acc and acc.enabled else (None,), None, "free! type /key in our Discord"),
            ("Linked to", (acc.who() if acc and acc.linked else "-") or "-", (None,), None, "ur Discord name"),
            ("Status", ellipsize(tr(acc.status if acc else "-"), font("head", 16), 300), (None,), None, None),
            ("Remove key", "remove", ("key_forget",) if acc and acc.linked else (None,), None, "tap twice"),
        ]
        rows_r = [
            ("Get a key", "open Discord", ("join_discord",), None, "then type /key there"),
            ("Beta Tester", tr("yes!! 🧪") if state.fun and state.fun.has("beta") else tr("link ur key to get it"), (None,), None,
             "role in the Discord + badge in the app"),
        ]
        note = ("why a key? it's still 100% free. the key links the app to the Fluff Discord, lets Fluff Bot keep global chat "
                "safe (bans + reports actually work), and gives beta testers their role. it's checked once, then works offline.")
    else:  # backup
        rows_l = [
            ("Export settings", "save", ("export_cfg",), None, "saves to the exports folder"),
            ("Import settings", "load newest", ("import_cfg",), None, "loads the newest file in exports (tap twice)"),
            ("Reset to defaults", "reset", ("reset_cfg",), None, "keeps ur key, kitty + badges (tap twice)"),
        ]
        rows_r = [
            ("Copy logs", "copy", ("copy_logs",), None, "paste them in a Discord ticket"),
            ("Safe mode", "mods back on" if state.safe_mode else "off", ("safe_off",) if state.safe_mode else (None,), None,
             "starts w/ mods off if it crashes twice"),
            ("Help + FAQ", "open", ("open_link", "https://wolfiecodesowo.github.io/fluff-vr-stats/faq.html"), None,
             "overlay not showing, OSC, conflicts..."),
        ]
    gap = 16
    cw = (x1 - x0 - gap) / 2
    rh, rg = 48, 8
    top = y0 + 50
    bottom = y1 - (96 if note else 0)
    for col, rows in enumerate((rows_l, rows_r)):
        cx = x0 + col * (cw + gap)
        for i, (lab, val, act, tog, sub) in enumerate(rows):
            ry = top + i * (rh + rg)
            if ry + rh > bottom:
                break
            a = act[0] if act and act[0] else None
            _setting_row(d, hit, [cx, ry, cx + cw, ry + rh], lab, val, t, a, *(act[1:] if a else ()), toggle=tog, sub=sub)
    if note:
        nb = [x0, y1 - 88, x1, y1]
        d.rounded_rectangle(nb, radius=16, fill=t["panel2"])
        for i, ln in enumerate(wrap(note, font("body2", 13), x1 - x0 - 32)[:4]):
            d.text((x0 + 16, y1 - 78 + i * 19), ln, font=font("body2", 13), fill=t["sub"])


# --------------------------------------------------------------- home ribbon ---
def home_news(state, t):
    """the most important lil message for the Home tab: (text, action, args, color) or None"""
    acc, fun, ev = state.access, state.fun, state.cevents
    if state.safe_mode:
        return ("safe mode: the app crashed twice so it started with mods off", "safe_off", (), t["warn"])
    if acc is not None and acc.enabled and not acc.linked:
        left = acc.grace_left()
        hrs = int(left // 3600)
        return ((tr("grab ur free app key: type /key in our Discord, then tap here") +
                 (f" ({hrs}h {tr('left without one')})" if left > 0 else "")), "key_enter", (), t["warn"])
    if ev is not None:
        live = ev.live()
        if live:
            return ("🎪 " + live[0]["title"] + " " + tr("is happening now!!"), "fun_page", ("events",), t["good"])
        up = ev.upcoming()
        if up and up[0]["start"] - time.time() < 3 * 86400:
            return ("🎪 " + up[0]["title"] + " · " + tr(fluffnet.fmt_when(up[0]["start"])), "fun_page", ("events",), t["primary"])
    if fun is not None:
        nb = fun.new_badges()
        if nb and nb[-1] in F.BADGE_MAP:
            b = F.BADGE_MAP[nb[-1]]
            return (f"{b[1]} " + tr("new badge") + ": " + tr(b[2]) + " ~ " + tr("tap to see"), "tab_fun", ("badges",), t["primary"])
        s = fun.season()
        if s:
            return (F.SEASONS[s]["emoji"] + " " + tr(F.SEASONS[s]["banner"]), "tab_fun", ("closet",), t["primary"])
    return None


# ----------------------------------------------------------------- overlays ---
def overlay_card(d, hit, state, t, box):
    """what's new / checklist / key lock: drawn on top of the body. Returns True if it drew something."""
    acc = state.access
    if getattr(state, "update_required", None):
        hit.add(list(box), "noop")
        _must_update(d, hit, state, t, box)
        return True
    if (acc is not None and acc.locked()) or state.whatsnew or (state.checklist and state.tab == "Home"):
        hit.add(list(box), "noop")              # the card blocks clicks to the tab behind it
    if acc is not None and acc.locked():
        _lock(d, hit, state, t, box)
        return True
    if state.whatsnew:
        _whatsnew(d, hit, state, t, box)
        return True
    if state.checklist and state.tab == "Home":
        _checklist(d, hit, state, t, box)
        return True
    return False


def _card(d, t, box, w, h, hit=None):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    b = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
    d.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=t["bg"][:3] + (200,))
    fluff_card(d, b, t, radius=28, ears_on=True, ear_size=34, glow=True)
    return b


def _must_update(d, hit, state, t, box):
    b = _card(d, t, box, 640, 340)
    tag, msg = state.update_required
    cx = (b[0] + b[2]) / 2
    d.text((cx, b[1] + 50), "time to update!", font=font("title", 36), fill=t["text"], anchor="mm")
    for i, ln in enumerate(wrap(tr(msg), font("body2", 17), b[2] - b[0] - 80)[:4]):
        rich_text(d, (b[0] + 40, b[1] + 92 + i * 26), ln, 17, t["sub"], kind="body2")
    rich_text(d, (cx, b[3] - 152), f"{getattr(state, 'version', '')}  →  {tag}", 22, t["primary"], kind="head", center=True)
    button(d, hit, [cx - 150, b[3] - 110, cx + 150, b[3] - 62], "update now", t, "update_now", primary=True, fsize=20)
    d.text((cx, b[3] - 34), "takes ~10 seconds, ur settings stay", font=font("body2", 14), fill=t["sub"], anchor="mm")


def _lock(d, hit, state, t, box):
    b = _card(d, t, box, 640, 380)
    acc = state.access
    cx = (b[0] + b[2]) / 2
    d.text((cx, b[1] + 50), "one lil thing first!", font=font("title", 36), fill=t["text"], anchor="mm")
    msg = ("Fluff VR Stats is free forever ~ u just need a free key from our Discord. "
           "join, type /key, and put the key here. it also gets u the 🧪 Beta Tester role!")
    for i, ln in enumerate(wrap(msg, font("body2", 17), b[2] - b[0] - 80)[:4]):
        rich_text(d, (b[0] + 40, b[1] + 92 + i * 26), ln, 17, t["sub"], kind="body2")
    bw = (b[2] - b[0] - 100) / 2
    button(d, hit, [b[0] + 40, b[3] - 120, b[0] + 40 + bw, b[3] - 72], "1. open the Discord", t, "join_discord", fsize=18)
    button(d, hit, [b[0] + 60 + bw, b[3] - 120, b[2] - 40, b[3] - 72], "2. enter my key", t, "key_enter", primary=True, fsize=18)
    d.text((cx, b[3] - 38), ellipsize(tr(acc.status), font("body2", 14), b[2] - b[0] - 60), font=font("body2", 14),
           fill=t["warn"] if "didn't" in acc.status or "offline" in acc.status else t["sub"], anchor="mm")


def _whatsnew(d, hit, state, t, box):
    title, bullets = state.whatsnew
    b = _card(d, t, box, 760, 420)
    d.text((b[0] + 36, b[1] + 30), "what's new", font=font("title", 32), fill=t["text"])
    d.text((b[2] - 36, b[1] + 44), getattr(state, "version", ""), font=font("head", 20), fill=t["primary"], anchor="ra")
    d.text((b[0] + 38, b[1] + 80), ellipsize(title, font("head", 18), b[2] - b[0] - 76), font=font("head", 18), fill=t["sub"])
    y = b[1] + 116
    for bl in bullets:
        lines = wrap(bl, font("body2", 15), b[2] - b[0] - 110)[:2]
        if y + 20 * len(lines) > b[3] - 70:
            break
        rich_text(d, (b[0] + 40, y), lines[0], 15, t["text"], kind="body2")
        for ln in lines[1:]:
            y += 20
            rich_text(d, (b[0] + 62, y), ln, 15, t["sub"], kind="body2")
        y += 26
    button(d, hit, [b[2] - 200, b[3] - 58, b[2] - 36, b[3] - 18], "yay, got it!", t, "whatsnew_close", primary=True, fsize=18)
    button(d, hit, [b[0] + 36, b[3] - 58, b[0] + 240, b[3] - 18], "full changelog", t, "open_link",
           "https://github.com/wolfiecodesowo/fluff-vr-stats/releases", fsize=16)


def _checklist(d, hit, state, t, box):
    b = _card(d, t, box, 760, 430)
    cfg = state.cfg
    d.text((b[0] + 36, b[1] + 28), "quick setup check :3", font=font("title", 30), fill=t["text"])
    x = state.extras or {}
    osc_ok = x.get("osc_last") and time.time() - x["osc_last"] < 30
    conflicts = getattr(state, "conflicts", []) or []
    acc = state.access
    items = [
        (bool(osc_ok), "VRChat OSC is on" if osc_ok else "turn on OSC: VRChat Action Menu > Options > OSC > Enabled",
         None, None),
        (not conflicts, "no apps fighting over ur chatbox/wrist" if not conflicts else
         tr("close these, they fight with us:") + " " + ", ".join(conflicts), None, None),
        (True, "stats on ur left wrist, kitty on the other" if cfg["wrist"]["hand"] == "left" else
         "stats on ur right wrist, kitty on the other", ("left_handed",), "swap"),
        (bool(acc and (acc.linked or not acc.enabled)), "app key linked" if acc and acc.linked else
         ("free app key: /key in our Discord" if acc and acc.enabled else "app key not needed yet"),
         ("key_enter",) if acc and acc.enabled and not acc.linked else None, "enter"),
        (bool(cfg.get("gchat", {}).get("name")), "global chat name: " + (cfg.get("gchat", {}).get("name") or "not picked"),
         ("mod_edit", "gchat_name"), "pick"),
        (True, tr("language") + ": " + lang.NAMES.get(cfg.get("language", "en"), "English"), ("lang",), "switch"),
    ]
    y = b[1] + 84
    for ok, text, act, lab in items:
        d.rounded_rectangle([b[0] + 30, y, b[2] - 30, y + 44], radius=14, fill=t["panel2"])
        col = t["good"] if ok else t["warn"]
        d.ellipse([b[0] + 44, y + 12, b[0] + 64, y + 32], fill=col)
        d.text((b[0] + 54, y + 22), "✓" if ok else "!", font=ui._ttf(ui.SYMBOL_FONT, 14) if ui.SYMBOL_FONT else font("body", 14),
               fill=(30, 20, 40), anchor="mm")
        d.text((b[0] + 78, y + 22), ellipsize(text, font("body", 15), b[2] - b[0] - 230), font=font("body", 15),
               fill=t["text"], anchor="lm")
        if act:
            button(d, hit, [b[2] - 130, y + 6, b[2] - 40, y + 38], lab, t, act[0], *act[1:], fsize=15)
        y += 50
    button(d, hit, [b[2] - 220, b[3] - 56, b[2] - 36, b[3] - 16], "all good!", t, "checklist", "done", primary=True, fsize=18)
    d.text((b[0] + 36, b[3] - 36), "open this again in Settings", font=font("body2", 13), fill=t["sub"], anchor="lm")


def locked_hud(state):
    """the wrist while there's no app key yet: a lil card that says where to get one"""
    from PIL import Image
    t = ui.get_theme(state.cfg)
    W, H = ui.HUD_IMG_W, 330
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = lang.ImageDraw.Draw(img)
    fluff_card(d, [20, 60, ui.HUD_W - 14, H - 14], t, radius=28, ears_on=True, ear_size=40)
    d = lang.ImageDraw.Draw(img)
    cx = (20 + ui.HUD_W - 14) / 2
    d.text((cx, 112), "one lil thing first!", font=font("title", 34), fill=t["text"], anchor="mm")
    for i, ln in enumerate(wrap("open the SteamVR menu > Fluff VR Stats and add ur free key from our Discord (/key)",
                                font("body2", 19), ui.HUD_W - 100)[:4]):
        d.text((cx, 160 + i * 28), ln, font=font("body2", 19), fill=t["sub"], anchor="mm")
    paw(d, cx, H - 50, 14, t["primary"])
    return img
