# Run Fluff Bot 24/7 for free ☁️

Ur PC doesn't have to stay on. Google Cloud gives everyone **one small server free forever** ("Always Free" e2-micro: 2 shared vCPU, 1 GB RAM, 30 GB disk). Fluff Bot only needs ~100 MB.

> Google needs a card to make the account (to prove u're a real person). The e2-micro stays **$0** as long as u follow the 3 rules in step 2. Set a budget alert (step 6) so u'd get an email if anything ever costs money.

## 1. make the account
console.cloud.google.com → sign in → accept → add the billing info. (The $300 trial is fine, the e2-micro stays free after it ends.)

## 2. make the server (the 3 free rules ⚠️)
Compute Engine → VM instances → **Create instance**
- **Region: `us-west1` (Oregon), `us-central1` or `us-east1`** ← only these are free
- **Machine type: `e2-micro`**
- **Boot disk: Ubuntu 24.04 LTS, Standard persistent disk, 30 GB** (not "Balanced", not SSD)
- everything else default → **Create**

## 3. install the bot
Click **SSH** next to the server (a terminal opens in ur browser), paste this and press enter:
```
curl -fsSL https://raw.githubusercontent.com/wolfiecodesowo/fluff-vr-stats/main/bot/cloud/setup_server.sh | bash
```

## 4. upload ur 3 secret files (only u can do this)
From ur PC's `FluffVRStats\bot` folder: **`bot_config.json`**, **`bot_key.pem`**, **`bot_data.json`**.
In the SSH window: **⚙ / UPLOAD FILE** (top right) → pick all 3. Then type:
```
./fluff move
```
It should say `active (running)` and Fluff Bot goes online in ur Discord.

> `bot_data.json` has every app key u've handed out, so everyone's keys keep working. Never post these 3 files anywhere.

## 5. turn off the PC copy
Close the Fluff Bot window on ur PC. **Only run one copy at a time**, two copies = double replies.

## 6. budget alert (peace of mind)
Billing → Budgets & alerts → Create budget → $1 → alert at 50% / 100%.

## everyday commands (in the SSH window)
| type | does |
|---|---|
| `./fluff logs` | what the bot's been doing |
| `./fluff restart` | restart it |
| `./fluff update` | grab the newest bot from GitHub + restart (do this after updates) |
| `./fluff backup` | saves a copy of `bot_data.json` (download it with ⚙ / DOWNLOAD FILE) |
| `./fluff stop` / `./fluff start` | turn it off / on |

It starts by itself when the server reboots and restarts itself if it ever crashes.
