#!/usr/bin/env python3
# ping_nebula.py
"""
Ping Nebula — tout-en-un.
- Expose run_ping_command(cmd_string) pour appeler depuis un autre script.
- Peut être utilisé en CLI ou en REPL simple (input("cmd> ")).
Remarque : ICMP brut nécessite les droits administrateur/root.
"""

import argparse
import os
import socket
import struct
import select
import time
import shlex
import sys

# Try to import icmplib if available
try:
    from icmplib import ping as icmplib_ping
    ICMPLIB_AVAILABLE = True
except Exception:
    ICMPLIB_AVAILABLE = False

# ---------- checksum helper ----------
def _icmp_checksum(source_bytes: bytes) -> int:
    """Compute the ICMP checksum for given bytes."""
    count_to = (len(source_bytes) // 2) * 2
    s = 0
    count = 0
    while count < count_to:
        this_val = source_bytes[count + 1] * 256 + source_bytes[count]
        s = s + this_val
        s = s & 0xffffffff
        count = count + 2
    if count_to < len(source_bytes):
        s = s + source_bytes[len(source_bytes) - 1]
        s = s & 0xffffffff
    s = (s >> 16) + (s & 0xffff)
    s = s + (s >> 16)
    answer = ~s & 0xffff
    return answer

# ---------- packet builder ----------
def _build_packet(identifier: int, sequence: int, payload_size: int):
    """Create ICMP Echo Request packet (type 8)."""
    header = struct.pack('!BBHHH', 8, 0, 0, identifier, sequence)
    payload = struct.pack('d', time.time()) + (b'Q' * max(0, payload_size - struct.calcsize('d')))
    chksum = _icmp_checksum(header + payload)
    header = struct.pack('!BBHHH', 8, 0, chksum, identifier, sequence)
    return header + payload

# ---------- raw socket single ping ----------
def _raw_icmp_ping_once(dest_addr: str, timeout: float, payload_size: int, identifier: int, sequence: int):
    """
    Send one ICMP Echo Request using raw sockets and wait for reply.
    Returns RTT in milliseconds or None on timeout.
    Raises PermissionError if raw socket cannot be created.
    """
    try:
        proto = socket.getprotobyname('icmp')
    except Exception:
        proto = socket.IPPROTO_ICMP

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, proto)
    except PermissionError:
        raise
    except OSError as e:
        # Reraise for caller to handle
        raise

    sock.settimeout(timeout)
    try:
        packet = _build_packet(identifier, sequence, payload_size)
        send_time = time.time()
        sock.sendto(packet, (dest_addr, 0))
        while True:
            remaining = timeout - (time.time() - send_time)
            if remaining <= 0:
                return None
            ready = select.select([sock], [], [], remaining)
            if not ready[0]:
                return None
            recv_packet, (addr, _) = sock.recvfrom(65535)
            recv_time = time.time()

            if len(recv_packet) < 20:
                continue
            ip_header_len = (recv_packet[0] & 0x0F) * 4
            icmp_offset = ip_header_len
            if len(recv_packet) < icmp_offset + 8:
                continue
            icmp_header = recv_packet[icmp_offset:icmp_offset + 8]
            r_type, r_code, r_checksum, r_id, r_seq = struct.unpack('!BBHHH', icmp_header)
            if r_type == 0 and r_id == identifier and r_seq == sequence:
                payload_offset = icmp_offset + 8
                if len(recv_packet) >= payload_offset + struct.calcsize('d'):
                    try:
                        sent_ts = struct.unpack('d', recv_packet[payload_offset:payload_offset + struct.calcsize('d')])[0]
                        return (recv_time - sent_ts) * 1000.0
                    except Exception:
                        return (recv_time - send_time) * 1000.0
                else:
                    return (recv_time - send_time) * 1000.0
    finally:
        sock.close()

