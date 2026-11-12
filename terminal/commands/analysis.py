"""Commandes d'analyse — tracewave (captures réseau) et reqforge (atelier HTTP).

Moteurs dans Tools/tracewave.py et Tools/reqforge.py ; affichage commun avec le dashboard
via terminal/blocks.py.
"""
import shlex

from terminal.blocks import print_blocks
from terminal.registry import REGISTRY


def _args(raw):
    """Découpe la ligne en respectant les guillemets, sans abîmer les chemins Windows (\\)."""
    out = []
    for token in shlex.split(raw, posix=False)[1:]:
        if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
            token = token[1:-1]
        out.append(token)
    return out


def _options(args, flags=(), valued=()):
    """Sépare les options (-k, -H valeur…) des arguments. Les options à valeur peuvent se répéter."""
    opts, rest, i = {f: False for f in flags} | {v: [] for v in valued}, [], 0
    while i < len(args):
        a = args[i]
        if a in flags:
            opts[a] = True
        elif a in valued:
            if i + 1 >= len(args):
                raise ValueError(f"L'option {a} attend une valeur")
            opts[a].append(args[i + 1])
            i += 1
        else:
            rest.append(a)
        i += 1
    return opts, rest


# ---------------------------------------------------------------------
# tracewave
# ---------------------------------------------------------------------
TRACE_HELP = """tracewave <capture>                 - Analyse complète d'un fichier .pcap ou .pcapng
tracewave <capture> -f <ip>         - Seulement le trafic d'une machine
tracewave compare <avant> <après>   - Ce qui est apparu ou a disparu entre deux captures

Affiche : constats automatiques (protocoles en clair, identifiants visibles — valeur masquée,
balayage de ports, conflit ARP), machines, conversations, services, domaines DNS,
sites HTTPS demandés et requêtes HTTP.

Faire une capture sous Windows sans rien installer (terminal administrateur) :
   pktmon start --capture --pkt-size 0 -f capture.etl
   pktmon stop
   pktmon etl2pcap capture.etl -o capture.pcapng
Ne capturez que des réseaux que vous êtes autorisé à observer."""


@REGISTRY.register("tracewave", aliases=("tw",), help_text=TRACE_HELP,
                   summary="Analyse d'une capture réseau (.pcap / .pcapng) avec constats automatiques")
def _tracewave(ctx, argv, raw):
    from Tools import tracewave as tw
    from terminal.commands.crypto import _path

    opts, args = _options(_args(raw), valued=("-f",))
    if not args:
        print("Usage : tracewave <capture> [-f ip]   |   tracewave compare <avant> <après>   (tracewave.help)")
        return
    from terminal.banner import tool_banner
    tool_banner("TRACEWAVE", "Analyse de captures réseau")
    if args[0] == "compare":
        if len(args) != 3:
            raise ValueError("Usage : tracewave compare <avant> <après>")
        print_blocks(tw.compare(_path(args[1]), _path(args[2])))
        return
    print_blocks(tw.blocks(tw.analyze(_path(" ".join(args)), opts["-f"][-1] if opts["-f"] else None)))


# ---------------------------------------------------------------------
# reqforge
# ---------------------------------------------------------------------
FORGE_HELP = """reqforge <MÉTHODE> <url> [-H "Nom: valeur"]... [-d corps] [-k] [-L]
reqforge raw <fichier> [-http] [-k]   - Envoie une requête brute enregistrée dans un fichier
reqforge list                         - Historique de la session
reqforge show <n> [-b]                - Revoir une requête et sa réponse (-b : corps complet)
reqforge replay <n> [-X MÉTHODE] [-u url] [-H "Nom: valeur"]... [-d corps]
reqforge diff <n> <m>                 - Comparer deux réponses
reqforge curl <n> | python <n>        - Exporter pour rejouer hors de Nebula

Options : -k = ne pas vérifier le certificat TLS, -L = suivre les redirections,
          -http = la requête brute est en HTTP (défaut : HTTPS).
Chaque réponse est analysée automatiquement. En mission, seules les cibles du périmètre sont autorisées.

Exemples :
   reqforge GET https://example.com/ -H "Accept-Language: fr"
   reqforge POST https://site.test/login -d "user=robin&pass=test" -H "Content-Type: application/x-www-form-urlencoded"
   reqforge replay 2 -H "Cookie: session=autre"
   reqforge diff 2 3"""


def _show(entry, full=False):
    print_blocks(entry_blocks(entry), max_text_lines=None if full else 40)


def entry_blocks(entry):
    from Tools import reqforge as rf
    return rf.blocks(entry)


@REGISTRY.register("reqforge", aliases=("rf",), help_text=FORGE_HELP,
                   summary="Atelier HTTP : envoyer, rejouer, comparer et analyser des requêtes")
def _reqforge(ctx, argv, raw):
    from Tools import reqforge as rf
    from terminal.commands.crypto import _path

    opts, args = _options(_args(raw), flags=("-k", "-L", "-b", "-http"), valued=("-H", "-d", "-X", "-u"))
    sub = args[0] if args else "list"
    if not args:  # écran d'accueil seulement : pas de bannière à chaque requête
        from terminal.banner import tool_banner
        tool_banner("REQFORGE", "Atelier de requêtes HTTP")
    headers = "\n".join(opts["-H"])
    body = opts["-d"][-1] if opts["-d"] else None
    if sub == "list":
        print_blocks([{"title": "Historique HTTP", "cols": rf.HISTORY_COLS, "rows": rf.history_rows()}])
    elif sub == "show" and len(args) == 2:
        _show(rf.get(args[1]), opts["-b"])
    elif sub == "diff" and len(args) == 3:
        print_blocks(rf.diff(rf.get(args[1]), rf.get(args[2])), max_text_lines=80)
    elif sub == "curl" and len(args) == 2:
        print(rf.to_curl(rf.get(args[1])))
    elif sub == "python" and len(args) == 2:
        print(rf.to_python(rf.get(args[1])))
    elif sub == "replay" and len(args) == 2:
        old = rf.get(args[1])
        req = rf.variant(old, opts["-X"][-1] if opts["-X"] else None, opts["-u"][-1] if opts["-u"] else None, headers, body)
        _show(rf.send(req, verify=not opts["-k"] and old["verify"], follow=opts["-L"] or old["follow"]))
    elif sub == "raw" and len(args) >= 2:
        with open(_path(" ".join(args[1:])), encoding="utf-8", errors="replace") as f:
            req = rf.parse_raw(f.read(), "http" if opts["-http"] else "https")
        _show(rf.send(req, verify=not opts["-k"], follow=opts["-L"]))
    elif len(args) == 2:
        _show(rf.send(rf.build(args[0], args[1], headers, body or ""), verify=not opts["-k"], follow=opts["-L"]))
    else:
        print("Usage : reqforge <MÉTHODE> <url> [options]   |   reqforge list|show|replay|diff|curl|python   (reqforge.help)")
