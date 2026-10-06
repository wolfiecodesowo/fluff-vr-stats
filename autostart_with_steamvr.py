"""Run once (with SteamVR open) to make Fluff VR Stats start automatically with SteamVR.
Run again with --remove to undo."""
import json, os, sys
import openvr

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = "fluffvr.stats"
manifest_path = os.path.join(HERE, "fluffvr_stats.vrmanifest")
pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
if not os.path.exists(pyw):
    pyw = sys.executable

manifest = {"source": "builtin", "applications": [{
    "app_key": KEY, "launch_type": "binary",
    "binary_path_windows": pyw,
    "arguments": f'"{os.path.join(HERE, "main.py")}"',
    "working_directory": HERE,
    "is_dashboard_overlay": True,
    "strings": {"en_us": {"name": "Fluff VR Stats", "description": "Cute wrist HUD + AI buddy"}},
}]}
openvr.init(openvr.VRApplication_Utility)
apps = openvr.VRApplications()
if "--remove" in sys.argv:
    apps.setApplicationAutoLaunch(KEY, False)
    apps.removeApplicationManifest(manifest_path)
    print("Removed - Fluff VR Stats won't autostart anymore.")
else:
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    apps.addApplicationManifest(manifest_path, False)
    apps.setApplicationAutoLaunch(KEY, True)
    print("Done! Fluff VR Stats will now start with SteamVR.")
openvr.shutdown()
input("Press Enter to close...")