# ---------- core ping function ----------
def nebula_ping(host: str, count: int = 0, interval: float = 1.0, timeout: float = 2.0, payload_size: int = 56):
    """
    Fonction ping portable (IPv4).
    - host: nom d'hôte ou adresse IPv4
    - count: nombre de paquets (0 = infini)
    - interval: intervalle en secondes
    - timeout: attente en secondes pour une réponse
    - payload_size: taille de la charge utile en bytes (approx)
    """
    # Resolve hostname -> IPv4
    try:
        dest = socket.gethostbyname(host)
    except Exception as e:
        print(f"Impossible de résoudre '{host}': {e}")
        return

    print(f"PING {host} ({dest}) {payload_size} bytes of data.")

    transmitted = 0
    received = 0
    latencies = []
    seq = 1
    identifier = (os.getpid() & 0xFFFF)

    use_icmplib = ICMPLIB_AVAILABLE
    if use_icmplib:
        try:
            # test icmplib signature and permission
            _ = icmplib_ping(dest, count=1, timeout=timeout, payload_size=payload_size, privileged=True)
        except TypeError:
            use_icmplib = False
        except PermissionError:
            print("Erreur: droits insuffisants pour envoyer des paquets ICMP (exécute en root/administrateur).")
            return
        except Exception:
            use_icmplib = False

    try:
        while True:
            transmitted += 1
            latency = None

            if use_icmplib:
                try:
                    res = icmplib_ping(dest, count=1, timeout=timeout, payload_size=payload_size, privileged=True)
                    if hasattr(res, 'rtt') and res.rtt is not None:
                        latency = res.rtt
                    elif hasattr(res, 'avg_rtt') and res.avg_rtt is not None:
                        latency = res.avg_rtt
                    elif hasattr(res, 'min_rtt') and res.min_rtt is not None:
                        latency = res.min_rtt
                    else:
                        latency = None
                except PermissionError:
                    print("Erreur: droits insuffisants pour envoyer des paquets ICMP (exécute en root/administrateur).")
                    return
                except Exception:
                    use_icmplib = False

            if not use_icmplib:
                try:
                    rtt = _raw_icmp_ping_once(dest, timeout, payload_size, identifier, seq)
                    latency = rtt
                except PermissionError:
                    print("Erreur: droits insuffisants pour envoyer des paquets ICMP (exécute en root/administrateur).")
                    return
                except Exception as e:
                    print(f"Erreur (raw fallback): {e}")
                    latency = None

            if latency is None:
                print(f"Request timeout for icmp_seq {seq}")
            else:
                received += 1
                latencies.append(latency)
                print(f"{payload_size} bytes from {dest}: icmp_seq={seq} ttl=64 time={latency:.3f} ms")

            if seq % 10 == 0:
                valid = [x for x in latencies if x is not None]
                if valid:
                    mn = min(valid); mx = max(valid); avg = sum(valid)/len(valid)
                    print(f"   Stats (last {len(valid)}/{len(latencies)}): min={mn:.3f} ms avg={avg:.3f} ms max={mx:.3f} ms")

            if count > 0 and seq >= count:
                break

            seq += 1
            time.sleep(interval)

    except KeyboardInterrupt:
        # utilisateur a pressé Ctrl-C -> sortir et afficher statistiques finales
        pass

    # final report
    loss = (1.0 - (received / transmitted)) * 100.0 if transmitted > 0 else 100.0
    print(f"\n--- {host} ping statistics ---")
    print(f"{transmitted} packets transmitted, {received} received, {loss:.0f}% packet loss")
    if latencies:
        mn = min(latencies)
        mx = max(latencies)
        avg = sum(latencies) / len(latencies)
        mdev = (sum((x - avg) ** 2 for x in latencies) / len(latencies)) ** 0.5
        print(f"rtt min/avg/max/mdev = {mn:.3f}/{avg:.3f}/{mx:.3f}/{mdev:.3f} ms")

# ---------- helper to parse args from a command string ----------
def _parse_ping_args_from_list(args_list):
    """Prend une liste d'arguments (comme sys.argv[1:]) et retourne les options."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("host", nargs='?', default=None)
    parser.add_argument("-c", "--count", type=int, default=0)
    parser.add_argument("-i", "--interval", type=float, default=1.0)
    parser.add_argument("-W", "--timeout", type=float, default=2.0)
    parser.add_argument("-s", "--size", type=int, default=56)
    ns, _ = parser.parse_known_args(args_list)
    return ns

# ---------- fonction publique à appeler depuis un autre script ----------
def run_ping_command(cmd_string: str):
    """
    Appel public : fournis la commande complète que l'utilisateur tape, par ex:
        run_ping_command("ping google.com -c 4 -i 0.5")
    ou si l'utilisateur a juste tapé "ping google.com" (ou "ping 8.8.8.8").
    Cette fonction ne termine pas le programme parent ; elle retourne après le ping.
    """
    if not cmd_string:
        return
    parts = shlex.split(cmd_string)
    # si l'utilisateur a entré "ping ..." et que le script est appelé directement par input,
    # on supprime le token "ping" initial s'il est présent.
    if parts and parts[0].lower() == 'ping':
        parts = parts[1:]
    if not parts:
        print("Usage: ping <host> [-c COUNT] [-i INTERVAL] [-W TIMEOUT] [-s SIZE]")
        return
    ns = _parse_ping_args_from_list(parts)
    if ns.host is None:
        print("Host manquant.")
        return
    nebula_ping(ns.host, count=ns.count, interval=ns.interval, timeout=ns.timeout, payload_size=ns.size)

# ---------- CLI / REPL ----------
def _cli_main():
    parser = argparse.ArgumentParser(description="ping_nebula.py — ping ICMP Python (IPv4)")
    parser.add_argument("host", nargs='?', help="hôte à pinger (nom ou IPv4)")
    parser.add_argument("-c", "--count", type=int, default=0, help="nombre de paquets à envoyer (0 = infini)")
    parser.add_argument("-i", "--interval", type=float, default=1.0, help="intervalle entre paquets en secondes")
    parser.add_argument("-W", "--timeout", type=float, default=2.0, help="timeout en secondes pour une réponse")
    parser.add_argument("-s", "--size", type=int, default=56, help="taille de la charge utile en bytes (approx)")
    parser.add_argument("--repl", action="store_true", help="démarrer en mode REPL (input loop)")
    args = parser.parse_args()

    if args.repl and args.host is None:
        # REPL loop: on lit des commandes de type "ping ...", ou "exit"
        print("Mode REPL. Tape 'exit' pour quitter. Exemple: ping google.com -c 4")
        try:
            while True:
                try:
                    cmd = input("cmd> ").strip()
                except EOFError:
                    break
                if not cmd:
                    continue
                if cmd.lower() in ('exit', 'quit'):
                    break
                # supporte soit "ping google.com ..." soit directement "google.com -c 4"
                if cmd.split()[0].lower() == 'ping':
                    run_ping_command(cmd)
                else:
                    # on essaie d'interpréter la ligne comme une commande ping sans le mot 'ping'
                    run_ping_command("ping " + cmd)
        except KeyboardInterrupt:
            print("\nInterrompu.")
        return

    # Mode CLI standard : arguments fournis directement
    if args.host is None:
        print("Usage: ping_nebula.py <host> [-c COUNT] [-i INTERVAL] [-W TIMEOUT] [-s SIZE]  (ou --repl)")
        return
    nebula_ping(args.host, count=args.count, interval=args.interval, timeout=args.timeout, payload_size=args.size)

if __name__ == "__main__":
    _cli_main()
