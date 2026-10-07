"""
Desktop mode: Fluff VR Stats without a headset.

The whole menu opens in a normal window (click with ur mouse, scroll the chat, type with ur keyboard),
and everything that talks to VRChat still works: chatbox stats, avatar toggles, music, global chat,
headpat/boop counters, Discord status... Lil Kitty lives on ur desktop as a tiny
always-on-top pet u can click to pat (drag across her head to stroke her).

Started by main.py when u pick "Desktop" (or run run_desktop.bat).
"""
import itertools
import os
import queue
import subprocess
import sys
import threading
import time
import traceback

import openvr

import main as core
import ui

HERE = os.path.dirname(os.path.abspath(__file__))


# ------------------------------------------------------------ no-SteamVR stand-ins ---
class _Null:
    def __getattr__(self, name):
        return lambda *a, **k: None


class NullVR(_Null):
    def getTrackedDeviceIndexForControllerRole(self, role):
        return openvr.k_unTrackedDeviceIndexInvalid

    def pollNextEvent(self, ev):
        return False

    def getTrackedDeviceClass(self, i):
        return openvr.TrackedDeviceClass_Invalid

    def getFloatTrackedDeviceProperty(self, *a):
        raise RuntimeError("no headset in desktop mode")

    getBoolTrackedDeviceProperty = getFloatTrackedDeviceProperty

    def getTrackedDeviceActivityLevel(self, i):
        return -1


class NullOverlay(_Null):
    def __init__(self):
        self._ids = itertools.count(1)

    def createOverlay(self, *a):
        return next(self._ids)

    def createDashboardOverlay(self, *a):
        return next(self._ids), next(self._ids)

    def isOverlayVisible(self, h):
        return True

    def pollNextOverlayEvent(self, h, ev):
        return False, ev


class NullComp(_Null):
    def getFrameTimings(self, *a):
        return 0


class _NoGL:
    def __init__(self, *a, **k):
        raise RuntimeError("desktop mode draws in a normal window")


# --------------------------------------------------------------------- the app ---
class DesktopApp(core.App):
    def __init__(self, cfg):
        openvr.IVROverlay = NullOverlay
        openvr.VRCompositor = NullComp
        core.GLUploader = _NoGL
        self.events = queue.Queue()
        self.frames = {}               # "dash" / "kitty" / "hud" -> PIL image
        self.kb_request = None
        self.quit = False
        super().__init__(cfg, NullVR())
        self.desktop = True
        self.state.desktop = True
        self.gchat.client = "desktop"
        self.raise_window = False

    # pictures go to the window instead of SteamVR
    def push(self, handle, img=None, key="img", frame=None):
        if img is None:
            return
        if handle == self.dash:
            self.frames["dash"] = img
        elif handle == self.kitty_ov:
            self.frames["kitty"] = img
        elif handle == self.hud:
            self.frames["hud"] = img

    def mouse_flipped(self):
        return False

    def on_hover(self, mx, my):
        # just the hover highlight; the real Windows cursor is used on desktop
        box = self.hit.find_box(mx, my)
        if box != self.state.hover_box:
            self.state.hover_box = box
            self.t["logo"] = 0

    def play_intro(self):
        pass

    def open_keyboard(self, desc, existing, target):
        self.state.kb_target = target
        self.kb_request = (desc, existing or "", target)
        return True

    def find_controller(self):
        pass

    def step_hud(self, now):
        st = self.state
        if st.hud_dirty and (self.cfg.get("desktop", {}).get("mini_hud") or now - self.t["hud"] > 5):
            st.hud_dirty = False
            self.t["hud"] = now
            # VR-only stats (headset fps, frame timing) are always empty on desktop, so hide them
            mods = self.cfg["modules"]
            vr_only = ("fps", "frametime_graph", "gpu_cpu_ms", "reprojection", "batteries", "look_to_show")
            saved = {k: mods.get(k) for k in vr_only}
            try:
                for k in vr_only:
                    mods[k] = False
                self.frames["hud"] = ui.render_hud(st)
            finally:
                mods.update(saved)

    def step_kitty(self, now):
        if not self.cfg["modules"].get("wrist_kitty", True):
            self.frames.pop("kitty", None)
            return
        self.kitty.tick(now)
        if self.kitty.changed and now - self.kitty_t > (1 / 12 if getattr(self.kitty, "fast", True) else 1 / 4) or "kitty" not in self.frames:
            self.kitty_t = now
            self.frames["kitty"] = self.kitty.render(ui.get_theme(self.cfg), now)
        if self.kitty.sound:
            self.kitty_mod.play(self.kitty.sound)
            self.kitty.sound = None

    def kitty_click(self, x, y, stroke=False):
        act = self.kitty.hit(x, y)
        if act is None or (stroke and act != "pat"):
            return
        msg = self.kitty.act(act)
        if msg:
            self.show_alert(msg, secs=6)
        self.state.dirty_cfg = True

    def poll_events(self):
        while True:
            try:
                ev = self.events.get_nowait()
            except queue.Empty:
                break
            kind = ev[0]
            if kind == "quit":
                raise core.QuitApp()
            if kind == "click":
                self.safe("click", self.on_click, ev[1], ev[2])
            elif kind == "move":
                self.safe("hover", self.on_hover, ev[1], ev[2])
            elif kind == "leave":
                self.state.cursor = None
                self.state.hover_box = None
                self.t["logo"] = 0
            elif kind == "scroll" and self.state.tab == "Global":
                self.scroll(ev[1] * 60)
            elif kind == "kb":
                self.safe("typing", self.stop_typing)
                if ev[1] is not None:
                    self.safe("keyboard", self.keyboard_done, ev[1])
            elif kind == "hud":
                self.safe("wrist button", self.hud_command, ev[1])
                self.t["hud"] = 0
            elif kind == "kitty":
                self.safe("kitty", self.kitty_click, ev[1], ev[2], ev[3])


