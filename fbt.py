"""
Fluff VR Stats - full-body estimation (v0.5). Sends VRChat's OSC trackers, so no SteamVR driver,
no mods and nothing touches VRChat's files.

Modes (cfg["fbt"]["mode"]):
  "off"        nothing is sent
  "standable"  hip + planted feet (+ knees) estimated from ur headset (+ controllers). no hardware.
               feet stay put until ur body really moves, then take a lil step = standable poses
  "camera"     the webcam add-on: a normal webcam sees ur legs (mediapipe pose), ur headset still
               drives the hip so it never drifts

VRChat OSC trackers (docs.vrchat.com/docs/osc-trackers):
  /tracking/trackers/1..8/position + /rotation   3 floats each, Unity space: meters, +Y up,
                                                 left-handed, euler degrees (Z, X, Y order)
  /tracking/trackers/head/position + /rotation   lines the OSC space up with the avatar's head
Real SteamVR trackers (Vive, Tundra, SlimeVR, Amethyst/Kinect) win: estimation pauses by itself.
"""
import math
import os
import subprocess
import sys
import threading
import time

import oscout

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON_DIR = os.path.join(HERE, "addons")
POSE_MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/"
                  "float16/latest/pose_landmarker_lite.task")

DEFAULT_CFG = {
    "mode": "off",            # off / standable / camera
    "trackers": "hips_feet",  # hips_feet (best for most) / full (adds knees + chest)
    "height": 0.0,            # ur eye height in meters, 0 = learn it from the headset
    "send_head": True,        # line the OSC space up with ur head every frame
    "step": 0.22,             # how far ur body moves before a foot steps (m)
    "camera": 0,              # webcam index for the camera add-on
    "camera_yaw": None,       # set by "calibrate camera" (which way the webcam looks)
    "rate": 50,               # sends per second
}

# tracker slots (VRChat works out which body part each one is when u calibrate)
SLOTS = {"hip": 1, "foot_l": 2, "foot_r": 3, "knee_l": 4, "knee_r": 5, "chest": 6, "elbow_l": 7, "elbow_r": 8}
BASIC = ("hip", "foot_l", "foot_r")
FULL = ("hip", "foot_l", "foot_r", "knee_l", "knee_r", "chest")

# other tracking apps we can spot (process name -> label)
TRACKING_APPS = {"amethyst.exe": "Amethyst", "slimevr.exe": "SlimeVR", "kinectservice.exe": "Kinect One",
                 "kinectmonitor.exe": "Kinect One", "driver4vr.exe": "Driver4VR", "standable.exe": "Standable"}
LINKS = {"amethyst": "https://k2vr.tech", "slimevr": "https://slimevr.dev",
         "kinect": "https://www.microsoft.com/en-us/download/details.aspx?id=44559"}


# ---------------------------------------------------------------------------------------- math ---
def wrap180(a):
    return (a + 180.0) % 360.0 - 180.0


def lerp(a, b, t):
    return a + (b - a) * t


def vlerp(a, b, t):
    return tuple(lerp(x, y, t) for x, y in zip(a, b))


def fwd_of(yaw):
    r = math.radians(yaw)
    return math.sin(r), 0.0, math.cos(r)


def right_of(yaw):
    r = math.radians(yaw)
    return math.cos(r), 0.0, -math.sin(r)


def add(*vs):
    return tuple(sum(c) for c in zip(*vs))


def mul(v, k):
    return tuple(c * k for c in v)


def dist_xz(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])


