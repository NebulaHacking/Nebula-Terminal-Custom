"""Commande `mission` — périmètre autorisé, registre de preuves, comparaison, rapport.

Moteur dans terminal/mission.py.
"""
from terminal import mission as ms
from terminal.registry import REGISTRY

HELP = """mission                          - État de la mission ouverte
mission new <nom> <cible> [...]  - Crée et ouvre une mission (cibles : domaine, IP ou réseau CIDR)
mission open <nom> | close | list
mission scope                    - Affiche le périmètre
mission scope add|rm <cible>     - Modifie le périmètre (inscrit au registre)
mission note <texte>             - Ajoute une note datée au registre
mission log [n]                  - Dernières lignes du registre (défaut : 15)
mission verify                   - Vérifie que le registre n'a pas été modifié
mission diff <commande>          - Ce qui a changé entre les 2 dernières exécutions d'une commande
mission constat <gravité> "<titre>" [options]
                                 - Ajoute un constat à la main (gravité : critique, haute, moyenne, basse, info)
       --preuve "..." --correction "..." --cat <famille> --cmd "<commande>" --attendu "<texte>"
       familles : chiffrement, configuration, exposition, authentification, vulnerabilite, application, autre
mission constats                 - Liste des constats et de leur état
mission retest                   - Rejoue la preuve de chaque constat : corrigé ou toujours présent ?
mission report [--open]          - Rapport Markdown + HTML (à imprimer en PDF) ; --open l'ouvre

Mission ouverte : les commandes réseau visant une cible hors périmètre sont refusées,
et tout ce qui est lancé (terminal, dashboard, Nebula IA) est inscrit au registre.

Retest : un constat est rejouable s'il a une commande (--cmd) et un texte attendu (--attendu)
qui apparaît dans la sortie TANT QUE le problème existe, et plus après la correction
(ex. « Strict-Transport-Security absent », pas juste « Strict-Transport-Security »).
Nebula IA les remplit elle-même.

Exemple :
   mission new audit-acme example.com 192.168.1.0/24
   headers example.com
   mission constat moyenne "HSTS absent" --cat chiffrement --cmd "headers example.com" --attendu "Strict-Transport-Security absent"
   mission retest
   mission report --open"""


def _constat(raw: str) -> None:
    import shlex

    words = shlex.split(raw, posix=True)[2:]
    if len(words) < 2:
        raise ValueError('Usage : mission constat <gravité> "<titre>" [--preuve ...] [--cmd ...] [--attendu ...]')
    severity, title, opts = words[0].lower(), words[1], {}
    if severity not in ms.SEVERITY_ORDER:
        raise ValueError(f"Gravité inconnue : {severity} ({', '.join(ms.SEVERITY_ORDER)})")
    rest = iter(words[2:])
    names = {"--preuve": "evidence", "--correction": "recommendation", "--cat": "category", "--cmd": "command", "--attendu": "expect"}
    for w in rest:
        if w not in names:
            raise ValueError(f"Option inconnue : {w}")
        opts[names[w]] = next(rest, "")
    if opts.get("category", "autre") not in ms.CATEGORIES:
        raise ValueError(f"Famille inconnue : {opts['category']} ({', '.join(ms.CATEGORIES)})")
    ms.finding(severity, title, opts.get("evidence", ""), opts.get("recommendation", ""),
               opts.get("category", "autre"), opts.get("command", ""), opts.get("expect", ""))
    print(f"[+] Constat inscrit au registre : [{severity}] {title}")


def _print_findings(items) -> None:
    if not items:
        print("Aucun constat dans cette mission.")
    marks = {"corrigé": "[+]", "toujours présent": "[!!]"}
    for f in items:
        print(f"  {marks.get(f['state'], '[*]'):<5} n°{f['n']:<4} [{f['severity']}] {f['title']}  —  {f['state']}")


def _need():
    if ms.active() is None:
        raise ValueError("Aucune mission ouverte (mission new <nom> <cible> ou mission open <nom>)")
    return ms.active()


