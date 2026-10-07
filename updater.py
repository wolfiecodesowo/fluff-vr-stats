"""
Auto-updater: every launch, checks GitHub for a newer Fluff VR Stats release. If there is one it
downloads it, swaps in the new files and restarts, so nobody has to reinstall or touch their files.

Never touched: config.json (settings + AI key), bot/bot_config.json (bot token), logs/, and anything
else the user added that isn't part of the app. Replaced files are backed up in .update_backup/ first,
and if anything goes wrong mid-update the old files are put back.

Turn it off: config.json -> "auto_update": false
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "wolfiecodesowo/fluff-vr-stats"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
VERSION_FILE = os.path.join(HERE, "VERSION")
UA = {"User-Agent": "FluffVRStats-updater", "Accept": "application/vnd.github+json"}

# never overwrite or delete these (user data / secrets)
KEEP = {"config.json", "config.json.tmp", "bot/bot_config.json", "bot/bot_config.json.tmp", "VERSION.skip"}
KEEP_DIRS = ("logs/", ".update_backup/", "__pycache__/", ".git/")
# not needed on PC (website + Quest source), skip to keep updates small
SKIP_DIRS = ("docs/", "quest/", ".github/")


def local_version():
    try:
        with open(VERSION_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "v0.0.0"


def parse(v):
    out = []
    for part in v.strip().lstrip("vV").split("-")[0].split("."):
        try:
            out.append(int(part))
        except ValueError:
            out.append(0)
    return tuple(out + [0] * (3 - len(out)))


def latest_release(timeout=5):
    req = urllib.request.Request(API, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _download(url, progress=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"]})
    with urllib.request.urlopen(req, timeout=60) as r:
        total = int(r.headers.get("Content-Length") or 0)
        buf, got = io.BytesIO(), 0
        while True:
            chunk = r.read(64 * 1024)
            if not chunk:
                break
            buf.write(chunk)
            got += len(chunk)
            if progress:
                progress(got, total)
    return buf.getvalue()


def _skip(rel):
    rel = rel.replace("\\", "/")
    return (rel in KEEP or rel.startswith(KEEP_DIRS) or rel.startswith(SKIP_DIRS)
            or rel.endswith((".pyc",)))


def apply_zip(data, tag, status=None):
    """Unpacks the release over the app folder (keeping user files), with a backup + rollback."""
    zf = zipfile.ZipFile(io.BytesIO(data))
    names = [n for n in zf.namelist() if not n.endswith("/")]
    root = os.path.commonprefix(names).split("/")[0] + "/" if names else ""   # GitHub's "repo-tag/" folder
    tmp = tempfile.mkdtemp(prefix="fluffvr_update_")
    backup = os.path.join(HERE, ".update_backup", time.strftime("%Y%m%d-%H%M%S"))
    written, new_req = [], None
    try:
        zf.extractall(tmp)
        src_root = os.path.join(tmp, root)
        files = []
        for n in names:
            rel = n[len(root):]
            if rel and not _skip(rel):
                files.append(rel)
        old_req = _read(os.path.join(HERE, "requirements.txt"))
        for i, rel in enumerate(files):
            dst = os.path.join(HERE, rel)
            src = os.path.join(src_root, rel)
            if os.path.exists(dst):
                if _same(src, dst):
                    continue
                os.makedirs(os.path.dirname(os.path.join(backup, rel)), exist_ok=True)
                shutil.copy2(dst, os.path.join(backup, rel))
            os.makedirs(os.path.dirname(dst) or HERE, exist_ok=True)
            shutil.copy2(src, dst)
            written.append(rel)
            if status and i % 10 == 0:
                status(f"installing… {i + 1}/{len(files)}")
        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            f.write(tag)
        new_req = _read(os.path.join(HERE, "requirements.txt"))
        return written, (new_req != old_req)
    except Exception:
        # put the old files back so the app still starts
        for rel in written:
            b = os.path.join(backup, rel)
            try:
                if os.path.exists(b):
                    shutil.copy2(b, os.path.join(HERE, rel))
            except OSError:
                pass
        raise
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _read(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return b""


def _same(a, b):
    try:
        if os.path.getsize(a) != os.path.getsize(b):
            return False
        return _read(a) == _read(b)
    except OSError:
        return False


def _cleanup_backups(keep=3):
    d = os.path.join(HERE, ".update_backup")
    try:
        olds = sorted(os.listdir(d))[:-keep]
        for o in olds:
            shutil.rmtree(os.path.join(d, o), ignore_errors=True)
    except OSError:
        pass


class _Window:
    """small 'updating…' window (falls back to the console if Tk isn't there)"""

    def __init__(self, title):
        self.root = None
        try:
            import tkinter as tk
            self.root = tk.Tk()
            self.root.title("Fluff VR Stats :3")
            self.root.configure(bg="#22162e")
            self.root.resizable(False, False)
            tk.Label(self.root, text=title, font=("Segoe UI", 15, "bold"), fg="#fff5fc", bg="#22162e").pack(padx=30, pady=(22, 6))
            self.var = tk.StringVar(value="downloading…")
            tk.Label(self.root, textvariable=self.var, font=("Segoe UI", 11), fg="#d8c0e8", bg="#22162e").pack(padx=30, pady=(0, 22))
            self.root.update_idletasks()
            x = (self.root.winfo_screenwidth() - self.root.winfo_width()) // 2
            y = (self.root.winfo_screenheight() - self.root.winfo_height()) // 3
            self.root.geometry(f"+{x}+{y}")
            self.root.attributes("-topmost", True)
            self.root.update()
        except Exception:
            self.root = None
            print("  " + title)

    def set(self, text):
        if self.root:
            try:
                self.var.set(text)
                self.root.update()
            except Exception:
                pass
        else:
            print("  " + text)

    def close(self):
        if self.root:
            try:
                self.root.destroy()
            except Exception:
                pass


def check_and_update(cfg=None, restart=True, log=None):
    """Call at startup. Returns the new tag if it updated (and restarts the app when restart=True)."""
    cfg = cfg or {}
    if cfg.get("auto_update", True) is False or os.path.isdir(os.path.join(HERE, ".git")):
        return None                       # turned off, or it's a developer's git checkout
    try:
        rel = latest_release()
    except Exception as e:                # offline / GitHub down -> just start normally
        if log:
            log.info("update check skipped: %s", e)
        return None
    tag = rel.get("tag_name") or ""
    if not tag or parse(tag) <= parse(local_version()):
        return None
    url = rel.get("zipball_url") or f"https://github.com/{REPO}/archive/refs/tags/{tag}.zip"
    win = _Window(f"✨ updating to {tag}…")
    try:
        def prog(got, total):
            win.set(f"downloading… {got * 100 // total}%" if total else f"downloading… {got // 1024} KB")
        data = _download(url, prog)
        win.set("installing…")
        written, req_changed = apply_zip(data, tag, win.set)
        if req_changed:
            win.set("installing new parts (pip)…")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", os.path.join(HERE, "requirements.txt")],
                               timeout=600)
            except Exception:
                pass
        _cleanup_backups()
        win.set(f"done!! updated {len(written)} files :3 restarting…")
        if log:
            log.info("updated to %s (%d files)", tag, len(written))
        time.sleep(1.2)
    except Exception as e:
        win.set(f"update failed ({e}), starting the old version")
        if log:
            log.warning("update to %s failed: %s", tag, e)
        time.sleep(2)
        win.close()
        return None
    win.close()
    if restart:
        args = [sys.executable, os.path.join(HERE, "main.py")] + sys.argv[1:]
        if sys.platform == "win32":
            subprocess.Popen(args, cwd=HERE)
            os._exit(0)
        os.execv(sys.executable, args)
    return tag


def check_in_background(on_found):
    """While the app runs: tells it when a new release is out (it installs on next launch)."""
    def run():
        try:
            rel = latest_release(timeout=10)
            tag = rel.get("tag_name") or ""
            if tag and parse(tag) > parse(local_version()):
                on_found(tag)
        except Exception:
            pass
    threading.Thread(target=run, daemon=True, name="update-check").start()


if __name__ == "__main__":
    print("  Fluff VR Stats updater: you have", local_version())
    t = check_and_update(restart=False)
    print("  updated to " + t if t else "  you're on the latest version :3")
