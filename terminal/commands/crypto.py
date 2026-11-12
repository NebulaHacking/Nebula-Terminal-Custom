"""Commandes crypto / encodage / fichiers — encode, decode, hash, hashid, ipcalc, jwt,
pwgen, pwstrength, ts, uuid, strings, fileinfo.

Moteurs dans Tools/cryptokit.py (stdlib uniquement, aucun import lourd).
Les fichiers visés par hash -f / strings / fileinfo sont de VRAIS fichiers du disque.
"""
import json
import os
import time

from terminal.registry import REGISTRY
from Tools import cryptokit as ck

_STRINGS_MAX = 2000        # lignes affichées au plus par `strings`
_READ_MAX = 50 * 1 << 20   # `strings` / entropie lisent au plus 50 Mo


def _rest(raw: str, skip: int = 1) -> str:
    """Tout ce qui suit les `skip` premiers mots, espaces internes conservés."""
    parts = raw.split(None, skip)
    return parts[skip] if len(parts) > skip else ""


def _path(text: str) -> str:
    """Chemin tapé par l'utilisateur : guillemets retirés, ~ développé."""
    path = os.path.expanduser(text.strip().strip('"').strip("'"))
    if not os.path.isfile(path):
        raise ValueError(f"Fichier introuvable : {path}")
    return path


def _table(rows) -> None:
    rows = list(rows)
    width = max(len(str(k)) for k, _ in rows)
    for k, v in rows:
        print(f"  {str(k):<{width}}  {v}")


# ---------------------------------------------------------------------
# Encodage
# ---------------------------------------------------------------------
_ENC_HELP = """{0} <format> <texte>

Formats : b64, b32, hex, url, rot13, bin, html
Exemples :
   encode b64 Bonjour Nebula
   decode b64 Qm9uam91cg==
   decode auto 4e6562756c61      (essaie tous les formats)"""


@REGISTRY.register("encode", help_text=_ENC_HELP.format("encode"),
                   summary="Encoder un texte (b64, b32, hex, url, rot13, bin, html)")
def _encode(ctx, argv, raw):
    if len(argv) < 3:
        print("Usage : encode <format> <texte>   (formats : " + ", ".join(ck.FORMATS) + ")")
        return
    print(ck.encode(argv[1], _rest(raw, 2)))


@REGISTRY.register("decode", help_text=_ENC_HELP.format("decode"),
                   summary="Décoder un texte (mêmes formats, ou 'auto' pour deviner)")
def _decode(ctx, argv, raw):
    if len(argv) < 3:
        print("Usage : decode <format|auto> <texte>   (formats : " + ", ".join(ck.FORMATS) + ")")
        return
    text = _rest(raw, 2)
    if argv[1].lstrip("-").lower() == "auto":
        found = ck.decode_auto(text)
        if found:
            _table(found)
        else:
            print("Aucun format reconnu.")
        return
    print(ck.decode(argv[1], text))


# ---------------------------------------------------------------------
# Hash
# ---------------------------------------------------------------------
@REGISTRY.register("hash", help_text=(
    "hash <texte>         - MD5, SHA-1, SHA-256 et SHA-512 d'un texte\n"
    "hash -f <fichier>    - Mêmes empreintes pour un fichier du disque\n"
    "hash -c <empreinte> <fichier> - Vérifie qu'un fichier correspond à une empreinte"),
    summary="Empreintes MD5/SHA d'un texte ou d'un fichier (-f, -c pour vérifier)")
def _hash(ctx, argv, raw):
    if len(argv) < 2:
        print("Usage : hash <texte> | hash -f <fichier> | hash -c <empreinte> <fichier>")
        return
    if argv[1] == "-c" and len(argv) > 3:
        expected = argv[2].lower()
        match = [a for a, h in ck.hash_file(_path(_rest(raw, 3))).items() if h == expected]
        print(f"[+] OK : le fichier correspond ({match[0]})" if match
              else "[!] DIFFERENT : aucune empreinte du fichier ne correspond")
        return
    if argv[1] == "-f" and len(argv) > 2:
        _table(ck.hash_file(_path(_rest(raw, 2))).items())
        return
    _table(ck.hash_text(_rest(raw)).items())


@REGISTRY.register("hashid", help_text="hashid <hash>    - Identifier le type probable d'un hash",
                   summary="Identifier le type probable d'un hash")
def _hashid(ctx, argv, raw):
    if len(argv) < 2:
        print("Usage : hashid <hash>")
        return
    kinds = ck.hashid(_rest(raw))
    if not kinds:
        print("Type inconnu (ni un format préfixé connu, ni de l'hexadécimal de longueur standard).")
        return
    print("Types probables (du plus au moins courant) :")
    for k in kinds:
        print(f"  - {k}")


# ---------------------------------------------------------------------
# Réseau / tokens
# ---------------------------------------------------------------------
@REGISTRY.register("ipcalc", help_text=(
    "ipcalc <ip/cidr>     - Réseau, masque, broadcast, plage d'hôtes\n"
    "Exemples : ipcalc 192.168.1.10/24   |   ipcalc 10.0.0.1 255.255.0.0   |   ipcalc 2001:db8::/48"),
    summary="Calcul réseau IP/CIDR (masque, broadcast, hôtes)")
