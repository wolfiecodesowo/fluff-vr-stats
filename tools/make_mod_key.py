"""
ONE TIME, on the owner's PC: makes the password-locked key for the dev panel (devpanel.py).

    python tools/make_mod_key.py                 (or double-click tools/make_mod_key.bat)
    python tools/make_mod_key.py --password      change the password (same key, nothing to re-upload)
    python tools/make_mod_key.py --staff NAME    (later) a separate key for a staff member

Writes:
  ~/.fluffvr/mod_key.pem   PRIVATE + encrypted with ur password. Lives outside the app folder, so updates
                           and reinstalls never touch it. Back it up (it's useless without the password).
  trust.json "mod"         PUBLIC half. Commit + push it and restart Fluff Bot: from then on the bot obeys
                           commands signed by this key, and nothing else.

Lost the password? Run this again with --new: it makes a fresh key (push trust.json + restart the bot again).
"""
import getpass
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import trust  # noqa: E402

KEY_DIR = os.path.join(os.path.expanduser("~"), ".fluffvr")


def key_path(staff=None):
    return os.path.join(KEY_DIR, f"mod_key_{staff}.pem" if staff else "mod_key.pem")


def ask_new_password():
    while True:
        a = getpass.getpass("  new password (min 8 characters, typing is hidden): ")
        if len(a) < 8:
            print("  too short, try again")
            continue
        if getpass.getpass("  same password again: ") != a:
            print("  they didn't match, try again")
            continue
        return a


def public_of(key):
    from cryptography.hazmat.primitives import serialization
    return trust.b64e(key.public_key().public_bytes(serialization.Encoding.DER,
                                                    serialization.PublicFormat.SubjectPublicKeyInfo))


def main(argv):
    if not trust.HAVE_CRYPTO:
        print("  run:  python -m pip install cryptography   then try again")
        return 1
    staff = None
    if "--staff" in argv:
        i = argv.index("--staff")
        staff = "".join(c for c in (argv[i + 1] if i + 1 < len(argv) else "") if c.isalnum())[:20].lower()
        if not staff:
            print("  usage: make_mod_key.py --staff NAME")
            return 1
    path, name = key_path(staff), ("mod_" + staff if staff else "mod")
    os.makedirs(KEY_DIR, exist_ok=True)

    if os.path.exists(path) and "--new" not in argv:
        if "--password" not in argv:
            print(f"  already have {path}")
            print("  (--password to change its password, --new to replace it)")
            key = None
            try:
                key = trust.load_private(path, getpass.getpass("  password (to check it + refresh trust.json): "))
            except (ValueError, TypeError):
                print("  wrong password")
                return 1
        else:
            try:
                key = trust.load_private(path, getpass.getpass("  current password: "))
            except (ValueError, TypeError):
                print("  wrong password")
                return 1
            from cryptography.hazmat.primitives import serialization
            pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                    serialization.BestAvailableEncryption(ask_new_password().encode("utf-8")))
            with open(path, "wb") as f:
                f.write(pem)
            print("  password changed (same key, nothing to upload)")
            return 0
        public = public_of(key)
    else:
        pem, public = trust.new_keypair(ask_new_password())
        with open(path, "wb") as f:
            f.write(pem)
        print(f"  made {path}  (PRIVATE + password-locked, never upload or share)")

    pub = trust.trust_keys()
    changed = pub.get(name) != public
    pub[name] = public
    pub["_note"] = "public keys only. made by tools/make_keys.py + tools/make_mod_key.py"
    with open(trust.TRUST_FILE, "w", encoding="utf-8") as f:
        json.dump(pub, f, indent=2)
        f.write("\n")
    if changed:
        print(f"\n  wrote \"{name}\" into trust.json (public, safe to upload)")
        print("  next: commit + push trust.json with the next release, and restart Fluff Bot.")
    else:
        print("\n  trust.json already has this key, nothing to do")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
