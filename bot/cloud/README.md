# Run Fluff Bot 24/7 for free ☁️

Ur PC doesn't have to stay on. Google Cloud gives everyone **one small server free forever** ("Always Free" e2-micro: 2 shared vCPU, 1 GB RAM, 30 GB disk). Fluff Bot only needs ~100 MB.

> Google needs a card to make the account (to prove u're a real person). The e2-micro stays **$0** as long as u follow the 3 rules in step 2. Set a budget alert (step 7) so u'd get an email if anything ever costs money.

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

## 4. stop the PC copy first ⚠️
Close the Fluff Bot window on ur PC. **Only one copy may run at a time.** The server copy refuses to start while another copy holds the lock, and two copies would double-reply.

## 5. upload ur 3 secret files (only u can do this)
From ur PC's `FluffVRStats\bot` folder: **`bot_config.json`**, **`bot_key.pem`**, **`bot_data.json`**.
In the SSH window: **⚙ / UPLOAD FILE** (top right) → pick all 3. Then type:
```
./fluff move
```
`move` keeps a timestamped copy of anything already on the server before it replaces it. It should say `service: running` and `discord: connected`, and Fluff Bot goes online in ur Discord.

> `bot_data.json` has every app key u've handed out, so everyone's keys keep working. `bot_key.pem` signs the app's chat and updates. Never post these 3 files anywhere.

## 6. confirm it works
`./fluff health` should say the service is running and Discord is connected. If the bot ever can't start (wrong token, a second copy running, a damaged data file), it DMs the server owner and `./fluff logs` shows why.

## 7. budget alert (peace of mind)
Billing → Budgets & alerts → Create budget → $1 → alert at 50% / 100%. (A budget alert only emails u. It doesn't stop charges.)

## how it looks after that
- **It restarts itself.** If it crashes, systemd restarts it after 15 s. If it hangs, a watchdog restarts it. If it fails 5 times in 5 min it stops and waits, so it doesn't spam Discord.
- **It watches itself.** Background loops that stop are restarted and the owner is DMed. Anything that needs a human (a bad token, a damaged data file, a failed backup, a raid) also DMs the owner, at most once an hour per problem.
- **Backups happen by themselves.** Once a day the bot keeps a copy of `bot_data.json` in `bot/backups/` (the newest 30, so about a month). A damaged data file is moved aside and the newest good backup is restored automatically.
- **A raid turns the key gate on.** More than 10 joins in a minute turns the gate on for 30 minutes and DMs the owner. `/raid off` ends it early.
- **Pause everything.** `/pause` stops the bot's own posts, welcomes, renames and role sweeps. Moderation and staff commands keep working. `/resume` turns it back on. (On the server you can also do `touch bot/PAUSED`.)

## everyday commands (in the SSH window)
| type | does |
|---|---|
| `./fluff health` | is it running, is it connected to Discord, how many backups |
| `./fluff logs` | what the bot's been doing |
| `./fluff restart` | restart it |
| `./fluff update` | grab the newest bot, install its pinned packages, restart. if the new version doesn't connect, it rolls back by itself |
| `./fluff backup` | makes one file with the data, config and signing key. download it (⚙ / DOWNLOAD FILE) and keep it private |
| `./fluff restore <file.tgz>` | puts a backup back (keeps the current files as `.bak`) |
| `./fluff stop` / `./fluff start` | turn it off / on |

It starts by itself when the server reboots.

## if u want an off-server copy too
The bot keeps its backups on the same disk. For a copy somewhere else, u can download `./fluff backup` files from time to time, or set up a Google Cloud Storage bucket and copy them there. (That's optional. The server copy already restores itself from `bot/backups/`.)