def smoothstep(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def openvr_to_unity(m):
    """HmdMatrix34 (OpenVR standing space, right-handed) -> (position, yaw) in VRChat's Unity space"""
    pos = (m[0][3], m[1][3], -m[2][3])
    fx, fz = -m[0][2], m[2][2]               # OpenVR looks down -Z; Unity flips Z
    yaw = math.degrees(math.atan2(fx, fz)) if (fx or fz) else 0.0
    return pos, yaw


# ------------------------------------------------------------------------------------ estimator ---
class Foot:
    def __init__(self, pos, yaw):
        self.pos, self.yaw = pos, yaw
        self.frm, self.to, self.to_yaw, self.frm_yaw = pos, pos, yaw, yaw
        self.t = 1.0                          # 1 = planted

    @property
    def stepping(self):
        return self.t < 1.0


class Estimator:
    """Headset (+ controllers) in, hip / feet / knees / chest out. Pure math, easy to test."""
    ANKLE = 0.07          # ankle height off the floor
    STEP_TIME = 0.30
    STEP_LIFT = 0.07
    TURN_DEADZONE = 35.0

    def __init__(self, cfg):
        self.cfg = cfg
        self.body_yaw = None
        self.eye_h = float(cfg.get("height") or 0) or None
        self.seen_h = []                      # head heights, to learn eye height
        self.feet = None
        self.hip = None

    # eye height: calibrated, or the tall end of what we've seen (people stand most of the time)
    def eye_height(self, head_y):
        if self.cfg.get("height"):
            return float(self.cfg["height"])
        self.seen_h.append(head_y)
        if len(self.seen_h) > 3000:
            del self.seen_h[:1000]
        srt = sorted(self.seen_h)
        h = srt[int(len(srt) * 0.9)] if len(srt) > 20 else max(head_y, 1.5)
        return min(2.1, max(1.1, h))

    def calibrate(self, head_y):
        """stand up straight + look ahead, then call this"""
        self.cfg["height"] = round(min(2.1, max(1.0, head_y)), 3)
        self.feet = None

    def update(self, head, head_yaw, dt, controllers=()):
        eye = self.eye_height(head[1])
        # which way ur body faces: follows the head, but only when the head turns a lot (or slowly over time)
        if self.body_yaw is None:
            self.body_yaw = head_yaw
        yaw_cue = head_yaw
        if len(controllers) >= 2:             # both hands out in front = a good hint where the chest points
            mid = mul(add(controllers[0], controllers[1]), 0.5)
            dx, dz = mid[0] - head[0], mid[2] - head[2]
            if math.hypot(dx, dz) > 0.15:
                cy = math.degrees(math.atan2(dx, dz))
                if abs(wrap180(cy - head_yaw)) < 70:
                    yaw_cue = head_yaw + wrap180(cy - head_yaw) * 0.35
        diff = wrap180(yaw_cue - self.body_yaw)
        if abs(diff) > self.TURN_DEADZONE:
            self.body_yaw += (abs(diff) - self.TURN_DEADZONE) * math.copysign(1, diff) * min(1.0, dt * 8)
        diff = wrap180(yaw_cue - self.body_yaw)     # lil glances (<12°) don't turn the hips...
        if abs(diff) > 12:
            self.body_yaw = wrap180(self.body_yaw + (abs(diff) - 12) * math.copysign(1, diff) * min(1.0, dt * 1.2))
        # ...but once the head holds still for a sec, the body finishes turning to face the same way
        self._yaw_hist = getattr(self, "_yaw_hist", [])
        self._yaw_hist = (self._yaw_hist + [head_yaw])[-int(1.0 / max(dt, 0.005)):]
        if max(abs(wrap180(y - head_yaw)) for y in self._yaw_hist) < 6:
            self.body_yaw = wrap180(self.body_yaw + wrap180(yaw_cue - self.body_yaw) * min(1.0, dt * 1.5))
        fwd, right = fwd_of(self.body_yaw), right_of(self.body_yaw)
        hfwd = fwd_of(head_yaw)

        # sitting: head low (< 68% of eye height) + not walking for 2s. stand up (> 80%) = back to standing
        last = getattr(self, "_last_head", None)
        speed = dist_xz(head, last) / max(dt, 1e-3) if last else 0.0
        self._last_head = head
        self._low_t = getattr(self, "_low_t", 0.0)
        self._low_t = self._low_t + dt if (head[1] < eye * 0.68 and speed < 0.3) else 0.0
        if head[1] > eye * 0.8:
            self.sitting = False
        elif self._low_t > 2.0:
            self.sitting = True
        if getattr(self, "sitting", False):
            return self._sit(head, head_yaw, eye, fwd, right, hfwd)

        # hip: under the head, a bit back. crouch -> legs bend, hip sinks + goes back
        crouch = min(1.0, max(0.0, 1.0 - head[1] / eye))          # 0 standing, 1 on the floor
        torso = eye * 0.40
        hip_y = max(0.18, head[1] - torso * (1.0 - crouch * 0.35))
        back = 0.07 + crouch * 0.22
        hip = (head[0] - hfwd[0] * back, hip_y, head[2] - hfwd[2] * back)
        self.hip = hip if self.hip is None else vlerp(self.hip, hip, min(1.0, dt * 20))
        hip = self.hip

        # feet: planted until the body really moves, then one foot at a time takes a step
        stance = 0.10 + eye * 0.012
        targets = [add((hip[0], self.ANKLE, hip[2]), mul(right, -stance), mul(fwd, 0.03)),
                   add((hip[0], self.ANKLE, hip[2]), mul(right, stance), mul(fwd, 0.03))]
        if self.feet is None or any(dist_xz(f.pos, tg) > 1.2 for f, tg in zip(self.feet, targets)):
            self.feet = [Foot(targets[0], self.body_yaw), Foot(targets[1], self.body_yaw)]   # snap (teleport/start)
        step = float(self.cfg.get("step") or 0.22)
        for i, (f, tg) in enumerate(zip(self.feet, targets)):
            other = self.feet[1 - i]
            if f.stepping:
                f.t = min(1.0, f.t + dt / self.STEP_TIME)
                k = smoothstep(f.t)
                x, _, z = vlerp(f.frm, f.to, k)
                f.pos = (x, self.ANKLE + math.sin(math.pi * f.t) * self.STEP_LIFT, z)
                f.yaw = f.frm_yaw + wrap180(f.to_yaw - f.frm_yaw) * k
            elif not other.stepping:
                far = dist_xz(f.pos, tg) > step
                twisted = abs(wrap180(self.body_yaw - f.yaw)) > 30
                # step the foot that's furthest behind first
                if (far or twisted) and dist_xz(f.pos, tg) >= dist_xz(other.pos, targets[1 - i]) - 0.02:
                    lead = mul((tg[0] - f.pos[0], 0, tg[2] - f.pos[2]), 0.25)    # land a lil ahead, like walking
                    f.frm, f.to, f.t = f.pos, add(tg, lead), 0.0
                    f.frm_yaw, f.to_yaw = f.yaw, self.body_yaw
        out = {"hip": (hip, (0.0, self.body_yaw, 0.0))}
        for name, f in (("foot_l", self.feet[0]), ("foot_r", self.feet[1])):
            out[name] = (f.pos, (0.0, f.yaw, 0.0))
        # knees: halfway down the leg, pushed forward as much as the leg is bent
        leg = max(0.3, eye * 0.57 - self.ANKLE)
        for side, f in (("l", self.feet[0]), ("r", self.feet[1])):
            d = max(1e-3, math.dist(hip, f.pos))
            bend = math.sqrt(max(0.0, (leg / 2) ** 2 - (min(d, leg) / 2) ** 2))
            axis = mul(add(f.pos, mul(hip, -1)), 1 / d)
            ff = fwd_of(f.yaw)                  # knees bend forward, square to the leg
            k = sum(a * b for a, b in zip(ff, axis))
            perp = add(ff, mul(axis, -k))
            pl = math.sqrt(sum(c * c for c in perp)) or 1.0
            out["knee_" + side] = (add(vlerp(hip, f.pos, 0.5), mul(perp, (bend + 0.03) / pl)), (0.0, f.yaw, 0.0))
        out["chest"] = (add(vlerp(hip, head, 0.55), mul(hfwd, 0.02)), (0.0, wrap180(lerp(self.body_yaw, head_yaw, 0.4)), 0.0))
        return out

    def _sit(self, head, head_yaw, eye, fwd, right, hfwd):
        """seat under ur hips, thighs forward, shins down to the floor (same pose as the Quest version)"""
        hip = (head[0] - fwd[0] * 0.12, max(0.15, head[1] - eye * 0.36), head[2] - fwd[2] * 0.12)
        self.hip = hip
        self.feet = None                       # feet re-plant under u when u stand up
        leg = max(0.3, eye * 0.57 - self.ANKLE)
        knee_y = max(0.1, hip[1] + 0.04)
        out = {"hip": (hip, (0.0, self.body_yaw, 0.0))}
        for side, s in (("l", -1), ("r", 1)):
            side_off = mul(right, 0.12 * s)
            knee = add(hip, side_off, mul(fwd, leg * 0.5))
            knee = (knee[0], knee_y, knee[2])
            foot = add(knee, mul(fwd, max(0.0, leg * 0.5 - knee_y) * 0.6))
            out["knee_" + side] = (knee, (0.0, self.body_yaw, 0.0))
            out["foot_" + side] = ((foot[0], self.ANKLE, foot[2]), (0.0, self.body_yaw, 0.0))
        out["chest"] = (add(vlerp(hip, head, 0.55), mul(hfwd, 0.02)), (0.0, self.body_yaw, 0.0))
        return out


def head_bone(head, head_yaw):
    """VRChat lines the OSC space up with the head BONE (below + behind ur eyes), not the eyes"""
    f = fwd_of(head_yaw)
    return head[0] - f[0] * 0.06, head[1] - 0.09, head[2] - f[2] * 0.06


# ------------------------------------------------------------------------------ webcam add-on ---
def addon_ready():
    try:
        import cv2  # noqa: F401
        import mediapipe  # noqa: F401
        return True
    except Exception:
        return False


def install_addon(log=None):
    """pip installs the webcam add-on (mediapipe + opencv). Returns '' or an error to show."""
    try:
        r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "mediapipe", "opencv-python"],
                           capture_output=True, text=True, timeout=900,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as e:
        return f"couldn't run pip ({e})"
    if r.returncode != 0:
        tail = (r.stderr or r.stdout or "").strip().splitlines()[-1:] or ["pip failed"]
        if log:
            log.warning("camera add-on install failed: %s", (r.stderr or r.stdout)[-2000:])
        if sys.version_info >= (3, 13):
            return (f"the camera add-on doesn't support python {sys.version_info[0]}.{sys.version_info[1]} yet ~ "
                    "use FluffVRStats-Setup.exe (it brings python 3.12) or install python 3.12")
        return tail[0][:140]
    return ""


