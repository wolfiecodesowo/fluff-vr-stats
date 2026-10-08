"""
ONE TIME, on the owner's PC: makes the signing keys for Fluff VR Stats.

    python tools/make_keys.py      (or double-click tools/make_keys.bat)

Writes:
  bot/bot_key.pem        PRIVATE. Fluff Bot signs chat, app keys + events with it. Stays next to the bot.
  keys/release_key.pem   PRIVATE. tools/sign_release.py signs each release with it. Back it up somewhere safe!
  trust.json             PUBLIC halves. Commit + push this one, that's what turns the safety stuff on.

Both .pem files are in .gitignore so they can't get uploaded by accident.
If u lose release_key.pem u can make a new one, but every app needs one manual update to trust it.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import trust  # noqa: E402

BOT_KEY = os.path.join(HERE, "bot", "bot_key.pem")
REL_KEY = os.path.join(HERE, "keys", "release_key.pem")


def main():
    if not trust.HAVE_CRYPTO:
        print("  run:  python -m pip install cryptography   then try again")
        return 1
    pub = trust.trust_keys()
    for name, path in (("bot", BOT_KEY), ("release", REL_KEY)):
        if os.path.exists(path):
            print(f"  {name}: already have {os.path.relpath(path, HERE)} (keeping it)")
            key = trust.load_private(path)
            from cryptography.hazmat.primitives import serialization
            pub[name] = trust.b64e(key.public_key().public_bytes(
                serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo))
            continue
        pem, public = trust.new_keypair()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(pem)
        pub[name] = public
        print(f"  {name}: made {os.path.relpath(path, HERE)}  (PRIVATE - never upload or share)")
    pub["_note"] = "public keys only. made by tools/make_keys.py"
    with open(trust.TRUST_FILE, "w", encoding="utf-8") as f:
        json.dump(pub, f, indent=2)
    print("\n  wrote trust.json (public, safe to upload)")
    print("  next: commit + push trust.json, restart Fluff Bot, then sign ur next release with")
    print("        python tools/sign_release.py vX.Y.Z\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
