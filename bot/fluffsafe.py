"""
Fluff Bot: app keys, the safe global chat relay, bans, reports, beta testers, badges, events, themes.

Needs bot/bot_key.pem (made by tools/make_keys.py). Without it, the old (v1) chat bridge keeps
working and these commands just say keys aren't set up yet.

Data lives in bot/bot_data.json (never uploaded):
  keys:  {key: discord user id}
  users: {uid: {key, gen, sids, v, c, last, first, badges, name}}
  bans:  {uids: [...], sids: [...]}
  events:{id: {...}}
"""
import asyncio
import datetime
import hashlib
import json
import os
import random
import sys
import time
import uuid

import discord
from discord import app_commands
from discord.ext import tasks

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import trust                     # noqa: E402
import fluffnet as N             # noqa: E402

DATA = os.path.join(HERE, "bot_data.json")
KEY_FILE = os.path.join(HERE, "bot_key.pem")
CODE_CHARS = N.CODE_CHARS
MSG_SLOW_S = 3.0
# after this, PC apps older than v0.4 can't send in global chat any more (they get a "please update" notice).
# The Quest Edition gets until QUEST_CUTOFF (old Quest versions before v0.7 have to update by hand). Change it in bot_config.json -> "old_cutoff" (unix time) if u need to.
OLD_CUTOFF = 1792044000          # Oct 15 2026, 00:00 Mountain time (PC)
QUEST_CUTOFF = 1793512800        # Nov 1 2026, 00:00 Mountain time (Quest Edition before v0.8.0)
OLD_NOTICE = ("this version of Fluff VR Stats is too old and doesn't get global chat any more ~ restart the app "
              "to update (it updates itself), then get ur free key with /key in our Discord :3")

try:
    import fun as F              # badge names + theme codes (needs Pillow)
except Exception:
    F = None


