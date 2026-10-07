"""
AI Look ("screen ESP", the fair kind): grabs what's on YOUR VRChat window and asks the AI
who it can see - nameplates, avatar looks, where they are on screen. It only reads the
picture you can already see (like a screenshot), never game memory, and it can't see
through walls. It runs only when you tap the button.
"""
import base64
import difflib
import io
import json
import re
import threading
import urllib.error

from PIL import Image

import ai
from zoom import vrchat_rect

try:
    import mss
    _MSS = getattr(mss, "MSS", None) or mss.mss
except Exception:
    _MSS = None

PROMPT = (
    "This is a screenshot of someone's VRChat view. List the other players' avatars you can SEE in the picture "
    "(max 8, nearest first). For each give: the name on their nameplate if you can read it (otherwise \"?\"), "
    "a very short avatar description (species/colors/outfit, under 8 words), and where they are "
    "(left/middle/right + close/far). Only describe avatars, never guess who a real person is. "
    "Reply ONLY with JSON like: {\"players\":[{\"name\":\"Kitsu\",\"look\":\"white fox, pink hoodie\",\"where\":\"middle, close\"}],"
    "\"vibe\":\"one short cute sentence about the scene\"}"
)


def grab_jpeg(monitor=1, max_w=1024):
    if _MSS is None:
        raise RuntimeError("screen capture isn't installed (pip install mss)")
    with _MSS() as sct:
        r = vrchat_rect()
        box = ({"left": r[0], "top": r[1], "width": r[2], "height": r[3]} if r
               else sct.monitors[min(monitor, len(sct.monitors) - 1)])
        shot = sct.grab(box)
    img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    if img.width > max_w:
        img = img.resize((max_w, round(img.height * max_w / img.width)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=72)
    return buf.getvalue()


def _parse(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except ValueError:
        return None


def match_name(name, instance_players):
    """Fix up a half-read nameplate using the players VRChat's log says are in the instance."""
    if not name or name.strip() in ("?", "") or not instance_players:
        return name, False
    exact = {p.lower(): p for p in instance_players}
    if name.lower() in exact:
        return exact[name.lower()], True
    close = difflib.get_close_matches(name.lower(), list(exact), n=1, cutoff=0.6)
    return (exact[close[0]], True) if close else (name, False)


def format_reply(data, instance_players):
    ps = (data or {}).get("players") or []
    if not ps:
        return "i don't see anyone on ur screen rn :3"
    lines = [f"i see {len(ps)} {'fluff' if len(ps) == 1 else 'fluffs'}:"]
    for p in ps[:8]:
        name, ok = match_name(str(p.get("name", "?")).strip(), instance_players)
        lines.append(f"• {name or '?'}{' ✓' if ok else ''} ({p.get('where', '?')}): {p.get('look', '')}".rstrip(": "))
    if data.get("vibe"):
        lines.append(str(data["vibe"])[:90])
    return "\n".join(lines)


def look_async(cfg, instance_players, on_done):
    def run():
        try:
            jpg = grab_jpeg(cfg.get("screen", {}).get("monitor", 1))
            text = ai.ask_image(cfg, PROMPT, base64.b64encode(jpg).decode())
            data = _parse(text)
            on_done(format_reply(data, instance_players) if data else (text or "")[:300], None)
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read().decode()).get("error", {})
                msg = msg.get("message", str(msg)) if isinstance(msg, dict) else str(msg)
            except Exception:
                msg = str(e)
            on_done(None, f"AI look error {e.code}: {msg}")
        except Exception as e:
            on_done(None, f"AI look error: {e}")
    threading.Thread(target=run, daemon=True, name="ai_look").start()