# mediapipe pose landmark ids
LM = {"nose": 0, "sh_l": 11, "sh_r": 12, "el_l": 13, "el_r": 14, "hip_l": 23, "hip_r": 24,
      "knee_l": 25, "knee_r": 26, "ank_l": 27, "ank_r": 28, "toe_l": 31, "toe_r": 32}


class CameraPose:
    """Reads the webcam in its own thread and keeps the newest 3D pose (meters, hip-centered)."""

    def __init__(self, index=0, log=None):
        self.index, self.log = index, log
        self.status, self.fps, self.pose, self.pose_t = "starting", 0.0, None, 0.0
        self.running = True
        threading.Thread(target=self._run, daemon=True, name="fbt-camera").start()

    def stop(self):
        self.running = False

    def _detector(self):
        import mediapipe as mp
        sol = getattr(mp, "solutions", None)
        if sol is not None and hasattr(sol, "pose"):
            p = sol.pose.Pose(model_complexity=1, smooth_landmarks=True, min_detection_confidence=0.5,
                              min_tracking_confidence=0.5)

            def detect(rgb, _t):
                r = p.process(rgb)
                lms = getattr(r, "pose_world_landmarks", None)
                return [(l.x, l.y, l.z, l.visibility) for l in lms.landmark] if lms else None
            return detect
        # newer mediapipe: the Tasks API + a small model file
        import urllib.request
        os.makedirs(ADDON_DIR, exist_ok=True)
        model = os.path.join(ADDON_DIR, "pose_landmarker_lite.task")
        if not os.path.exists(model):
            self.status = "downloading the pose model…"
            urllib.request.urlretrieve(POSE_MODEL_URL, model)
        from mediapipe.tasks.python import BaseOptions, vision
        lm = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model), running_mode=vision.RunningMode.VIDEO))

        def detect(rgb, t):
            r = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int(t * 1000))
            if not r.pose_world_landmarks:
                return None
            return [(l.x, l.y, l.z, getattr(l, "visibility", 1.0) or 1.0) for l in r.pose_world_landmarks[0]]
        return detect

    def _run(self):
        try:
            import cv2
            detect = self._detector()
            cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW) if sys.platform == "win32" else cv2.VideoCapture(self.index)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            if not cap.isOpened():
                self.status = f"no webcam #{self.index} found"
                return
        except Exception as e:
            self.status = f"camera add-on error: {e}"
            if self.log:
                self.log.warning("fbt camera failed to start: %s", e)
            return
        self.status = "looking for u…"
        n, t0 = 0, time.time()
        try:
            while self.running:
                ok, frame = cap.read()
                if not ok:
                    self.status = "webcam stopped sending frames"
                    time.sleep(0.5)
                    continue
                now = time.time()
                lms = detect(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), now)
                if lms:
                    self.pose, self.pose_t = lms, now
                    self.status = "tracking :3"
                elif now - self.pose_t > 1.5:
                    self.status = "can't see ur body ~ step back so ur feet are in view"
                n += 1
                if now - t0 >= 1:
                    self.fps, n, t0 = n / (now - t0), 0, now
        finally:
            cap.release()

    def offsets(self, max_age=0.5):
        """body parts relative to the middle of ur hips, in the camera's frame:
        (right, up, toward-camera) as the webcam sees it. None when stale."""
        if not self.pose or time.time() - self.pose_t > max_age:
            return None
        p = self.pose
        mid = [(p[LM["hip_l"]][i] + p[LM["hip_r"]][i]) / 2 for i in range(3)]

        def rel(name):
            x, y, z, vis = p[LM[name]]
            # mediapipe: x = image right, y = down, z = away from the camera
            return (-(x - mid[0]), -(y - mid[1]), -(z - mid[2])), vis
        return {k: rel(k) for k in LM}


