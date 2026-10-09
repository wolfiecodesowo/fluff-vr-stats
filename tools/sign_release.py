"""
Signs a release so the auto-updater will accept it.

    python tools/sign_release.py v0.4.0           (makes fluff-manifest.json)
    python tools/sign_release.py v0.4.0 --upload  (also attaches it to the GitHub release, needs `gh`)

How: builds the exact same zip GitHub serves for that tag (`git archive`), hashes every file
(SHA-256), and signs the list with keys/release_key.pem. The app checks the signature + every
hash before installing. Run it AFTER the tag is pushed and BEFORE people start updating
(apps refuse an unsigned release, they just stay on the old version until it's signed).

Using GitHub Actions instead? Put the contents of release_key.pem in a repo secret called
RELEASE_KEY and .github/workflows/release.yml signs + builds the installer for u.
"""
import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import trust  # noqa: E402

KEY = os.environ.get("RELEASE_KEY_FILE") or os.path.join(HERE, "keys", "release_key.pem")


def _zip_bytes(tag):
    """the release's files: from git if this is a git checkout, otherwise straight from GitHub"""
    try:
        return subprocess.run(["git", "-C", HERE, "archive", "--format=zip", tag], capture_output=True,
                              check=True).stdout, False
    except Exception:
        import urllib.request
        url = f"https://github.com/wolfiecodesowo/fluff-vr-stats/archive/refs/tags/{tag}.zip"
        print(f"  no git here, downloading {url}")
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "FluffVRStats-sign"}),
                                    timeout=120) as r:
            return r.read(), True


def manifest_for(tag):
    data, prefixed = _zip_bytes(tag)
    zf = zipfile.ZipFile(io.BytesIO(data))
    files = {}
    for n in zf.namelist():
        if n.endswith("/"):
            continue
        rel = n.split("/", 1)[1] if prefixed else n       # GitHub's zip has a "repo-tag/" folder on top
        if rel:
            files[rel] = hashlib.sha256(zf.read(n)).hexdigest()
    return {"v": 1, "tag": tag, "files": files}


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    tag = argv[1]
    if not os.path.exists(KEY):
        print("  no keys/release_key.pem ~ run tools/make_keys.py first")
        return 1
    man = trust.sign_payload(trust.load_private(KEY), manifest_for(tag))
    if not trust.verify_payload("release", man):
        print("  !! the signature doesn't match trust.json's release key. did u push the newest trust.json?")
        return 1
    out = os.path.join(HERE, "fluff-manifest.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(man, f, indent=1)
    print(f"  signed {len(man['files'])} files for {tag} -> fluff-manifest.json")
    if "--upload" in argv:
        subprocess.run(["gh", "release", "upload", tag, out, "--clobber"], cwd=HERE, check=True)
        print("  attached to the GitHub release :3")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
