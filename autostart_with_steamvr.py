"""Make Fluff VR Stats start automatically with SteamVR (or --remove to undo).
The app also has this as a switch now: Settings -> general -> Start with SteamVR.
--quiet = no "press Enter" at the end (used by the installer)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = "fluffvr.stats"
CFG = os.path.join(HERE, "config.json")
quiet = "--quiet" in sys.argv
remove = "--remove" in sys.argv


def remember(on):
    """SteamVR isn't open: save the choice, the app applies it next time it starts"""
    try:
        with open(CFG, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        cfg = {}
    cfg["start_with_steamvr"] = on
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def main():
    manifest_path = os.path.join(HERE, "fluffvr_stats.vrmanifest")
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable
    manifest = {"source": "builtin", "applications": [{
        "app_key": KEY, "launch_type": "binary",
        "binary_path_windows": pyw,
        "arguments": f'"{os.path.join(HERE, "main.py")}" --vr',
        "working_directory": HERE,
        "is_dashboard_overlay": True,
        "strings": {"en_us": {"name": "Fluff VR Stats", "description": "Cute furry wrist HUD for VRChat"}},
    }]}
    try:
        import openvr
        openvr.init(openvr.VRApplication_Utility)
    except Exception:
        remember(not remove)
        print("SteamVR isn't open, so the app will set this up next time it starts :3")
        return
    try:
        apps = openvr.VRApplications()
        if remove:
            apps.setApplicationAutoLaunch(KEY, False)
            apps.removeApplicationManifest(manifest_path)
            print("Removed - Fluff VR Stats won't autostart anymore.")
        else:
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
            apps.addApplicationManifest(manifest_path, False)
            apps.setApplicationAutoLaunch(KEY, True)
            print("Done! Fluff VR Stats will now start with SteamVR.")
        remember(not remove)
    finally:
        openvr.shutdown()


if __name__ == "__main__":
    main()
    if not quiet:
        input("Press Enter to close...")
