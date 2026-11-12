"""reqforge — atelier de requêtes HTTP : construire, envoyer, rejouer, comparer, analyser.

Chaque envoi reçoit un numéro (historique partagé entre le terminal et le dashboard).
Ce qui va plus loin qu'un « Repeater » classique :
  - analyse passive automatique de chaque réponse, en français (en-têtes, cookies, CORS,
    paramètres renvoyés tels quels, erreurs techniques exposées, adresses internes…) ;
  - comparaison de deux réponses en un coup d'œil (statut, taille, temps, en-têtes, corps) ;
  - export en commande curl ou en script Python, pour rejouer hors de Nebula ;
  - périmètre de mission respecté : impossible d'envoyer vers une cible non autorisée.
Pas de fuzzing ni d'envoi en masse : une requête = une action de l'utilisateur.
"""
import difflib
import itertools
import json
import os
import re
import shlex
import time
from urllib.parse import parse_qsl, urlsplit

MAX_BODY = 2 * 1024 * 1024
MAX_HISTORY = 200
SHOW_BODY = 20000
METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")
DEFAULT_UA = "Mozilla/5.0 (Nebula reqforge)"
HISTORY: list[dict] = []
_ids = itertools.count(1)
_loaded_for = None  # mission dont l'historique a été rechargé
_METHOD = re.compile(r"^[A-Z]{1,16}$")

_ERRORS = (("Traceback (most recent call last)", "Python"), ("SQLSTATE[", "SQL (PDO)"),
           ("You have an error in your SQL syntax", "MySQL"), ("ORA-0", "Oracle"), ("Microsoft OLE DB", "SQL Server"),
           ("Fatal error:", "PHP"), ("Warning: ", "PHP"), ("Exception in thread", "Java"),
           ("at java.", "Java"), ("Whitelabel Error Page", "Spring"), ("System.NullReferenceException", ".NET"),
           ("Server Error in '/' Application", "ASP.NET"), ("pg_query()", "PostgreSQL"))
_PRIVATE_IP = re.compile(r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]{2,}\b")
_SECRET_PARAM = re.compile(r"pass|pwd|token|secret|apikey|api_key|auth", re.I)


# ---------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------
def parse_headers(text):
    """Texte « Nom: valeur » (un par ligne) → liste de paires. Ligne mal formée → ValueError."""
    headers = []
    for line in (text or "").replace("\r\n", "\n").split("\n"):
        if not line.strip():
            continue
        name, sep, value = line.partition(":")
        if not sep or not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name.strip()):
            raise ValueError(f"En-tête mal formé : {line.strip()!r} (format attendu : Nom: valeur)")
        headers.append((name.strip(), value.strip()))
    return headers


def parse_raw(text, scheme="https"):
    """Requête HTTP brute (copiée depuis les outils du navigateur, Burp…) → requête reqforge."""
    text = text.replace("\r\n", "\n").lstrip("\n")
    head, _, body = text.partition("\n\n")
    first, *lines = head.split("\n")
    parts = first.split()
    if len(parts) < 2:
        raise ValueError("Première ligne attendue : MÉTHODE /chemin HTTP/1.1")
    headers = [h for h in parse_headers("\n".join(lines)) if h[0].lower() != "content-length"]
    if parts[1].startswith(("http://", "https://")):
        url = parts[1]
    else:
        host = next((v for k, v in headers if k.lower() == "host"), "")
        if not host:
            raise ValueError("En-tête Host manquant : impossible de savoir où envoyer la requête")
        url = f"{scheme}://{host}{parts[1]}"
    return build(parts[0], url, [h for h in headers if h[0].lower() != "host"], body.rstrip("\n"))


def build(method, url, headers=(), body=""):
    from Tools.recon import clean_host

    method = method.strip().upper()
    if not _METHOD.match(method):
        raise ValueError(f"Méthode invalide : {method!r}")
    url = url.strip()
    if "://" not in url:
        url = "https://" + url
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise ValueError("Seules les URL http:// et https:// sont acceptées")
    if not parts.hostname:
        raise ValueError(f"URL sans nom d'hôte : {url}")
    clean_host(parts.hostname)
    headers = parse_headers(headers) if isinstance(headers, str) else [tuple(h) for h in headers]
    return {"method": method, "url": url, "headers": headers, "body": body or ""}


