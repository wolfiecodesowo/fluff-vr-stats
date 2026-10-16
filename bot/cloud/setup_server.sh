#!/usr/bin/env bash
# Fluff Bot on a free Linux server (Google Cloud e2-micro / Oracle Always Free / any Ubuntu or Debian box).
# Run once:   curl -fsSL https://raw.githubusercontent.com/wolfiecodesowo/fluff-vr-stats/main/bot/cloud/setup_server.sh | bash
# It installs Python, downloads the bot, and makes it start by itself + restart if it ever crashes or hangs.
# Ur secret files (bot_config.json, bot_key.pem, bot_data.json) are NOT in GitHub ~ u upload those urself after.
set -e
DIR="$HOME/fluff-vr-stats"
echo "== installing python + git"
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-venv python3-pip git
if [ -d "$DIR/.git" ]; then git -C "$DIR" pull -q; else git clone -q https://github.com/wolfiecodesowo/fluff-vr-stats.git "$DIR"; fi
echo "== installing the bot's python stuff (pinned versions)"
python3 -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install -q --upgrade pip
"$DIR/.venv/bin/pip" install -q -r "$DIR/bot/requirements-server.txt"
# a lil swap so 1 GB servers never run out of memory
if [ ! -f /swapfile ]; then
  sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile && sudo mkswap -q /swapfile && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi
echo "== making it run 24/7"
sudo tee /etc/systemd/system/fluffbot.service >/dev/null <<UNIT
[Unit]
Description=Fluff Bot :3
After=network-online.target
Wants=network-online.target
# if it fails 5 times in 5 minutes, stop trying and leave it for the owner to look at (./fluff status)
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
User=$USER
WorkingDirectory=$DIR/bot
ExecStart=$DIR/.venv/bin/python fluffbot.py
Restart=always
RestartSec=15
# exit 3 = bad/missing token or intents off, exit 4 = already running: restarting these would just spam Discord
RestartPreventExitStatus=3 4
# the bot pings systemd every couple of minutes. if it stops responding (a hang), systemd restarts it
WatchdogSec=300
NotifyAccess=main
# keep a leak from thrashing the VM: the bot gets restarted before it can eat all the memory
MemoryHigh=600M
MemoryMax=800M
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable -q fluffbot
cp "$DIR/bot/cloud/fluff" "$HOME/fluff" || { echo "!! couldn't copy the ./fluff helper"; exit 1; }
chmod +x "$HOME/fluff"
echo
echo "done!! now upload ur 3 secret files from ur PC's bot folder (bot_config.json, bot_key.pem, bot_data.json)"
echo "then type:   ./fluff move    (puts them in place + starts the bot)"
