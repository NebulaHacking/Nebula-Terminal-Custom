"""Boîte à outils crypto / encodage / fichiers — fonctions pures (stdlib uniquement).

L'affichage est fait dans terminal/commands/crypto.py ; ici on ne fait que calculer,
pour que tout soit testable (tests/test_tools.py).
"""
import base64
import binascii
import codecs
import hashlib
import html
import ipaddress
import json
import math
import re
import secrets
import string
import time
import urllib.parse
from datetime import datetime, timezone

# ---------------------------------------------------------------------
# Encodage
# ---------------------------------------------------------------------
_ENCODERS = {
    "b64": lambda s: base64.b64encode(s.encode()).decode(),
    "b32": lambda s: base64.b32encode(s.encode()).decode(),
    "hex": lambda s: s.encode().hex(),
    "url": lambda s: urllib.parse.quote(s, safe=""),
    "rot13": lambda s: codecs.encode(s, "rot13"),
    "bin": lambda s: " ".join(f"{b:08b}" for b in s.encode()),
    "html": html.escape,
}


def _unpad_b64(s: str) -> bytes:
    s = s.strip().replace("-", "+").replace("_", "/")  # accepte aussi le base64 "URL-safe"
    return base64.b64decode(s + "=" * (-len(s) % 4), validate=True)


_DECODERS = {
    "b64": lambda s: _unpad_b64(s).decode("utf-8", "replace"),
    "b32": lambda s: base64.b32decode(s.strip().upper() + "=" * (-len(s.strip()) % 8)).decode("utf-8", "replace"),
    "hex": lambda s: bytes.fromhex(re.sub(r"0x|[\s:,]", "", s)).decode("utf-8", "replace"),
    "url": urllib.parse.unquote,
    "rot13": lambda s: codecs.decode(s, "rot13"),
    "bin": lambda s: bytes(int(b, 2) for b in s.split()).decode("utf-8", "replace"),
    "html": html.unescape,
}
FORMATS = tuple(_ENCODERS)
_ALIASES = {"base64": "b64", "base32": "b32", "binaire": "bin", "binary": "bin", "rot": "rot13"}


def _fmt(name: str) -> str:
    name = name.lstrip("-").lower()
    name = _ALIASES.get(name, name)
    if name not in _ENCODERS:
        raise ValueError(f"Format inconnu '{name}'. Formats : {', '.join(FORMATS)}")
    return name


def encode(fmt: str, text: str) -> str:
    return _ENCODERS[_fmt(fmt)](text)


def decode(fmt: str, text: str) -> str:
    try:
        return _DECODERS[_fmt(fmt)](text)
    except (binascii.Error, ValueError) as e:
        if "Format inconnu" in str(e):
            raise
        raise ValueError(f"Ce texte n'est pas du {_fmt(fmt)} valide ({e})") from e


def decode_auto(text: str) -> list[tuple[str, str]]:
    """Essaie les formats non ambigus et renvoie ceux qui donnent du texte lisible."""
    found = []
    for fmt in ("hex", "bin", "b64", "b32", "url", "html"):
        try:
            out = _DECODERS[fmt](text)
        except Exception:
            continue
        if out and out != text and out.isprintable() and "�" not in out:
            found.append((fmt, out))
    return found


# ---------------------------------------------------------------------
# Hash
# ---------------------------------------------------------------------
HASH_ALGOS = ("md5", "sha1", "sha256", "sha512")


def hash_text(text: str) -> dict[str, str]:
    data = text.encode()
    return {a: hashlib.new(a, data).hexdigest() for a in HASH_ALGOS}


def hash_file(path: str) -> dict[str, str]:
    hs = {a: hashlib.new(a) for a in HASH_ALGOS}
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):  # par blocs : marche sur les gros fichiers
            for h in hs.values():
                h.update(chunk)
    return {a: h.hexdigest() for a, h in hs.items()}


