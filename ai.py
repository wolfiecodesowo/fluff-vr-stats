"""AI chat backend. Runs in a background thread so VR never stutters.

Providers (set in config.json -> ai.provider):
  "anthropic"          - Claude via api.anthropic.com (needs api_key)
  "openai_compatible"  - anything with an OpenAI-style /chat/completions endpoint:
                         OpenAI, Groq, OpenRouter, LM Studio, Ollama (base_url
                         e.g. http://localhost:11434/v1, api_key can be blank)
"""
import json
import threading
import urllib.request
import urllib.error


UA = {"user-agent": "FluffVRStats/1.0 (+furry VR overlay)", "accept": "application/json"}


def _post(url, headers, body, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={**UA, **headers},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


_MODEL_CACHE = {}
PREFERRED = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-20b",
             "moonshotai/kimi-k2-instruct", "gpt-4o-mini", "gpt-4.1-mini", "llama3.2", "llama3.1"]


def _get(url, headers, timeout=20):
    req = urllib.request.Request(url, headers={**UA, **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def list_models(base, headers):
    data = _get(base + "/models", headers)
    ids = [m.get("id", "") for m in data.get("data", data.get("models", [])) if isinstance(m, dict)]
    skip = ("whisper", "tts", "embed", "guard", "audio", "image", "dall", "moderation", "playai")
    return [i for i in ids if i and not any(k in i.lower() for k in skip)]


def pick_model(base, headers):
    """Choose a chat model the account actually has (so a renamed model never breaks Fluff)."""
    if base in _MODEL_CACHE:
        return _MODEL_CACHE[base]
    ids = list_models(base, headers)
    choice = next((p for p in PREFERRED if p in ids), ids[0] if ids else None)
    if not choice:
        raise RuntimeError("no chat models available on this account")
    _MODEL_CACHE[base] = choice
    return choice


def ask(cfg, history):
    """history: list of (role, text). Returns reply text (raises on error)."""
    ai = cfg["ai"]
    msgs = [{"role": r, "content": t} for r, t in history[-20:]]
    if ai["provider"] == "anthropic":
        if not ai.get("api_key"):
            raise RuntimeError("No API key yet - run setup_ai.bat in the app folder :3")
        data = _post(
            (ai.get("base_url") or "https://api.anthropic.com") + "/v1/messages",
            {"content-type": "application/json", "x-api-key": ai["api_key"],
             "anthropic-version": "2023-06-01"},
            {"model": ai["model"], "max_tokens": ai.get("max_tokens", 300),
             "system": ai["system_prompt"], "messages": msgs})
        return "".join(b.get("text", "") for b in data.get("content", [])).strip()
    else:
        base = (ai.get("base_url") or "https://api.openai.com/v1").rstrip("/")
        headers = {"content-type": "application/json"}
        if ai.get("api_key"):
            headers["authorization"] = "Bearer " + ai["api_key"]
        elif "localhost" not in base and "127.0.0.1" not in base:
            raise RuntimeError("No API key yet - run setup_ai.bat in the app folder :3")
        model = ai.get("model") or ""
        if model in ("", "auto"):
            model = pick_model(base, headers)
        body = {"model": model, "max_tokens": ai.get("max_tokens", 300),
                "messages": [{"role": "system", "content": ai["system_prompt"]}] + msgs}
        try:
            data = _post(base + "/chat/completions", headers, body)
        except urllib.error.HTTPError as e:
            if e.code in (400, 404) and ai.get("model") not in ("", "auto"):
                # model was renamed/retired -> pick one that exists and retry once
                body["model"] = pick_model(base, headers)
                data = _post(base + "/chat/completions", headers, body)
            else:
                raise
        return data["choices"][0]["message"]["content"].strip()


VISION_PREFERRED = ["meta-llama/llama-4-scout-17b-16e-instruct", "meta-llama/llama-4-maverick-17b-128e-instruct",
                    "gpt-4o-mini", "gpt-4.1-mini", "gpt-4o", "llava", "llama3.2-vision", "qwen2.5vl"]


def ask_image(cfg, prompt, jpeg_b64):
    """One question about one picture (used by AI Look). Returns the reply text."""
    ai = cfg["ai"]
    if ai["provider"] == "anthropic":
        if not ai.get("api_key"):
            raise RuntimeError("No API key yet - run setup_ai.bat in the app folder :3")
        data = _post(
            (ai.get("base_url") or "https://api.anthropic.com") + "/v1/messages",
            {"content-type": "application/json", "x-api-key": ai["api_key"], "anthropic-version": "2023-06-01"},
            {"model": ai.get("vision_model") or ai["model"], "max_tokens": 500,
             "messages": [{"role": "user", "content": [
                 {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": jpeg_b64}},
                 {"type": "text", "text": prompt}]}]}, timeout=90)
        return "".join(b.get("text", "") for b in data.get("content", [])).strip()
    base = (ai.get("base_url") or "https://api.openai.com/v1").rstrip("/")
    headers = {"content-type": "application/json"}
    if ai.get("api_key"):
        headers["authorization"] = "Bearer " + ai["api_key"]
    model = ai.get("vision_model") or ""
    if not model:
        try:
            ids = list_models(base, headers)
        except Exception:
            ids = []
        model = next((m for p in VISION_PREFERRED for m in ids if p in m), None)
        if not model:
            raise RuntimeError("ur AI provider has no picture-reading model. set ai.vision_model in config.json "
                               "(Groq: meta-llama/llama-4-scout-17b-16e-instruct)")
    data = _post(base + "/chat/completions", headers, {
        "model": model, "max_tokens": 500,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + jpeg_b64}}]}]}, timeout=90)
    return data["choices"][0]["message"]["content"].strip()


def ask_async(cfg, history, on_done):
    def run():
        try:
            on_done(ask(cfg, history), None)
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read().decode()).get("error", {})
                msg = msg.get("message", str(msg)) if isinstance(msg, dict) else str(msg)
            except Exception:
                msg = str(e)
            on_done(None, f"AI error {e.code}: {msg}")
        except Exception as e:
            on_done(None, f"AI error: {e}")
    threading.Thread(target=run, daemon=True).start()
