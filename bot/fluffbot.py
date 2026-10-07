"""
Fluff Bot: the official Discord bot for Fluff VR Stats :3

- /setup builds the whole server: roles, channels, permissions, info posts, role buttons
- reads Discord presence: anyone running Fluff VR Stats gets the 🥽 In VR Now role
  and counts toward the live "In VR now" counter
- welcomes new members, logs joins/leaves/edits/deletes to #mod-log
- blocks invite-link spam in the open channels
- auto-posts new GitHub releases
- connects to the client: saves the server id + invite + app id into ../config.json so
  the app's Discord status and "join our discord" button work

Run it with run_bot.bat (first time: setup_bot.bat).
"""
import asyncio
import datetime
import json
import logging
import os
import re
import sys
import urllib.request

import discord
from discord import app_commands
from discord.ext import tasks

import content as C

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    import gchat as G           # same rules + topic as the app's Global chat
except Exception:               # (bot copied somewhere without the app next to it)
    G = None

HERE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(HERE, "bot_config.json")
CLIENT_CFG = os.path.join(os.path.dirname(HERE), "config.json")
REPO_API = "https://api.github.com/repos/wolfiecodesowo/fluff-vr-stats/releases/latest"
PRESENCE_NAMES = ("fluff vr stats",)
THREAD_CHANNELS = {"support", "suggestions", "bugs"}
INVITE_RE = re.compile(r"(discord\.gg/|discord(app)?\.com/invite/)\S+", re.I)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fluffbot")


# ------------------------------------------------------------------ config ---
def load_cfg():
    try:
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    cfg.setdefault("channels", {})
    cfg.setdefault("roles", {})
    return cfg


def save_cfg(cfg):
    tmp = CFG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    os.replace(tmp, CFG_PATH)


def update_client_cfg(**discord_keys):
    """Writes server id / invite / app id into the app's config.json (the 'connection')."""
    try:
        with open(CLIENT_CFG, "r", encoding="utf-8") as f:
            ccfg = json.load(f)
    except Exception:
        ccfg = {}
    d = ccfg.setdefault("discord", {})
    d.update({k: v for k, v in discord_keys.items() if v})
    tmp = CLIENT_CFG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(ccfg, f, indent=2)
    os.replace(tmp, CLIENT_CFG)


CFG = load_cfg()


def make_embed(spec):
    e = discord.Embed(title=spec.get("title"), description=spec.get("description"),
                      color=spec.get("color") or C.PINK)
    for name, value, inline in spec.get("fields", []):
        e.add_field(name=name, value=value, inline=inline)
    if spec.get("image"):
        e.set_image(url=spec["image"])
    if spec.get("thumb"):
        e.set_thumbnail(url=spec["thumb"])
    if spec.get("footer"):
        e.set_footer(text=spec["footer"])
    return e


# --------------------------------------------------------------- the bot ---
intents = discord.Intents.default()
intents.members = True          # welcome + roles      (turn on in Developer Portal)
intents.presences = True        # "In VR now" detection (turn on in Developer Portal)
intents.message_content = True  # invite-link filter    (turn on in Developer Portal)


class RoleButtons(discord.ui.View):
    """Self-assign roles. Persistent: keeps working after the bot restarts."""

    def __init__(self):
        super().__init__(timeout=None)
        labels = {"pings": "📢 Update Pings", "beta": "🧪 Beta Tester",
                  "vrchat": "🌍 VRChat Player", "artist": "🎨 Artist", "bumper": "🔔 Bumper"}
        for key in C.SELF_ROLES:
            b = discord.ui.Button(label=labels[key], style=discord.ButtonStyle.secondary,
                                  custom_id=f"fluff_role:{key}")
            b.callback = self._make_cb(key)
            self.add_item(b)

    @staticmethod
    def _make_cb(key):
        async def cb(inter: discord.Interaction):
            role = inter.guild.get_role(CFG["roles"].get(key, 0))
            if role is None:
                return await inter.response.send_message("that role isn't set up yet, ask staff :3", ephemeral=True)
            if role in inter.user.roles:
                await inter.user.remove_roles(role, reason="self-role")
                await inter.response.send_message(f"removed {role.name}", ephemeral=True)
            else:
                await inter.user.add_roles(role, reason="self-role")
                await inter.response.send_message(f"gave u {role.name} :3", ephemeral=True)
        return cb


async def open_ticket(inter: discord.Interaction, topic: str = ""):
    c = bot.ch("support")
    if c is None:
        return await inter.response.send_message("tickets aren't set up yet, ask staff :3", ephemeral=True)
    for t in c.threads:                       # one open ticket per person
        if not t.archived and t.name.endswith(f"· {inter.user.name}"):
            return await inter.response.send_message(f"u already have a ticket open: {t.mention}", ephemeral=True)
    n = CFG.get("ticket_no", 0) + 1
    CFG["ticket_no"] = n
    save_cfg(CFG)
    t = await c.create_thread(name=f"🎫 {n:03d} · {inter.user.name}", type=discord.ChannelType.private_thread,
                              invitable=False, auto_archive_duration=10080)
    await t.add_user(inter.user)
    staff = bot.role("staff")
    e = discord.Embed(title=f"🎫 ticket #{n:03d}", color=C.PINK,
                      description=f"hiii {inter.user.mention}! staff will be here soon :3\n\n"
                                  "tell us what's going on + add a screenshot and your `logs/fluffvr.log` "
                                  "if the app is acting up.\n\npress **close ticket** when you're all sorted.")
    if topic:
        e.add_field(name="topic", value=topic[:1000], inline=False)
    await t.send(content=staff.mention if staff else None, embed=e, view=CloseTicket(),
                 allowed_mentions=discord.AllowedMentions(roles=True, users=True))
    await inter.response.send_message(f"made ur ticket: {t.mention} 🐾", ephemeral=True)
    log_c = bot.ch("tickets_log")
    if log_c:
        await log_c.send(f"🎫 #{n:03d} opened by {inter.user.mention}: {t.mention}" + (f" — {topic}" if topic else ""))


class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 open a ticket", style=discord.ButtonStyle.primary, custom_id="fluff_ticket_open")
    async def open_btn(self, inter: discord.Interaction, _):
        await open_ticket(inter)


class CloseTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ close ticket", style=discord.ButtonStyle.secondary, custom_id="fluff_ticket_close")
    async def close_btn(self, inter: discord.Interaction, _):
        t = inter.channel
        if not isinstance(t, discord.Thread):
            return await inter.response.send_message("this only works in a ticket", ephemeral=True)
        await inter.response.send_message(f"ticket closed by {inter.user.mention}. thank u! 💜")
        log_c = bot.ch("tickets_log")
        if log_c:
            await log_c.send(f"✅ {t.name} closed by {inter.user.mention}")
        await t.edit(archived=True, locked=True)


class FluffBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents, activity=discord.Game("Fluff VR Stats :3"))
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(RoleButtons())
        self.add_view(TicketPanel())
        self.add_view(CloseTicket())
        gid = CFG.get("guild_id")
        if gid:
            g = discord.Object(id=int(gid))
            self.tree.copy_global_to(guild=g)
            await self.tree.sync(guild=g)
        else:
            await self.tree.sync()
        self.stats_loop.start()
        self.release_loop.start()
        self.bump_loop.start()
        if G is not None:
            self.gchat_task = asyncio.create_task(self.gchat_listen())

    # ---- helpers
    def guild(self):
        gid = CFG.get("guild_id")
        return self.get_guild(int(gid)) if gid else (self.guilds[0] if self.guilds else None)

    def ch(self, key):
        g = self.guild()
        return g.get_channel(CFG["channels"].get(key, 0)) if g else None

    def role(self, key):
        g = self.guild()
        return g.get_role(CFG["roles"].get(key, 0)) if g else None

    def is_staff(self, member):
        if member.guild_permissions.administrator or member.id == member.guild.owner_id:
            return True
        return any(r.id in (CFG["roles"].get("staff"), CFG["roles"].get("owner")) for r in member.roles)

    async def modlog(self, text, color=C.PURPLE):
        c = self.ch("modlog")
        if c:
            try:
                await c.send(embed=discord.Embed(description=text[:4000], color=color,
                                                 timestamp=datetime.datetime.now(datetime.timezone.utc)))
            except discord.HTTPException:
                pass

    @staticmethod
    def using_fluff(member):
        for a in member.activities or []:
            name = (getattr(a, "name", "") or "").lower()
            if any(n in name for n in PRESENCE_NAMES):
                return True
            app_id = getattr(a, "application_id", None)
            if app_id and CFG.get("app_id") and str(app_id) == str(CFG["app_id"]):
                return True
        return False

    # ---- events
    async def on_ready(self):
        log.info("logged in as %s (app id %s)", self.user, self.application_id)
        if not CFG.get("app_id"):
            CFG["app_id"] = str(self.application_id)
            save_cfg(CFG)
        g = self.guild()
        if g and not CFG.get("guild_id"):
            CFG["guild_id"] = str(g.id)
            save_cfg(CFG)
        update_client_cfg(app_id=str(self.application_id), guild_id=CFG.get("guild_id"),
                          invite=CFG.get("invite"))
        if g is not None and not getattr(self, "_synced_guild", False):
            self._synced_guild = True
            self.tree.copy_global_to(guild=g)
            await self.tree.sync(guild=g)
        if g is None:
            perms = 8
            print(f"\n  invite me to your server:\n  https://discord.com/oauth2/authorize?client_id="
                  f"{self.application_id}&permissions={perms}&scope=bot%20applications.commands\n")
        else:
            print(f"\n  Fluff Bot is online in '{g.name}'! type /setup in your server to build it :3\n")

    async def on_presence_update(self, before, after):
        if CFG.get("guild_id") and after.guild.id != int(CFG["guild_id"]):
            return
        role = self.role("invr")
        if role is None:
            return
        on = self.using_fluff(after)
        try:
            if on and role not in after.roles:
                await after.add_roles(role, reason="using Fluff VR Stats")
            elif not on and role in after.roles:
                await after.remove_roles(role, reason="stopped Fluff VR Stats")
        except discord.HTTPException:
            pass

    async def on_member_join(self, m):
        role = self.role("member")
        if role:
            try:
                await m.add_roles(role, reason="new fluff")
            except discord.HTTPException:
                pass
        main = self.ch("joins") or self.ch("main")
        if main:
            e = discord.Embed(description=f"welcome {m.mention}!! 🐾 grab the client in "
                                          f"{self.ch('download').mention if self.ch('download') else '#download'} "
                                          f"and say hi :3", color=C.PINK)
            e.set_thumbnail(url=m.display_avatar.url)
            await main.send(embed=e)
        await self.modlog(f"📥 **joined:** {m.mention} ({m}) · account made "
                          f"<t:{int(m.created_at.timestamp())}:R>", C.MINT)

    async def on_member_remove(self, m):
        await self.modlog(f"📤 **left:** {m} ({m.id})", C.GOLD)

    async def on_message_delete(self, msg):
        if msg.author.bot or not msg.guild:
            return
        await self.modlog(f"🗑️ **deleted** in {msg.channel.mention} by {msg.author.mention}:\n{msg.content or '*(no text)*'}",
                          0xFF6B6B)

    async def on_message_edit(self, before, after):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        await self.modlog(f"✏️ **edited** in {before.channel.mention} by {before.author.mention}:\n"
                          f"**before:** {before.content}\n**after:** {after.content}")

    async def on_message(self, msg):
        if msg.guild and msg.author.id == C.DISBOARD_ID:
            await self.on_disboard(msg)
            return
        if msg.author.bot or not msg.guild or not isinstance(msg.author, discord.Member):
            return
        gc = self.ch("gchat")
        if gc and msg.channel.id == gc.id and G is not None:
            await self.gchat_from_discord(msg)
            return
        if INVITE_RE.search(msg.content or "") and not self.is_staff(msg.author):
            try:
                await msg.delete()
                await msg.channel.send(f"{msg.author.mention} no invite links pls :3 (rule 3)", delete_after=8)
                await self.modlog(f"🚫 removed an invite link from {msg.author.mention} in {msg.channel.mention}")
            except discord.HTTPException:
                pass

    # ---- global chat bridge: #global-chat <-> the Global chat tab in the app (via ntfy.sh)
    async def ensure_gchat(self, guild):
        if self.ch("gchat"):
            return
        main = self.ch("main")
        try:
            c = await guild.create_text_channel("🌐・global-chat", category=main.category if main else None,
                                                topic=C.TOPICS.get("gchat"), slowmode_delay=3,
                                                reason="Fluff Bot global chat bridge")
            CFG.setdefault("channels", {})["gchat"] = c.id
            for spec in C.POSTS.get("gchat", []):
                await c.send(embed=make_embed(spec))
            save_cfg(CFG)
        except discord.HTTPException:
            pass

    async def gchat_listen(self):
        """App -> Discord: every message from the app gets posted in #global-chat."""
        import aiohttp
        await self.wait_until_ready()
        g = self.guild()
        if g:
            await self.ensure_gchat(g)
        since, backoff, posted = "10m", 2, set()
        while not self.is_closed():
            t0 = asyncio.get_event_loop().time()
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None, sock_read=90)) as s:
                    async with s.get(f"{G.BASE}/{G.TOPIC}/json?since={since}", headers=G.UA) as r:
                        async for raw in r.content:
                            line = raw.decode("utf-8", "ignore").strip()
                            if not line:
                                continue
                            try:
                                ev = json.loads(line)
                            except ValueError:
                                continue
                            if ev.get("event") != "message" or not ev.get("id"):
                                continue
                            since = ev["id"]                     # resume from here after a reconnect
                            if ev["id"] in posted:
                                continue
                            posted.add(ev["id"])
                            if len(posted) > 500:
                                posted = set(list(posted)[-200:])
                            m = G.GlobalChat.parse(self._gc_parser(), line)
                            if not m or m["client"] == "discord":
                                continue
                            c = self.ch("gchat")
                            if c:
                                tag = {"quest": " · quest", "desktop": " · desktop", "phone": " · phone"}.get(m["client"], "")
                                name = discord.utils.escape_markdown(m["name"])
                                text = discord.utils.escape_mentions(discord.utils.escape_markdown(m["text"]))
                                try:
                                    await c.send(f"**{name}**{tag}: {text}", allowed_mentions=discord.AllowedMentions.none())
                                except discord.HTTPException:
                                    pass
            except asyncio.CancelledError:
                raise
            except (aiohttp.ClientPayloadError, aiohttp.ServerDisconnectedError, asyncio.TimeoutError, ConnectionResetError):
                pass                                   # ntfy cut the long stream (normal), reconnect below
            except Exception as e:
                log.info("global chat relay: %s", e)
            # it was running fine for a while -> reconnect right away, otherwise back off a bit
            if asyncio.get_event_loop().time() - t0 > 20:
                backoff = 2
                await asyncio.sleep(0.5)
            else:
                await asyncio.sleep(backoff)
                backoff = min(60, backoff * 2)

    def _gc_parser(self):
        """tiny stand-in 'self' so the app's parser can be reused (no thread, no network)"""
        p = getattr(self, "_gcp", None)
        if p is None:
            p = self._gcp = type("P", (), {"sid": "fluffbot"})()
        return p

    async def gchat_from_discord(self, msg):
        """Discord -> app: messages typed in #global-chat show up in the app."""
        text, why = G.clean(msg.content)
        if text is None:
            if why and why != "empty":
                try:
                    await msg.delete()
                    await msg.channel.send(f"{msg.author.mention} {why}", delete_after=6)
                except discord.HTTPException:
                    pass
            return
        last = getattr(self, "_gc_last", {})
        self._gc_last = last
        now = asyncio.get_event_loop().time()
        if now - last.get(msg.author.id, 0) < G.SLOW_S:
            return
        last[msg.author.id] = now
        body = json.dumps({"v": 1, "n": G.clean_name(msg.author.display_name) or "fluff", "m": text,
                           "s": "d" + str(msg.author.id)[-9:], "c": "discord"}, ensure_ascii=False).encode("utf-8")
        import aiohttp
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(f"{G.BASE}/{G.TOPIC}", data=body, headers=G.UA) as r:
                    if r.status >= 300:
                        log.info("global chat send failed: %s", r.status)
        except Exception as e:
            log.info("global chat send failed: %s", e)

    # ---- bumping (DISBOARD)
    BUMP_COOLDOWN = 2 * 3600

    def bump_data(self):
        return CFG.setdefault("bump", {"last": 0, "by": None, "reminded": True, "counts": {}})

    async def ensure_bump(self, guild):
        """makes the 🔔 Bumper role + 🔔・bump channel if the server was built before they existed"""
        changed = False
        if not self.role("bumper"):
            try:
                r = await guild.create_role(name="🔔 Bumper", colour=discord.Colour(0x96ECB0), mentionable=False,
                                            reason="Fluff Bot bump reminders")
                CFG.setdefault("roles", {})["bumper"] = r.id
                changed = True
            except discord.HTTPException:
                pass
        if not self.ch("bump"):
            main = self.ch("main")
            try:
                c = await guild.create_text_channel("🔔・bump", category=main.category if main else None,
                                                    topic=C.TOPICS.get("bump"), reason="Fluff Bot bump reminders")
                CFG.setdefault("channels", {})["bump"] = c.id
                for spec in C.POSTS.get("bump", []):
                    await c.send(embed=make_embed(spec))
                changed = True
            except discord.HTTPException:
                pass
        if changed:
            save_cfg(CFG)

    async def on_disboard(self, msg):
        """DISBOARD said 'Bump done!' -> thank the bumper, count it, start the 2h timer"""
        text = " ".join((e.description or "") + " " + (e.title or "") for e in msg.embeds).lower()
        if not ("bump done" in text or ":thumbsup:" in text or "👍" in text):
            return
        meta = getattr(msg, "interaction_metadata", None) or getattr(msg, "interaction", None)
        user = getattr(meta, "user", None)
        b = self.bump_data()
        b.update(last=msg.created_at.timestamp(), by=user.id if user else None, reminded=False)
        if user:
            b["counts"][str(user.id)] = b["counts"].get(str(user.id), 0) + 1
        save_cfg(CFG)
        n = b["counts"].get(str(user.id), 0) if user else 0
        nxt = int(b["last"] + self.BUMP_COOLDOWN)
        e = discord.Embed(description=(f"thank u {user.mention}!! 💚 that's bump **#{n}** from u :3\n" if user else "thanks for the bump!! 💚\n")
                          + f"next bump <t:{nxt}:R>. i'll ping 🔔 Bumpers when it's time", color=C.MINT)
        try:
            await msg.channel.send(embed=e)
        except discord.HTTPException:
            pass

    @tasks.loop(minutes=1)
    async def bump_loop(self):
        g = self.guild()
        if not g:
            return
        if not getattr(self, "_bump_ready", False):
            self._bump_ready = True
            await self.ensure_bump(g)
        b = self.bump_data()
        if b.get("last") and not b.get("reminded") and datetime.datetime.now().timestamp() >= b["last"] + self.BUMP_COOLDOWN:
            b["reminded"] = True
            save_cfg(CFG)
            c, r = self.ch("bump"), self.role("bumper")
            if c:
                e = discord.Embed(title="🔔 bump time!!", description="type `/bump` (the **DISBOARD** one) to push us up the list "
                                  "so more fluffs find us :3", color=C.MINT)
                await c.send(content=r.mention if r else None, embed=e, allowed_mentions=discord.AllowedMentions(roles=True))

    @bump_loop.before_loop
    async def _wait3(self):
        await self.wait_until_ready()

    # ---- background loops
    @tasks.loop(minutes=10)      # Discord allows 2 channel renames per 10 min
    async def stats_loop(self):
        g = self.guild()
        if not g:
            return
        invr = sum(1 for m in g.members if not m.bot and self.using_fluff(m))
        names = {"stat_members": f"🐾 Members: {sum(1 for m in g.members if not m.bot)}",
                 "stat_invr": f"🥽 In VR now: {invr}"}
        if CFG.get("last_release"):
            names["stat_version"] = f"⬇️ Latest: {CFG['last_release']}"
        for key, name in names.items():
            c = self.ch(key)
            if c and c.name != name:
                try:
                    await c.edit(name=name)
                except discord.HTTPException:
                    pass
        role = self.role("invr")       # catch anyone presence events missed
        if role:
            for m in g.members:
                on = self.using_fluff(m)
                try:
                    if on and role not in m.roles:
                        await m.add_roles(role)
                    elif not on and role in m.roles:
                        await m.remove_roles(role)
                except discord.HTTPException:
                    pass

    @stats_loop.before_loop
    async def _wait1(self):
        await self.wait_until_ready()

    @tasks.loop(minutes=20)
    async def release_loop(self):
        rel = await asyncio.to_thread(fetch_release)
        if not rel or not rel.get("tag_name"):
            return
        if rel["tag_name"] != CFG.get("last_release"):
            first = CFG.get("last_release") is None
            CFG["last_release"] = rel["tag_name"]
            save_cfg(CFG)
            if not first:          # don't announce the release that already existed
                await self.post_release(rel, ping=True)

    @release_loop.before_loop
    async def _wait2(self):
        await self.wait_until_ready()

    async def post_release(self, rel, ping=False):
        e = discord.Embed(title=f"🎉 {rel.get('name') or rel['tag_name']}", url=rel.get("html_url"),
                          description=(rel.get("body") or "")[:3500], color=C.PINK)
        e.add_field(name="download", value=rel.get("html_url", C.RELEASES))
        e.set_thumbnail(url=C.LOGO)
        pr = self.role("pings")
        for key in ("announcements", "changelog", "github"):
            c = self.ch(key)
            if c:
                await c.send(content=pr.mention if (ping and pr and key == "announcements") else None,
                             embed=e, allowed_mentions=discord.AllowedMentions(roles=True))


