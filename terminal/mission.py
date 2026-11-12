"""Mode mission — encadre un audit autorisé : périmètre, registre de preuves, rapport.

Une mission = un dossier `missions/<nom>/` contenant :
    mission.json   nom, date, périmètre autorisé
    ledger.jsonl   registre : une ligne par commande, chaînée par hash à la précédente
Tant qu'une mission est ouverte :
  - les commandes réseau (GUARDED) sont REFUSÉES si leur cible sort du périmètre ;
  - tout ce qui est lancé (terminal ou dashboard) est inscrit au registre, refus compris.
Modifier ou supprimer une ligne du registre casse la chaîne : `verify()` le détecte.
"""
import difflib
import hashlib
import ipaddress
import json
import re
import socket
import threading
import time
from pathlib import Path

from terminal import events

ROOT = Path(__file__).resolve().parent.parent / "missions"
# Commandes qui contactent une cible : leur 1er argument (hors options) doit être dans le périmètre.
GUARDED = {"scan", "dirb", "banner", "sslscan", "headers", "subdomain", "hostscan", "dns", "whois",
           "ping", "shadowviper", "nexariescan", "iptracker"}
_NAME = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
_GENESIS = "0" * 64
_lock = threading.Lock()
_active: dict | None = None   # {"name", "created", "scope": [...]} de la mission ouverte


# ---------------------------------------------------------------------
# Périmètre
# ---------------------------------------------------------------------
def _host_of(target: str) -> str:
    from Tools.recon import clean_host
    return clean_host(target.split("/")[0] if _is_network(target) else target)


def _is_network(text: str) -> bool:
    try:
        ipaddress.ip_network(text.strip(), strict=False)
        return True
    except ValueError:
        return False


def normalize(entry: str) -> str:
    """Entrée de périmètre valide : IP, réseau CIDR ou domaine (qui couvre ses sous-domaines)."""
    entry = entry.strip().lower()
    if _is_network(entry):
        return str(ipaddress.ip_network(entry, strict=False))
    return _host_of(entry)


def _nets(scope):
    return [ipaddress.ip_network(s) for s in scope if _is_network(s)]


def in_scope(target: str, scope: list[str]) -> bool:
    target = target.strip().lower()
    nets = _nets(scope)
    if _is_network(target):  # IP ou réseau : doit être entièrement contenu dans une entrée
        net = ipaddress.ip_network(target, strict=False)
        return any(net.version == n.version and net.subnet_of(n) for n in nets)
    host = _host_of(target)
    if any(host == d or host.endswith("." + d) for d in scope if not _is_network(d)):
        return True
    try:  # domaine non listé : accepté seulement si TOUTES ses adresses sont dans le périmètre
        ips = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except (socket.gaierror, UnicodeError):
        return False
    return bool(ips) and all(in_scope(ip, scope) for ip in ips)


def guard(command: str, argv: list[str]) -> str | None:
    """Raison du refus si la commande vise une cible hors périmètre, sinon None."""
    if _active is None or command not in GUARDED:
        return None
    target = next((a for a in argv[1:] if not a.startswith("-")), None)
    if target is None:
        if command != "hostscan":
            return None  # pas de cible : la commande affichera son aide
        from Tools.recon import local_network
        target = local_network()
    return check(target)


def check(target: str) -> str | None:
    if _active is None:
        return None
    try:
        ok = in_scope(target, _active["scope"])
    except ValueError:
        ok = False
    if ok:
        return None
    return (f"REFUSÉ : {target} est hors du périmètre de la mission « {_active['name']} » "
            f"({', '.join(_active['scope']) or 'vide'}). Ajoutez-le avec : mission scope add {target}")


# ---------------------------------------------------------------------
# Cycle de vie
# ---------------------------------------------------------------------
def _dir(name: str) -> Path:
    if not _NAME.match(name):
        raise ValueError("Nom de mission : lettres, chiffres, - et _ uniquement (40 max)")
    return ROOT / name


def _write_meta() -> None:
    path = _dir(_active["name"]) / "mission.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(_active, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def active() -> dict | None:
    return _active


def names() -> list[str]:
    return sorted(p.parent.name for p in ROOT.glob("*/mission.json")) if ROOT.is_dir() else []


