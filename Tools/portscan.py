"""Scan de ports — une seule fonction `scan_ports()`, configurée par mode.

Modes :
  fast    - ports 1-1024, 300 connexions en parallèle
  all     - ports 1-65535, 500 connexions en parallèle (~1 à 2 minutes)
  stealth - 4 passes de 256 ports, UNE connexion à la fois (lent exprès, pour rester discret)
  normal  - ports 1-1024, 100 connexions en parallèle

Les connexions sont parallèles (ThreadPoolExecutor) ; l'unique boucle est dans `_scan_range`.
"""
import socket
import time
from concurrent.futures import ThreadPoolExecutor

from colorama import Fore, Style

_SCAN_MODES = {
    "fast":    {"timeout": 0.3, "port_min": 1, "port_max": 1024, "workers": 300},
    "all":     {"timeout": 0.5, "port_min": 1, "port_max": 65535, "workers": 500},
    "stealth": {"timeout": 0.1, "port_min": 1, "port_max": 256, "workers": 1, "chunked": True},
    "normal":  {"timeout": 0.5, "port_min": 1, "port_max": 1024, "workers": 100},
}


def _probe(host: str, port: int, timeout: float) -> bool:
    """True si le port est ouvert (connect_ex == 0)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0
    except OSError:
        return False
    finally:
        s.close()


def _scan_range(host: str, port_min: int, port_max: int, timeout: float,
                label: int | None = None, workers: int = 100) -> list[int]:
    """Une passe de scan sur [port_min, port_max], en parallèle. Renvoie les ports ouverts.
    label=None -> "Scan terminé ...", sinon "Scan {label} terminé ..." (mode -s)."""
    print(f"Scan des ports de {host} ({port_min}-{port_max})...")
    start_time = time.time()
    ports = range(port_min, port_max + 1)
    open_ports = []

    pool = ThreadPoolExecutor(workers)
    try:
        for port, is_open in zip(ports, pool.map(lambda p: _probe(host, p, timeout), ports)):
            if is_open:
                open_ports.append(port)
                print(Style.BRIGHT + Fore.GREEN + f"Port {port} ouvert" + Style.RESET_ALL)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)  # Ctrl+C : on n'attend pas les ports restants

    duration = time.time() - start_time
    done = "Scan terminé" if label is None else f"Scan {label} terminé"
    print(Fore.YELLOW + f"{done} en {duration:.2f} secondes ({len(open_ports)} ports ouverts)." + Style.RESET_ALL)
    return open_ports


def scan_ports(host: str, mode: str = "normal",
               port_min: int | None = None, port_max: int | None = None) -> list[int]:
    """Scanne `host` selon `mode` et renvoie les ports ouverts. port_min/port_max (si fournis)
    ne s'appliquent qu'aux modes fast/normal."""
    config = _SCAN_MODES.get(mode, _SCAN_MODES["normal"])
    timeout, workers = config["timeout"], config["workers"]
    pmin = config["port_min"] if port_min is None else port_min
    pmax = config["port_max"] if port_max is None else port_max
    if not 1 <= pmin <= pmax <= 65535:
        raise ValueError("Ports attendus : 1 <= min <= max <= 65535")
    try:
        ip = socket.gethostbyname(host)  # une seule résolution DNS au lieu d'une par port
    except socket.gaierror as e:
        raise ValueError(f"Hôte introuvable : {host}") from e

    if not config.get("chunked"):
        return _scan_range(ip, pmin, pmax, timeout, workers=workers)
    # -s : 4 passes de 256 ports successives (1-256, 257-512, ..., 769-1024)
    open_ports = []
    for i in range(4):
        open_ports += _scan_range(ip, pmin + 256 * i, pmax + 256 * i, timeout, label=i + 1, workers=workers)
    return open_ports


if __name__ == "__main__":
    import sys
    scan_ports(sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1")
