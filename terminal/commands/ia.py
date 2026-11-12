"""Commande `ia` — Nebula IA, copilote de pentest (moteur : Nebula_IA/agent.py)."""
import json
import sys

from colorama import Fore, Style

from terminal import mission
from terminal.registry import REGISTRY
from terminal.theme import get_prompt_colors

HELP = """ia - Nebula IA : copilote de pentest qui utilise les outils du terminal

  ia                          conversation (exit pour revenir au terminal)
  ia <question>               une question, ex. : ia audite les en-têtes de example.com
  ia ?  [question]            explique le résultat de la dernière commande (alias : ia explique)
  ia config                   fournisseur, modèle, clés disponibles
  ia provider <nom> [modèle]  anthropic (claude), openai (chatgpt), gemini, mistral, groq,
                              deepseek, openrouter, ollama (local, gratuit, rien ne sort du PC)
  ia model <modèle>           change le modèle du fournisseur actuel
  ia key <fournisseur>        enregistre la clé API dans .env (saisie masquée)
  ia auto on|off              autopilote : commandes réseau sans confirmation, DANS le périmètre
                              de la mission ouverte uniquement
  ia constats                 constats relevés pendant la session
  ia test [fournisseur]       vérifie la clé et le modèle (petit appel réel à chaque fournisseur)
  ia audit <type> <cible>     playbook complet dans la mission ouverte :
                              web, tls, reseau, complet  (ex. : ia audit web example.com)
  ia reset                    nouvelle conversation
  Ctrl+C                      arrête la réponse en cours (bouton Stop dans le dashboard)

Ce qu'elle fait : elle lance elle-même les commandes Nebula (scan, headers, sslscan, reqforge,
tracewave…), lit les résultats, enchaîne et relève les faiblesses avec preuve et correction.
Garde-fous (appliqués par le terminal, pas par le modèle) :
  - commande réseau = votre accord, sauf autopilote en mission ;
  - mission ouverte : cible hors périmètre refusée, et l'IA ne peut pas modifier la mission ;
  - chacune de ses actions est inscrite au registre chaîné (source « ia »), ses constats vont
    dans le rapport (mission report) ;
  - exec, run, update, import/export et les fenêtres lui sont interdits.
Même conversation dans le dashboard (nebulaGui → Nebula IA)."""

_DIM, _RST = Style.DIM, Style.RESET_ALL
_stream = {"on": False}


def _markdown(text: str) -> None:
    try:
        from rich.console import Console
        from rich.markdown import Markdown
        Console().print(Markdown(text))
    except ImportError:
        print(text)


def _printer(item: dict) -> None:
    kind, text = item["kind"], item["text"]
    if kind == "thinking":
        print(f"{_DIM}  ... {text}{_RST}")
    elif kind == "delta":  # réponse en flux : affichée au fil de l'écriture
        if not _stream["on"]:
            _stream["on"] = True
            print()
        sys.stdout.write(text)
        sys.stdout.flush()
    elif kind == "delta_end":
        _stream["on"] = False
        print("\n")
    elif kind == "assistant":
        print()
        _markdown(text)
        print()
    elif kind == "tool":
        status = item.get("status")
        if status == "en cours":
            print(f"{Fore.CYAN}  > {text}{_RST}  {_DIM}{item.get('why', '')}{_RST}")
        elif status in ("bloqué", "refusé par vous"):
            print(f"{Fore.YELLOW}  x {text} : {status}{_RST}")
        else:
            color = Fore.GREEN if status == "ok" else Fore.RED
            print(f"    {color}{status}{_RST}{_DIM} · {item.get('lines', 0)} lignes · {item.get('duration', 0)} s{_RST}")
    elif kind == "finding":
        print(f"{Fore.MAGENTA}  * constat {text}{_RST}")
    elif kind == "error":
        print(f"{Fore.RED}[!] {text}{_RST}")


def _approve(item: dict) -> bool:
    print(f"{Fore.YELLOW}  ? Nebula IA veut lancer : {item['command']}   ({item['reason']}){_RST}")
    if item.get("why"):
        print(f"    raison : {item['why']}")
    try:
        return input("    Autoriser ? [o/N] ").strip().lower() in ("o", "oui", "y", "yes")
    except EOFError:
        return False


def _ask(ctx, text: str) -> None:
    from Nebula_IA import agent

    try:
        agent.get().ask(text, ctx, _approve, _printer)
    except RuntimeError as e:
        print(f"[!] {e}")


def _explain(ctx, extra: str) -> None:
    from Nebula_IA import agent

    e = agent.last_output()
    if e is None:
        print("Aucune commande récente à expliquer : lancez-en une, puis  ia ?")
        return
    output = json.dumps(e["blocks"], ensure_ascii=False) if e.get("blocks") else e["detail"]
    _ask(ctx, f"Explique le résultat de la commande `{e['title']}` (statut : {e['status']}) : ce qui est important, "
              f"les risques éventuels, la prochaine étape logique. Ne relance la commande que si c'est utile."
              f"{' Question : ' + extra if extra else ''}\n<sortie_commande>\n{agent._cap(output) or '(aucune sortie)'}\n</sortie_commande>")