# ---------------------------------------------------------------------
# Envoi
# ---------------------------------------------------------------------
def _mission_file():
    from terminal import mission
    m = mission.active()
    return (mission.ROOT / m["name"] / "reqforge.jsonl") if m else None


def _sync():
    """Mission ouverte : recharge une fois son historique HTTP (il survit à la fermeture de Nebula)."""
    global _ids, _loaded_for
    path = _mission_file()
    if path is None or _loaded_for == path:
        return
    _loaded_for = path
    known = {e["n"] for e in HISTORY}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
            except ValueError:
                continue  # ligne abîmée : on garde le reste
            if entry.get("n") not in known:
                HISTORY.append(entry)
        HISTORY.sort(key=lambda e: e["n"])
        del HISTORY[:-MAX_HISTORY]
    _ids = itertools.count(max((e["n"] for e in HISTORY), default=0) + 1)


def send(req, verify=True, follow=False, timeout=20):
    """Envoie la requête telle quelle (aucun en-tête ajouté, sauf User-Agent s'il manque)."""
    import requests
    from terminal import mission

    _sync()
    refusal = mission.check(req["url"])
    if refusal:
        raise PermissionError(refusal)
    headers = list(req["headers"])
    if not any(k.lower() == "user-agent" for k, _ in headers):
        headers.append(("User-Agent", DEFAULT_UA))
    session = requests.Session()
    session.headers.clear()  # pas d'en-têtes ajoutés en douce : on envoie ce que l'utilisateur a écrit
    if not verify:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    started = time.perf_counter()
    # shortcut: deux en-têtes du même nom sont fusionnés (le dernier gagne) ; à revoir si un test l'exige.
    r = session.request(req["method"], req["url"], headers=dict(headers), data=req["body"].encode() or None,
                        allow_redirects=follow, verify=verify, timeout=timeout, stream=True)
    content, truncated = b"", False
    for chunk in r.iter_content(65536):
        content += chunk
        if len(content) > MAX_BODY:
            content, truncated = content[:MAX_BODY], True
            break
    r.close()
    elapsed = (time.perf_counter() - started) * 1000
    raw_headers = list(r.raw.headers.items())
    binary = b"\x00" in content[:2048]
    text = f"(contenu binaire, {len(content)} octets)" if binary else _decode(content, r.headers.get("Content-Type", ""))
    resp = {"status": r.status_code, "reason": r.reason or "", "url": r.url, "headers": raw_headers, "body": text,
            "size": len(content), "truncated": truncated, "ms": round(elapsed), "redirects": [h.url for h in r.history],
            "version": {10: "HTTP/1.0", 11: "HTTP/1.1"}.get(getattr(r.raw, "version", 11), "HTTP")}
    entry = {"n": next(_ids), "time": time.strftime("%H:%M:%S"), "verify": verify, "follow": follow,
             "request": {**req, "headers": headers}, "response": resp, "findings": analyze(req, resp)}
    HISTORY.append(entry)
    del HISTORY[:-MAX_HISTORY]
    path = _mission_file()
    if path is not None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def _decode(content, ctype):
    """Charset annoncé, sinon UTF-8, sinon Latin-1. (requests suppose Latin-1 pour tout text/* sans
    charset, ce qui casse les accents des sites francophones.)"""
    m = re.search(r"charset=[\"']?([\w.-]+)", ctype, re.I)
    if m:
        try:
            return content.decode(m.group(1), "replace")
        except LookupError:
            pass
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")


def get(n):
    _sync()
    for entry in HISTORY:
        if entry["n"] == int(n):
            return entry
    raise ValueError(f"Requête n°{n} introuvable (reqforge list pour l'historique)")


def variant(entry, method=None, url=None, headers=(), body=None):
    """Copie d'une requête de l'historique avec des modifications (en-têtes remplacés par nom)."""
    req = entry["request"]
    replaced = {k.lower(): (k, v) for k, v in (parse_headers(headers) if isinstance(headers, str) else headers)}
    merged = [replaced.pop(k.lower(), (k, v)) for k, v in req["headers"]]
    return build(method or req["method"], url or req["url"], merged + list(replaced.values()),
                 req["body"] if body is None else body)


