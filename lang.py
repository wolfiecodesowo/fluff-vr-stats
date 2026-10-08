"""
Fluff VR Stats - translations.

How it works: every bit of text the app draws goes through LDraw.text(). When a
language other than English is picked (Settings -> Language), the English text
is looked up in lang/<code>.json and swapped for the translation. If a
translation is wider than the English, it shrinks a little so layouts stay tidy.
Languages that need other letters (Japanese, Korean, Chinese, Russian...) get a
font that has them (Windows ships these, so nothing extra to download).

Add or fix a translation: edit lang/<code>.json ("english": "translation").
Missing lines just stay English. `python tools/lang_check.py` lists what's missing.
"""
import json
import os
import re
from functools import lru_cache

from PIL import ImageDraw as _PILDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
LANG_DIR = os.path.join(HERE, "lang")

# (code, name in its own language)
LANGS = [
    ("en", "English"),
    ("ja", "日本語"),
    ("ko", "한국어"),
    ("zh", "简体中文"),
    ("es", "Español"),
    ("pt", "Português"),
    ("fr", "Français"),
    ("de", "Deutsch"),
    ("it", "Italiano"),
    ("pl", "Polski"),
    ("ru", "Русский"),
    ("uk", "Українська"),
]
CODES = [c for c, _ in LANGS]
NAMES = dict(LANGS)

# fonts that have the letters each script needs: Windows first, then common Linux/Noto paths
_WIN = r"C:\Windows\Fonts"
_NOTO = "/usr/share/fonts/opentype/noto"
SCRIPT_FONTS = {
    "ja": [(_WIN, "YuGothB.ttc"), (_WIN, "meiryob.ttc"), (_WIN, "msgothic.ttc"), (_NOTO, "NotoSansCJK-Bold.ttc"),
           (_NOTO, "NotoSansCJK-Regular.ttc")],
    "ko": [(_WIN, "malgunbd.ttf"), (_WIN, "malgun.ttf"), (_NOTO, "NotoSansCJK-Bold.ttc"),
           (_NOTO, "NotoSansCJK-Regular.ttc")],
    "zh": [(_WIN, "msyhbd.ttc"), (_WIN, "msyh.ttc"), (_WIN, "simhei.ttf"), (_NOTO, "NotoSansCJK-Bold.ttc"),
           (_NOTO, "NotoSansCJK-Regular.ttc")],
    "cyr": [(os.path.join(HERE, "fonts"), "Nunito-Bold.ttf"), (_WIN, "seguisb.ttf"), (_WIN, "segoeuib.ttf"),
            ("/usr/share/fonts/truetype/dejavu", "DejaVuSans-Bold.ttf")],     # first one that really has Cyrillic
}
# which face inside a .ttc collection has the right glyph shapes for that language
_TTC_INDEX = {("ja", "NotoSansCJK-Bold.ttc"): 0, ("ja", "NotoSansCJK-Regular.ttc"): 0,
              ("ko", "NotoSansCJK-Bold.ttc"): 1, ("ko", "NotoSansCJK-Regular.ttc"): 1,
              ("zh", "NotoSansCJK-Bold.ttc"): 2, ("zh", "NotoSansCJK-Regular.ttc"): 2}

_CJK = re.compile(r"[\u3000-\u30ff\u3400-\u9fff\uf900-\ufaff\uff00-\uffef]")
_HANGUL = re.compile(r"[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]")
_CYR = re.compile(r"[\u0400-\u04ff]")
_KANA = re.compile(r"[\u3040-\u30ff]")

_cur = "en"
_table = {}
_lower = {}
_record = None          # set of strings seen (for tools/lang_check.py --record)


