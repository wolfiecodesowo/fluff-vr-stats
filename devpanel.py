"""
Fluff VR Stats - dev panel (owner only): kick / mute / ban people in global chat.

How it stays owner-only (even though the app is open source):
  - Every command is signed with the "mod" key. Its private half only exists on the owner's PC
    (~/.fluffvr/mod_key.pem, made by tools/make_mod_key.py) and is encrypted with the owner's password.
  - Fluff Bot checks the signature against trust.json and ignores anything else, so reading this file,
    or posting to ntfy by hand, doesn't let anyone moderate.
  - Commands expire after 5 minutes and can't be sent twice (so nobody can replay an old one).

Fluff Bot does the actual kick/mute/ban, so it works on every app version (PC, desktop, Quest, even old
v1 apps), and announces it publicly in the app's global chat as "Fluff Mod" (not in Discord).
Staff keys later: tools/make_mod_key.py --staff NAME, then the panel opens with that key's password.

Open it: Desktop window -> Dev menu (only shows on a PC that has the key), or tools/dev_panel.bat.
"""
import glob
import json
import os
import sys
import threading
import time
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gchat as G  # noqa: E402
import trust  # noqa: E402

KEY_DIR = os.path.join(os.path.expanduser("~"), ".fluffvr")
KEY_FILE = os.path.join(KEY_DIR, "mod_key.pem")
AUTO_LOCK_S = 20 * 60
UA = {"User-Agent": "FluffVRStats-devpanel"}
MUTE_CHOICES = (("5 min", 5), ("15 min", 15), ("1 hour", 60), ("1 day", 1440), ("1 week", 10080), ("no end", 0))

BG, CARD, FG, SUB = "#160e22", "#22162e", "#fff5fc", "#d8c0e8"
PINK, PURPLE, YELLOW, RED, GREEN = "#ff96ca", "#b58cff", "#ffe246", "#ff6b6b", "#7ee0a0"


def key_files():
    """this PC's mod keys: [(label, path)], the owner's first"""
    out = [("owner", KEY_FILE)] if os.path.exists(KEY_FILE) else []
    for p in sorted(glob.glob(os.path.join(KEY_DIR, "mod_key_*.pem"))):
        out.append((os.path.basename(p)[8:-4], p))
    return out


def available():
    """True on a PC that has a mod key (that's the only place the panel shows up)"""
    return trust.HAVE_CRYPTO and bool(key_files())


def make_command(key, action, **fields):
    p = {"v": 2, "t": "mod", "a": action, "ts": int(time.time()), "nonce": uuid.uuid4().hex}
    for k, v in fields.items():
        if v not in (None, ""):
            p[k] = int(v) if isinstance(v, float) else v
    return trust.sign_payload(key, p)


