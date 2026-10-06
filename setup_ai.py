"""Fluff VR Stats :3 - AI setup helper. Pick a service, paste your key, done."""
import json
import os
import sys
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "config.json")
sys.path.insert(0, HERE)
import ai  # noqa: E402

OPTIONS = [
    ("Groq  (FREE, no card needed, fast)", "openai_compatible", "https://api.groq.com/openai/v1", "auto",
     "https://console.groq.com/keys"),
    ("Claude by Anthropic  (needs ~$5 credit, very good)", "anthropic", "", "claude-haiku-4-5",
     "https://console.anthropic.com/settings/keys"),
    ("OpenAI  (needs credit)", "openai_compatible", "https://api.openai.com/v1", "auto",
     "https://platform.openai.com/api-keys"),
    ("Ollama on this PC  (free, no key, but uses your GPU = less VRChat FPS)", "openai_compatible",
     "http://localhost:11434/v1", "auto", None),
]


def main():
    print("\n  ~ Fluff VR Stats :3 - AI setup ~\n")
    print("  Fluff needs an AI service to talk. Pick one:\n")
    for i, o in enumerate(OPTIONS, 1):
        print(f"    {i}) {o[0]}")
    choice = input("\n  number (1-4, Enter = 1): ").strip() or "1"
    if choice not in "1234" or len(choice) != 1:
        print("  hmm that's not 1-4, try again later!")
        return
    label, provider, base, model, url = OPTIONS[int(choice) - 1]
    key = ""
    if url:
        print(f"\n  opening {url} in your browser...")
        print("  sign in, make a new API key, copy it, then come back here.")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        key = input("\n  paste your key here (right-click pastes in this window): ").strip().strip('"')
        if not key:
            print("  no key pasted, nothing changed.")
            return
    try:
        with open(CFG, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    cfg.setdefault("ai", {})
    cfg["ai"].update({"provider": provider, "api_key": key, "base_url": base, "model": model})
    cfg["ai"].setdefault("max_tokens", 300)
    cfg["ai"].setdefault("system_prompt", "You are Fluff, a cute, playful, supportive furry companion "
                         "living inside a VR wrist overlay. Keep replies short (1-3 sentences).")
    print("\n  testing... ", end="", flush=True)
    try:
        reply = ai.ask(cfg, [("user", "say hi to me in under 12 words, you're a cute furry assistant")])
        print("it works!! :3\n")
        print(f"  Fluff says: {reply}\n")
    except Exception as e:
        msg = str(e)
        if hasattr(e, "read"):
            try:
                msg = json.loads(e.read().decode()).get("error", {}).get("message", msg)
            except Exception:
                pass
        print(f"didn't work >w<\n  {msg}\n")
        if input("  save it anyway? (y/N): ").strip().lower() != "y":
            return
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    print("  saved! restart Fluff VR Stats and open the Chat tab <3")


if __name__ == "__main__":
    try:
        main()
    finally:
        input("\n  press Enter to close...")