def cam_to_world(off, cam_yaw):
    """camera-frame offset -> world offset. cam_yaw = the way u faced when u calibrated (facing the cam)"""
    r, f = right_of(cam_yaw), fwd_of(cam_yaw)
    return add(mul(r, off[0]), (0.0, off[1], 0.0), mul(f, off[2]))


def apply_camera(est_out, offs, cam_yaw, scale=1.0):
    """replaces the estimated legs with what the webcam sees (hip position stays headset-driven)"""
    if not offs or cam_yaw is None:
        return est_out
    hip = est_out["hip"][0]
    out = dict(est_out)
    # hip turn from the line between ur hips (much better than guessing from the head)
    (hl, vl), (hr, vr) = offs["hip_l"], offs["hip_r"]
    if min(vl, vr) > 0.5:
        side = cam_to_world((hr[0] - hl[0], 0, hr[2] - hl[2]), cam_yaw)
        if math.hypot(side[0], side[2]) > 0.08:
            hip_yaw = math.degrees(math.atan2(-side[2], side[0]))      # right vector -> yaw
            out["hip"] = (hip, (0.0, hip_yaw, 0.0))
    hip_yaw = out["hip"][1][1]
    for part, lm_name in (("foot_l", "ank_l"), ("foot_r", "ank_r"), ("knee_l", "knee_l"), ("knee_r", "knee_r"),
                          ("elbow_l", "el_l"), ("elbow_r", "el_r")):
        off, vis = offs[lm_name]
        if vis < 0.5:
            continue
        p = add(hip, mul(cam_to_world(off, cam_yaw), scale))
        if part.startswith("foot"):
            p = (p[0], max(Estimator.ANKLE, p[1]), p[2])
            toe, tv = offs["toe_" + part[-1]]
            yaw = hip_yaw
            if tv > 0.5:
                d = cam_to_world((toe[0] - off[0], 0, toe[2] - off[2]), cam_yaw)
                if math.hypot(d[0], d[2]) > 0.04:
                    yaw = math.degrees(math.atan2(d[0], d[2]))
            out[part] = (p, (0.0, yaw, 0.0))
        else:
            out[part] = (p, (0.0, hip_yaw, 0.0))
    return out


