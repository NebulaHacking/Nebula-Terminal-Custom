"""Fournisseurs d'IA — une seule fonction `chat()` pour OpenAI, Claude, Gemini, Ollama et les API compatibles OpenAI.

Pas de SDK : de simples appels HTTP (`requests`), donc aucune dépendance en plus.
L'historique est gardé dans un format neutre et traduit à chaque appel : on peut changer
de fournisseur au milieu d'une conversation.

Format neutre :
    {"role": "user", "text": "..."}
    {"role": "assistant", "text": "...", "calls": [{"id", "name", "args"}], "raw": {"provider", "content"}}
    {"role": "tool", "id": "...", "name": "...", "result": "..."}

Avec `on_text`, la réponse arrive en flux (streaming) : `on_text(morceau)` est appelé au fil de l'eau.
Une exception levée par `on_text` (bouton Stop) coupe la connexion.
"""
import json
import os
import uuid

import requests

TIMEOUT = 180

# nom -> (protocole, URL de base, variable d'environnement de la clé, modèle par défaut)
PROVIDERS = {
    "anthropic":  ("anthropic", "https://api.anthropic.com/v1", "ANTHROPIC_API_KEY", "claude-sonnet-5-5"),
    "openai":     ("openai", "https://api.openai.com/v1", "OPENAI_API_KEY", "gpt-4.1-mini"),
    "gemini":     ("gemini", "https://generativelanguage.googleapis.com/v1beta", "GEMINI_API_KEY", "gemini-2.5-flash"),
    "mistral":    ("openai", "https://api.mistral.ai/v1", "MISTRAL_API_KEY", "mistral-large-latest"),
    "groq":       ("openai", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "llama-3.3-70b-versatile"),
    "deepseek":   ("openai", "https://api.deepseek.com/v1", "DEEPSEEK_API_KEY", "deepseek-chat"),
    "openrouter": ("openai", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "openrouter/auto"),
    "ollama":     ("ollama", "http://localhost:11434", None, "llama3.1:8b"),
}
ALIASES = {"claude": "anthropic", "chatgpt": "openai", "gpt": "openai", "google": "gemini", "local": "ollama"}


class ProviderError(Exception):
    pass


def resolve(name: str) -> str:
    name = ALIASES.get(name.lower(), name.lower())
    if name not in PROVIDERS:
        raise ProviderError(f"Fournisseur inconnu : {name}. Choix : {', '.join(PROVIDERS)}")
    return name


def key_env(provider: str) -> str | None:
    return PROVIDERS[provider][2]


def ready(provider: str) -> bool:
    env = key_env(provider)
    return env is None or bool(os.getenv(env))


def _key(provider: str) -> str:
    env = key_env(provider)
    value = os.getenv(env) if env else ""
    if env and not value:
        raise ProviderError(f"Clé {env} absente. Ajoutez-la avec : ia key {provider}")
    return value


def _request(url: str, headers: dict, body: dict, stream: bool) -> requests.Response:
    try:
        r = requests.post(url, headers=headers, json=body, timeout=TIMEOUT, stream=stream)
    except requests.ConnectionError:
        if "localhost" in url or "127.0.0.1" in url:
            raise ProviderError("Ollama ne répond pas : lancez-le (ollama serve) ou installez-le avec nebula_ia_install")
        raise ProviderError("Fournisseur injoignable (connexion réseau ?)")
    except requests.RequestException as e:
        raise ProviderError(f"Erreur réseau : {e}")
    if r.status_code != 200:
        try:
            err = r.json().get("error", r.text)
            err = err.get("message", err) if isinstance(err, dict) else err
        except ValueError:
            err = r.text
        r.close()
        raise ProviderError(f"Erreur {r.status_code} du fournisseur : {str(err)[:300]}")
    return r


def _post(url: str, headers: dict, body: dict) -> dict:
    return _request(url, headers, body, False).json()


def _events(url: str, headers: dict, body: dict):
    """Réponse en flux : un objet JSON par ligne SSE (`data: {...}`) ou NDJSON (Ollama)."""
    with _request(url, headers, body, True) as r:
        try:
            for line in r.iter_lines(decode_unicode=False):
                line = line.decode("utf-8", "replace").strip()
                if line.startswith("data:"):
                    line = line[5:].strip()
                elif line.startswith(("event:", ":")) or not line:
                    continue
                if line == "[DONE]":
                    return
                try:
                    data = json.loads(line)
                except ValueError:
                    continue
                if isinstance(data, dict) and data.get("type") == "error":  # erreur au milieu du flux (Claude)
                    raise ProviderError(f"Erreur du fournisseur : {data.get('error', {}).get('message', data)}")
                yield data
        except requests.RequestException as e:
            raise ProviderError(f"Flux interrompu : {e}")