# ---------------------------------------------------------------------- window ---
def run():
    import tkinter as tk
    from tkinter import simpledialog
    from PIL import Image, ImageTk

    cfg = core.load_cfg()
    dcfg = cfg.setdefault("desktop", {"mini_hud": True, "kitty_pos": None})
    if not dcfg.get("hud_v2"):            # the floating wrist menu is on by default now
        dcfg.update(mini_hud=True, hud_v2=True)
    cfg["first_run"] = False                  # the VR welcome tip talks about SteamVR
    app = DesktopApp(cfg)
    app.state.dash_dirty = True
    app.show_alert("ur wrist menu floats on ur screen! drag it anywhere · scroll to resize · F9 hides it", secs=12)

    def worker():
        try:
            app.run()
        except core.QuitApp:
            pass
        except Exception as e:
            core.log.error("desktop app crashed: %s\n%s", e, traceback.format_exc())
        finally:
            app.quit = True
    threading.Thread(target=worker, daemon=True, name="fluff-desktop").start()

    root = tk.Tk()
    root.title("Fluff VR Stats :3  (desktop)")
    try:
        root.iconphoto(True, ImageTk.PhotoImage(Image.open(os.path.join(HERE, "assets", "logo.gif")).convert("RGBA").resize((64, 64))))
    except Exception:
        pass
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    scale = min(1.0, sw * 0.8 / ui.DASH_W, sh * 0.8 / ui.DASH_H)
    W, H = int(ui.DASH_W * scale), int(ui.DASH_H * scale)
    root.configure(bg="#160e22")
    canvas = tk.Canvas(root, width=W, height=H, bg="#160e22", highlightthickness=0, cursor="hand2")
    canvas.pack(fill="both", expand=True)
    view = {"scale": scale, "img": None, "item": None, "last": None, "W": W, "H": H}

    def to_dash(e):
        return e.x / view["scale"], e.y / view["scale"]

    canvas.bind("<Motion>", lambda e: app.events.put(("move", *to_dash(e))))
    canvas.bind("<Leave>", lambda e: app.events.put(("leave",)))
    canvas.bind("<Button-1>", lambda e: app.events.put(("click", *to_dash(e))))
    canvas.bind("<MouseWheel>", lambda e: app.events.put(("scroll", e.delta / 120)))
    canvas.bind("<Button-4>", lambda e: app.events.put(("scroll", 1)))
    canvas.bind("<Button-5>", lambda e: app.events.put(("scroll", -1)))

    def on_resize(e):
        s = min(e.width / ui.DASH_W, e.height / ui.DASH_H)
        if abs(s - view["scale"]) > 0.01:
            view["scale"], view["last"] = s, None
    canvas.bind("<Configure>", on_resize)

    # ---- kitty: tiny always-on-top desktop pet
    kwin = tk.Toplevel(root)
    kwin.overrideredirect(True)
    kwin.attributes("-topmost", True)
    KEY = "#ff00fe"
    try:
        kwin.attributes("-transparentcolor", KEY)
    except tk.TclError:
        pass
    KS = 240
    kc = tk.Canvas(kwin, width=KS, height=KS, bg=KEY, highlightthickness=0, cursor="hand2")
    kc.pack()
    pos = dcfg.get("kitty_pos") or [sw - KS - 40, sh - KS - 90]
    kwin.geometry(f"{KS}x{KS}+{int(pos[0])}+{int(pos[1])}")
    kview = {"img": None, "last": None, "drag": None, "stroke": 0.0}
    import kitty as kmod

    def k_xy(e):
        return e.x * kmod.SIZE / KS, e.y * kmod.SIZE / KS

    def k_down(e):
        x, y = k_xy(e)
        act = app.kitty.hit(x, y)
        if act is None:                       # empty spot -> drag her around
            kview["drag"] = (e.x_root - kwin.winfo_x(), e.y_root - kwin.winfo_y())
        else:
            kview["drag"] = None
            kview["stroke"] = time.time()
            app.events.put(("kitty", x, y, False))

    def k_move(e):
        if kview["drag"]:
            dx, dy = kview["drag"]
            kwin.geometry(f"+{e.x_root - dx}+{e.y_root - dy}")
        elif time.time() - kview["stroke"] > 0.6:       # stroking her head = more pats
            kview["stroke"] = time.time()
            app.events.put(("kitty", *k_xy(e), True))

    def k_up(e):
        if kview["drag"]:
            dcfg["kitty_pos"] = [kwin.winfo_x(), kwin.winfo_y()]
            app.state.dirty_cfg = True
        kview["drag"] = None
    kc.bind("<Button-1>", k_down)
    kc.bind("<B1-Motion>", k_move)
    kc.bind("<ButtonRelease-1>", k_up)

    # ---- floating wrist menu (the VR wrist HUD, as an always-on-top screen)
    hwin = tk.Toplevel(root)
    hwin.overrideredirect(True)
    hwin.attributes("-topmost", True)
    try:
        hwin.attributes("-transparentcolor", KEY)
        hwin.attributes("-alpha", float(dcfg.get("hud_alpha", 0.95)))
    except tk.TclError:
        pass
    hc = tk.Canvas(hwin, width=340, height=220, bg=KEY, highlightthickness=0, cursor="hand2")
    hc.pack()
    hp = dcfg.get("hud_pos") or [40, sh - 420]
    hwin.geometry(f"+{int(hp[0])}+{int(hp[1])}")
    hview = {"img": None, "last": None, "press": None, "moved": False, "size": None}

    def h_down(e):
        hview["press"] = (e.x_root, e.y_root, e.x_root - hwin.winfo_x(), e.y_root - hwin.winfo_y(), e.x, e.y)
        hview["moved"] = False

    def h_move(e):
        p = hview["press"]
        if not p:
            return
        if abs(e.x_root - p[0]) + abs(e.y_root - p[1]) > 6:
            hview["moved"] = True
        if hview["moved"]:
            hwin.geometry(f"+{e.x_root - p[2]}+{e.y_root - p[3]}")

    def h_up(e):
        p = hview["press"]
        hview["press"] = None
        if not p:
            return
        if hview["moved"]:
            dcfg["hud_pos"] = [hwin.winfo_x(), hwin.winfo_y()]
            app.state.dirty_cfg = True
            return
        h, size = app.frames.get("hud"), hview["size"]
        if h is None or not size:          # a tap: press the HUD button under the mouse (music etc.)
            return
        x, y = p[4] * h.width / size[0], p[5] * h.height / size[1]
        for (x0, y0, x1, y1), cmd in list(getattr(app.state, "hud_hits", []) or []):
            if x0 <= x <= x1 and y0 <= y <= y1:
                app.events.put(("hud", cmd))
                break

    def h_wheel(e):
        d = 1 if (getattr(e, "delta", 0) > 0 or getattr(e, "num", 0) == 4) else -1
        dcfg["hud_w"] = max(220, min(760, int(dcfg.get("hud_w", 340)) + d * 30))
        hview["last"] = None
        app.state.dirty_cfg = True

    def hud_menu(e):
        m = tk.Menu(hwin, tearoff=0)
        m.add_command(label="bigger", command=lambda: h_wheel(type("E", (), {"delta": 1})()))
        m.add_command(label="smaller", command=lambda: h_wheel(type("E", (), {"delta": -1})()))
        for a in (1.0, 0.85, 0.65):
            m.add_command(label=f"see-through {int((1 - a) * 100)}%", command=lambda a=a: (
                dcfg.__setitem__("hud_alpha", a), hwin.attributes("-alpha", a), app.state.__setattr__("dirty_cfg", True)))
        m.add_separator()
        m.add_command(label="hide (F9 brings it back)", command=lambda: toggle("hud"))
        m.tk_popup(e.x_root, e.y_root)

    hc.bind("<Button-1>", h_down)
    hc.bind("<B1-Motion>", h_move)
    hc.bind("<ButtonRelease-1>", h_up)
    hc.bind("<MouseWheel>", h_wheel)
    hc.bind("<Button-4>", h_wheel)
    hc.bind("<Button-5>", h_wheel)
    hc.bind("<Button-3>", hud_menu)

    # ---- zoom magnifier (desktop version of the VR zoom lens): round, always on top, drag to move,
    # scroll to resize. It's hidden from screen capture so it doesn't zoom into itself.
    zwin = tk.Toplevel(root)
    zwin.overrideredirect(True)
    zwin.attributes("-topmost", True)
    try:
        zwin.attributes("-transparentcolor", KEY)
    except tk.TclError:
        pass
    zs = {"size": int(dcfg.get("zoom_px", 320)), "img": None, "last": None, "drag": None, "hidden_set": False}
    zc = tk.Canvas(zwin, width=zs["size"], height=zs["size"], bg=KEY, highlightthickness=0, cursor="fleur")
    zc.pack()
    zp = dcfg.get("zoom_pos") or [sw - zs["size"] - 60, 80]
    zwin.geometry(f"+{int(zp[0])}+{int(zp[1])}")

    def z_down(e):
        zs["drag"] = (e.x_root - zwin.winfo_x(), e.y_root - zwin.winfo_y())

    def z_move(e):
        if zs["drag"]:
            zwin.geometry(f"+{e.x_root - zs['drag'][0]}+{e.y_root - zs['drag'][1]}")

    def z_up(e):
        zs["drag"] = None
        dcfg["zoom_pos"] = [zwin.winfo_x(), zwin.winfo_y()]
        app.state.dirty_cfg = True

    def z_wheel(e):
        d_ = 1 if (getattr(e, "delta", 0) > 0 or getattr(e, "num", 0) == 4) else -1
        zs["size"] = max(160, min(720, zs["size"] + d_ * 40))
        dcfg["zoom_px"] = zs["size"]
        zc.config(width=zs["size"], height=zs["size"])
        zs["img"], zs["last"] = None, None
        app.state.dirty_cfg = True
    zc.bind("<Button-1>", z_down)
    zc.bind("<B1-Motion>", z_move)
    zc.bind("<ButtonRelease-1>", z_up)
    zc.bind("<MouseWheel>", z_wheel)
    zc.bind("<Button-4>", z_wheel)
    zc.bind("<Button-5>", z_wheel)
    zc.bind("<Button-3>", lambda e: app.events.put(("hud", "zoom")))      # right-click closes it
    zc.bind("<Double-Button-1>", lambda e: app.events.put(("hud", "zoom")))

    def hide_from_capture():
        if sys.platform != "win32" or zs["hidden_set"]:
            return
        try:
            import ctypes
            u = ctypes.windll.user32
            hwnd = u.GetParent(zwin.winfo_id()) or zwin.winfo_id()
            if not u.SetWindowDisplayAffinity(hwnd, 0x11):        # WDA_EXCLUDEFROMCAPTURE (Win10 2004+)
                u.SetWindowDisplayAffinity(hwnd, 0x01)             # older Windows: WDA_MONITOR
            zs["hidden_set"] = True
        except Exception:
            zs["hidden_set"] = True

    # F9 anywhere (even while VRChat is focused) shows / hides the floating wrist menu, F10 = zoom
    hotkey = {"hit": False, "zoom": False}
    if sys.platform == "win32":
        def hotkey_thread():
            import ctypes
            import ctypes.wintypes as wt
            u = ctypes.windll.user32
            ok9 = u.RegisterHotKey(None, 0xF1F, 0x4000, 0x78)       # MOD_NOREPEAT, VK_F9
            ok10 = u.RegisterHotKey(None, 0xF20, 0x4000, 0x79)      # VK_F10
            if not (ok9 or ok10):
                return
            msg = wt.MSG()
            while u.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == 0x0312:                            # WM_HOTKEY
                    if msg.wParam == 0xF20:
                        hotkey["zoom"] = True
                    else:
                        hotkey["hit"] = True
        threading.Thread(target=hotkey_thread, daemon=True, name="hotkey").start()

    # ---- menu
    def switch_vr():
        cfg["launch_mode"] = "vr"
        core.save_cfg(cfg)
        subprocess.Popen([sys.executable, os.path.join(HERE, "main.py"), "--vr"], cwd=HERE)
        close()

    def toggle(key):
        if key == "kitty":
            cfg["modules"]["wrist_kitty"] = not cfg["modules"].get("wrist_kitty", True)
        else:
            dcfg["mini_hud"] = not dcfg.get("mini_hud")
            app.state.hud_dirty = True
        app.state.dirty_cfg = app.state.dash_dirty = True

    def ask_each_time():
        cfg["launch_mode"] = "ask"
        app.state.dirty_cfg = True

    menu = tk.Menu(root)
    m1 = tk.Menu(menu, tearoff=0)
    m1.add_command(label="Lil Kitty on desktop (on/off)", command=lambda: toggle("kitty"))
    m1.add_command(label="Floating wrist menu (on/off)   F9", command=lambda: toggle("hud"))
    m1.add_command(label="Zoom magnifier (on/off)   F10", command=lambda: app.events.put(("hud", "zoom")))
    menu.add_cascade(label="View", menu=m1)
    m2 = tk.Menu(menu, tearoff=0)
    m2.add_command(label="Switch to VR mode", command=switch_vr)
    m2.add_command(label="Ask VR or Desktop every launch", command=ask_each_time)
    menu.add_cascade(label="Mode", menu=m2)
    root.config(menu=menu)

    def close():
        app.events.put(("quit",))
        try:
            core.save_cfg(cfg)
        except Exception:
            pass
        root.after(300, root.destroy)
    root.protocol("WM_DELETE_WINDOW", close)

    def show(canvas_, store, img, size):
        if img is store["last"] and store["img"] is not None:
            return
        store["last"] = img
        pic = img.resize(size, Image.BILINEAR) if img.size != size else img
        if pic.mode == "RGBA":
            bg = Image.new("RGBA", pic.size, (255, 0, 254, 255))
            bg.alpha_composite(pic)
            pic = bg.convert("RGB")
        if store["img"] is not None and (store["img"].width(), store["img"].height()) == size:
            store["img"].paste(pic)
        else:
            store["img"] = ImageTk.PhotoImage(pic)
            canvas_.delete("all")
            canvas_.create_image(0, 0, image=store["img"], anchor="nw")

    def refresh():
        if app.quit:
            root.destroy()
            return
        f = app.frames.get("dash")
        if f is not None:
            s = view["scale"]
            if f is not view["last"]:
                size = (int(ui.DASH_W * s), int(ui.DASH_H * s))
                pic = f.convert("RGB")
                if pic.size != size:
                    pic = pic.resize(size, Image.BILINEAR)
                if view["img"] is not None and (view["img"].width(), view["img"].height()) == size:
                    view["img"].paste(pic)                  # reuse the same picture = much faster
                else:
                    view["img"] = ImageTk.PhotoImage(pic)
                    canvas.delete("all")
                    canvas.create_image(0, 0, image=view["img"], anchor="nw")
                view["last"] = f
        k = app.frames.get("kitty")
        if k is not None and cfg["modules"].get("wrist_kitty", True):
            if kwin.state() == "withdrawn":
                kwin.deiconify()
            show(kc, kview, k, (KS, KS))
        elif kwin.state() != "withdrawn":
            kwin.withdraw()
        if hotkey["hit"]:
            hotkey["hit"] = False
            toggle("hud")
        if hotkey["zoom"]:
            hotkey["zoom"] = False
            app.events.put(("hud", "zoom"))
        if app.raise_window:
            app.raise_window = False
            try:
                root.deiconify()
                root.lift()
                root.focus_force()
            except tk.TclError:
                pass
        zimg = app.zoom.image if (app.zoom.active and cfg["zoom"].get("enabled")) else None
        if zimg is not None:
            if zwin.state() == "withdrawn":
                zwin.deiconify()
                root.after(50, hide_from_capture)
            show(zc, zs, zimg, (zs["size"], zs["size"]))
        elif zwin.state() != "withdrawn":
            zwin.withdraw()
        h = app.frames.get("hud")
        if h is not None and dcfg.get("mini_hud"):
            hw = int(dcfg.get("hud_w", 340))
            hs = (hw, int(hw * h.height / h.width))
            if hview["size"] != hs:
                hc.config(width=hs[0], height=hs[1])
                hview["size"], hview["img"] = hs, None
            if hwin.state() == "withdrawn":
                hwin.deiconify()
            show(hc, hview, h, hs)
        elif hwin.state() != "withdrawn":
            hwin.withdraw()
        if app.kb_request:
            desc, existing, target = app.kb_request
            app.kb_request = None
            text = simpledialog.askstring("Fluff VR Stats :3", desc, initialvalue=existing, parent=root)
            app.events.put(("kb", text))
        root.after(33, refresh)

    hwin.withdraw()
    zwin.withdraw()
    root.after(100, refresh)
    print("  Fluff VR Stats :3 is running in desktop mode! (close the window to quit)")
    root.mainloop()
    app.close()
    core.save_cfg(cfg)


