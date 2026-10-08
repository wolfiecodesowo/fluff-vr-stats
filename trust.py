"""
Fluff VR Stats - signatures (so nobody can fake chat messages, keys or updates).

Two key pairs, both ECDSA P-256:
  - "bot":     Fluff Bot signs every global chat message, every app key it hands out, and
               community-night events. The app only shows/accepts things with a good signature,
               so posting straight to ntfy with curl does nothing.
  - "release": signs each release's file list (SHA-256 of every file). The auto-updater checks it
               before it swaps a single file.

Only the PUBLIC halves live in the repo (trust.json). The private halves are made on the owner's
PC by tools/make_keys.py and never get uploaded (they're in .gitignore).
"""
import base64
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TRUST_FILE = os.path.join(HERE, "trust.json")

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    HAVE_CRYPTO = True
except Exception:          # not installed yet (old install) -> run install.bat
    HAVE_CRYPTO = False

_pub_cache = {}


def canonical(payload):
    """the exact bytes that get signed: sorted keys, no spaces, no 'sig' field"""
    d = {k: v for k, v in payload.items() if k != "sig"}
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def b64e(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def b64d(s):
    s = str(s)
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def trust_keys():
    try:
        with open(TRUST_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def configured(name):
    """True once the owner ran tools/make_keys.py and pushed trust.json"""
    return bool(trust_keys().get(name))


def public_key(name):
    if not HAVE_CRYPTO:
        return None
    if name in _pub_cache:
        return _pub_cache[name]
    raw = trust_keys().get(name)
    key = None
    if raw:
        try:
            key = serialization.load_der_public_key(b64d(raw))
        except Exception:
            key = None
    _pub_cache[name] = key
    return key


def verify(name, data, sig):
    """True = good signature. False = bad/missing (or no key to check with)."""
    key = public_key(name)
    if key is None or not sig:
        return False
    try:
        key.verify(b64d(sig), data, ec.ECDSA(hashes.SHA256()))
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False
    except Exception:
        return False


def verify_payload(name, payload):
    return isinstance(payload, dict) and verify(name, canonical(payload), payload.get("sig"))


# --------------------------------------------------------- owner/bot side ---
def load_private(path):
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def sign(private_key, data):
    return b64e(private_key.sign(data, ec.ECDSA(hashes.SHA256())))


def sign_payload(private_key, payload):
    out = dict(payload)
    out["sig"] = sign(private_key, canonical(payload))
    return out


def new_keypair():
    k = ec.generate_private_key(ec.SECP256R1())
    pem = k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                          serialization.NoEncryption())
    pub = k.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return pem, b64e(pub)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