def _ipcalc(ctx, argv, raw):
    if len(argv) < 2:
        print("Usage : ipcalc <ip/cidr>   (ex : ipcalc 192.168.1.10/24)")
        return
    _table(ck.ipcalc(_rest(raw)).items())


@REGISTRY.register("jwt", help_text=(
    "jwt <token>      - Décoder un JWT (header + payload) et signaler les problèmes\n"
    "La signature n'est PAS vérifiée : c'est un outil de lecture."),
    summary="Décoder un JWT (sans vérifier la signature)")
def _jwt(ctx, argv, raw):
    if len(argv) < 2:
        print("Usage : jwt <token>")
        return
    res = ck.jwt_decode(argv[1])
    for part in ("header", "payload"):
        print(f"--- {part} ---")
        print(json.dumps(res[part], indent=2, ensure_ascii=False))
    for w in res["warnings"]:
        print(f"[!] {w}")


# ---------------------------------------------------------------------
# Mots de passe
# ---------------------------------------------------------------------
@REGISTRY.register("pwgen", help_text=(
    "pwgen [longueur] [nombre]   - Générer des mots de passe forts (défaut : 20 caractères, 1)"),
    summary="Générer un mot de passe fort (pwgen [longueur] [nombre])")
def _pwgen(ctx, argv, raw):
    length = int(argv[1]) if len(argv) > 1 else 20
    count = min(int(argv[2]), 100) if len(argv) > 2 else 1
    for _ in range(count):
        print(ck.pwgen(length))


@REGISTRY.register("pwstrength", help_text=(
    "pwstrength       - Évaluer la force d'un mot de passe (entropie)\n"
    "Le mot de passe est demandé ensuite : il n'entre jamais dans l'historique."),
    summary="Évaluer la force d'un mot de passe")
def _pwstrength(ctx, argv, raw):
    if len(argv) > 1:
        # L'historique est sauvegardé sur disque : on refuse le mot de passe en argument et on l'efface.
        if ctx.history and ctx.history[-1] == raw:
            ctx.history[-1] = "pwstrength"
        print("[!] Ne tapez pas le mot de passe sur la ligne de commande (retiré de l'historique).")
    res = ck.pwstrength(input("Mot de passe à évaluer : "))
    print(f"  Entropie : {res['bits']} bits  ->  {res['verdict']}")
    for n in res["notes"]:
        print(f"  [!] {n}")


# ---------------------------------------------------------------------
# Divers
# ---------------------------------------------------------------------
@REGISTRY.register("ts", help_text=(
    "ts               - Timestamp actuel\n"
    "ts <timestamp>   - Timestamp Unix (secondes ou millisecondes) -> date\n"
    "ts <date>        - Date (2026-11-10 ou 2026-11-10 14:30) -> timestamp"),
    summary="Convertir timestamp Unix <-> date")
def _ts(ctx, argv, raw):
    _table(ck.ts_convert(_rest(raw)).items())


@REGISTRY.register("uuid", help_text="uuid [nombre]    - Générer un ou plusieurs UUID v4",
                   summary="Générer des UUID v4")
def _uuid(ctx, argv, raw):
    import uuid
    for _ in range(min(int(argv[1]), 1000) if len(argv) > 1 else 1):
        print(uuid.uuid4())


# ---------------------------------------------------------------------
# Fichiers (disque réel)
# ---------------------------------------------------------------------
def _read_capped(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read(_READ_MAX)


@REGISTRY.register("strings", help_text=(
    "strings <fichier> [-n longueur_min]   - Chaînes lisibles d'un fichier binaire (défaut : 4)\n"
    f"Affiche au plus {_STRINGS_MAX} lignes ; lit au plus 50 Mo."),
    summary="Extraire les chaînes lisibles d'un fichier binaire")
def _strings(ctx, argv, raw):
    if len(argv) < 2:
        print("Usage : strings <fichier> [-n longueur_min]")
        return
    rest, min_len = _rest(raw), 4
    if " -n " in rest:
        rest, _, n = rest.rpartition(" -n ")
        min_len = int(n)
    found = ck.strings(_read_capped(_path(rest)), min_len)
    print("\n".join(found[:_STRINGS_MAX]))
    more = f" ({_STRINGS_MAX} affichées)" if len(found) > _STRINGS_MAX else ""
    print(f"[*] {len(found)} chaînes trouvées{more}")


@REGISTRY.register("fileinfo", help_text=(
    "fileinfo <fichier>   - Type réel (signature), taille, dates, entropie et empreintes"),
    summary="Type réel, taille, dates, entropie et empreintes d'un fichier")
def _fileinfo(ctx, argv, raw):
    if len(argv) < 2:
        print("Usage : fileinfo <fichier>")
        return
    path = _path(_rest(raw))
    st = os.stat(path)
    data = _read_capped(path)
    ent = ck.entropy(data)

    def fmt(t):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))

    _table([
        ("Fichier", os.path.abspath(path)),
        ("Type", ck.file_type(data[:32])),
        ("Taille", f"{st.st_size:,} octets".replace(",", " ")),
        ("Modifié", fmt(st.st_mtime)),
        ("Créé", fmt(st.st_ctime)),
        ("Entropie", f"{ent:.2f} / 8" + ("  (chiffré ou compressé)" if ent > 7.5 else "")),
        *ck.hash_file(path).items(),
    ])