# --------------------------------------------------------------- VR or desktop? ---
def pick_mode(cfg):
    """Little window: VR or Desktop? (with 'remember my choice'). Returns 'vr' / 'desktop' / None."""
    import tkinter as tk
    from PIL import Image, ImageTk
    choice = {"mode": None}
    root = tk.Tk()
    root.title("Fluff VR Stats :3")
    root.configure(bg="#22162e")
    root.resizable(False, False)
    try:
        logo = ImageTk.PhotoImage(Image.open(os.path.join(HERE, "assets", "logo.gif")).convert("RGBA").resize((110, 110)))
        root.iconphoto(True, logo)
        tk.Label(root, image=logo, bg="#22162e").pack(pady=(18, 0))
    except Exception:
        pass
    tk.Label(root, text="how are u playing today?", font=("Segoe UI", 18, "bold"), fg="#fff5fc", bg="#22162e").pack(pady=(8, 2))
    tk.Label(root, text="u can switch any time", font=("Segoe UI", 10), fg="#d8c0e8", bg="#22162e").pack()
    row = tk.Frame(root, bg="#22162e")
    row.pack(padx=24, pady=16)
    remember = tk.BooleanVar(value=False)

    def go(m):
        choice["mode"] = m
        cfg["launch_mode"] = m if remember.get() else "ask"
        root.destroy()

    for m, title, sub in (("vr", "🥽  VR", "SteamVR wrist HUD,\nmenu, kitty on ur wrist"),
                          ("desktop", "🖥️  Desktop", "normal window,\nkitty on ur desktop")):
        b = tk.Button(row, text=f"{title}\n{sub}", font=("Segoe UI", 13, "bold"), width=16, height=4,
                      bg="#ff96ca" if m == "vr" else "#b58cff", fg="#180e22", activebackground="#ffe246",
                      relief="flat", cursor="hand2", command=lambda m=m: go(m))
        b.pack(side="left", padx=8)
    tk.Checkbutton(root, text="remember my choice", variable=remember, font=("Segoe UI", 10),
                   fg="#fff5fc", bg="#22162e", selectcolor="#382650", activebackground="#22162e",
                   activeforeground="#fff5fc").pack(pady=(0, 6))
    tk.Label(root, text="(to get this question back: run pick_mode.bat)", font=("Segoe UI", 9),
             fg="#a890b8", bg="#22162e").pack(pady=(0, 14))
    root.update_idletasks()
    x = (root.winfo_screenwidth() - root.winfo_width()) // 2
    y = (root.winfo_screenheight() - root.winfo_height()) // 3
    root.geometry(f"+{x}+{y}")
    root.attributes("-topmost", True)
    root.after(800, lambda: root.attributes("-topmost", False))
    root.mainloop()
    return choice["mode"]


if __name__ == "__main__":
    run()