def _merge(messages: list, role: str, content: list) -> None:
    """Deux messages de même rôle à la suite sont fusionnés (Claude l'exige)."""
    if messages and messages[-1]["role"] == role:
        messages[-1]["content"].extend(content)
    else:
        messages.append({"role": role, "content": content})


def _parse_args(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw or "{}")
        return value if isinstance(value, dict) else {}
    except ValueError:
        return {}


# ---------------------------------------------------------------------
# OpenAI et compatibles (Mistral, Groq, DeepSeek, OpenRouter) + Ollama
# ---------------------------------------------------------------------
def _openai_messages(system, history, ollama=False):
    out = [{"role": "system", "content": system}]
    for m in history:
        if m["role"] == "user":
            out.append({"role": "user", "content": m["text"]})
        elif m["role"] == "assistant":
            msg = {"role": "assistant", "content": m["text"] or ("" if ollama else None)}
            if m.get("calls"):
                msg["tool_calls"] = [{"id": c["id"], "type": "function", "function": {
                    "name": c["name"], "arguments": c["args"] if ollama else json.dumps(c["args"], ensure_ascii=False)}}
                    for c in m["calls"]]
            out.append(msg)
        else:
            msg = {"role": "tool", "content": m["result"]}
            msg.update({"tool_name": m["name"]} if ollama else {"tool_call_id": m["id"]})
            out.append(msg)
    return out


def _with_tools(body: dict, tools: list) -> dict:
    if tools:  # une liste vide est refusée par certaines API
        body["tools"] = [{"type": "function", "function": t} for t in tools]
    return body


def _chat_openai(provider, model, system, history, tools, on_text):
    url = f"{PROVIDERS[provider][1]}/chat/completions"
    headers = {"Authorization": f"Bearer {_key(provider)}"}
    body = _with_tools({"model": model, "messages": _openai_messages(system, history)}, tools)
    if not on_text:
        msg = (_post(url, headers, body).get("choices") or [{}])[0].get("message") or {}
        calls = [{"id": c.get("id") or uuid.uuid4().hex[:12], "name": c["function"]["name"],
                  "args": _parse_args(c["function"].get("arguments"))} for c in msg.get("tool_calls") or []]
        return {"text": msg.get("content") or "", "calls": calls}
    text, parts = [], {}
    for data in _events(url, headers, {**body, "stream": True}):
        delta = ((data.get("choices") or [{}])[0].get("delta")) or {}
        if delta.get("content"):
            text.append(delta["content"])
            on_text(delta["content"])
        for tc in delta.get("tool_calls") or []:  # arguments envoyés par morceaux, regroupés par index
            p = parts.setdefault(tc.get("index", 0), {"id": "", "name": "", "args": ""})
            p["id"] = tc.get("id") or p["id"]
            fn = tc.get("function") or {}
            p["name"] += fn.get("name") or ""
            p["args"] += fn.get("arguments") or ""
    calls = [{"id": p["id"] or uuid.uuid4().hex[:12], "name": p["name"], "args": _parse_args(p["args"])}
             for _, p in sorted(parts.items())]
    return {"text": "".join(text), "calls": calls}


def _chat_ollama(provider, model, system, history, tools, on_text):
    base = os.getenv("OLLAMA_HOST") or PROVIDERS["ollama"][1]
    base = (base if base.startswith("http") else "http://" + base).rstrip("/")
    body = _with_tools({"model": model, "stream": bool(on_text), "messages": _openai_messages(system, history, ollama=True)}, tools)
    chunks = _events(f"{base}/api/chat", {}, body) if on_text else [_post(f"{base}/api/chat", {}, body)]
    text, calls = [], []
    for data in chunks:
        msg = data.get("message") or {}
        if msg.get("content"):
            text.append(msg["content"])
            if on_text:
                on_text(msg["content"])
        calls += [{"id": uuid.uuid4().hex[:12], "name": c["function"]["name"], "args": _parse_args(c["function"].get("arguments"))}
                  for c in msg.get("tool_calls") or []]
    return {"text": "".join(text), "calls": calls}