_HASH_PREFIXES = (
    (r"^\$2[abxy]\$\d\d\$", "bcrypt"),
    (r"^\$argon2(id|i|d)\$", "Argon2"),
    (r"^\$1\$", "md5crypt (Unix)"),
    (r"^\$5\$", "sha256crypt (Unix)"),
    (r"^\$6\$", "sha512crypt (Unix)"),
    (r"^\$y\$", "yescrypt (Unix)"),
    (r"^\$apr1\$", "MD5 Apache (apr1)"),
    (r"^\$P\$|^\$H\$", "phpass (WordPress / phpBB)"),
    (r"^pbkdf2[-_]sha256\$", "PBKDF2-SHA256 (Django)"),
    (r"^\*[0-9A-Fa-f]{40}$", "MySQL 4.1+"),
    (r"^[0-9a-fA-F]{32}:[0-9a-fA-F]{32}$", "LM:NTLM (Windows)"),
    (r"^eyJ[\w-]+\.eyJ[\w-]+\.", "Ce n'est pas un hash : c'est un JWT (essayez la commande jwt)"),
)
_HEX_LENGTHS = {
    8: ["CRC32", "Adler-32"],
    16: ["MySQL 3.23", "Demi-hash LM"],
    32: ["MD5", "NTLM", "MD4", "LM"],
    40: ["SHA-1", "RIPEMD-160"],
    56: ["SHA-224", "SHA3-224"],
    64: ["SHA-256", "SHA3-256", "BLAKE2s"],
    96: ["SHA-384", "SHA3-384"],
    128: ["SHA-512", "SHA3-512", "BLAKE2b", "Whirlpool"],
}


def hashid(h: str) -> list[str]:
    """Types probables d'un hash, du plus au moins probable (liste vide si inconnu)."""
    h = h.strip()
    for pattern, name in _HASH_PREFIXES:
        if re.search(pattern, h):
            return [name]
    if re.fullmatch(r"[0-9a-fA-F]+", h):
        return list(_HEX_LENGTHS.get(len(h), []))
    return []


# ---------------------------------------------------------------------
# Réseau : calcul IP
# ---------------------------------------------------------------------
def ipcalc(spec: str) -> dict[str, str]:
    """Infos d'un réseau `ip/cidr` (ou `ip masque`). Une IP seule = /32 (ou /128)."""
    iface = ipaddress.ip_interface(spec.strip().replace(" ", "/"))
    net = iface.network
    hosts = net.num_addresses
    info = {
        "Adresse": str(iface.ip),
        "Réseau": str(net),
        "Masque": str(net.netmask),
        "Type": ("privée" if iface.ip.is_private else "publique")
                + (" / loopback" if iface.ip.is_loopback else "")
                + (" / link-local" if iface.ip.is_link_local else ""),
    }
    if net.version == 4:
        info["Masque inverse"] = str(net.hostmask)
        info["Broadcast"] = str(net.broadcast_address)
        if net.prefixlen < 31:
            hosts -= 2
            info["Premier hôte"] = str(net.network_address + 1)
            info["Dernier hôte"] = str(net.broadcast_address - 1)
    info["Hôtes utilisables"] = f"{hosts:,}".replace(",", " ")
    return info


# ---------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------
def jwt_decode(token: str) -> dict:
    """Décode un JWT SANS vérifier la signature. Renvoie header, payload et alertes."""
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise ValueError("Un JWT a 3 parties séparées par des points (header.payload.signature)")
    try:
        header, payload = (json.loads(_unpad_b64(p)) for p in parts[:2])
    except (binascii.Error, ValueError) as e:
        raise ValueError(f"JWT illisible ({e})") from e
    warnings = []
    if str(header.get("alg", "")).lower() == "none":
        warnings.append("alg=none : le token n'est PAS signé (falsifiable)")
    if not parts[2]:
        warnings.append("signature vide")
    exp = payload.get("exp") if isinstance(payload, dict) else None
    if isinstance(exp, (int, float)):
        when = datetime.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M:%S")
        warnings.append(f"expiré depuis le {when}" if exp < time.time() else f"valide jusqu'au {when}")
    elif isinstance(payload, dict):
        warnings.append("pas de date d'expiration (exp)")
    return {"header": header, "payload": payload, "warnings": warnings}


# ---------------------------------------------------------------------
# Mots de passe
# ---------------------------------------------------------------------
_PW_ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{};:,.?"


def pwgen(length: int = 20) -> str:
    """Mot de passe aléatoire (CSPRNG) avec au moins 1 minuscule, majuscule, chiffre et symbole."""
    if not 8 <= length <= 256:
        raise ValueError("Longueur entre 8 et 256")
    while True:
        pw = "".join(secrets.choice(_PW_ALPHABET) for _ in range(length))
        if (any(c.islower() for c in pw) and any(c.isupper() for c in pw)
                and any(c.isdigit() for c in pw) and any(not c.isalnum() for c in pw)):
            return pw