# ----------------------------------------------------------------------------------- the runner ---
def tracking_apps():
    found = set()
    try:
        import psutil
        for pr in psutil.process_iter(["name"]):
            nm = (pr.info.get("name") or "").lower()
            if nm in TRACKING_APPS:
                found.add(TRACKING_APPS[nm])
    except Exception:
        pass
    return sorted(found)


class FullBody:
    """Runs in its own thread. pose_fn() -> (head HmdMatrix34, [controller HmdMatrix34...]) or None.
    trackers_fn() -> how many real SteamVR trackers are on (estimation steps aside for them)."""

    def __init__(self, cfg, pose_fn, trackers_fn=None, log=None, port_fn=None):
        self.root = cfg
        self.cfg = cfg.setdefault("fbt", {})
        for k, v in DEFAULT_CFG.items():
            self.cfg.setdefault(k, v)
        self.pose_fn, self.trackers_fn, self.log = pose_fn, trackers_fn, log
        self.port_fn = port_fn or (lambda: cfg.get("osc_port", 9000))
        self.est = Estimator(self.cfg)
        self.cam = None
        self.status = {"state": "off", "rate": 0.0, "real_trackers": 0, "apps": [], "msg": "", "last": {}}
        self.running = True
        self.installing = False
        self._sender = None
        self._last_head = None
        self._last_yaw = 0.0
        threading.Thread(target=self._run, daemon=True, name="fbt").start()

    def stop(self):
        self.running = False
        if self.cam:
            self.cam.stop()

    # ---- buttons
    def set_mode(self, mode):
        self.cfg["mode"] = mode
        self.est.feet = None
        if mode != "camera" and self.cam:
            self.cam.stop()
            self.cam = None

    def calibrate_height(self):
        if self._last_head:
            self.est.calibrate(self._last_head[1])
            return self.cfg["height"]
        return None

    def calibrate_camera(self):
        """face ur webcam, stand straight, press. remembers which way the webcam looks."""
        self.cfg["camera_yaw"] = round(self._last_yaw, 1)
        return self.cfg["camera_yaw"]

    def install_camera_addon(self, done=None):
        if self.installing:
            return
        self.installing = True
        self.status["msg"] = "installing the camera add-on (mediapipe + opencv)… this takes a few min"

        def work():
            why = install_addon(self.log)
            self.installing = False
            self.status["msg"] = why or "camera add-on installed!! pick camera mode :3"
            if done:
                done(why)
        threading.Thread(target=work, daemon=True).start()

    # ---- loop
    def _parts(self):
        return FULL if self.cfg.get("trackers") == "full" else BASIC

    def _run(self):
        last, scan_t, n, rate_t = time.time(), 0.0, 0, time.time()
        while self.running:
            mode = self.cfg.get("mode", "off")
            now = time.time()
            if now - scan_t > 3:
                scan_t = now
                self.status["apps"] = tracking_apps()
                try:
                    self.status["real_trackers"] = int(self.trackers_fn() or 0) if self.trackers_fn else 0
                except Exception:
                    self.status["real_trackers"] = 0
            if mode == "off":
                self.status["state"] = "off"
                time.sleep(0.25)
                last = time.time()
                continue
            if self.status["real_trackers"]:
                self.status["state"] = "paused"
                self.status["msg"] = f"{self.status['real_trackers']} real tracker(s) on ~ estimation is resting so they win"
                time.sleep(0.5)
                continue
            try:
                got = self.pose_fn()
            except Exception:
                got = None
            if not got:
                self.status["state"] = "waiting"
                self.status["msg"] = "waiting for ur headset…"
                time.sleep(0.25)
                continue
            head_m, ctrl_m = got
            head, yaw = openvr_to_unity(head_m)
            ctrls = [openvr_to_unity(m)[0] for m in ctrl_m if m is not None]
            self._last_head, self._last_yaw = head, yaw
            dt = min(0.1, max(0.001, now - last))
            last = now
            out = self.est.update(head, yaw, dt, ctrls)
            parts = list(self._parts())
            if mode == "camera":
                if self.cam is None or self.cam.index != int(self.cfg.get("camera", 0)):
                    if self.cam:
                        self.cam.stop()
                    self.cam = CameraPose(int(self.cfg.get("camera", 0)), self.log) if addon_ready() else None
                if self.cam is None:
                    self.status["msg"] = "camera mode needs the camera add-on ~ press install"
                elif self.cfg.get("camera_yaw") is None:
                    self.status["msg"] = "face ur webcam + press calibrate camera"
                else:
                    out = apply_camera(out, self.cam.offsets(), float(self.cfg["camera_yaw"]))
                    self.status["msg"] = self.cam.status
                    if self.cfg.get("trackers") == "full":
                        parts += ["elbow_l", "elbow_r"]
            else:
                self.status["msg"] = "standing, walking + crouching all estimated :3"
            self._send(out, parts, head, yaw)
            self.status["state"] = "on"
            self.status["last"] = out
            n += 1
            if now - rate_t >= 1:
                self.status["rate"], n, rate_t = n / (now - rate_t), 0, now
            time.sleep(max(0.0, 1.0 / max(10, int(self.cfg.get("rate") or 50)) - (time.time() - now)))

    def _send(self, out, parts, head, yaw):
        port = int(self.port_fn() or 9000)
        if self._sender is None or self._sender.addr[1] != port:
            if self._sender:
                self._sender.close()
            self._sender = oscout.Sender(port)
        msgs = []
        for part in parts:
            if part not in out:
                continue
            pos, rot = out[part]
            base = f"/tracking/trackers/{SLOTS[part]}/"
            msgs.append((base + "position", tuple(round(c, 4) for c in pos)))
            msgs.append((base + "rotation", tuple(round(c, 2) for c in rot)))
        if self.cfg.get("send_head", True):
            msgs.append(("/tracking/trackers/head/position", tuple(round(c, 4) for c in head_bone(head, yaw))))
            msgs.append(("/tracking/trackers/head/rotation", (0.0, round(yaw, 2), 0.0)))
        self._sender.send_many(msgs)
