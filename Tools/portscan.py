"""Scan de ports — portage dédupliqué des 4 copies de l'ancien main.py (lignes 1189-1290).

Les anciens modes `-f` / `-a` / `-s` / normal étaient 4 boucles quasi identiques.
Ils ne sont plus que des configurations (timeout + range + chunking) d'une seule
fonction `scan_ports()`. Vérification : il n'existe qu'UNE boucle de scan
(dans `_scan_range`).

Modes :
  fast    - timeout 0.01, ports 1-1024 (override port_min/port_max possible)
  all     - timeout 0.3,  ports 1-65535 (fixes)
  stealth - timeout 0.1,  4 scans successifs de 256 ports (1-256, 257-512, ...)
  normal  - timeout 0.3,  ports 1-1024 (override port_min/port_max possible)
"""
import socket
import time

from colorama import Fore, Style

_SCAN_MODES = {
    "fast":    {"timeout": 0.01, "port_min": 1, "port_max": 1024},
    "all":     {"timeout": 0.30, "port_min": 1, "port_max": 65535},
    "stealth": {"timeout": 0.10, "port_min": 1, "port_max": 256, "chunked": True},
    "normal":  {"timeout": 0.30, "port_min": 1, "port_max": 1024},
}


def _probe(host: str, port: int, timeout: float) -> bool:
    """True si le port est ouvert (connect_ex == 0)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0
    finally:
        s.close()


def _scan_range(host: str, port_min: int, port_max: int, timeout: float,
                label: int | None = None) -> None:
    """Une passe de scan sur [port_min, port_max]. label=None -> "Scan terminé ...",
    sinon "Scan {label} terminé ..." (parité avec le mode -s de l'original)."""
    print(f"Scan des ports de {host} ({port_min}-{port_max})...")
    start_time = time.time()

    for port in range(port_min, port_max + 1):
        if _probe(host, port, timeout):
            print(Style.BRIGHT + Fore.GREEN + f"Port {port} ouvert")

    duration = time.time() - start_time
    timing = f"Scan terminé en {duration:.2f} secondes." if label is None \
        else f"Scan {label} terminé en {duration:.2f} secondes."
    print(Fore.YELLOW + timing)


def scan_ports(host: str, mode: str = "normal",
               port_min: int | None = None, port_max: int | None = None) -> None:
    """Scanne `host` selon `mode`. port_min/port_max (si fournis) ne s'appliquent
    qu'aux modes fast/normal — parité avec l'ancien main.py (-a et -s ignorent
    les overrides)."""
    config = _SCAN_MODES.get(mode, _SCAN_MODES["normal"])
    timeout = config["timeout"]
    pmin = config["port_min"] if port_min is None else port_min
    pmax = config["port_max"] if port_max is None else port_max

    if config.get("chunked"):
        # -s : 4 passes de 256 ports successives (1-256, 257-512, ..., 1025-1280)
        for i in range(4):
            _scan_range(host, pmin, pmax, timeout, label=i + 1)
            pmin += 256
            pmax += 256
    else:
        _scan_range(host, pmin, pmax, timeout)


if __name__ == "__main__":
    import sys
    scan_ports(sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1")