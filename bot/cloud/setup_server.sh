#!/usr/bin/env bash
# Fluff Bot on a free Linux server (Google Cloud e2-micro / Oracle Always Free / any Ubuntu or Debian box).
# Run once:   curl -fsSL https://raw.githubusercontent.com/wolfiecodesowo/fluff-vr-stats/main/bot/cloud/setup_server.sh | bash
# It installs Python, downloads the bot, and makes it start by itself + restart if it ever crashes.
# Ur secret files (bot_config.json, bot_key.pem, bot_data.json) are NOT in GitHub ~ u upload those urself after.
set -e
DIR="$HOME/fluff-vr-stats"
echo "== installing python + git"
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-venv python3-pip git
if [ -d "$DIR/.git" ]; then git -C "$DIR" pull -q; else git clone -q https://github.com/wolfiecodesowo/fluff-vr-stats.git "$DIR"; fi
echo "== installing the bot's python stuff"
python3 -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install -q --upgrade pip
"$DIR/.venv/bin/pip" install -q discord.py aiohttp cryptography pillow
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

[Service]
User=$USER
WorkingDirectory=$DIR/bot
ExecStart=$DIR/.venv/bin/python fluffbot.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable -q fluffbot
cp "$DIR/bot/cloud/fluff" "$HOME/fluff" 2>/dev/null && chmod +x "$HOME/fluff"
echo
echo "done!! now upload ur 3 secret files from ur PC's bot folder (bot_config.json, bot_key.pem, bot_data.json)"
echo "then type:   ./fluff move    (puts them in place + starts the bot)"