def _status():
    m = ms.active()
    if m is None:
        print("Aucune mission ouverte." + (f" Missions existantes : {', '.join(ms.names())}" if ms.names() else ""))
        print("Créer : mission new <nom> <cible> [cible...]")
        return
    ok, detail = ms.verify()
    print(f"  Mission    {m['name']}  (créée le {m['created']})")
    print(f"  Périmètre  {', '.join(m['scope'])}")
    print(f"  Registre   {'[+]' if ok else '[!] ANOMALIE :'} {detail}")


@REGISTRY.register("mission", help_text=HELP,
                   summary="Mode mission : périmètre autorisé, registre de preuves, rapport")
def _mission(ctx, argv, raw):
    sub = argv[1] if len(argv) > 1 else ""
    args = argv[2:]
    if not sub:
        _status()
    elif sub == "new" and len(args) >= 2:
        m = ms.new(args[0], args[1:], ctx.current_user)
        print(f"[+] Mission « {m['name']} » ouverte. Périmètre : {', '.join(m['scope'])}")
    elif sub == "open" and args:
        m = ms.open_(args[0])
        print(f"[+] Mission « {m['name']} » ouverte. Périmètre : {', '.join(m['scope'])}")
    elif sub == "close":
        name = _need()["name"]
        ms.close()
        print(f"[*] Mission « {name} » fermée. Les commandes ne sont plus enregistrées ni limitées.")
    elif sub == "list":
        current = (ms.active() or {}).get("name")
        print("\n".join(f"  {'*' if n == current else ' '} {n}" for n in ms.names()) or "Aucune mission.")
    elif sub == "scope":
        _need()
        if len(args) == 2 and args[0] == "add":
            print(f"[+] Ajouté au périmètre : {ms.scope_add(args[1])}")
        elif len(args) == 2 and args[0] in ("rm", "remove"):
            print("[+] Retiré du périmètre." if ms.scope_remove(args[1]) else "[-] Cette entrée n'est pas dans le périmètre.")
        else:
            print("\n".join(f"  {s}" for s in _need()["scope"]) or "  (vide)")
    elif sub == "note" and args:
        _need()
        ms.note(raw.split(None, 2)[2])
        print("[+] Note inscrite au registre.")
    elif sub == "log":
        _need()
        for e in ms.entries()[-(int(args[0]) if args else 15):]:
            print(f"  {e['n']:>4}  {e['time']}  {e['source']:<9} {e['status']:<10} {e['command'][:70]}")
    elif sub == "verify":
        _need()
        ok, detail = ms.verify()
        print(f"[+] Registre intact : {detail}" if ok else f"[!] REGISTRE ALTÉRÉ : {detail}")
    elif sub == "diff" and args:
        _need()
        lines = ms.diff(raw.split(None, 2)[2])
        if lines is None:
            print("Il faut au moins deux exécutions réussies de cette commande dans la mission.")
        else:
            print("\n".join(lines) if lines else "Aucune différence entre les deux dernières exécutions.")
    elif sub == "report":
        _need()
        path = ms.report()
        html_path = path.with_suffix(".html")
        print(f"[+] Rapport écrit : {path}\n[+] Version HTML (Ctrl+P → PDF) : {html_path}")
        if "--open" in args:
            import webbrowser
            webbrowser.open(html_path.as_uri())
    elif sub == "constat" and args:
        _need()
        _constat(raw)
    elif sub == "constats":
        _need()
        _print_findings(ms.findings())
    elif sub == "retest":
        _need()
        if not any(f["command"] for f in ms.findings()):
            print("Aucun constat rejouable (il faut --cmd et --attendu, voir mission.help).")
            return
        print("[*] Rejeu des preuves (les commandes passent par le périmètre et sont inscrites au registre)...")
        _print_findings(ms.retest(lambda cmd: REGISTRY.run_quiet(ctx, cmd, "retest")[:2]))
    else:
        print("Usage : mission [new|open|close|list|scope|note|log|verify|diff|constat|constats|retest|report]   (mission.help)")