_COMMON_PW = {"123456", "password", "123456789", "12345678", "azerty", "qwerty", "111111",
              "motdepasse", "admin", "letmein", "welcome", "iloveyou", "000000", "abc123",
              "password1", "azertyuiop", "qwertyuiop", "root", "toor", "doudou", "loulou"}


def pwstrength(pw: str) -> dict:
    """Entropie estimée (taille de l'alphabet utilisé × longueur) + verdict."""
    pool = (26 * any(c.islower() for c in pw) + 26 * any(c.isupper() for c in pw)
            + 10 * any(c.isdigit() for c in pw) + 33 * any(not c.isalnum() for c in pw))
    bits = len(pw) * math.log2(pool) if pool else 0.0
    notes = []
    if pw.lower() in _COMMON_PW:
        bits, notes = 0.0, ["fait partie des mots de passe les plus courants"]
    if len(set(pw)) <= 2 and pw:
        bits = min(bits, 10.0)
        notes.append("caractères répétés")
    if len(pw) < 12:
        notes.append("moins de 12 caractères")
    verdict = ("très faible" if bits < 28 else "faible" if bits < 50 else
               "correct" if bits < 70 else "fort" if bits < 100 else "très fort")
    return {"bits": round(bits, 1), "verdict": verdict, "notes": notes}


# ---------------------------------------------------------------------
# Temps
# ---------------------------------------------------------------------
def ts_convert(value: str = "") -> dict[str, str]:
    """'' → maintenant ; nombre → date ; date ISO (`2026-11-10` ou `2026-11-10 14:30`) → timestamp."""
    value = value.strip()
    if not value:
        t = time.time()
    elif re.fullmatch(r"-?\d+(\.\d+)?", value):
        t = float(value)
        if abs(t) > 1e11:  # millisecondes (JavaScript, Java…)
            t /= 1000
    else:
        try:
            t = datetime.fromisoformat(value.replace("T", " ")).timestamp()
        except ValueError as e:
            raise ValueError("Format attendu : un timestamp, ou une date AAAA-MM-JJ [HH:MM[:SS]]") from e
    return {
        "Timestamp": str(int(t)),
        "Local": datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S"),
        "UTC": datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    }


# ---------------------------------------------------------------------
# Fichiers
# ---------------------------------------------------------------------
_MAGIC = (
    (b"MZ", "Exécutable Windows (PE : .exe / .dll)"),
    (b"\x7fELF", "Exécutable Linux (ELF)"),
    (b"%PDF", "Document PDF"),
    (b"PK\x03\x04", "Archive ZIP (ou .docx / .xlsx / .jar / .apk)"),
    (b"\x89PNG\r\n\x1a\n", "Image PNG"),
    (b"\xff\xd8\xff", "Image JPEG"),
    (b"GIF8", "Image GIF"),
    (b"\x1f\x8b", "Archive GZIP"),
    (b"7z\xbc\xaf\x27\x1c", "Archive 7-Zip"),
    (b"Rar!", "Archive RAR"),
    (b"SQLite format 3", "Base de données SQLite"),
    (b"\xd0\xcf\x11\xe0", "Document Office ancien (.doc / .xls)"),
    (b"\xca\xfe\xba\xbe", "Classe Java / binaire Mach-O"),
    (b"\xd4\xc3\xb2\xa1", "Capture réseau PCAP"),
    (b"\x0a\x0d\x0d\x0a", "Capture réseau PCAPNG"),
    (b"-----BEGIN ", "Clé ou certificat PEM"),
    (b"#!", "Script (shebang)"),
)


def file_type(head: bytes) -> str:
    for magic, name in _MAGIC:
        if head.startswith(magic):
            return name
    if not head:
        return "Fichier vide"
    try:
        head.decode("utf-8")
        return "Texte (UTF-8)"
    except UnicodeDecodeError:
        return "Binaire inconnu"


def entropy(data: bytes) -> float:
    """Entropie de Shannon en bits/octet (0 à 8). Au-dessus de ~7.5 : chiffré ou compressé."""
    if not data:
        return 0.0
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    n = len(data)
    return -sum(c / n * math.log2(c / n) for c in counts if c)


def strings(data: bytes, min_len: int = 4) -> list[str]:
    """Chaînes ASCII imprimables d'au moins `min_len` caractères (comme l'outil Unix `strings`)."""
    return [m.decode("ascii") for m in re.findall(rb"[\x20-\x7e]{%d,}" % max(1, min_len), data)]