def _config() -> None:
    from Nebula_IA import agent, providers

    a = agent.get()
    print(f"  Fournisseur  {a.provider}  ·  modèle {a.model}")
    print(f"  Autopilote   {'actif' if a.autopilot() else 'demandé, inactif hors mission' if a.cfg['auto'] else 'non'}")
    print()
    for name, (_, _, env, _) in providers.PROVIDERS.items():
        mark = "[+]" if providers.ready(name) else "[ ]"
        model = a.cfg["models"].get(name) or providers.PROVIDERS[name][3]
        print(f"  {mark} {name:<11} {model:<28} {env or 'local, sans clé'}")
    print(f"\n  {_DIM}[ ] = clé absente : ia key <fournisseur>{_RST}")
    if mission.active() and a.provider != "ollama":
        print(f"  {Fore.YELLOW}[!] Mission ouverte : les sorties des commandes partent chez {a.provider}. "
              f"Pour garder les données du client sur ce PC : ia provider ollama{_RST}")


def _chat(ctx) -> None:
    from Nebula_IA import agent

    from terminal.banner import tool_banner

    a = agent.get()
    m = mission.active()
    tool_banner("NEBULA IA", "Copilote de pentest")
    print(f"{get_prompt_colors()['primary']}Nebula IA{_RST} · {a.provider} · {a.model}"
          + (f" · mission {m['name']}" + (" · autopilote" if a.autopilot() else "") if m else " · pas de mission"))
    print(f"{_DIM}exit pour revenir au terminal · /config, /reset, /provider <nom>… pour les réglages{_RST}")
    while True:
        try:
            text = input(f"{get_prompt_colors()['accent']}ia> {_RST}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if text.lower() in ("exit", "quit", "q"):
            return
        if text.startswith("/"):
            if not _sub(ctx, text[1:].split(), text[1:]):
                print("Réglage inconnu (voir ia.help)")
        elif text:
            _ask(ctx, text)


def _sub(ctx, args: list[str], rest: str) -> bool:
    """Sous-commandes de réglage. False si `args` n'en est pas une (c'est alors une question)."""
    from Nebula_IA import agent

    sub = args[0].lower() if args else ""
    a = agent.get()
    try:
        if sub in ("?", "explique", "explain"):
            _explain(ctx, rest.split(None, 1)[1] if len(args) > 1 else "")
        elif sub == "config" and len(args) == 1:
            _config()
        elif sub == "provider" and 2 <= len(args) <= 3:
            a.configure(provider=args[1], model=args[2] if len(args) == 3 else None)
            print(f"[+] Nebula IA utilise {a.provider} · {a.model} (la conversation continue)")
            if not agent.providers.ready(a.provider):
                print(f"[!] Clé absente : ia key {a.provider}")
        elif sub == "model" and len(args) == 2:
            a.configure(model=args[1])
            print(f"[+] Modèle : {a.model}")
        elif sub == "key" and len(args) == 2:
            import getpass
            env = agent.providers.key_env(agent.providers.resolve(args[1]))
            if env is None:
                print(f"{args[1]} n'a pas besoin de clé.")
                return True
            value = getpass.getpass(f"  {env} (saisie masquée) : ")
            print(f"[+] {agent.save_key(args[1], value)} enregistrée dans .env")
        elif sub == "auto" and len(args) == 2 and args[1] in ("on", "off"):
            a.configure(auto=args[1] == "on")
            print("[+] Autopilote actif dans le périmètre de la mission." if args[1] == "on" else "[+] Autopilote coupé.")
        elif sub == "constats" and len(args) == 1:
            for f in a.findings or []:
                print(f"  [{f['severity']}] {f['title']}\n      preuve : {f['evidence'][:200]}\n      correction : {f['recommendation'][:200]}")
            if not a.findings:
                print("Aucun constat pendant cette session." + (" Voir aussi : mission report" if mission.active() else ""))
        elif sub == "test" and len(args) <= 2:
            names = [agent.providers.resolve(args[1])] if len(args) == 2 else None
            print("[*] Petit appel à chaque fournisseur configuré...")
            marks = {"ok": Fore.GREEN + "[+]", "erreur": Fore.RED + "[!]"}
            for name, status, detail in agent.test_providers(names):
                print(f"  {marks.get(status, _DIM + '[ ]')}{_RST} {name:<11} {detail}")
        elif sub == "audit" and len(args) == 3:
            _ask(ctx, agent.playbook_prompt(args[1].lower(), args[2]))
        elif sub == "reset" and len(args) == 1:
            a.reset()
            print("[+] Nouvelle conversation.")
        else:
            return False
    except (ValueError, agent.providers.ProviderError) as e:
        print(f"[!] {e}")
    return True


@REGISTRY.register("ia", aliases=("nebula_ia", "ai"), help_text=HELP,
                   summary="Nebula IA : copilote de pentest (Claude, ChatGPT, Gemini, Ollama…) qui utilise les outils")
def _ia(ctx, argv, raw):
    rest = raw.split(None, 1)[1] if len(argv) > 1 else ""
    if not rest:
        _chat(ctx)
    elif not _sub(ctx, argv[1:], rest):
        _ask(ctx, rest)