def new(name: str, scope: list[str], user: str = "") -> dict:
    folder = _dir(name)
    if (folder / "mission.json").exists():
        raise ValueError(f"La mission « {name} » existe déjà (mission open {name})")
    scope = list(dict.fromkeys(normalize(s) for s in scope))
    if not scope:
        raise ValueError("Indiquez au moins une cible autorisée")
    folder.mkdir(parents=True)
    _activate({"name": name, "created": time.strftime("%Y-%m-%d %H:%M:%S"), "owner": user, "scope": scope})
    _write_meta()
    note(f"Mission créée. Périmètre : {', '.join(scope)}")
    return _active


def open_(name: str) -> dict:
    path = _dir(name) / "mission.json"
    if not path.exists():
        raise ValueError(f"Mission inconnue : {name}")
    _activate(json.loads(path.read_text(encoding="utf-8")))
    return _active


def _activate(meta: dict) -> None:
    global _active
    _active = meta
    ROOT.mkdir(exist_ok=True)
    (ROOT / ".active").write_text(meta["name"], encoding="utf-8")
    events.enable()  # capture la sortie des commandes pour le registre
    if _record not in events.listeners:
        events.listeners.append(_record)


def close() -> None:
    global _active
    _active = None
    (ROOT / ".active").unlink(missing_ok=True)