# ---------------------------------------------------------------------
# Anthropic (Claude)
# ---------------------------------------------------------------------
def _anthropic_messages(history):
    out = []
    for m in history:
        if m["role"] == "user":
            _merge(out, "user", [{"type": "text", "text": m["text"]}])
        elif m["role"] == "assistant":
            content = [{"type": "text", "text": m["text"]}] if m["text"] else []
            content += [{"type": "tool_use", "id": c["id"], "name": c["name"], "input": c["args"]} for c in m.get("calls", [])]
            _merge(out, "assistant", content or [{"type": "text", "text": "…"}])
        else:
            _merge(out, "user", [{"type": "tool_result", "tool_use_id": m["id"], "content": m["result"]}])
    return out


def _chat_anthropic(provider, model, system, history, tools, on_text):
    url = f"{PROVIDERS[provider][1]}/messages"
    headers = {"x-api-key": _key(provider), "anthropic-version": "2023-06-01"}
    body = {"model": model, "max_tokens": 4096, "system": system, "messages": _anthropic_messages(history)}
    if tools:
        body["tools"] = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in tools]
    if not on_text:
        blocks = _post(url, headers, body).get("content") or []
    else:
        blocks = {}
        for ev in _events(url, headers, {**body, "stream": True}):
            if ev.get("type") == "content_block_start":
                b = dict(ev["content_block"])
                b["json"] = ""
                blocks[ev["index"]] = b
            elif ev.get("type") == "content_block_delta":
                b, d = blocks[ev["index"]], ev["delta"]
                if d.get("type") == "text_delta":
                    b["text"] = b.get("text", "") + d["text"]
                    on_text(d["text"])
                elif d.get("type") == "input_json_delta":
                    b["json"] += d.get("partial_json", "")
        blocks = [{**b, "input": _parse_args(b["json"])} if b.get("type") == "tool_use" else b
                  for _, b in sorted(blocks.items())]
    return {"text": "\n".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip(),
            "calls": [{"id": b["id"], "name": b["name"], "args": b.get("input") or {}} for b in blocks if b.get("type") == "tool_use"]}


# ---------------------------------------------------------------------
# Google Gemini
# ---------------------------------------------------------------------
def _merge_parts(contents, role, parts):
    if contents and contents[-1]["role"] == role:
        contents[-1]["parts"].extend(parts)
    else:
        contents.append({"role": role, "parts": list(parts)})


def _gemini_contents(history):
    out = []
    for m in history:
        if m["role"] == "user":
            _merge_parts(out, "user", [{"text": m["text"]}])
        elif m["role"] == "assistant":
            raw = m.get("raw") or {}
            if raw.get("provider") == "gemini":  # tel quel : garde les « thoughtSignature » exigées par Gemini 3
                parts = raw["content"]
            else:
                parts = [{"text": m["text"]}] if m["text"] else []
                parts += [{"functionCall": {"name": c["name"], "args": c["args"]},
                           "thoughtSignature": "skip_thought_signature_validator"} for c in m.get("calls", [])]
            _merge_parts(out, "model", parts or [{"text": "…"}])
        else:
            _merge_parts(out, "user", [{"functionResponse": {"name": m["name"], "response": {"result": m["result"]}}}])
    return out


def _chat_gemini(provider, model, system, history, tools, on_text):
    base, headers = f"{PROVIDERS[provider][1]}/models/{model}", {"x-goog-api-key": _key(provider)}
    body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": _gemini_contents(history)}
    if tools:
        body["tools"] = [{"functionDeclarations": tools}]
    chunks = _events(f"{base}:streamGenerateContent?alt=sse", headers, body) if on_text \
        else [_post(f"{base}:generateContent", headers, body)]
    parts = []
    for data in chunks:
        for p in (((data.get("candidates") or [{}])[0].get("content") or {}).get("parts")) or []:
            parts.append(p)
            if on_text and p.get("text") and not p.get("thought"):
                on_text(p["text"])
    calls = [{"id": uuid.uuid4().hex[:12], "name": p["functionCall"]["name"], "args": p["functionCall"].get("args") or {}}
             for p in parts if "functionCall" in p]
    text = "".join(p["text"] for p in parts if "text" in p and not p.get("thought")).strip()
    return {"text": text, "calls": calls, "raw": {"provider": "gemini", "content": parts}}


_IMPL = {"openai": _chat_openai, "anthropic": _chat_anthropic, "gemini": _chat_gemini, "ollama": _chat_ollama}


def chat(provider: str, model: str, system: str, history: list, tools: list, on_text=None) -> dict:
    """Un tour de modèle. Renvoie {"text", "calls": [{"id", "name", "args"}], "raw"?}."""
    provider = resolve(provider)
    return _IMPL[PROVIDERS[provider][0]](provider, model, system, history, tools, on_text)