def load_data():
    try:
        with open(DATA, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        d = {}
    for k, v in (("keys", {}), ("users", {}), ("bans", {"uids": [], "sids": []}), ("events", {})):
        d.setdefault(k, v)
    d["bans"].setdefault("uids", [])
    d["bans"].setdefault("sids", [])
    return d


def save_data(d):
    tmp = DATA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
    os.replace(tmp, DATA)


def uid_hash(uid):
    return hashlib.sha256(f"fluffuid:{uid}".encode()).hexdigest()[:16]


def new_key():
    return "-".join("".join(random.SystemRandom().choice(CODE_CHARS) for _ in range(4)) for _ in range(3))


def key_norm(k):
    return N.clean_code(str(k).replace("FLUFF", "").replace("KEY", ""))[:12]


def install(bot, env):
    """called from fluffbot.py: adds the listeners, loops + slash commands"""
    C, G, CFG = env["C"], env["G"], env["CFG"]
    staff_only, log = env["staff_only"], env["log"]
    D = load_data()
    PK = None
    if trust.HAVE_CRYPTO and os.path.exists(KEY_FILE):
        try:
            PK = trust.load_private(KEY_FILE)
        except Exception as e:
            log.warning("bot_key.pem couldn't load: %s", e)
    if PK is None:
        log.info("no bot/bot_key.pem yet: app keys + safe chat are off (run tools/make_keys.py)")
    state = {"recent": {}, "last_msg": {}, "uid_by_hash": {}}

    def keys_on():
        return PK is not None

    def uid_from_hash(h):
        if not state["uid_by_hash"]:
            state["uid_by_hash"] = {uid_hash(u): u for u in D["users"]}
        return state["uid_by_hash"].get(h)

    def check_tok(tok, sid=None):
        """token -> (uid, user dict) if it's real, current, not banned, and matches the sid"""
        info = N.read_token(tok)
        if not info:
            return None, None
        uid = uid_from_hash(info.get("u"))
        u = D["users"].get(uid) if uid else None
        if not u or info.get("g", 0) != u.get("gen", 0):
            return None, None
        if sid is not None and info.get("s") != sid:
            return None, None
        if uid in D["bans"]["uids"] or info.get("s") in D["bans"]["sids"]:
            return None, None
        return uid, u

    async def ntfy_post(topic, payload):
        import aiohttp
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(f"{N.BASE}/{topic}", data=body, headers=N.UA) as r:
                    return r.status < 300
        except Exception as e:
            log.info("ntfy post failed: %s", e)
            return False

    async def signed(topic, payload):
        if PK is None:
            return False
        # whole numbers only: floats print differently in Python vs Kotlin, so the Quest app couldn't
        # rebuild the exact signed bytes
        payload = {k: (int(v) if isinstance(v, float) else v) for k, v in payload.items()}
        return await ntfy_post(topic, trust.sign_payload(PK, payload))

    async def listen(topic, handler, since="1m"):
        """follows an ntfy topic forever (reconnects when ntfy cuts the stream, that's normal)"""
        import aiohttp
        await bot.wait_until_ready()
        backoff, seen = 2, []
        while not bot.is_closed():
            t0 = asyncio.get_event_loop().time()
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None, sock_read=90)) as s:
                    async with s.get(f"{N.BASE}/{topic}/json?since={since}", headers=N.UA) as r:
                        async for raw in r.content:
                            try:
                                ev = json.loads(raw.decode("utf-8", "ignore"))
                            except ValueError:
                                continue
                            if ev.get("event") != "message" or not ev.get("id"):
                                continue
                            since = ev["id"]
                            if ev["id"] in seen:
                                continue
                            seen.append(ev["id"])
                            del seen[:-300]
                            try:
                                p = json.loads(ev.get("message", ""))
                            except ValueError:
                                continue
                            if isinstance(p, dict):
                                try:
                                    await handler(p, ev)
                                except Exception as e:
                                    log.info("%s handler: %s", topic, e)
            except asyncio.CancelledError:
                raise
            except Exception:
                pass
            if asyncio.get_event_loop().time() - t0 > 20:
                backoff = 2
                await asyncio.sleep(0.5)
            else:
                await asyncio.sleep(backoff)
                backoff = min(60, backoff * 2)

    def member(uid):
        g = bot.guild()
        return g.get_member(int(uid)) if g and uid else None

    ONLINE_S = 7 * 60          # apps ping every 3 min, so 7 min = still on

    def app_online(uid):
        u = D["users"].get(str(uid))
        if not u or time.time() - float(u.get("last", 0) or 0) > ONLINE_S:
            return None
        return u.get("c") or "pc"

    type(bot).APP_ONLINE = staticmethod(app_online)

    async def give_role(uid, key, reason):
        m, r = member(uid), bot.role(key)
        if m and r and r not in m.roles:
            try:
                await m.add_roles(r, reason=reason)
            except discord.HTTPException:
                pass

    # ------------------------------------------------------------ app keys ---
    async def on_auth(p, ev):
        t = p.get("t")
        if t == "activate":
            nonce, sid = str(p.get("nonce", ""))[:32], str(p.get("sid", ""))[:16]
            key = key_norm(p.get("key", ""))
            uid = D["keys"].get(key)

            async def bad(why):
                await signed(N.AUTH_TOPIC, {"t": "bad_key", "nonce": nonce, "why": why})
            if not nonce or not sid:
                return
            if not uid:
                return await bad("that key isn't real ~ type /key in the Fluff Discord to get urs")
            if uid in D["bans"]["uids"]:
                return await bad("this key was turned off by staff")
            u = D["users"].setdefault(uid, {"key": key, "gen": 0, "sids": [], "badges": [], "first": time.time()})
            if sid not in u["sids"]:
                if len(u["sids"]) >= 5:          # one key, up to 5 installs (PC, laptop, Quest, phone...)
                    u["sids"] = u["sids"][-4:]
                u["sids"].append(sid)
            u.update(v=str(p.get("v", ""))[:20], c=str(p.get("c", ""))[:8], last=time.time(),
                     name=G.clean_name(p.get("n")) if G else str(p.get("n", ""))[:20])
            u.setdefault("activated", time.time())
            save_data(D)
            state["uid_by_hash"] = {}
            body = json.dumps({"u": uid_hash(uid), "s": sid, "g": u.get("gen", 0), "i": int(time.time())},
                              separators=(",", ":")).encode()
            tok = trust.b64e(body) + "." + trust.sign(PK, body)
            m = member(uid)
            await signed(N.AUTH_TOPIC, {"t": "activated", "nonce": nonce, "tok": tok,
                                        "who": (m.display_name if m else "u")[:40], "beta": True})
            await give_role(uid, "beta", "activated the app with their key")
            await bot.modlog(f"🧪 **beta tester:** <@{uid}> activated the app · `{u['v']}` · {u['c']}", C.GOLD)
        elif t == "hb":
            uid, u = check_tok(p.get("tok"), p.get("sid"))
            if u:
                fresh = time.time() - float(u.get("last", 0) or 0) > ONLINE_S
                u.update(v=str(p.get("v", ""))[:20], c=str(p.get("c", ""))[:8], last=time.time())
                save_data(D)
                await give_role(uid, "beta", "using the app")
                if fresh:
                    await give_role(uid, "invr", "app is open")
        elif t == "badges":
            uid, u = check_tok(p.get("tok"), p.get("sid"))
            if u:
                got = [str(b)[:24] for b in (p.get("b") or [])[:40]]
                u["badges"] = sorted(set(u.get("badges", [])) | set(got))
                save_data(D)
                if len(u["badges"]) >= 10:
                    await give_role(uid, "badges", "10+ app badges")

    # --------------------------------------------------------- chat relay ---
    async def relay(msg_id, name, text, sid, client, uid=None, to_discord=True, to_v1=True):
        """the ONE way messages get into the v2 room: signed by us"""
        ts = time.time()
        await signed(G.ROOM2, {"t": "msg", "id": msg_id, "n": name, "m": text, "s": sid, "c": client, "ts": ts})
        state["recent"][msg_id] = {"uid": uid, "sid": sid, "name": name, "text": text, "ts": ts, "c": client}
        if len(state["recent"]) > 400:
            for k in list(state["recent"])[:100]:
                state["recent"].pop(k, None)
        if to_v1:       # Quest Edition + old apps still read the v1 room
            await ntfy_post(G.TOPIC, {"v": 1, "n": name, "m": text, "s": sid, "c": client, "r": 1})
        if to_discord:
            c = bot.ch("gchat")
            if c:
                tag = {"quest": " · quest", "desktop": " · desktop", "phone": " · phone"}.get(client, "")
                safe = discord.utils.escape_mentions(discord.utils.escape_markdown(text))
                try:
                    await c.send(f"**{discord.utils.escape_markdown(name)}**{tag}: {safe}",
                                 allowed_mentions=discord.AllowedMentions.none())
                except discord.HTTPException:
                    pass

    async def on_inbox(p, ev):
        t = p.get("t")
        sid = str(p.get("s", ""))[:16]
        uid, u = check_tok(p.get("tok"), sid)
        if not u:
            return                                   # no real key / banned -> silently dropped
        if t == "msg":
            text, why = G.clean(p.get("m"))
            if text is None:
                return
            now = time.time()
            if now - state["last_msg"].get(uid, 0) < MSG_SLOW_S:
                return
            state["last_msg"][uid] = now
            name = G.clean_name(p.get("n")) or "fluff"
            await relay(uuid.uuid4().hex[:16], name, text, sid, str(p.get("c", "pc"))[:8], uid)
        elif t == "report":
            m = state["recent"].get(str(p.get("id", "")))
            who = f"<@{m['uid']}>" if m and m.get("uid") else (f"sid `{m['sid']}`" if m else "?")
            txt = (f"🚩 **chat report** from <@{uid}>\n**about:** {who} ({m['name'] if m else '?'})\n"
                   f"**message:** {m['text'] if m else '(too old to find)'}\n**reason:** {str(p.get('why', ''))[:120]}\n"
                   f"msg id `{p.get('id')}` · `/chatban` to ban, `/chatdelete` to remove it")
            await bot.modlog(txt, 0xFF6B6B)

    def old_cut(client="pc"):
        if client in ("quest", "phone"):
            return time.time() >= float(CFG.get("quest_cutoff", QUEST_CUTOFF))
        return time.time() >= float(CFG.get("old_cutoff", OLD_CUTOFF))

    async def on_v1(p, ev):
        """messages from old (v0.3) apps in the v1 room -> filtered + signed into the v2 room
        (until the cutoff; after it they just get told to update)"""
        if p.get("r") or p.get("c") == "discord" or "m" not in p:
            return
        if old_cut(str(p.get("c", "pc"))):
            now = time.time()
            if now - state.get("old_notice", 0) > 600:     # at most one notice every 10 min
                state["old_notice"] = now
                await ntfy_post(G.TOPIC, {"v": 1, "n": "Fluff Bot", "m": OLD_NOTICE, "s": "fluffbot", "c": "sys", "r": 1})
            return
        sid = str(p.get("s", ""))[:16]
        if sid in D["bans"]["sids"]:
            return
        text, why = G.clean(p.get("m"))
        if text is None:
            return
        now = time.time()
        if now - state["last_msg"].get("v1:" + sid, 0) < MSG_SLOW_S:
            return
        state["last_msg"]["v1:" + sid] = now
        await relay(uuid.uuid4().hex[:16], G.clean_name(p.get("n")) or "fluff", text, sid,
                    str(p.get("c", "pc"))[:8], None, to_discord=True, to_v1=False)

    async def from_discord(msg, text):
        """Discord #global-chat -> v2 room (old apps get it from fluffbot's v1 bridge)"""
        if not keys_on():
            return False
        if str(msg.author.id) in D["bans"]["uids"]:
            return True
        await relay(uuid.uuid4().hex[:16], G.clean_name(msg.author.display_name) or "fluff", text,
                    "d" + str(msg.author.id)[-9:], "discord", str(msg.author.id), to_discord=False, to_v1=True)
        return True

    bot.safe_from_discord = from_discord
    bot.safe_keys_on = keys_on

    # ---------------------------------------------------------------- events ---
    @tasks.loop(hours=6)
    async def events_loop():
        now = time.time()
        for e in list(D["events"].values()):
            if e.get("end", 0) < now - 3600:
                continue
            await signed(N.EVENT_TOPIC, dict(e, t="event"))

    @events_loop.before_loop
    async def _w():
        await bot.wait_until_ready()

    async def start():
        await bot.wait_until_ready()
        bot.add_view(GateView())
        g = bot.guild()
        if g and not bot.role("badges"):
            try:
                r = await g.create_role(name="🏅 Badge Hunter", colour=discord.Colour(0xFFB86E), reason="app badges")
                CFG.setdefault("roles", {})["badges"] = r.id
                env["save_cfg"](CFG)
            except discord.HTTPException:
                pass
        if g and not bot.ch("theme_share"):
            main = bot.ch("main")
            try:
                c = await g.create_text_channel("🎨・theme-share", category=main.category if main else None,
                                                topic="share ur Fluff VR Stats look! /sharetheme with ur code "
                                                      "(Fun tab > themes in the app)", reason="theme codes")
                CFG.setdefault("channels", {})["theme_share"] = c.id
                env["save_cfg"](CFG)
            except discord.HTTPException:
                pass
        if keys_on():
            asyncio.create_task(listen(N.AUTH_TOPIC, on_auth))
            asyncio.create_task(listen(G.INBOX2, on_inbox))
            asyncio.create_task(listen(G.TOPIC, on_v1, since="2m"))
            events_loop.start()

    bot.safe_start = start

    # -------------------------------------------------------------- commands ---
    tree = bot.tree

    # ---------------------------------------------------------- key gate ---
    # New people only see 🔑・get-your-key until they grab their key (button or /key).
    # Getting a key opens the rest of the server AND is what they put in the app.
    def gate_on():
        return bool(CFG.get("gate"))

    async def unlock(user):
        """gives the 🐾 Fluff role (= sees the whole server)"""
        g = bot.guild()
        m = g.get_member(user.id) if g else None
        r = bot.role("member")
        if m and r and r not in m.roles:
            try:
                await m.add_roles(r, reason="got their app key")
                return True
            except discord.HTTPException:
                pass
        return False

    async def give_key(inter: discord.Interaction):
        uid = str(inter.user.id)
        if uid in D["bans"]["uids"]:
            return await inter.response.send_message("ur key was turned off by staff. open a /ticket if u think "
                                                     "that's a mistake", ephemeral=True)
        key = next((k for k, v in D["keys"].items() if v == uid), None)
        if not key:
            key = new_key()
            while key_norm(key) in D["keys"]:
                key = new_key()
            D["keys"][key_norm(key)] = uid
            save_data(D)
        else:
            key = "-".join(key[i:i + 4] for i in range(0, 12, 4))
        opened = await unlock(inter.user)
        app_note = ("put it in the app: **Settings → App key** (or the popup the first time u open it). "
                    "it works on up to 5 installs (PC, Quest, phone...), links the app to this server, gives u "
                    "**🧪 Beta Tester** and unlocks global chat + Fluff Friends." if keys_on() else
                    "the app doesn't ask for it yet, keep it for when it does (it'll ask soon!).")
        e = discord.Embed(title="🔑 ur Fluff VR Stats key", color=C.PINK,
                          description=f"# `{key}`\n\n" + ("🎉 **u're in! the rest of the server is open now.**\n\n" if opened else "")
                          + app_note + "\n-# it's free + it's urs. don't share it ~ if it leaks, `/resetkey` makes a new one")
        await inter.response.send_message(embed=e, ephemeral=True)
        try:
            await inter.user.send(embed=e)
        except discord.HTTPException:
            pass
        if opened:
            main = bot.ch("main")
            if main:
                try:
                    await main.send(f"welcome in {inter.user.mention}!! 🐾 grab the client in "
                                    f"{bot.ch('download').mention if bot.ch('download') else '#download'} :3",
                                    allowed_mentions=discord.AllowedMentions(users=True))
                except discord.HTTPException:
                    pass

    class GateView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="🔑 get my key + join the server", style=discord.ButtonStyle.success,
                           custom_id="fluff:gate_key")
        async def get(self, inter: discord.Interaction, _):
            await give_key(inter)

    GATE_POST = ("# 🔑 welcome to Fluff VR Stats!!\n"
                 "to see the rest of the server, grab ur **free key**: tap the button below or type `/key`.\n\n"
                 "the same key unlocks the app (PC + Quest), so u're all set in one step :3\n"
                 "-# it's 100% free. it just keeps the server + global chat safe from bots and trolls")

    async def apply_gate(guild, on=True):
        """on: everyone only sees 🔑・get-your-key, the 🐾 Fluff role sees the rest.
        off: back to everyone seeing everything. Never touches staff-only channels."""
        everyone, member_r = guild.default_role, bot.role("member")
        if member_r is None:
            raise RuntimeError("no 🐾 Fluff role ~ run /setup first")
        gate = bot.ch("gate")
        if on and gate is None:
            cat = await guild.create_category("🔑 START", position=0, reason="key gate")
            gate = await guild.create_text_channel("🔑・get-your-key", category=cat, reason="key gate", overwrites={
                everyone: discord.PermissionOverwrite(view_channel=True, send_messages=False, add_reactions=False,
                                                      use_application_commands=True, read_message_history=True),
                member_r: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True)})
            for key in ("owner", "staff"):
                r = bot.role(key)
                if r:
                    await gate.set_permissions(r, view_channel=True, send_messages=True)
            CFG.setdefault("channels", {})["gate"] = gate.id
            await gate.send(GATE_POST, view=GateView())
        changed = 0
        for ch in guild.channels:
            if gate and (ch.id == gate.id or ch.id == gate.category_id):
                continue
            ow = ch.overwrites
            ev = ow.get(everyone, discord.PermissionOverwrite())
            if on:
                if ev.view_channel is False and member_r not in ow:
                    continue                                    # hidden (staff-only) already
                mem = ow.get(member_r) or discord.PermissionOverwrite(**{k: v for k, v in ev if v is not None})
                mem.view_channel = True
                ev.view_channel = False
                ow[member_r], ow[everyone] = mem, ev
            else:
                mem = ow.get(member_r)
                if mem is None or mem.view_channel is not True:
                    continue
                ev.view_channel = True
                ow[everyone] = ev
            try:
                await ch.edit(overwrites=ow, reason="key gate " + ("on" if on else "off"))
                changed += 1
            except discord.HTTPException as e:
                log.info("gate: couldn't edit %s: %s", ch, e)
        CFG["gate"] = on
        env["save_cfg"](CFG)
        return changed

    bot.apply_gate = apply_gate

    @tree.command(name="gate", description="(owner) new people must get a key before they see the server")
    @app_commands.describe(on="on = key needed to see the server, off = everyone sees everything",
                           let_current_in="give the 🐾 Fluff role to everyone already here (so nobody gets locked out)")
    async def gate_cmd(inter: discord.Interaction, on: bool, let_current_in: bool = True):
        if inter.user.id != inter.guild.owner_id:
            return await inter.response.send_message("only the server owner can do this", ephemeral=True)
        await inter.response.send_message("🔧 working on it… (editing every channel takes a minute)", ephemeral=True)
        given = 0
        if on and let_current_in:
            r = bot.role("member")
            for m in inter.guild.members:
                if not m.bot and r and r not in m.roles:
                    try:
                        await m.add_roles(r, reason="was here before the key gate")
                        given += 1
                    except discord.HTTPException:
                        pass
        try:
            n = await apply_gate(inter.guild, on)
        except Exception as e:
            return await inter.followup.send(f"gate hit a snag: {e}", ephemeral=True)
        gate = bot.ch("gate")
        await inter.followup.send(
            (f"🔑 key gate **on**! new people only see {gate.mention if gate else '#get-your-key'} until they grab "
             f"their key. updated {n} channels" + (f", let {given} current members in" if given else "") + ".")
            if on else f"key gate **off**, everyone sees everything again ({n} channels).", ephemeral=True)

    @tree.command(name="key", description="get ur free Fluff VR Stats key (opens the server + unlocks the app)")
    async def key_cmd(inter: discord.Interaction):
        await give_key(inter)

    @tree.command(name="resetkey", description="make a new app key (ur old one stops working)")
    async def resetkey_cmd(inter: discord.Interaction):
        if not keys_on():
            return await inter.response.send_message("app keys aren't switched on yet", ephemeral=True)
        uid = str(inter.user.id)
        for k in [k for k, v in D["keys"].items() if v == uid]:
            D["keys"].pop(k, None)
        u = D["users"].get(uid)
        if u:
            u["gen"] = u.get("gen", 0) + 1
            u["sids"] = []
        key = new_key()
        D["keys"][key_norm(key)] = uid
        save_data(D)
        await inter.response.send_message(f"new key: `{key}` ~ the old one is dead now. put the new one in the app "
                                          "(Settings → App key)", ephemeral=True)

    @tree.command(name="testers", description="(staff) who's actually beta testing the app")
    @staff_only()
    async def testers_cmd(inter: discord.Interaction):
        rows = []
        now = time.time()
        for uid, u in sorted(D["users"].items(), key=lambda x: -x[1].get("last", 0)):
            if not u.get("activated"):
                continue
            ago = now - u.get("last", 0)
            seen = "now" if ago < 600 else f"{int(ago // 3600)}h ago" if ago < 86400 * 2 else f"{int(ago // 86400)}d ago"
            rows.append(f"<@{uid}> · `{u.get('v', '?')}` · {u.get('c', '?')} · seen {seen} · {len(u.get('badges', []))} badges")
        active = sum(1 for u in D["users"].values() if now - u.get("last", 0) < 7 * 86400)
        e = discord.Embed(title=f"🧪 beta testers: {len(rows)} ({active} active this week)",
                          description="\n".join(rows[:40]) or "nobody yet ~ tell people to type /key :3", color=C.GOLD)
        await inter.response.send_message(embed=e, ephemeral=True)

    @tree.command(name="badges", description="see app badges (urs or someone's)")
    async def badges_cmd(inter: discord.Interaction, who: discord.Member = None):
        who = who or inter.user
        u = D["users"].get(str(who.id))
        if not u or not u.get("badges"):
            return await inter.response.send_message(f"{who.display_name} has no synced badges yet ~ "
                                                     "link the app with /key and they sync by themselves", ephemeral=True)
        lines = []
        for b in u["badges"]:
            meta = F.BADGE_MAP.get(b) if F else None
            lines.append(f"{meta[1]} **{meta[2]}** · {meta[3]}" if meta else f"🏅 {b}")
        total = len(F.BADGES) if F else "?"
        e = discord.Embed(title=f"🏅 {who.display_name}'s badges ({len(u['badges'])}/{total})",
                          description="\n".join(lines)[:4000], color=C.PINK)
        e.set_thumbnail(url=who.display_avatar.url)
        await inter.response.send_message(embed=e)

    @tree.command(name="chatban", description="(staff) ban someone from global chat (app + Discord)")
    @staff_only()
    async def chatban_cmd(inter: discord.Interaction, who: discord.Member = None, sid: str = None,
                          reason: str = "broke the rules"):
        if not who and not sid:
            return await inter.response.send_message("pick a member, or paste the sid from a report", ephemeral=True)
        sids = []
        if who:
            uid = str(who.id)
            if uid not in D["bans"]["uids"]:
                D["bans"]["uids"].append(uid)
            sids = list(D["users"].get(uid, {}).get("sids", [])) + ["d" + uid[-9:]]
        if sid:
            sids.append(sid.strip()[:16])
        for s in sids:
            if s not in D["bans"]["sids"]:
                D["bans"]["sids"].append(s)
            await signed(G.ROOM2, {"t": "ban", "s": s, "ts": time.time()})
        save_data(D)
        await bot.modlog(f"🔨 **chat ban** by {inter.user.mention}: {who.mention if who else sid} · {reason}", 0xFF6B6B)
        await inter.response.send_message("banned from global chat everywhere (takes effect right away, no app "
                                          "update needed)", ephemeral=True)

    @tree.command(name="chatunban", description="(staff) unban someone from global chat")
    @staff_only()
    async def chatunban_cmd(inter: discord.Interaction, who: discord.Member = None, sid: str = None):
        if who:
            uid = str(who.id)
            D["bans"]["uids"] = [x for x in D["bans"]["uids"] if x != uid]
            drop = set(D["users"].get(uid, {}).get("sids", [])) | {"d" + uid[-9:]}
            D["bans"]["sids"] = [x for x in D["bans"]["sids"] if x not in drop]
        if sid:
            D["bans"]["sids"] = [x for x in D["bans"]["sids"] if x != sid.strip()]
        save_data(D)
        await inter.response.send_message("unbanned ~ they can chat again (apps that hid their old msgs show "
                                          "new ones fine)", ephemeral=True)

    @tree.command(name="chatdelete", description="(staff) remove a global chat message from everyone's app")
    @staff_only()
    async def chatdelete_cmd(inter: discord.Interaction, msg_id: str):
        await signed(G.ROOM2, {"t": "del", "id": msg_id.strip(), "ts": time.time()})
        await inter.response.send_message("removed from the room :3", ephemeral=True)

    event_grp = app_commands.Group(name="event", description="community nights")

    @event_grp.command(name="create", description="(staff) schedule a community night (shows up in the app)")
    @staff_only()
    async def event_create(inter: discord.Interaction, title: str, when: str, hours: app_commands.Range[float, 0.5, 12.0] = 2.0,
                           world: str = "", details: str = ""):
        """when = 'YYYY-MM-DD HH:MM' in the bot PC's time zone"""
        try:
            start = datetime.datetime.strptime(when.strip(), "%Y-%m-%d %H:%M").astimezone()
        except ValueError:
            return await inter.response.send_message("when needs to look like `2026-10-31 20:00` (ur PC's time zone)",
                                                     ephemeral=True)
        end = start + datetime.timedelta(hours=hours)
        eid = uuid.uuid4().hex[:10]
        ev = {"id": eid, "title": title[:60], "start": start.timestamp(), "end": end.timestamp(),
              "world": world[:60], "desc": details[:160]}
        D["events"][eid] = ev
        save_data(D)
        await inter.response.defer(ephemeral=True)
        if keys_on():
            await signed(N.EVENT_TOPIC, dict(ev, t="event"))
        try:
            await inter.guild.create_scheduled_event(name=title[:100], start_time=start, end_time=end,
                                                     entity_type=discord.EntityType.external,
                                                     location=(f"VRChat · {world}" if world else "VRChat")[:100],
                                                     description=(details or "hang out with the Fluff community :3")[:1000],
                                                     privacy_level=discord.PrivacyLevel.guild_only)
        except Exception as e:
            log.info("scheduled event: %s", e)
        c = bot.ch("announcements")
        if c:
            emb = discord.Embed(title=f"🎪 {title}", color=C.PINK,
                                description=f"<t:{int(start.timestamp())}:F> (<t:{int(start.timestamp())}:R>)\n"
                                            + (f"**world:** {world}\n" if world else "") + (details or "")
                                            + "\n\nbe in VR with the app open during it for the 🎪 **Community Night** badge!")
            pr = bot.role("pings")
            await c.send(content=pr.mention if pr else None, embed=emb, allowed_mentions=discord.AllowedMentions(roles=True))
        await inter.followup.send(f"scheduled! id `{eid}` ~ it shows on everyone's Home tab", ephemeral=True)

    @event_grp.command(name="cancel", description="(staff) cancel a community night")
    @staff_only()
    async def event_cancel(inter: discord.Interaction, event_id: str):
        ev = D["events"].get(event_id.strip())
        if not ev:
            return await inter.response.send_message("no event with that id (see /event list)", ephemeral=True)
        ev["cancel"] = True
        save_data(D)
        await signed(N.EVENT_TOPIC, dict(ev, t="event"))
        await inter.response.send_message("cancelled ~ it's gone from the app", ephemeral=True)

    @event_grp.command(name="list", description="upcoming community nights")
    async def event_list(inter: discord.Interaction):
        now = time.time()
        evs = sorted((e for e in D["events"].values() if e["end"] > now and not e.get("cancel")), key=lambda e: e["start"])
        txt = "\n".join(f"`{e['id']}` **{e['title']}** · <t:{int(e['start'])}:F>" + (f" · {e['world']}" if e["world"] else "")
                        for e in evs) or "nothing planned yet ~ stay tuned :3"
        await inter.response.send_message(embed=discord.Embed(title="🎪 community nights", description=txt, color=C.PINK))

    tree.add_command(event_grp)

    @tree.command(name="sharetheme", description="share ur app theme code in #theme-share")
    async def sharetheme_cmd(inter: discord.Interaction, code: str, name: str = ""):
        got = F.read_theme_code(code) if F else None
        if not got:
            return await inter.response.send_message("that's not a real theme code ~ copy it from Fun → themes in the app",
                                                     ephemeral=True)
        import themes
        p = themes.PRESET_MAP.get(got["theme"])
        accent = tuple(got["accent"] or p[3])
        e = discord.Embed(title=f"🎨 {name or (inter.user.display_name + chr(39) + 's theme')}",
                          color=discord.Colour.from_rgb(*accent),
                          description=f"```{code.strip().upper()}```paste it in the app: **Fun → themes → use a code**")
        e.add_field(name="base", value=p[1])
        e.add_field(name="ears", value=got["ears"])
        e.add_field(name="cursor", value=got["cursor"])
        e.set_author(name=inter.user.display_name, icon_url=inter.user.display_avatar.url)
        c = bot.ch("theme_share") or inter.channel
        await c.send(embed=e)
        await inter.response.send_message(f"posted in {c.mention} :3", ephemeral=True)

    @tree.command(name="emotes", description="(owner) upload the Fluff emote pack to this server")
    async def emotes_cmd(inter: discord.Interaction):
        if inter.user.id != inter.guild.owner_id:
            return await inter.response.send_message("only the server owner can do this", ephemeral=True)
        folder = os.path.join(ROOT, "assets", "emotes")
        files = sorted(f for f in os.listdir(folder) if f.endswith(".png")) if os.path.isdir(folder) else []
        if not files:
            return await inter.response.send_message("no emotes yet ~ run `python tools/make_emotes.py` first",
                                                     ephemeral=True)
        await inter.response.defer(ephemeral=True)
        have = {e.name for e in inter.guild.emojis}
        added = []
        for fn in files:
            nm = os.path.splitext(fn)[0]
            if nm in have:
                continue
            try:
                with open(os.path.join(folder, fn), "rb") as f:
                    em = await inter.guild.create_custom_emoji(name=nm, image=f.read(), reason="Fluff emote pack")
                added.append(str(em))
            except discord.HTTPException as e:
                log.info("emote %s: %s", nm, e)
        await inter.followup.send(("added " + " ".join(added)) if added else "all the emotes are already here :3",
                                  ephemeral=True)
