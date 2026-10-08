"""
Translation helper.

    python tools/lang_check.py            how much of each language is done + what's missing
    python tools/lang_check.py --record   re-collect every English line the app draws -> lang/_strings.json
    python tools/lang_check.py --missing ja   print the missing lines for one language (copy into lang/ja.json)

Want to help translate? Open lang/<code>.json, add  "english line": "ur translation",  and send a PR
or post it in the Discord. Lines u skip just stay English.
"""
import ast
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
os.chdir(HERE)
import lang  # noqa: E402

STRINGS = os.path.join(lang.LANG_DIR, "_strings.json")
SKIP = re.compile(r"^[\W\d_]*$|^[a-z0-9_]+\.[a-z]{2,4}$|^https?://|^#|^[A-Z0-9_]{2,}$|^v\d")


def static_strings():
    out = set()
    import fun
    import kitty
    import ui
    import main
    for cat in ui.MOD_CATS:
        out.add(cat)
        for _, name, desc in ui.MOD_INFO[cat]:
            out.update((name, desc))
    for b in fun.BADGES:
        out.update((b[2], b[3]))
    for i in fun.ITEMS:
        out.add(i[2])
    for s in fun.SEASONS.values():
        out.update((s["name"], s["banner"]))
    for lines in kitty.LINES.values():
        out.update(lines)
    out.update(main.LUCKY)
    out.update(main.BREAK_MSGS)
    for _, lab in ui.WRIST_ACTIONS.values():
        out.add(lab)
    # every show_alert("literal") / lang.tr("literal") in the app
    for fn in ("main.py", "desktop.py", "ui_fun.py", "fun.py", "fluffnet.py", "gchat.py"):
        tree = ast.parse(open(os.path.join(HERE, fn), encoding="utf-8").read())
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
                name = getattr(n.func, "attr", None) or getattr(n.func, "id", None)
                if name in ("show_alert", "tr", "_tr", "trf", "open_keyboard"):
                    out.add(n.args[0].value)
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str) \
                    and any(getattr(t, "attr", getattr(t, "id", "")) == "status" for t in n.targets):
                out.add(n.value.value)
    return out


def record():
    seen = lang.start_recording()
    import subprocess
    import tempfile
    tmp = tempfile.mkdtemp()
    # run the preview (renders every tab) in this process so the recorder sees it
    sys.argv = ["preview.py", tmp]
    try:
        import runpy
        runpy.run_path(os.path.join(HERE, "preview.py"), run_name="__main__")
    except SystemExit:
        pass
    allstr = {s for s in seen | static_strings() if isinstance(s, str)}
    keep = sorted(s for s in allstr if s.strip() and not SKIP.match(s.strip()) and len(s) < 700
                  and re.search(r"[A-Za-z]{2}", s) and not s.endswith("…") and "\n" not in s
                  and not re.search(r"\b\d+/\d+\b|^\d+ |\d+:\d\d", s))
    full = set(keep)

    def fragment(x):      # a piece of a longer line that got word-wrapped (the long line is what gets translated)
        if len(x.split()) < 3:
            return False
        return any(L != x and (L.startswith(x + " ") or L.endswith(" " + x) or (" " + x + " ") in L) for L in full)
    keep = [x for x in keep if not fragment(x)]
    try:      # names, theme names + preview data that stay English on purpose
        stay = set(json.load(open(os.path.join(lang.LANG_DIR, "_keep_english.json"), encoding="utf-8")))
        keep = [x for x in keep if x not in stay]
    except (OSError, ValueError):
        pass
    with open(STRINGS, "w", encoding="utf-8") as f:
        json.dump(keep, f, indent=1, ensure_ascii=False)
    print(f"  {len(keep)} lines -> lang/_strings.json")
    del subprocess


def report(only=None):
    try:
        want = json.load(open(STRINGS, encoding="utf-8"))
    except OSError:
        print("  run with --record first")
        return
    for code, name in lang.LANGS[1:]:
        if only and code != only:
            continue
        have = lang.load_table(code)
        missing = [s for s in want if s not in have]
        pct = 100 * (len(want) - len(missing)) / max(1, len(want))
        print(f"  {code} {name:12s} {pct:5.1f}%  ({len(missing)} missing)")
        if only:
            print(json.dumps({m: "" for m in missing}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    if "--record" in sys.argv:
        record()
    elif "--missing" in sys.argv:
        report(sys.argv[sys.argv.index("--missing") + 1])
    else:
        report()