# ---------------------------------------------------------------------
# Analyse passive
# ---------------------------------------------------------------------
def _params(req):
    parts = urlsplit(req["url"])
    params = parse_qsl(parts.query, keep_blank_values=True)
    ctype = next((v for k, v in req["headers"] if k.lower() == "content-type"), "")
    if req["body"] and ("form" in ctype or ("=" in req["body"] and "{" not in req["body"][:1])):
        params += parse_qsl(req["body"], keep_blank_values=True)
    if req["body"][:1] in "{[":
        try:
            data = json.loads(req["body"])
            if isinstance(data, dict):
                params += [(k, str(v)) for k, v in data.items() if isinstance(v, (str, int, float))]
        except ValueError:
            pass
    return params


def analyze(req, resp):
    notes, body = [], resp["body"]
    h = {}
    for k, v in resp["headers"]:
        h.setdefault(k.lower(), []).append(v)
    one = lambda name: (h.get(name) or [""])[-1]  # noqa: E731
    ctype = one("content-type").lower()

    if resp["status"] >= 500:
        notes.append(["warn", f"Erreur serveur {resp['status']}"])
    for marker, tech in _ERRORS:
        if marker in body:
            notes.append(["bad", f"Message d'erreur technique {tech} exposé dans la réponse"])
            break
    for name in ("server", "x-powered-by", "x-aspnet-version", "x-generator"):
        if re.search(r"\d", one(name)):
            notes.append(["warn", f"Version logicielle exposée : {name.title()}: {one(name)}"])
    if "html" in ctype:
        from Tools.recon import SECURITY_HEADERS
        missing = [k for k in SECURITY_HEADERS if k.lower() not in h
                   and not (k == "Strict-Transport-Security" and resp["url"].startswith("http://"))]
        if missing:
            notes.append(["warn", f"En-têtes de sécurité absents : {', '.join(missing)}"])
    for cookie in h.get("set-cookie", []):
        low = cookie.lower()
        miss = [f for f, t in (("Secure", "secure"), ("HttpOnly", "httponly"), ("SameSite", "samesite")) if t not in low]
        if miss:
            notes.append(["warn", f"Cookie {cookie.split('=', 1)[0].strip()} sans {', '.join(miss)}"])
    acao, origin = one("access-control-allow-origin"), next((v for k, v in req["headers"] if k.lower() == "origin"), "")
    credentials = one("access-control-allow-credentials").lower() == "true"
    if origin and acao == origin and origin != "null":
        if credentials:  # n'importe quel site peut lire les réponses avec la session de la victime
            notes.append(["bad", f"CORS : l'origine envoyée ({origin}) est acceptée AVEC identifiants"])
        else:
            notes.append(["warn", f"CORS : l'origine envoyée ({origin}) est renvoyée telle quelle"])
    elif acao == "*":
        notes.append(["info", "CORS : toutes les origines peuvent lire cette réponse"])
    for name, value in _params(req):
        if len(value) >= 4 and value in body:
            if re.search(r"[<>\"']", value):
                notes.append(["bad", f"Paramètre « {name} » renvoyé SANS échappement dans la réponse (risque XSS à vérifier)"])
            else:
                notes.append(["warn", f"Paramètre « {name} » renvoyé tel quel dans la réponse (tester l'échappement)"])
    internal = sorted(set(_PRIVATE_IP.findall(body)))[:5]
    if internal:
        notes.append(["warn", f"Adresses IP internes visibles : {', '.join(internal)}"])
    emails = sorted(set(_EMAIL.findall(body)))
    if emails:
        notes.append(["info", f"{len(emails)} adresse(s) e-mail dans la réponse : {', '.join(emails[:3])}"])
    if req["url"].startswith("http://") and (any(k.lower() in ("authorization", "cookie") for k, _ in req["headers"])
                                            or any(_SECRET_PARAM.search(k) for k, _ in _params(req))):
        notes.append(["bad", "Identifiants ou session envoyés sans chiffrement (HTTP)"])
    if resp["truncated"]:
        notes.append(["info", f"Réponse coupée à {MAX_BODY // 1024 // 1024} Mo"])
    return notes or [["ok", "Aucun constat"]]


