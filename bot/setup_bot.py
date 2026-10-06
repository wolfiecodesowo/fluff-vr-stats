"""One-time setup for Fluff Bot: installs discord.py and saves your bot token (on your PC only)."""
import getpass
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "bot_config.json")

print("\n  ~ Fluff Bot setup :3 ~\n")
print("  installing discord.py ...")
subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", "discord.py"])
try:
    cfg = json.load(open(CFG, encoding="utf-8"))
except Exception:
    cfg = {}
print("\n  1. go to https://discord.com/developers/applications -> your Fluff VR Stats app")
print("  2. Bot -> Reset Token -> Copy")
print("  3. paste it below (it stays hidden while you paste, that's normal)\n")
tok = getpass.getpass("  bot token: ").strip()
if tok:
    cfg["token"] = tok
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    print("\n  saved! (bot/bot_config.json - never share or upload this file)")
    print("  now double-click run_bot.bat :3\n")
else:
    print("\n  no token pasted, nothing changed.\n")
input("  press Enter to close")