def restore() -> None:
    """Rouvre la mission restée ouverte à la dernière fermeture du terminal."""
    try:
        open_((ROOT / ".active").read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        pass


def scope_add(entry: str) -> str:
    entry = normalize(entry)
    if entry not in _active["scope"]:
        _active["scope"].append(entry)
        _write_meta()
        note(f"Périmètre : ajout de {entry}")
    return entry


def scope_remove(entry: str) -> bool:
    entry = normalize(entry)
    if entry not in _active["scope"]:
        return False
    _active["scope"].remove(entry)
    _write_meta()
    note(f"Périmètre : retrait de {entry}")
    return True


# ---------------------------------------------------------------------
# Registre chaîné
# ---------------------------------------------------------------------
def _ledger(name: str) -> Path:
    return _dir(name) / "ledger.jsonl"


def _digest(entry: dict) -> str:
    body = {k: v for k, v in entry.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def entries(name: str | None = None) -> list[dict]:
    path = _ledger(name or _active["name"])
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _append(source: str, command: str, status: str, duration: float, output: str) -> None:
    with _lock:
        past = entries()
        entry = {"n": len(past) + 1, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "source": source,
                 "command": command, "status": status, "duration": duration, "output": output,
                 "prev": past[-1]["hash"] if past else _GENESIS}
        entry["hash"] = _digest(entry)
        with open(_ledger(_active["name"]), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _record(event: dict) -> None:
    """Appelé pour chaque événement du journal d'activité tant qu'une mission est ouverte."""
    if _active is None or event["source"] == "système":
        return
    output = event["detail"]
    if event.get("blocks"):
        output = json.dumps(event["blocks"], ensure_ascii=False, indent=1)
    try:
        _append(event["source"], event["title"], event["status"], event["duration"], output)
    except OSError as e:
        print(f"[!] Registre de mission : écriture impossible ({e})")


def note(text: str) -> None:
    _append("note", text, "info", 0, "")


# Familles de constats -> référentiels. nLPD art. 8 = « Sécurité des données » (loi suisse sur la protection des données).
# ISO/IEC 27001:2022 = mesures de l'annexe A ; NIS2 = directive (UE) 2022/2555, art. 21 § 2.
CATEGORIES = {
    "chiffrement": ("Chiffrement des échanges", "A.8.24 Utilisation de la cryptographie", "art. 21 § 2 h (cryptographie)",
                    "Les données qui circulent peuvent être lues ou modifiées en chemin."),
    "configuration": ("Configuration", "A.8.9 Gestion des configurations", "art. 21 § 2 e (sécurité des systèmes)",
                      "Un réglage par défaut ou oublié donne des informations ou des possibilités à un attaquant."),
    "exposition": ("Services exposés", "A.8.20 Sécurité des réseaux", "art. 21 § 2 e (sécurité des systèmes)",
                   "Un service accessible depuis Internet alors qu'il ne devrait pas l'être augmente la surface d'attaque."),
    "authentification": ("Authentification", "A.8.5 Authentification sécurisée", "art. 21 § 2 i et j (accès, MFA)",
                         "Des identifiants peuvent être interceptés, devinés ou contournés."),
    "vulnerabilite": ("Logiciel vulnérable ou obsolète", "A.8.8 Gestion des vulnérabilités techniques",
                      "art. 21 § 2 e (gestion des vulnérabilités)",
                      "Une faille connue et publiée peut être exploitée avec des outils disponibles pour tous."),
    "application": ("Sécurité applicative", "A.8.28 Codage sécurisé", "art. 21 § 2 e (développement sécurisé)",
                    "Le site traite mal les données envoyées par les visiteurs (ex. XSS) : vol de session, hameçonnage."),
    "autre": ("Autre", "", "", ""),
}
SEVERITY_ORDER = ["critique", "haute", "moyenne", "basse", "info"]


def finding(severity: str, title: str, evidence: str, recommendation: str,
            category: str = "autre", command: str = "", expect: str = "") -> None:
    """Constat de sécurité : chaîné dans le registre, repris par le rapport.
    `command` + `expect` (texte présent tant que le problème existe) permettent `retest`."""
    _append("constat", f"[{severity}] {title}", "info", 0,
            json.dumps({"severity": severity, "title": title, "evidence": evidence, "recommendation": recommendation,
                        "category": category if category in CATEGORIES else "autre",
                        "command": command, "expect": expect}, ensure_ascii=False))


def findings(name: str | None = None) -> list[dict]:
    """Constats de la mission, triés par gravité, avec le résultat de leur dernier retest."""
    items = entries(name)
    last = {}
    for e in items:
        if e["source"] == "retest" and e["status"] == "info":
            data = json.loads(e["output"])
            last[data["finding"]] = (data["state"], e["time"])
    out = []
    for e in items:
        if e["source"] == "constat":
            f = {"category": "autre", "command": "", "expect": ""} | json.loads(e["output"]) | {"n": e["n"]}
            f["state"], f["checked"] = last.get(e["n"], ("non revérifié", ""))
            out.append(f)
    return sorted(out, key=lambda f: SEVERITY_ORDER.index(f["severity"]) if f["severity"] in SEVERITY_ORDER else 9)


def retest(run) -> list[dict]:
    """Rejoue la preuve de chaque constat. `run(commande)` -> (sortie, statut) ; la commande passe par le
    dispatcher (périmètre appliqué, exécution inscrite au registre). Chaque verdict est inscrit au registre."""
    results = []
    for f in findings():
        if not f["command"] or not f["expect"]:
            state = "non rejouable"
        else:
            output, status = run(f["command"])
            if status != "ok":
                state = f"indéterminé ({status})"
            else:
                state = "toujours présent" if f["expect"].lower() in output.lower() else "corrigé"
            _append("retest", f"retest n°{f['n']} : {state}", "info", 0,
                    json.dumps({"finding": f["n"], "state": state, "command": f["command"]}, ensure_ascii=False))
        results.append(f | {"state": state})
    return results


def verify(name: str | None = None) -> tuple[bool, str]:
    """Recalcule toute la chaîne. (True, résumé) ou (False, première anomalie)."""
    prev, items = _GENESIS, entries(name)
    for i, e in enumerate(items, 1):
        if e.get("n") != i:
            return False, f"ligne {i} : numéro {e.get('n')} (une ligne a été supprimée ou déplacée)"
        if e.get("prev") != prev:
            return False, f"ligne {i} : ne suit pas la ligne précédente (ligne supprimée ou insérée)"
        if e.get("hash") != _digest(e):
            return False, f"ligne {i} : contenu modifié après coup"
        prev = e["hash"]
    return True, f"{len(items)} lignes, chaîne intacte" + (f", empreinte finale {prev[:16]}…" if items else "")


# ---------------------------------------------------------------------
# Comparaison et rapport
# ---------------------------------------------------------------------
def diff(command: str) -> list[str] | None:
    """Différences entre les deux dernières exécutions réussies de `command`. None s'il en manque."""
    runs = [e for e in entries() if e["command"].strip() == command.strip() and e["status"] == "ok"]
    if len(runs) < 2:
        return None
    old, new_ = runs[-2], runs[-1]
    return list(difflib.unified_diff(old["output"].splitlines(), new_["output"].splitlines(),
                                     f"{old['time']} (n°{old['n']})", f"{new_['time']} (n°{new_['n']})",
                                     lineterm="", n=1))


def report(max_lines: int = 60) -> Path:
    """Écrit le rapport de la mission (rapport.md + rapport.html à imprimer en PDF) et renvoie le chemin du .md."""
    m, items = _active, entries()
    ok, detail = verify()
    runs = [e for e in items if e["source"] not in ("note", "constat", "retest")]
    refused = [e for e in runs if e["status"] == "refusé"]
    found = findings()
    cell = lambda s: str(s).replace("|", "\\|").replace("\n", " ")  # noqa: E731
    out = [f"# Rapport de mission — {m['name']}", "",
           f"- **Créée le :** {m['created']}" + (f" par {m['owner']}" if m.get("owner") else ""),
           f"- **Périmètre autorisé :** {', '.join(m['scope'])}",
           f"- **Période :** {items[0]['time']} → {items[-1]['time']}" if items else "- **Période :** aucune activité",
           f"- **Commandes :** {len(runs)} dont {len(refused)} refusées (hors périmètre)",
           f"- **Intégrité du registre :** {'intacte' if ok else 'ANOMALIE'} — {detail}", ""]
    if found:
        out += ["## Constats", "", "| Gravité | Constat | Catégorie | État | Registre |", "|---|---|---|---|---|"]
        out += [f"| {f['severity']} | {cell(f['title'])} | {CATEGORIES[f['category']][0]} | {f['state']} | n°{f['n']} |"
                for f in found]
        for f in found:
            out += ["", f"### [{f['severity']}] {f['title']}", "", f"**Preuve :** {f['evidence']}", "",
                    f"**Correction :** {f['recommendation']}"]
            if f["command"]:
                out += ["", f"**Vérifier la correction :** `{f['command']}` (le problème est corrigé quand "
                            f"« {f['expect']} » n'apparaît plus) — état : {f['state']}"
                            + (f", le {f['checked']}" if f["checked"] else "")]
        compliance = _compliance(found)
        if compliance:
            out += ["", "## Conformité", "",
                    "Ce que chaque famille de constats touche dans les référentiels (repères, pas un audit de conformité).", "",
                    "| Famille | Constats | nLPD | ISO/IEC 27001:2022 | NIS2 | En clair |", "|---|---|---|---|---|---|"]
            out += [f"| {c['label']} | {c['count']} | art. 8 | {c['iso']} | {c['nis2']} | {c['plain']} |" for c in compliance]
        out.append("")
    out += ["## Chronologie", "", "| N° | Heure | Source | Commande | Statut | Durée |", "|---|---|---|---|---|---|"]
    out += [f"| {e['n']} | {e['time']} | {e['source']} | {cell(e['command'])} | {e['status']} | {e['duration']} s |"
            for e in items]
    if refused:
        out += ["", "## Tentatives hors périmètre (refusées, rien n'a été envoyé)", ""]
        out += [f"- n°{e['n']} — {e['time']} — `{e['command']}`" for e in refused]
    out += ["", "## Résultats", ""]
    for e in runs:
        if e["status"] == "refusé" or not e["output"].strip():
            continue
        lines = e["output"].splitlines()
        more = [f"… ({len(lines) - max_lines} lignes de plus dans le registre)"] if len(lines) > max_lines else []
        fence = "````" if any("```" in l for l in lines) else "```"
        out += [f"### n°{e['n']} — `{e['command']}`", f"{e['time']} · {e['status']} · {e['duration']} s", "",
                fence, *lines[:max_lines], *more, fence, ""]
    folder = _dir(m["name"])
    path = folder / "rapport.md"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    from terminal import report_html
    (folder / "rapport.html").write_text(
        report_html.render(m, items, runs, refused, found, _compliance(found), ok, detail, max_lines), encoding="utf-8")
    return path


def _compliance(found: list[dict]) -> list[dict]:
    rows = []
    for key, (label, iso, nis2, plain) in CATEGORIES.items():
        count = sum(1 for f in found if f["category"] == key)
        if count and key != "autre":
            rows.append({"label": label, "count": count, "iso": iso, "nis2": nis2, "plain": plain})
    return rows