# ---------------------------------------------------------------------
# Comparaison et exports
# ---------------------------------------------------------------------
def diff(a, b):
    ra, rb = a["response"], b["response"]
    ha = {k.lower(): v for k, v in ra["headers"]}
    hb = {k.lower(): v for k, v in rb["headers"]}
    skip = {"date", "age", "expires", "set-cookie", "cf-ray", "x-request-id", "report-to", "nel"}
    rows = [[k, ha.get(k, "—"), hb.get(k, "—")] for k in sorted(set(ha) | set(hb))
            if ha.get(k) != hb.get(k) and k not in skip]
    lines = list(difflib.unified_diff(ra["body"].splitlines(), rb["body"].splitlines(),
                                      f"n°{a['n']}", f"n°{b['n']}", lineterm="", n=2))
    same = ra["status"] == rb["status"] and ra["body"] == rb["body"] and not rows
    delta = rb["size"] - ra["size"]
    notes = [["ok", "Réponses identiques (hors en-têtes variables)"]] if same else [
        ["warn" if ra["status"] != rb["status"] else "info", f"Statut : {ra['status']} → {rb['status']}"],
        ["info", f"Taille : {ra['size']} → {rb['size']} octets ({delta:+d})"],
        ["info", f"Temps : {ra['ms']} → {rb['ms']} ms"]]
    return [{"notes": notes},
            {"title": "Requêtes", "cols": ["", f"n°{a['n']}", f"n°{b['n']}"],
             "rows": [["Méthode", a["request"]["method"], b["request"]["method"]],
                      ["URL", a["request"]["url"], b["request"]["url"]]]},
            {"title": "En-têtes différents", "cols": ["En-tête", f"n°{a['n']}", f"n°{b['n']}"], "rows": rows},
            {"title": "Corps (différences)", "text": "\n".join(lines[:400]) + ("\n…" if len(lines) > 400 else "")
             if lines else "Corps identiques."}]


def to_curl(entry):
    req = entry["request"]
    # Sous Windows, « curl » dans PowerShell est un alias d'Invoke-WebRequest : curl.exe est le vrai.
    parts = ["curl.exe" if os.name == "nt" else "curl", "-i", "-X", req["method"]] + (["-k"] if not entry["verify"] else []) + (["-L"] if entry["follow"] else [])
    for k, v in req["headers"]:
        parts += ["-H", f"{k}: {v}"]
    if req["body"]:
        parts += ["--data-raw", req["body"]]
    return " ".join(shlex.quote(p) for p in parts + [req["url"]])


def to_python(entry):
    req = entry["request"]
    return "\n".join([
        "import requests", "",
        "r = requests.request(",
        f"    {req['method']!r},", f"    {req['url']!r},",
        f"    headers={dict(req['headers'])!r},",
        *([f"    data={req['body']!r},"] if req["body"] else []),
        f"    verify={entry['verify']!r}, allow_redirects={entry['follow']!r}, timeout=20,", ")",
        "print(r.status_code, r.reason)", "print(r.text[:2000])"])


def blocks(entry):
    req, resp = entry["request"], entry["response"]
    body = resp["body"]
    shown = body[:SHOW_BODY] + (f"\n… ({len(body) - SHOW_BODY} caractères de plus)" if len(body) > SHOW_BODY else "")
    return [{"notes": entry["findings"]},
            {"title": f"Réponse n°{entry['n']}", "kv": [
                ["Statut", f"{resp['status']} {resp['reason']}"], ["Temps", f"{resp['ms']} ms"],
                ["Taille", f"{resp['size']} octets" + (" (coupée)" if resp["truncated"] else "")],
                ["URL finale", resp["url"]], *([["Redirections", " → ".join(resp["redirects"])]] if resp["redirects"] else [])]},
            {"title": "En-têtes de réponse", "kv": [[k, v] for k, v in resp["headers"]]},
            {"title": "Corps de la réponse", "text": shown},
            {"title": "Requête envoyée", "text": "\n".join(
                [f"{req['method']} {req['url']}", *(f"{k}: {v}" for k, v in req["headers"]),
                 *(["", req["body"]] if req["body"] else [])])},
            {"title": "Rejouer hors de Nebula (curl)", "text": to_curl(entry)}]


def history_rows():
    _sync()
    return [[str(e["n"]), e["time"], e["request"]["method"], e["request"]["url"][:90],
             str(e["response"]["status"]), f"{e['response']['size']} o", f"{e['response']['ms']} ms",
             str(sum(1 for lvl, _ in e["findings"] if lvl in ("bad", "warn")))] for e in reversed(HISTORY)]


HISTORY_COLS = ["N°", "Heure", "Méthode", "URL", "Statut", "Taille", "Temps", "Constats"]