def fetch_release():
    try:
        req = urllib.request.Request(REPO_API, headers={"User-Agent": "FluffBot", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


bot = FluffBot()


@bot.tree.error
async def on_app_error(inter: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        return                                    # staff_only already answered
    log.warning("command error: %s", error)
    msg = "oops, something went wrong >w< (staff can check the bot window)"
    if isinstance(error, app_commands.CommandInvokeError) and isinstance(error.original, discord.Forbidden):
        msg = "I don't have permission to do that here :c"
    try:
        if inter.response.is_done():
            await inter.followup.send(msg, ephemeral=True)
        else:
            await inter.response.send_message(msg, ephemeral=True)
    except discord.HTTPException:
        pass


# ----------------------------------------------------------- server build ---
async def build_server(guild: discord.Guild, status):
    me = guild.me
    everyone = guild.default_role

    await status("🎨 making roles…")
    existing = {r.name: r for r in guild.roles}
    roles = {}
    for spec in reversed(C.ROLES):       # create bottom-up so the order comes out right
        perms = discord.Permissions.none()
        if spec["perms"] == "admin":
            perms = discord.Permissions.all()
        elif spec["perms"] == "staff":
            perms = discord.Permissions(manage_messages=True, kick_members=True, moderate_members=True,
                                        manage_nicknames=True, mute_members=True, move_members=True,
                                        deafen_members=True, manage_threads=True, mention_everyone=True,
                                        view_audit_log=True)
        r = existing.get(spec["name"])
        if r is None:
            r = await guild.create_role(name=spec["name"], colour=discord.Colour(spec["color"]),
                                        hoist=spec["hoist"], permissions=perms, mentionable=False,
                                        reason="Fluff Bot setup")
        else:
            await r.edit(colour=discord.Colour(spec["color"]), hoist=spec["hoist"], permissions=perms)
        roles[spec["key"]] = r
    # order them right under the bot's own role
    top = me.top_role.position
    positions = {}
    for i, spec in enumerate(C.ROLES):
        positions[roles[spec["key"]]] = max(1, top - 1 - i)
    try:
        await guild.edit_role_positions(positions=positions)
    except discord.HTTPException:
        pass
    CFG["roles"] = {k: r.id for k, r in roles.items()}
    owner = guild.owner or await guild.fetch_member(guild.owner_id)
    try:
        await owner.add_roles(roles["owner"], roles["member"])
    except discord.HTTPException:
        pass
    for m in guild.members:            # existing people become fluffs
        if not m.bot and roles["member"] not in m.roles:
            try:
                await m.add_roles(roles["member"])
            except discord.HTTPException:
                pass

    await status("🧹 clearing old channels…")
    for c in list(guild.channels):
        try:
            await c.delete(reason="Fluff Bot setup")
        except discord.HTTPException:
            pass

    staff_roles = [roles["owner"], roles["staff"]]
    def overwrites(access):
        ow = {me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True,
                                              manage_messages=True, embed_links=True, connect=True)}
        if access == "read":
            ow[everyone] = discord.PermissionOverwrite(view_channel=True, send_messages=False,
                                                       add_reactions=True, create_public_threads=False,
                                                       create_private_threads=False, send_messages_in_threads=False)
            for r in staff_roles:
                ow[r] = discord.PermissionOverwrite(send_messages=True, send_messages_in_threads=True)
        elif access == "open":
            ow[everyone] = discord.PermissionOverwrite(view_channel=True, send_messages=True, connect=True,
                                                       speak=True, embed_links=True, attach_files=True)
        elif access == "staff":
            ow[everyone] = discord.PermissionOverwrite(view_channel=False)
            for r in staff_roles:
                ow[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, connect=True, speak=True)
        elif access == "stat":
            ow[everyone] = discord.PermissionOverwrite(view_channel=True, connect=False)
        return ow

    await status("🏗️ building channels…")
    chans = {}
    for cat_name, access, items in C.LAYOUT:
        cat = await guild.create_category(cat_name, overwrites=overwrites(access), reason="Fluff Bot setup")
        for kind, key, name in items:
            ow = overwrites(access)
            if key in THREAD_CHANNELS:      # people can talk inside threads here (tickets, ideas, bugs)
                ow[everyone] = discord.PermissionOverwrite(view_channel=True, send_messages=False,
                                                           add_reactions=True, send_messages_in_threads=True,
                                                           create_public_threads=False, create_private_threads=False,
                                                           attach_files=True, embed_links=True)
            if kind == "voice":
                c = await guild.create_voice_channel(name, category=cat, overwrites=ow)
            else:
                c = await guild.create_text_channel(name, category=cat, overwrites=ow,
                                                    topic=C.TOPICS.get(key))
            chans[key] = c
    CFG["channels"] = {k: c.id for k, c in chans.items()}
    await chans["main"].edit(slowmode_delay=2)
    save_cfg(CFG)

    await status("⚙️ server settings…")
    try:
        await guild.edit(verification_level=discord.VerificationLevel.medium,
                         explicit_content_filter=discord.ContentFilter.all_members,
                         default_notifications=discord.NotificationLevel.only_mentions,
                         system_channel=None, afk_channel=chans["vc_afk"], afk_timeout=900,
                         reason="Fluff Bot setup")
    except discord.HTTPException as e:
        log.warning("guild settings: %s", e)
    try:
        await guild.edit_widget(enabled=True, channel=chans["welcome"])
    except discord.HTTPException as e:
        log.warning("widget: %s", e)

    await status("✍️ writing the info channels…")
    await post_info(chans)

    await status("🔗 making the invite + connecting the client…")
    inv = await chans["welcome"].create_invite(max_age=0, max_uses=0, unique=False, reason="main invite")
    CFG["invite"] = inv.url
    rel = await asyncio.to_thread(fetch_release)
    if rel and rel.get("tag_name"):
        CFG["last_release"] = rel["tag_name"]
    save_cfg(CFG)
    update_client_cfg(app_id=str(bot.application_id), guild_id=str(guild.id), invite=inv.url)
    bot.stats_loop.restart()
    return inv.url


async def post_info(chans):
    for key, specs in C.POSTS.items():
        c = chans.get(key)
        if not c:
            continue
        for spec in specs:
            if spec.get("content"):              # plain message (video links auto-play in Discord)
                await c.send(spec["content"])
                continue
            if key == "get_roles":
                await c.send(embed=make_embed(spec), view=RoleButtons())
            elif key == "support":
                await c.send(embed=make_embed(spec), view=TicketPanel())
            else:
                await c.send(embed=make_embed(spec))


class ConfirmSetup(discord.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=60)
        self.author_id = author_id

    @discord.ui.button(label="yes, build it (deletes current channels)", style=discord.ButtonStyle.danger)
    async def go(self, inter: discord.Interaction, _):
        if inter.user.id != self.author_id:
            return await inter.response.send_message("not ur button :3", ephemeral=True)
        await inter.response.edit_message(content="🐾 building… this takes about a minute", view=None)
        user = inter.user

        async def status(text):
            log.info(text)
        try:
            url = await build_server(inter.guild, status)
            try:
                await user.send(f"✨ Fluff VR Stats server is built!! invite link: {url}")
            except discord.HTTPException:
                pass
            main = bot.ch("main")
            if main:
                await main.send(embed=discord.Embed(
                    title="the den is open!! 🐾", color=C.PINK,
                    description=f"invite ur friends: {url}"))
        except Exception as e:
            log.exception("setup failed")
            try:
                await user.send(f"setup hit a snag: {e}")
            except discord.HTTPException:
                pass

    @discord.ui.button(label="cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, inter: discord.Interaction, _):
        await inter.response.edit_message(content="cancelled :3", view=None)


# --------------------------------------------------------------- commands ---
def staff_only():
    async def pred(inter: discord.Interaction):
        if isinstance(inter.user, discord.Member) and bot.is_staff(inter.user):
            return True
        await inter.response.send_message("staff only :3", ephemeral=True)
        return False
    return app_commands.check(pred)


@bot.tree.command(name="setup", description="(owner) build the whole Fluff VR Stats server")
async def setup_cmd(inter: discord.Interaction):
    if inter.user.id != inter.guild.owner_id:
        return await inter.response.send_message("only the server owner can do this", ephemeral=True)
    CFG["guild_id"] = str(inter.guild.id)
    save_cfg(CFG)
    await inter.response.send_message(
        "this builds roles, channels, permissions and all the info posts.\n"
        "⚠️ **it deletes every channel that's here right now.** ready?",
        view=ConfirmSetup(inter.user.id), ephemeral=True)


def is_info_post(m, key):
    """only the bot's own info posts for this channel (never release posts, welcomes or anything else)"""
    if m.author != bot.user:
        return False
    titles = {spec.get("title") for spec in C.POSTS.get(key, []) if spec.get("title")}
    texts = {spec.get("content") for spec in C.POSTS.get(key, []) if spec.get("content")}
    if m.embeds:
        return any(e.title in titles for e in m.embeds)
    return bool(m.content) and m.content in texts


def fetch_all_releases():
    try:
        req = urllib.request.Request(REPO_API.replace("/latest", "?per_page=50"),
                                     headers={"User-Agent": "FluffBot", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            rels = json.loads(r.read().decode("utf-8"))
        rels = [x for x in rels if not x.get("draft") and not x.get("prerelease")]
        return sorted(rels, key=lambda x: x.get("published_at") or x.get("created_at") or "")
    except Exception:
        return []


@bot.tree.command(name="repost-updates", description="(staff) post every Fluff VR Stats update again, oldest to newest")
@app_commands.describe(ping_latest="ping 📢 Update Pings on the newest one")
@staff_only()
async def repost_updates_cmd(inter: discord.Interaction, ping_latest: bool = False):
    await inter.response.send_message("grabbing every release from GitHub… 🐾", ephemeral=True)
    rels = await asyncio.to_thread(fetch_all_releases)
    if not rels:
        return await inter.followup.send("couldn't reach GitHub, try again in a minute :<", ephemeral=True)
    for i, rel in enumerate(rels):
        await bot.post_release(rel, ping=ping_latest and i == len(rels) - 1)
        await asyncio.sleep(1.5)                       # be gentle with Discord's rate limits
    CFG["last_release"] = rels[-1].get("tag_name")
    save_cfg(CFG)
    await inter.followup.send(f"done!! re-posted {len(rels)} updates ({rels[0].get('tag_name')} → {rels[-1].get('tag_name')}) 💜",
                              ephemeral=True)


@bot.tree.command(name="refresh-info", description="(staff) re-post the info channels from content.py")
@staff_only()
async def refresh_cmd(inter: discord.Interaction):
    await inter.response.send_message("refreshing… 🐾", ephemeral=True)
    chans = {}
    for key, cid in CFG["channels"].items():
        c = inter.guild.get_channel(cid)
        if c and key in C.POSTS and isinstance(c, discord.TextChannel):
            await c.purge(limit=50, check=lambda m: is_info_post(m, key))
            chans[key] = c
    await post_info(chans)


@bot.tree.command(name="download", description="get Fluff VR Stats")
async def download_cmd(inter: discord.Interaction):
    await inter.response.send_message(embed=make_embed(C.POSTS["download"][0]))


@bot.tree.command(name="faq", description="frequently asked questions")
async def faq_cmd(inter: discord.Interaction):
    await inter.response.send_message(embed=make_embed(C.POSTS["faq"][0]), ephemeral=True)


@bot.tree.command(name="install", description="how to install Fluff VR Stats")
async def install_cmd(inter: discord.Interaction):
    await inter.response.send_message(embed=make_embed(C.POSTS["install"][0]))


@bot.tree.command(name="stats", description="server stats + who's in VR right now")
async def stats_cmd(inter: discord.Interaction):
    g = inter.guild
    vr = [m for m in g.members if not m.bot and bot.using_fluff(m)]
    e = discord.Embed(title="📊 Fluff stats", color=C.PURPLE)
    e.add_field(name="🐾 members", value=str(sum(1 for m in g.members if not m.bot)))
    e.add_field(name="🥽 in VR now", value=str(len(vr)))
    e.add_field(name="⬇️ latest", value=CFG.get("last_release") or "?")
    if vr:
        e.add_field(name="currently fluffing", value=", ".join(m.display_name for m in vr[:20]), inline=False)
    await inter.response.send_message(embed=e)


@bot.tree.command(name="announce", description="(staff) post an announcement")
@app_commands.describe(title="headline", message="the announcement text", ping="ping 📢 Update Pings?")
@staff_only()
async def announce_cmd(inter: discord.Interaction, title: str, message: str, ping: bool = False):
    c = bot.ch("announcements")
    if not c:
        return await inter.response.send_message("run /setup first", ephemeral=True)
    e = discord.Embed(title=title, description=message.replace("\\n", "\n"), color=C.PINK)
    e.set_footer(text=f"— {inter.user.display_name}")
    pr = bot.role("pings")
    await c.send(content=pr.mention if ping and pr else None, embed=e,
                 allowed_mentions=discord.AllowedMentions(roles=True))
    await inter.response.send_message("posted :3", ephemeral=True)


@bot.tree.command(name="release", description="(staff) post the latest GitHub release")
@staff_only()
async def release_cmd(inter: discord.Interaction):
    await inter.response.defer(ephemeral=True)
    rel = await asyncio.to_thread(fetch_release)
    if not rel:
        return await inter.followup.send("couldn't reach GitHub", ephemeral=True)
    CFG["last_release"] = rel["tag_name"]
    save_cfg(CFG)
    await bot.post_release(rel, ping=True)
    await inter.followup.send(f"posted {rel['tag_name']} :3", ephemeral=True)


@bot.tree.command(name="feature", description="(staff) feature a message in #featured-setups")
@app_commands.describe(message_link="right-click the message → Copy Message Link")
@staff_only()
async def feature_cmd(inter: discord.Interaction, message_link: str):
    m = re.search(r"/(\d+)/(\d+)/(\d+)", message_link)
    if not m:
        return await inter.response.send_message("that doesn't look like a message link", ephemeral=True)
    src = inter.guild.get_channel(int(m.group(2)))
    try:
        msg = await src.fetch_message(int(m.group(3)))
    except Exception:
        return await inter.response.send_message("couldn't find that message", ephemeral=True)
    e = discord.Embed(description=msg.content or None, color=C.GOLD, url=msg.jump_url,
                      title=f"✨ featured: {msg.author.display_name}")
    e.set_thumbnail(url=msg.author.display_avatar.url)
    imgs = [a.url for a in msg.attachments if (a.content_type or "").startswith("image")]
    if imgs:
        e.set_image(url=imgs[0])
    await bot.ch("featured").send(embed=e)
    await inter.response.send_message("featured!! 🌟", ephemeral=True)


@bot.tree.command(name="purge", description="(staff) delete the last N messages here")
@staff_only()
async def purge_cmd(inter: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
    await inter.response.defer(ephemeral=True)
    gone = await inter.channel.purge(limit=amount)
    await inter.followup.send(f"swept {len(gone)} messages 🧹", ephemeral=True)
    await bot.modlog(f"🧹 {inter.user.mention} purged {len(gone)} messages in {inter.channel.mention}")


@bot.tree.command(name="slowmode", description="(staff) set slowmode seconds in this channel")
@staff_only()
async def slowmode_cmd(inter: discord.Interaction, seconds: app_commands.Range[int, 0, 21600]):
    await inter.channel.edit(slowmode_delay=seconds)
    await inter.response.send_message(f"slowmode: {seconds}s", ephemeral=True)


# ---- client info commands (all post the same embeds as the info channels)
def _info_cmd(name, key, desc, idx=0):
    @bot.tree.command(name=name, description=desc)
    async def _cmd(inter: discord.Interaction):
        specs = [x for x in C.POSTS[key] if x.get("title") or x.get("description")]
        await inter.response.send_message(embed=make_embed(specs[idx]))
    return _cmd


for _n, _k, _d in [("features", "features", "what Fluff VR Stats can do"),
                   ("mods", "mods", "all the mods you can toggle"),
                   ("themes", "themes", "themes + style options"),
                   ("boost", "boost", "the FPS boost tweaks"),
                   ("chatbox", "chatbox", "set up chatbox stats in VRChat"),
                   ("troubleshoot", "troubleshoot", "fix common problems"),
                   ("roadmap", "roadmap", "what's coming next"),
                   ("links", "links", "all the important links"),
                   ("safe", "safety", "is Fluff VR Stats safe?"),
                   ("requirements", "requirements", "what you need to run it")]:
    _info_cmd(_n, _k, _d)


@bot.tree.command(name="help", description="everything Fluff Bot can do")
async def help_cmd(inter: discord.Interaction):
    await inter.response.send_message(embed=make_embed(C.POSTS["commands"][0]), ephemeral=True)


@bot.tree.command(name="version", description="the latest Fluff VR Stats version")
async def version_cmd(inter: discord.Interaction):
    v = CFG.get("last_release") or "v0.1.0"
    e = discord.Embed(title=f"⬇️ latest: {v}", url=C.RELEASES, color=C.PINK,
                      description=f"[download it here]({C.RELEASES}) · check 📝・changelog for what's new")
    e.set_thumbnail(url=C.LOGO)
    await inter.response.send_message(embed=e)


@bot.tree.command(name="changelog", description="what changed in the latest version")
async def changelog_cmd(inter: discord.Interaction):
    await inter.response.send_message(embed=make_embed(C.POSTS["changelog"][0]))


@bot.tree.command(name="invr", description="who's using Fluff VR Stats right now")
async def invr_cmd(inter: discord.Interaction):
    vr = [m for m in inter.guild.members if not m.bot and bot.using_fluff(m)]
    if not vr:
        return await inter.response.send_message("nobody's in VR with Fluff VR Stats right now... go be the first! 🥽")
    lines = []
    for m in vr[:25]:
        act = next((a for a in m.activities if bot.using_fluff(type("x", (), {"activities": [a]})())), None)
        extra = f" · {act.details}" if act is not None and getattr(act, "details", None) else ""
        lines.append(f"🥽 **{m.display_name}**{extra}")
    await inter.response.send_message(embed=discord.Embed(title=f"🥽 {len(vr)} in VR right now",
                                                          description="\n".join(lines), color=C.PURPLE))


@bot.tree.command(name="ticket", description="open a private help chat with staff")
@app_commands.describe(topic="what do u need help with?")
async def ticket_cmd(inter: discord.Interaction, topic: str = ""):
    await open_ticket(inter, topic)


@bot.tree.command(name="suggest", description="suggest an idea for the client or server")
@app_commands.describe(idea="ur idea!")
async def suggest_cmd(inter: discord.Interaction, idea: app_commands.Range[str, 5, 1500]):
    c = bot.ch("suggestions")
    if not c:
        return await inter.response.send_message("suggestions aren't set up yet", ephemeral=True)
    e = discord.Embed(description=idea, color=C.MINT)
    e.set_author(name=f"💡 idea from {inter.user.display_name}", icon_url=inter.user.display_avatar.url)
    msg = await c.send(embed=e)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")
    await msg.create_thread(name=f"💬 {idea[:80]}")
    await inter.response.send_message(f"posted ur idea in {c.mention}! 💡", ephemeral=True)


@bot.tree.command(name="bug", description="report a bug in Fluff VR Stats")
@app_commands.describe(title="short name for the bug", what_happened="what did u do + what went wrong?")
async def bug_cmd(inter: discord.Interaction, title: app_commands.Range[str, 3, 100],
                  what_happened: app_commands.Range[str, 5, 1500]):
    c = bot.ch("bugs")
    if not c:
        return await inter.response.send_message("bug reports aren't set up yet", ephemeral=True)
    n = CFG.get("bug_no", 0) + 1
    CFG["bug_no"] = n
    save_cfg(CFG)
    e = discord.Embed(title=f"🐛 #{n:03d} {title}", description=what_happened, color=C.GOLD)
    e.set_author(name=inter.user.display_name, icon_url=inter.user.display_avatar.url)
    e.set_footer(text="status: 🟡 open")
    msg = await c.send(embed=e)
    t = await msg.create_thread(name=f"🐛 #{n:03d} {title}"[:100])
    await t.send(f"{inter.user.mention} thanks for reporting! drop screenshots + `logs/fluffvr.log` here 🐾")
    await inter.response.send_message(f"bug #{n:03d} posted in {c.mention} — thank u! 🐛", ephemeral=True)


@bot.tree.command(name="videos", description="watch Fluff VR Stats in action")
@app_commands.choices(which=[app_commands.Choice(name=t, value=n) for n, t, _ in C.VIDEOS])
async def videos_cmd(inter: discord.Interaction, which: app_commands.Choice[str] = None):
    if which:
        return await inter.response.send_message(f"**{which.name}**\n{C.VIDEO}{which.value}.mp4")
    lines = "\n".join(f"• [{t}]({C.VIDEO}{n}.mp4)" for n, t, _ in C.VIDEOS)
    await inter.response.send_message(embed=discord.Embed(title="🎬 feature videos", description=lines,
                                                          color=C.PINK))


@bot.tree.command(name="vrtip", description="a random VR tip")
async def vrtip_cmd(inter: discord.Interaction):
    import random
    await inter.response.send_message(f"💡 **VR tip:** {random.choice(C.VR_TIPS)}")


@bot.tree.command(name="randomtheme", description="can't pick a theme? let Fluff pick")
async def randomtheme_cmd(inter: discord.Interaction):
    import random
    themes = ["Pride Pastel", "Trans Soft", "Cotton Candy", "Gay Ocean", "Lava Dragon", "Honey Bear",
              "Neon Rave", "Midnight Kitty", "Matcha Latte", "Sunset Fox", "Bubblegum", "Cyber Wolf"]
    ears = ["cat", "fox", "wolf", "bunny", "bear", "dragon", "none"]
    await inter.response.send_message(f"🎨 try **{random.choice(themes)}** with **{random.choice(ears)} ears**! "
                                      "(🎨 Style tab)")


def _action(name, desc, verb, emoji):
    @bot.tree.command(name=name, description=desc)
    async def _cmd(inter: discord.Interaction, who: discord.Member):
        if who.id == inter.user.id:
            return await inter.response.send_message(f"{emoji} {inter.user.mention} {verb} themselves... "
                                                     "someone help this fluff out")
        key = f"{name}_count"
        counts = CFG.setdefault(key, {})
        counts[str(who.id)] = counts.get(str(who.id), 0) + 1
        save_cfg(CFG)
        await inter.response.send_message(f"{emoji} {inter.user.mention} {verb} {who.mention}! "
                                          f"(that's {counts[str(who.id)]} total)")
    return _cmd


_action("headpat", "give someone a headpat", "headpats", "🫳")
_action("boop", "boop someone's snoot", "boops", "👉")
_action("hug", "give someone a big fluffy hug", "hugs", "🫂")


@bot.tree.command(name="fluffrate", description="how fluffy is someone?")
async def fluffrate_cmd(inter: discord.Interaction, who: discord.Member = None):
    who = who or inter.user
    score = (who.id * 7 + 13) % 101           # same answer every time for the same person
    bar = "🟪" * (score // 10) + "⬛" * (10 - score // 10)
    await inter.response.send_message(f"☁️ {who.mention} is **{score}% fluffy**\n{bar}")


@bot.tree.command(name="8ball", description="ask the magic floof a question")
async def eightball_cmd(inter: discord.Interaction, question: str):
    import random
    await inter.response.send_message(f"🎱 **{question}**\n{random.choice(C.FUN_8BALL)}")


@bot.tree.command(name="coinflip", description="flip a coin")
async def coin_cmd(inter: discord.Interaction):
    import random
    await inter.response.send_message(random.choice(["🪙 heads!", "🪙 tails!", "🪙 it landed on its side?? (heads)"]))


@bot.tree.command(name="pet", description="check on Lil Fluff")
async def pet_cmd(inter: discord.Interaction):
    import random
    moods = [("( ˘ω˘ ) zzz", "napping. shhh."), ("ฅ^•ﻌ•^ฅ", "happy to see u!"),
             ("(≧◡≦) ♪", "vibing to music"), ("(°ロ°) !!", "panicking about someone's fps"),
             ("ε=ε=ε=┌(;*´Д`)ﾉ", "doing zoomies"), ("(=^･ω･^=)", "waiting for headpats")]
    face, mood = random.choice(moods)
    await inter.response.send_message(f"🐾 **Lil Fluff** `{face}`\n*{mood}*")


# ---- staff tools
@bot.tree.command(name="poll", description="(staff) post a poll in #polls")
@app_commands.describe(question="the question", answers="answers split with | (up to 10)", hours="how long (1-168)")
@staff_only()
async def poll_cmd(inter: discord.Interaction, question: str, answers: str, hours: app_commands.Range[int, 1, 168] = 24):
    c = bot.ch("polls") or inter.channel
    opts = [a.strip() for a in answers.split("|") if a.strip()][:10]
    if len(opts) < 2:
        return await inter.response.send_message("give at least 2 answers, split with |", ephemeral=True)
    poll = discord.Poll(question=question[:300], duration=datetime.timedelta(hours=hours))
    for o in opts:
        poll.add_answer(text=o[:55])
    await c.send(poll=poll)
    await inter.response.send_message(f"poll posted in {c.mention} 📊", ephemeral=True)


@bot.tree.command(name="warn", description="(staff) warn someone")
@staff_only()
async def warn_cmd(inter: discord.Interaction, who: discord.Member, reason: str):
    w = CFG.setdefault("warns", {}).setdefault(str(who.id), [])
    w.append({"by": inter.user.id, "reason": reason[:300], "at": int(datetime.datetime.now().timestamp())})
    save_cfg(CFG)
    try:
        await who.send(f"⚠️ you got a warning in **{inter.guild.name}**: {reason}\n(warning #{len(w)}). pls read the rules :3")
    except discord.HTTPException:
        pass
    await inter.response.send_message(f"warned {who.mention} (#{len(w)})", ephemeral=True)
    await bot.modlog(f"⚠️ {inter.user.mention} warned {who.mention} (#{len(w)}): {reason}", C.GOLD)


@bot.tree.command(name="warnings", description="(staff) see someone's warnings")
@staff_only()
async def warnings_cmd(inter: discord.Interaction, who: discord.Member):
    w = CFG.get("warns", {}).get(str(who.id), [])
    if not w:
        return await inter.response.send_message(f"{who.display_name} has no warnings ✨", ephemeral=True)
    lines = [f"**#{i + 1}** <t:{x['at']}:R> by <@{x['by']}>: {x['reason']}" for i, x in enumerate(w[-15:])]
    await inter.response.send_message(embed=discord.Embed(title=f"⚠️ {who.display_name}: {len(w)} warnings",
                                                          description="\n".join(lines), color=C.GOLD), ephemeral=True)


@bot.tree.command(name="timeout", description="(staff) time someone out")
@staff_only()
async def timeout_cmd(inter: discord.Interaction, who: discord.Member,
                      minutes: app_commands.Range[int, 1, 40320], reason: str = "no reason given"):
    await who.timeout(datetime.timedelta(minutes=minutes), reason=reason)
    await inter.response.send_message(f"timed out {who.mention} for {minutes} min", ephemeral=True)
    await bot.modlog(f"⏳ {inter.user.mention} timed out {who.mention} for {minutes} min: {reason}", C.GOLD)


@bot.tree.command(name="say", description="(staff) make Fluff Bot post a message")
@staff_only()
async def say_cmd(inter: discord.Interaction, message: str, channel: discord.TextChannel = None):
    c = channel or inter.channel
    await c.send(message.replace("\\n", "\n"), allowed_mentions=discord.AllowedMentions.none())
    await inter.response.send_message("sent :3", ephemeral=True)


@bot.tree.command(name="lockdown", description="(staff) lock or unlock the community chats")
@staff_only()
async def lockdown_cmd(inter: discord.Interaction, locked: bool):
    for key in ("main", "memes"):
        c = bot.ch(key)
        if c:
            ow = c.overwrites_for(inter.guild.default_role)
            ow.send_messages = not locked
            await c.set_permissions(inter.guild.default_role, overwrite=ow)
    await inter.response.send_message("🔒 chats locked" if locked else "🔓 chats open again!")
    await bot.modlog(f"{'🔒' if locked else '🔓'} {inter.user.mention} {'locked' if locked else 'unlocked'} the community chats")


@bot.tree.command(name="bugstatus", description="(staff) set a bug report's status (use inside its thread)")
@app_commands.choices(status=[app_commands.Choice(name=n, value=n) for n in
                              ["🟡 open", "🔵 investigating", "🟢 fixed", "⚪ can't reproduce", "🔴 won't fix"]])
@staff_only()
async def bugstatus_cmd(inter: discord.Interaction, status: app_commands.Choice[str]):
    t = inter.channel
    if not isinstance(t, discord.Thread):
        return await inter.response.send_message("use this inside a bug's thread", ephemeral=True)
    try:
        start = await t.parent.fetch_message(t.id)
        e = start.embeds[0]
        e.set_footer(text=f"status: {status.value}")
        await start.edit(embed=e)
    except Exception:
        pass
    await inter.response.send_message(f"status → **{status.value}**")


# ---- bumping + growth
@bot.tree.command(name="bumpstatus", description="when can we bump on DISBOARD next?")
async def bumpstatus_cmd(inter: discord.Interaction):
    b = bot.bump_data()
    nxt = b.get("last", 0) + FluffBot.BUMP_COOLDOWN
    now = datetime.datetime.now().timestamp()
    if not b.get("last") or now >= nxt:
        msg = "✅ **we can bump right now!** type `/bump` and pick the one with the **DISBOARD** icon :3"
    else:
        msg = f"⏳ next bump <t:{int(nxt)}:R> (<t:{int(nxt)}:t>). grab 🔔 Bumper and i'll ping u!"
    if b.get("by"):
        msg += f"\nlast bump by <@{b['by']}> <t:{int(b['last'])}:R>"
    await inter.response.send_message(embed=discord.Embed(description=msg, color=C.MINT))


@bot.tree.command(name="bumpers", description="top DISBOARD bumpers 🏆")
async def bumpers_cmd(inter: discord.Interaction):
    counts = bot.bump_data().get("counts", {})
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:10]
    if not top:
        return await inter.response.send_message("no bumps yet!! be the first: `/bump` (DISBOARD) 🔔")
    medals = ["🥇", "🥈", "🥉"] + ["🐾"] * 7
    lines = [f"{medals[i]} <@{uid}> · **{n}** bump{'s' if n != 1 else ''}" for i, (uid, n) in enumerate(top)]
    e = discord.Embed(title="🏆 top bumpers", description="\n".join(lines), color=C.GOLD)
    await inter.response.send_message(embed=e, allowed_mentions=discord.AllowedMentions.none())


@bot.tree.command(name="bumpremind", description="get (or stop) a ping when it's time to bump")
async def bumpremind_cmd(inter: discord.Interaction):
    r = bot.role("bumper")
    if r is None:
        return await inter.response.send_message("the 🔔 Bumper role isn't made yet, give me a minute :3", ephemeral=True)
    if r in inter.user.roles:
        await inter.user.remove_roles(r, reason="bump reminders off")
        await inter.response.send_message("ok! no more bump pings 🔕", ephemeral=True)
    else:
        await inter.user.add_roles(r, reason="bump reminders on")
        await inter.response.send_message("yay!! i'll ping u every time we can bump 🔔", ephemeral=True)


@bot.tree.command(name="invite", description="get the server invite + a lil message to share it")
async def invite_cmd(inter: discord.Interaction):
    link = CFG.get("invite") or ""
    if not link:
        try:
            ch = bot.ch("main") or inter.channel
            inv = await ch.create_invite(max_age=0, max_uses=0, unique=False, reason="/invite")
            link = inv.url
            CFG["invite"] = link
            save_cfg(CFG)
        except discord.HTTPException:
            return await inter.response.send_message("i can't make invites here, ask staff :3", ephemeral=True)
    share = (f"come hang with us!! 🐾 Fluff VR Stats :3 is a free cute wrist HUD + mods for VRChat "
             f"(PC + Quest). get help, show ur setup + meet fluffs: {link}")
    e = discord.Embed(title="💌 invite ur friends!", color=C.PINK,
                      description=f"**link:** {link}\n\n**copy + paste this anywhere:**\n```{share}```")
    await inter.response.send_message(embed=e)


def main():
    token = (CFG.get("token") or os.environ.get("FLUFFBOT_TOKEN") or "").strip()
    if not token:
        print("  no bot token yet! double-click setup_bot.bat first :3")
        input("  press Enter to close")
        sys.exit(1)
    try:
        bot.run(token, log_handler=None)
    except discord.PrivilegedIntentsRequired:
        print("\n  >w< turn on the 3 switches in the Developer Portal → your app → Bot → "
              "Privileged Gateway Intents (Presence, Server Members, Message Content), then run again.\n")
        input("  press Enter to close")
    except discord.LoginFailure:
        print("\n  that token didn't work. run setup_bot.bat again and paste a fresh one.\n")
        input("  press Enter to close")


if __name__ == "__main__":
    main()