def post(payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(f"{G.BASE}/{G.INBOX2}", data=body, method="POST",
                                 headers=dict(UA, **{"Content-Type": "text/plain; charset=utf-8"}))
    with urllib.request.urlopen(req, timeout=10) as r:
        r.read()


class Panel:
    def __init__(self):
        import tkinter as tk
        from tkinter import ttk
        self.tk, self.ttk = tk, ttk
        self.key = None
        self.key_label = ""
        self.last_use = time.time()
        self.pending = {}                      # nonce -> what we asked for
        self.acks = []                         # (ok, msg) from the ack listener thread
        self.selected = None                   # chat message dict
        self.chat = None
        self.chat_ver = -1
        self.shown = []

        self.root = tk.Tk()
        self.root.title("Fluff dev panel")
        self.root.configure(bg=BG)
        self.root.minsize(860, 560)
        try:
            from PIL import Image, ImageTk
            self._icon = ImageTk.PhotoImage(Image.open(os.path.join(HERE, "assets", "logo.gif")).convert("RGBA").resize((64, 64)))
            self.root.iconphoto(True, self._icon)
        except Exception:
            pass
        st = ttk.Style(self.root)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("TCombobox", fieldbackground=CARD, background=CARD, foreground=FG)
        self.frame = None
        self.show_lock()

    # ------------------------------------------------------------------ helpers
    def lbl(self, parent, text, size=10, bold=False, fg=FG, bg=CARD, **kw):
        return self.tk.Label(parent, text=text, font=("Segoe UI", size, "bold" if bold else "normal"),
                             fg=fg, bg=bg, **kw)

    def btn(self, parent, text, cmd, color=PINK, width=12):
        return self.tk.Button(parent, text=text, command=cmd, font=("Segoe UI", 10, "bold"), width=width,
                              bg=color, fg="#180e22", activebackground=YELLOW, relief="flat", cursor="hand2")

    def entry(self, parent, width=24, show=None):
        return self.tk.Entry(parent, width=width, show=show, font=("Segoe UI", 10), bg="#382650", fg=FG,
                             insertbackground=FG, relief="flat")

    def clear(self):
        if self.frame is not None:
            self.frame.destroy()
        self.frame = self.tk.Frame(self.root, bg=BG)
        self.frame.pack(fill="both", expand=True)
        return self.frame

    # ------------------------------------------------------------------ lock screen
    def show_lock(self, why=""):
        tk = self.tk
        self.key = None
        f = self.clear()
        box = tk.Frame(f, bg=CARD, padx=30, pady=24)
        box.place(relx=0.5, rely=0.45, anchor="center")
        self.lbl(box, "🛡️ Fluff dev panel", 18, True).pack()
        keys = key_files()
        if not trust.HAVE_CRYPTO:
            self.lbl(box, "needs the cryptography package ~ run install.bat", fg=RED).pack(pady=12)
            return
        if not keys:
            self.lbl(box, "no mod key on this PC.\nthe owner makes one with tools/make_mod_key.bat", fg=SUB,
                     justify="center").pack(pady=12)
            return
        if not trust.mod_key_names():
            self.lbl(box, "⚠️ trust.json has no \"mod\" key yet, so Fluff Bot won't listen.\n"
                          "run tools/make_mod_key.bat, then push trust.json + restart the bot", fg=YELLOW,
                     justify="center").pack(pady=(8, 0))
        self.lbl(box, why or "owner only ~ type ur password", fg=RED if why else SUB).pack(pady=(10, 6))
        self.which = tk.StringVar(value=keys[0][0])
        if len(keys) > 1:
            self.ttk.Combobox(box, textvariable=self.which, values=[k[0] for k in keys], state="readonly",
                              width=20).pack(pady=4)
        pw = self.entry(box, 28, show="•")
        pw.pack(pady=6, ipady=4)
        pw.focus_set()
        msg = self.lbl(box, "", fg=SUB)

        def unlock(_=None):
            path = dict(keys).get(self.which.get(), keys[0][1])
            secret = pw.get()
            pw.delete(0, "end")
            msg.config(text="checking…", fg=SUB)
            go.config(state="disabled")

            def work():
                from cryptography.hazmat.primitives import serialization
                try:
                    k = trust.load_private(path, secret)
                    pub = trust.b64e(k.public_key().public_bytes(serialization.Encoding.DER,
                                                                 serialization.PublicFormat.SubjectPublicKeyInfo))
                    known = pub in [trust.trust_keys().get(n) for n in trust.mod_key_names()]
                    self.root.after(0, self.unlocked, k, self.which.get(), known)
                except (ValueError, TypeError):
                    time.sleep(1.5)                         # slows down password guessing
                    self.root.after(0, lambda: (msg.config(text="wrong password", fg=RED), go.config(state="normal")))
                except Exception as e:
                    self.root.after(0, lambda: (msg.config(text=f"couldn't open the key: {e}"[:80], fg=RED),
                                                go.config(state="normal")))
            threading.Thread(target=work, daemon=True).start()
        go = self.btn(box, "🔓 unlock", unlock, width=14)
        go.pack(pady=6)
        msg.pack()
        pw.bind("<Return>", unlock)

    def unlocked(self, key, label, known):
        self.key, self.key_label, self.last_use = key, label, time.time()
        self.show_main()
        if not known:
            self.log("⚠️ this key isn't in this app's trust.json ~ push trust.json + restart Fluff Bot or it "
                     "won't listen", YELLOW)
        self.send("ping")

    # ------------------------------------------------------------------ main screen
    def show_main(self):
        tk = self.tk
        f = self.clear()
        top = tk.Frame(f, bg=BG)
        top.pack(fill="x", padx=14, pady=(12, 6))
        self.lbl(top, "🛡️ Fluff dev panel", 16, True, bg=BG).pack(side="left")
        self.lbl(top, f"  · {self.key_label}", 11, fg=SUB, bg=BG).pack(side="left")
        self.btn(top, "🔒 lock", lambda: self.show_lock("locked"), PURPLE, 8).pack(side="right")
        self.status = self.lbl(top, "global chat: connecting…", 10, fg=SUB, bg=BG)
        self.status.pack(side="right", padx=12)

        body = tk.Frame(f, bg=BG)
        body.pack(fill="both", expand=True, padx=14)
        # left: live global chat
        left = tk.Frame(body, bg=CARD, padx=10, pady=8)
        left.pack(side="left", fill="both", expand=True)
        self.lbl(left, "live global chat ~ click a message to pick who", 10, True).pack(anchor="w")
        lf = tk.Frame(left, bg=CARD)
        lf.pack(fill="both", expand=True, pady=(6, 0))
        sb = tk.Scrollbar(lf)
        sb.pack(side="right", fill="y")
        self.list = tk.Listbox(lf, font=("Segoe UI", 10), bg="#1c1228", fg=FG, selectbackground=PURPLE,
                               selectforeground="#180e22", relief="flat", activestyle="none", yscrollcommand=sb.set)
        self.list.pack(side="left", fill="both", expand=True)
        sb.config(command=self.list.yview)
        self.list.bind("<<ListboxSelect>>", self.on_pick)

        # right: actions
        right = tk.Frame(body, bg=CARD, padx=12, pady=8, width=330)
        right.pack(side="right", fill="y", padx=(10, 0))
        self.lbl(right, "who", 10, True).pack(anchor="w")
        self.target = self.lbl(right, "nobody picked yet", 10, fg=SUB, wraplength=300, justify="left")
        self.target.pack(anchor="w", pady=(0, 4))
        self.lbl(right, "or type their sid / Discord user id:", 9, fg=SUB).pack(anchor="w")
        self.manual = self.entry(right, 30)
        self.manual.pack(anchor="w", ipady=3, pady=(0, 8))
        self.lbl(right, "reason (shown publicly):", 9, fg=SUB).pack(anchor="w")
        self.reason = self.entry(right, 30)
        self.reason.pack(anchor="w", ipady=3, pady=(0, 8))
        row = tk.Frame(right, bg=CARD)
        row.pack(anchor="w", pady=(0, 8))
        self.lbl(row, "mute for:", 9, fg=SUB).pack(side="left")
        self.mute_for = tk.StringVar(value="15 min")
        self.ttk.Combobox(row, textvariable=self.mute_for, values=[m[0] for m in MUTE_CHOICES], state="readonly",
                          width=10).pack(side="left", padx=6)

        grid = tk.Frame(right, bg=CARD)
        grid.pack(anchor="w", pady=4)
        acts = (("👢 kick", "kick", PINK), ("🔇 mute", "mute", PURPLE), ("🔊 unmute", "unmute", GREEN),
                ("🔨 ban", "ban", RED), ("✅ unban", "unban", GREEN), ("🗑️ delete msg", "del", YELLOW))
        for i, (txt, a, c) in enumerate(acts):
            self.btn(grid, txt, lambda a=a: self.act(a), c, 13).grid(row=i // 2, column=i % 2, padx=3, pady=3)
        self.lbl(right, "kick = their recent msgs vanish + 10 min out", 8, fg=SUB).pack(anchor="w", pady=(2, 10))

        self.lbl(right, "say something as Fluff Mod:", 9, fg=SUB).pack(anchor="w")
        self.say = self.entry(right, 30)
        self.say.pack(anchor="w", ipady=3)
        self.say.bind("<Return>", lambda e: self.act("say"))
        self.btn(right, "📢 post in app chat", lambda: self.act("say"), PINK, 18).pack(anchor="w", pady=6)

        # bottom: what happened
        logf = tk.Frame(f, bg=CARD, padx=10, pady=6)
        logf.pack(fill="x", padx=14, pady=10)
        self.logbox = tk.Text(logf, height=6, font=("Consolas", 9), bg="#1c1228", fg=FG, relief="flat",
                              state="disabled", wrap="word")
        self.logbox.pack(fill="x")
        for name, color in (("ok", GREEN), ("bad", RED), ("warn", YELLOW), ("info", SUB)):
            self.logbox.tag_config(name, foreground=color)

        if self.chat is None:
            self.start_listeners()
        self.chat_ver = -1
        self.gen = getattr(self, "gen", 0) + 1         # one tick loop per unlock
        self.tick(self.gen)

    def log(self, text, color=SUB):
        tag = {GREEN: "ok", RED: "bad", YELLOW: "warn"}.get(color, "info")
        try:
            self.logbox.config(state="normal")
            self.logbox.insert("end", time.strftime("%H:%M:%S ") + text + "\n", tag)
            self.logbox.see("end")
            self.logbox.config(state="disabled")
        except Exception:
            pass

    def on_pick(self, _=None):
        sel = self.list.curselection()
        if not sel or sel[0] >= len(self.shown):
            return
        m = self.shown[sel[0]]
        self.selected = m
        self.manual.delete(0, "end")
        self.target.config(text=f"{m['name']} ({m['client']}) · sid {m['sid'] or '?'}\n“{m['text'][:80]}”", fg=FG)

    def target_fields(self):
        manual = self.manual.get().strip()
        if manual:
            return {"uid": manual} if manual.isdigit() and len(manual) >= 15 else {"sid": manual[:16]}, manual
        m = self.selected
        if not m:
            return None, None
        return {"mid": m["id"], "sid": m["sid"]}, m["name"]

    def act(self, a):
        from tkinter import messagebox
        self.last_use = time.time()
        if a == "say":
            text = self.say.get().strip()
            if not text:
                return
            self.say.delete(0, "end")
            return self.send("say", text=text[:G.MAX_LEN])
        fields, who = self.target_fields()
        if a == "del":
            if not self.selected or self.manual.get().strip():
                return self.log("pick a message in the chat list to delete it", YELLOW)
            return self.send("del", mid=self.selected["id"])
        if not fields:
            return self.log("pick someone first (click one of their messages)", YELLOW)
        if fields.get("sid") == "fluffmod":
            return self.log("that's a Fluff Mod notice, pick a person :3", YELLOW)
        why = self.reason.get().strip()[:100]
        mins = dict(MUTE_CHOICES).get(self.mute_for.get(), 15)
        if a == "ban" and not messagebox.askyesno("ban?", f"ban {who} from global chat on every device?\n"
                                                           "(everyone sees it in chat)", parent=self.root):
            return
        self.send(a, why=why, mins=mins if a == "mute" else None, **fields)

    def send(self, a, **fields):
        if self.key is None:
            return
        try:
            p = make_command(self.key, a, **fields)
        except Exception as e:
            return self.log(f"couldn't sign: {e}", RED)
        self.pending[p["nonce"]] = (a, time.time())
        if a != "ping":
            self.log(f"→ {a} sent, waiting for Fluff Bot…")

        def go():
            try:
                post(p)
            except Exception as e:
                self.acks.append((False, f"couldn't send {a}: {e}"))
        threading.Thread(target=go, daemon=True).start()

    # ------------------------------------------------------------------ background
    def start_listeners(self):
        cfg = {"modules": {"global_chat": True}, "gchat": {"sid": "devpanel00", "muted": [], "name": "devpanel"}}
        self.chat = G.GlobalChat(cfg, client="dev", on_message=lambda m: m.get("fx") and
                                 time.time() - m["time"] < G.FX_FRESH_S and G.play_fx(m["fx"]))
        threading.Thread(target=self.ack_loop, daemon=True, name="modack").start()

    def ack_loop(self):
        since = "1m"
        while True:
            try:
                req = urllib.request.Request(f"{G.BASE}/{G.MODACK2}/json?since={since}", headers=UA)
                with urllib.request.urlopen(req, timeout=75) as r:
                    for line in r:
                        try:
                            ev = json.loads(line.decode("utf-8", "ignore"))
                            if ev.get("event") != "message":
                                continue
                            since = ev.get("id") or since
                            p = json.loads(ev.get("message", ""))
                        except ValueError:
                            continue
                        if not isinstance(p, dict) or not trust.verify_payload("bot", p):
                            continue
                        n = p.get("nonce")
                        if n in self.pending:
                            a, _ = self.pending.pop(n)
                            self.acks.append((bool(p.get("ok")), ("✓ " if p.get("ok") else "✗ ") + str(p.get("msg", ""))))
            except Exception:
                time.sleep(3)

    def tick(self, gen):
        if self.key is None or gen != self.gen:
            return
        if time.time() - self.last_use > AUTO_LOCK_S:
            return self.show_lock("locked after 20 min of no use")
        while self.acks:
            ok, msg = self.acks.pop(0)
            self.log(msg, GREEN if ok else RED)
        now = time.time()
        for n, (a, t0) in list(self.pending.items()):
            if now - t0 > 20:
                self.pending.pop(n, None)
                self.log(f"✗ Fluff Bot didn't answer the {a} (is it running + up to date?)", RED)
        c = self.chat
        st = {"live": ("● global chat live", GREEN), "offline": ("● global chat offline", RED)}.get(
            c.status, ("● global chat connecting…", SUB))
        self.status.config(text=st[0], fg=st[1])
        ver = (len(c.msgs), c.msgs[-1]["id"] if c.msgs else None)
        if ver != self.chat_ver:
            self.chat_ver = ver
            keep = self.selected["id"] if self.selected else None
            at_bottom = self.list.yview()[1] > 0.98
            self.shown = list(c.msgs)
            self.list.delete(0, "end")
            for i, m in enumerate(self.shown):
                tag = "🛡️ " if m["sid"] == "fluffmod" else "👑 " if m.get("role") == "owner" else ""
                self.list.insert("end", f"{time.strftime('%H:%M', time.localtime(m['time']))}  {tag}{G.shown_name(m)}"
                                        f" · {m['client']}:  {m['text']}")
                if m["sid"] == "fluffmod" or m.get("role") == "owner":
                    self.list.itemconfig(i, fg=YELLOW)
                if m["id"] == keep:
                    self.list.selection_set(i)
            if at_bottom:
                self.list.see("end")
        self.root.after(300, self.tick, gen)

    def run(self):
        self.root.mainloop()


def main():
    if not trust.HAVE_CRYPTO:
        print("  dev panel needs: python -m pip install cryptography")
    Panel().run()


if __name__ == "__main__":
    main()