def load_table(code):
    path = os.path.join(LANG_DIR, f"{code}.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if isinstance(v, str) and v and not k.startswith("_")}
    except (OSError, ValueError):
        return {}


def set_lang(code):
    """Switch the whole app's language. Unknown codes fall back to English."""
    global _cur, _table, _lower
    code = code if code in CODES else "en"
    _cur = code
    _table = load_table(code) if code != "en" else {}
    _lower = {k.lower(): v for k, v in _table.items()}
    _fit_font.cache_clear()


def current():
    return _cur


def next_lang(code):
    i = CODES.index(code) if code in CODES else 0
    return CODES[(i + 1) % len(CODES)]


def tr(text):
    """English -> current language. Exact match first, then ignoring case
    (a lowercased label gets the translation lowercased too, for Latin scripts)."""
    if _record is not None and isinstance(text, str):
        _record.add(text)
    if _cur == "en" or not isinstance(text, str) or not text:
        return text
    v = _table.get(text)
    if v is not None:
        return v
    v = _lower.get(text.lower())
    if v is not None:
        return v.lower() if text.islower() else v
    # keep leading/trailing spaces + punctuation, translate the middle ("  hello!  ")
    m = re.match(r"^(\W*)(.*?)(\W*)$", text, re.S)
    if m and m.group(2) and (m.group(1) or m.group(3)):
        core = m.group(2)
        v = _table.get(core) or _lower.get(core.lower())
        if v is not None:
            return m.group(1) + (v.lower() if core.islower() else v) + m.group(3)
    return text


def trf(text, **kw):
    """Translate a template then fill it: trf("{n} pats today", n=4)."""
    try:
        return tr(text).format(**kw)
    except (KeyError, IndexError, ValueError):
        return text.format(**kw)


def _script_of(text):
    if _HANGUL.search(text):
        return "ko"
    if _CJK.search(text):
        if _KANA.search(text):
            return "ja"
        return _cur if _cur in ("ja", "zh") else "zh"
    if _CYR.search(text):
        return "cyr"
    return None


@lru_cache(maxsize=24)
def _script_font_path(script):
    for d, name in SCRIPT_FONTS.get(script, []):
        p = os.path.join(d, name)
        idx = _TTC_INDEX.get((script, name), 0)
        if os.path.exists(p) and _covers(p, idx, script):
            return p, idx
    return None


@lru_cache(maxsize=256)
def _fit_font(path, index, size):
    try:
        return ImageFont.truetype(path, size, index=index)
    except Exception:
        return None


_SAMPLE = {"cyr": "ДЖя", "ja": "あ日", "ko": "한", "zh": "中"}


@lru_cache(maxsize=64)
def _covers(path, index, script):
    """does this font really have the letters? (missing ones all draw the same 'tofu' box)"""
    try:
        f = ImageFont.truetype(path, 24, index=index)
        missing = bytes(f.getmask("\U0010FFFD"))
        return all(bytes(f.getmask(ch)) != missing for ch in _SAMPLE.get(script, "A"))
    except Exception:
        return False


def font_for_text(text, fnt):
    """The given font, or one with the right letters if the text uses another script."""
    script = _script_of(text)
    if not script:
        return fnt
    path = getattr(fnt, "path", None)
    if path and _covers(str(path), getattr(fnt, "index", 0) or 0, script):
        return fnt
    got = _script_font_path(script)
    size = getattr(fnt, "size", 16)
    if not got:
        return fnt
    # CJK fonts sit a bit bigger than the cute latin fonts: nudge them down so lines don't crowd
    adj = 0.9 if script in ("ja", "ko", "zh") else 1.0
    return _fit_font(got[0], got[1], max(8, int(round(size * adj)))) or fnt


def _shrink(text, fnt, max_w):
    """same font, smaller, until it fits max_w (never below 70%)"""
    path = getattr(fnt, "path", None)
    size = getattr(fnt, "size", None)
    if not path or not size:
        return fnt
    idx = getattr(fnt, "index", 0) if hasattr(fnt, "index") else 0
    s = size
    f = fnt
    while s > max(8, size * 0.7) and f.getlength(text) > max_w:
        s -= 1
        f = _fit_font(path, idx, s) or f
    return f


class LDraw(_PILDraw.ImageDraw):
    """ImageDraw that translates + picks a font with the right letters."""

    def text(self, xy, text, fill=None, font=None, anchor=None, *args, **kwargs):
        if isinstance(text, str) and text:
            orig = text
            if _cur != "en" or _record is not None:
                text = tr(text)
            if font is not None and hasattr(font, "getlength"):
                f2 = font_for_text(text, font)
                if text != orig:
                    try:
                        ew = font.getlength(orig)
                        room = max(ew * 1.5, ew + 40)     # translations can be a bit wider, then they shrink
                        if ew > 24 and f2.getlength(text) > room:
                            f2 = _shrink(text, f2, room)
                    except Exception:
                        pass
                font = f2
        return super().text(xy, text, fill, font, anchor, *args, **kwargs)


    def raw_text(self, xy, text, fill=None, font=None, anchor=None, *args, **kwargs):
        """draw exactly this text (no translating, no font swap)"""
        return super().text(xy, text, fill, font, anchor, *args, **kwargs)


class ImageDrawShim:
    """Drop-in for `PIL.ImageDraw` inside the UI modules: Draw() gives an LDraw."""

    @staticmethod
    def Draw(im, mode=None):
        return LDraw(im, mode)

    def __getattr__(self, name):
        return getattr(_PILDraw, name)


ImageDraw = ImageDrawShim()


def start_recording():
    global _record
    _record = set()
    return _record
