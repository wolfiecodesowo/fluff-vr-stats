"""Collects SteamVR frame timing, device batteries and PC load."""
import ctypes
import time

import openvr
import psutil

try:
    import pynvml  # optional, NVIDIA GPU load
    pynvml.nvmlInit()
    _NV = pynvml.nvmlDeviceGetHandleByIndex(0)
except Exception:
    _NV = None

N_FRAMES = 90  # ~1 second of history at 90Hz


class StatsCollector:
    def __init__(self, vr_system):
        self.sys = vr_system
        self.comp = openvr.VRCompositor()
        self.history = []          # GPU frametimes for the graph
        self.last_bat_check = 0
        self.batteries = []
        self.refresh = None
        psutil.cpu_percent(None)   # prime

        self._timings = (openvr.Compositor_FrameTiming * N_FRAMES)()
        self._timings[0].m_nSize = ctypes.sizeof(openvr.Compositor_FrameTiming)

    def _refresh_rate(self):
        try:
            return self.sys.getFloatTrackedDeviceProperty(
                openvr.k_unTrackedDeviceIndex_Hmd, openvr.Prop_DisplayFrequency_Float)
        except Exception:
            return None

    def _frame_stats(self):
        out = {"fps": None, "gpu_ms": None, "cpu_ms": None, "reproj_pct": None, "vr_ok": False}
        try:
            res = self.comp.getFrameTimings(self._timings)
        except Exception:
            return out
        # pyopenvr returns (count, array); older builds return just the count
        n = res[0] if isinstance(res, tuple) else res
        try:
            n = max(0, min(int(n or 0), N_FRAMES))
        except (TypeError, ValueError):
            n = 0
        if not n:
            return out
        # SteamVR fills the array from the start, oldest -> newest
        frames = list(self._timings)[:n]
        # each app frame is shown for m_nNumFramePresents vsyncs; >1 means reprojected
        vsyncs = sum(max(1, f.m_nNumFramePresents) for f in frames)
        reproj = sum(1 for f in frames if f.m_nNumFramePresents > 1 or
                     (f.m_nReprojectionFlags & (openvr.VRCompositor_ReprojectionReason_Cpu |
                                                openvr.VRCompositor_ReprojectionReason_Gpu)))
        if self.refresh:
            out["fps"] = min(self.refresh, self.refresh * len(frames) / vsyncs)
        gpu = [f.m_flTotalRenderGpuMs for f in frames if 0 < f.m_flTotalRenderGpuMs < 1000]
        cpu = [f.m_flNewFrameReadyMs - f.m_flNewPosesReadyMs for f in frames
               if 0 < f.m_flNewFrameReadyMs - f.m_flNewPosesReadyMs < 1000]
        out["gpu_ms"] = sum(gpu) / len(gpu) if gpu else None
        out["cpu_ms"] = sum(cpu) / len(cpu) if cpu else None
        out["reproj_pct"] = 100.0 * reproj / len(frames)
        out["vr_ok"] = True
        self.history = gpu[-60:]
        return out

    def _battery_stats(self):
        res = []
        names = {openvr.TrackedDeviceClass_HMD: "HMD",
                 openvr.TrackedDeviceClass_GenericTracker: "Trk"}
        trk = 0
        for i in range(openvr.k_unMaxTrackedDeviceCount):
            cls = self.sys.getTrackedDeviceClass(i)
            if cls == openvr.TrackedDeviceClass_Invalid:
                continue
            try:
                if not self.sys.getBoolTrackedDeviceProperty(i, openvr.Prop_DeviceProvidesBatteryStatus_Bool):
                    continue
                pct = self.sys.getFloatTrackedDeviceProperty(i, openvr.Prop_DeviceBatteryPercentage_Float) * 100
                try:
                    chg = self.sys.getBoolTrackedDeviceProperty(i, openvr.Prop_DeviceIsCharging_Bool)
                except Exception:
                    chg = False
            except Exception:
                continue
            if cls == openvr.TrackedDeviceClass_Controller:
                role = self.sys.getControllerRoleForTrackedDeviceIndex(i)
                label = "L" if role == openvr.TrackedControllerRole_LeftHand else \
                        "R" if role == openvr.TrackedControllerRole_RightHand else "Ctl"
            elif cls == openvr.TrackedDeviceClass_GenericTracker:
                trk += 1
                label = f"T{trk}"
            else:
                label = names.get(cls, "Dev")
            res.append((label, pct, chg))
        order = {"HMD": 0, "L": 1, "R": 2}
        res.sort(key=lambda r: order.get(r[0], 3))
        return res

    def collect(self):
        """Each stat is collected on its own, so one failing never blanks the rest."""
        now = time.time()
        s = {"fps": None, "gpu_ms": None, "cpu_ms": None, "reproj_pct": None, "vr_ok": False}
        if self.refresh is None or now - self.last_bat_check > 10:
            self.refresh = self._refresh_rate()
        try:
            s.update(self._frame_stats())
        except Exception:
            pass
        s["refresh"] = self.refresh
        s["frametimes"] = self.history
        if now - self.last_bat_check > 10:   # batteries change slowly
            self.last_bat_check = now
            try:
                self.batteries = self._battery_stats()
            except Exception:
                pass
        s["batteries"] = self.batteries
        try:
            s["cpu_pct"] = psutil.cpu_percent(None)
            s["ram_pct"] = psutil.virtual_memory().percent
        except Exception:
            s["cpu_pct"] = s["ram_pct"] = None
        s["gpu_pct"] = s["gpu_temp"] = s["vram_used"] = s["vram_total"] = None
        if _NV is not None:
            try:
                s["gpu_pct"] = float(pynvml.nvmlDeviceGetUtilizationRates(_NV).gpu)
                s["gpu_temp"] = float(pynvml.nvmlDeviceGetTemperature(_NV, 0))
                mem = pynvml.nvmlDeviceGetMemoryInfo(_NV)
                s["vram_used"], s["vram_total"] = mem.used / 1024 ** 3, mem.total / 1024 ** 3
            except Exception:
                pass
        return s
