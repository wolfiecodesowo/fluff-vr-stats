"""
Fluff VR Stats - YouTube search (v0.5). Search right from the menu, then:
  copy link  -> paste it into any world's video player (click the URL box in VRChat, Ctrl+V)
  open       -> plays on ur desktop (shows up in the Screen tab + Music tab controls)
  chatbox    -> "🎥 watching: <title>" in ur chatbox

No API key, no account: it asks YouTube's own website search, like a browser does.
"""
import json
import re
import threading
import time
import urllib.request

SEARCH_URL = "https://www.youtube.com/youtubei/v1/search?prettyPrint=false"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36")


def _text(node):
    if not node:
        return ""
    if "simpleText" in node:
        return node["simpleText"]
    return "".join(r.get("text", "") for r in node.get("runs", []))


def _walk(obj, key):
    """every value stored under `key` anywhere inside YouTube's (deeply nested) reply"""
    stack = [obj]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            for k, v in o.items():
                if k == key:
                    yield v
                elif isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(o, list):
            stack.extend(reversed(o))


def _dig(o, *keys):
    for k in keys:
        if isinstance(o, dict):
            o = o.get(k)
        elif isinstance(o, list) and isinstance(k, int) and len(o) > k:
            o = o[k]
        else:
            return None
    return o


def _newer_layouts(data):
    """YouTube A/B tests newer layouts (~1 in 4 searches): Shorts lockups + lockupViewModel videos"""
    out = []
    for v in _walk(data, "shortsLockupViewModel"):
        vid = _dig(v, "onTap", "innertubeCommand", "reelWatchEndpoint", "videoId")
        title = _dig(v, "overlayMetadata", "primaryText", "content") or (v.get("accessibilityText") or "").split(", ")[0]
        if vid and title:
            out.append({"id": vid, "title": title, "channel": "Shorts", "length": "SHORT",
                        "views": _dig(v, "overlayMetadata", "secondaryText", "content") or "",
                        "thumb": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg", "url": f"https://www.youtube.com/watch?v={vid}"})
    for v in _walk(data, "lockupViewModel"):
        vid = v.get("contentId")
        if not vid or "VIDEO" not in str(v.get("contentType", "VIDEO")):
            continue
        md = _dig(v, "metadata", "lockupMetadataViewModel") or {}
        rows = _dig(md, "metadata", "contentMetadataViewModel", "metadataRows") or []
        parts = [p.get("text", {}).get("content", "") for r in rows for p in (r.get("metadataParts") or [])]
        out.append({"id": vid, "title": _dig(md, "title", "content") or "", "channel": parts[0] if parts else "",
                    "length": "", "views": parts[1] if len(parts) > 1 else "",
                    "thumb": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg", "url": f"https://www.youtube.com/watch?v={vid}"})
    return out


def parse_results(data, limit=12):
    out = []
    for v in _walk(data, "videoRenderer"):
        vid = v.get("videoId")
        if not vid or any(r["id"] == vid for r in out):
            continue
        live = any("LIVE" in json.dumps(b) for b in v.get("badges", [])) or not v.get("lengthText")
        out.append({
            "id": vid,
            "title": _text(v.get("title")),
            "channel": _text(v.get("ownerText") or v.get("longBylineText")),
            "length": "LIVE" if live else _text(v.get("lengthText")),
            "views": _text(v.get("shortViewCountText") or v.get("viewCountText")),
            "thumb": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
            "url": f"https://www.youtube.com/watch?v={vid}",
        })
        if len(out) >= limit:
            break
    for r in _newer_layouts(data):          # fill up from the newer layouts (or use only them if that's all we got)
        if len(out) >= limit:
            break
        if r["title"] and not any(x["id"] == r["id"] for x in out):
            out.append(r)
    return out


def search(query, limit=12, timeout=10):
    res = _search_once(query, limit, timeout)
    return res or _search_once(query, limit, timeout)       # rare empty answer: ask once more


def _search_once(query, limit=12, timeout=10):
    body = json.dumps({"context": {"client": {"clientName": "WEB", "clientVersion": "2.20240101.00.00",
                                              "hl": "en", "gl": "US"}},
                       "query": query}).encode("utf-8")
    req = urllib.request.Request(SEARCH_URL, data=body, headers={"Content-Type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return parse_results(json.loads(r.read().decode("utf-8")), limit)


def is_url(text):
    return bool(re.match(r"^\s*(https?://)?(www\.|m\.)?(youtube\.com|youtu\.be)/", text or ""))


class YouTube:
    """Search in the background so the menu never freezes; thumbnails load one by one."""

    def __init__(self, log=None):
        self.log = log
        self.query, self.results, self.status = "", [], ""
        self.thumbs = {}            # id -> PIL image
        self.page = 0
        self.busy = False
        self.changed = False
        self.picked = None
        self.history = []           # recent searches

    def search(self, query):
        query = (query or "").strip()
        if not query or self.busy:
            return
        self.query, self.busy, self.status, self.page = query, True, "searching…", 0
        self.history = ([query] + [h for h in self.history if h != query])[:6]
        threading.Thread(target=self._work, args=(query,), daemon=True).start()

    def _work(self, query):
        try:
            res = search(query)
            self.results = res
            self.status = f"{len(res)} results" if res else "no results ~ try other words"
        except Exception as e:
            self.results = []
            self.status = "couldn't reach YouTube (offline?)"
            if self.log:
                self.log.warning("youtube search failed: %s", e)
        self.busy = False
        self.changed = True
        for r in list(self.results):
            if r["id"] in self.thumbs:
                continue
            try:
                from PIL import Image
                import io
                with urllib.request.urlopen(urllib.request.Request(r["thumb"], headers={"User-Agent": UA}), timeout=8) as f:
                    self.thumbs[r["id"]] = Image.open(io.BytesIO(f.read())).convert("RGBA")
                self.changed = True
            except Exception:
                pass
            time.sleep(0.05)
