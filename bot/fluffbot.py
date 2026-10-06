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

HERE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(HERE, "bot_config.json")
CLIENT_CFG = os.path.join(os.path.dirname(HERE), "config.json")
REPO_API = "https://api.github.com/repos/wolfiecodesowo/fluff-vr-stats/releases/latest"
PRESENCE_NAMES = ("fluff vr stats",)
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
                  "vrchat": "🌍 VRChat Player", "artist": "🎨 Artist"}
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


class FluffBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents, activity=discord.Game("Fluff VR Stats :3"))
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(RoleButtons())
        gid = CFG.get("guild_id")
        if gid:
            g = discord.Object(id=int(gid))
            self.tree.copy_global_to(guild=g)
            await self.tree.sync(guild=g)
        else:
            await self.tree.sync()
        self.stats_loop.start()
        self.release_loop.start()

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
        main = self.ch("main")
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
        if msg.author.bot or not msg.guild or not isinstance(msg.author, discord.Member):
            return
        if INVITE_RE.search(msg.content or "") and not self.is_staff(msg.author):
            try:
                await msg.delete()
                await msg.channel.send(f"{msg.author.mention} no invite links pls :3 (rule 3)", delete_after=8)
                await self.modlog(f"🚫 removed an invite link from {msg.author.mention} in {msg.channel.mention}")
            except discord.HTTPException:
                pass

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
            if kind == "voice":
                c = await guild.create_voice_channel(name, category=cat, overwrites=overwrites(access))
            else:
                c = await guild.create_text_channel(name, category=cat, overwrites=overwrites(access),
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
            if key == "get_roles":
                await c.send(embed=make_embed(spec), view=RoleButtons())
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


@bot.tree.command(name="refresh-info", description="(staff) re-post the info channels from content.py")
@staff_only()
async def refresh_cmd(inter: discord.Interaction):
    await inter.response.send_message("refreshing… 🐾", ephemeral=True)
    chans = {}
    for key, cid in CFG["channels"].items():
        c = inter.guild.get_channel(cid)
        if c and key in C.POSTS and isinstance(c, discord.TextChannel):
            await c.purge(limit=50, check=lambda m: m.author == bot.user)
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
