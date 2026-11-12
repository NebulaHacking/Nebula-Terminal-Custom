"""tracewave — analyse de captures réseau (.pcap / .pcapng), en Python pur.

Lit une capture que vous avez faite (Wireshark, tcpdump, ou `pktmon` intégré à Windows) et
répond directement aux questions d'un audit : qui parle à qui, quels services, quels domaines,
et surtout ce qui pose problème (protocoles en clair, identifiants visibles, balayage de ports,
conflit ARP). Les valeurs sensibles (mots de passe, jetons) ne sont JAMAIS affichées.

`analyze()` renvoie des données ; `blocks()` les met au format d'affichage commun
(terminal : terminal/blocks.py, dashboard : NebulaGui).
"""
import ipaddress
import socket
import struct
import time
from collections import Counter, defaultdict

MAX_PACKETS = 2_000_000
_MAX_RECORD = 1 << 20

PORTS = {20: "ftp-data", 21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns", 67: "dhcp", 68: "dhcp",
         69: "tftp", 80: "http", 88: "kerberos", 110: "pop3", 123: "ntp", 135: "msrpc", 137: "netbios",
         138: "netbios", 139: "netbios", 143: "imap", 161: "snmp", 389: "ldap", 443: "https", 445: "smb",
         465: "smtps", 514: "syslog", 587: "smtp-submission", 636: "ldaps", 853: "dns-over-tls", 993: "imaps",
         995: "pop3s", 1433: "mssql", 1900: "ssdp", 3306: "mysql", 3389: "rdp", 5353: "mdns", 5355: "llmnr",
         5432: "postgresql", 5900: "vnc", 6379: "redis", 8080: "http-alt", 8443: "https-alt", 27017: "mongodb"}
# Protocoles qui transportent tout en clair (contenu lisible par n'importe qui sur le chemin).
CLEARTEXT = {21: "FTP", 23: "Telnet", 25: "SMTP", 80: "HTTP", 110: "POP3", 143: "IMAP", 161: "SNMP",
             389: "LDAP", 69: "TFTP", 8080: "HTTP"}
_HTTP_METHODS = (b"GET ", b"POST ", b"PUT ", b"DELETE ", b"HEAD ", b"OPTIONS ", b"PATCH ")
SCAN_THRESHOLD = 15  # ports différents sondés (SYN sans ACK) d'une même machine vers une autre


# ---------------------------------------------------------------------
# Lecture des fichiers
# ---------------------------------------------------------------------
def _packets(path):
    """Génère (timestamp, linktype, data, taille_originale) pour chaque paquet."""
    with open(path, "rb") as f:
        head = f.read(4)
        if len(head) < 4:
            raise ValueError("Fichier vide ou trop court pour être une capture")
        yield from (_pcapng(f) if head == b"\x0a\x0d\x0d\x0a" else _pcap(f, head))


def _pcap(f, magic):
    endian = {b"\xd4\xc3\xb2\xa1": "<", b"\x4d\x3c\xb2\xa1": "<", b"\xa1\xb2\xc3\xd4": ">", b"\xa1\xb2\x3c\x4d": ">"}.get(magic)
    if endian is None:
        raise ValueError("Ce fichier n'est pas une capture pcap ou pcapng")
    divisor = 1e9 if magic in (b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d") else 1e6
    rest = f.read(20)
    if len(rest) < 20:
        raise ValueError("En-tête pcap tronqué")
    linktype = struct.unpack(endian + "I", rest[16:20])[0] & 0x0FFFFFFF
    while True:
        header = f.read(16)
        if len(header) < 16:
            return
        sec, frac, incl, orig = struct.unpack(endian + "IIII", header)
        if incl > _MAX_RECORD:
            raise ValueError("Capture corrompue (paquet de taille impossible)")
        data = f.read(incl)
        if len(data) < incl:
            return  # capture coupée en cours d'écriture : on garde ce qui a été lu
        yield sec + frac / divisor, linktype, data, orig


def _pcapng(f):
    endian, interfaces, block = "<", [], b"\x0a\x0d\x0d\x0a"
    while True:
        size_raw = f.read(4)
        if len(size_raw) < 4:
            return
        if block == b"\x0a\x0d\x0d\x0a":  # Section Header : fixe l'ordre des octets de la section
            bom = f.read(4)
            if bom not in (b"\x4d\x3c\x2b\x1a", b"\x1a\x2b\x3c\x4d"):
                raise ValueError("pcapng corrompu (en-tête de section)")
            endian = "<" if bom == b"\x4d\x3c\x2b\x1a" else ">"
            length = struct.unpack(endian + "I", size_raw)[0]
            f.read(length - 12)
            interfaces = []
        else:
            btype, length = struct.unpack(endian + "I", block)[0], struct.unpack(endian + "I", size_raw)[0]
            if not 12 <= length <= _MAX_RECORD + 64:
                raise ValueError("pcapng corrompu (bloc de taille impossible)")
            body = f.read(length - 8)
            if len(body) < length - 8:
                return
            body = body[:-4]
            if btype == 1:  # Interface Description
                linktype, resolution, opts, i = struct.unpack(endian + "H", body[:2])[0], 1e6, body[8:], 0
                while i + 4 <= len(opts):
                    code, olen = struct.unpack(endian + "HH", opts[i:i + 4])
                    if code == 0:
                        break
                    if code == 9 and olen >= 1:  # if_tsresol
                        v = opts[i + 4]
                        resolution = 2 ** (v & 0x7F) if v & 0x80 else 10 ** v
                    i += 4 + ((olen + 3) & ~3)
                interfaces.append((linktype, resolution))
            elif btype == 6 and len(body) >= 20:  # Enhanced Packet
                iface, high, low, cap, orig = struct.unpack(endian + "IIIII", body[:20])
                if iface < len(interfaces):
                    linktype, resolution = interfaces[iface]
                    yield ((high << 32) | low) / resolution, linktype, body[20:20 + cap], orig
            elif btype == 3 and interfaces and len(body) >= 4:  # Simple Packet
                orig = struct.unpack(endian + "I", body[:4])[0]
                yield 0.0, interfaces[0][0], body[4:4 + orig], orig
        block = f.read(4)
        if len(block) < 4:
            return


# ---------------------------------------------------------------------
# Décodage des couches
# ---------------------------------------------------------------------
def _l3(linktype, d):
    """(ethertype, données) selon le type de lien, ou None si inconnu."""
    if linktype == 1 and len(d) >= 14:  # Ethernet (+ VLAN)
        et, off = struct.unpack("!H", d[12:14])[0], 14
        while et in (0x8100, 0x88A8) and len(d) >= off + 4:
            et, off = struct.unpack("!H", d[off + 2:off + 4])[0], off + 4
        return et, d[off:], d
    if linktype in (101, 12, 14, 228, 229) and d:  # IP brut
        return {4: 0x0800, 6: 0x86DD}.get(d[0] >> 4, 0), d, None
    if linktype == 113 and len(d) >= 16:  # Linux « cooked »
        return struct.unpack("!H", d[14:16])[0], d[16:], None
    if linktype == 276 and len(d) >= 20:  # Linux « cooked » v2
        return struct.unpack("!H", d[0:2])[0], d[20:], None
    if linktype == 0 and len(d) >= 4:  # loopback BSD / Windows
        family = struct.unpack("<I", d[:4])[0]
        return (0x0800 if family == 2 else 0x86DD if family in (10, 23, 24, 28, 30) else 0), d[4:], None
    return None


def _ip(et, p):
    """(source, destination, protocole, données de transport) ou None."""
    if et == 0x0800 and len(p) >= 20:
        ihl, total = (p[0] & 15) * 4, struct.unpack("!H", p[2:4])[0]
        first_fragment = struct.unpack("!H", p[6:8])[0] & 0x1FFF == 0
        payload = p[ihl:total] if total >= ihl else p[ihl:]
        return socket.inet_ntoa(p[12:16]), socket.inet_ntoa(p[16:20]), p[9], payload if first_fragment else b""
    if et == 0x86DD and len(p) >= 40:
        nh, off = p[6], 40
        while nh in (0, 43, 60, 44) and len(p) >= off + 8:  # en-têtes d'extension
            nh, off = p[off], off + (8 if nh == 44 else (p[off + 1] + 1) * 8)
        return (str(ipaddress.IPv6Address(p[8:24])), str(ipaddress.IPv6Address(p[24:40])), nh, p[off:])
    return None


def _qname(p, i):
    labels = []
    while i < len(p) and p[i] and len(labels) < 64:
        if p[i] & 0xC0:  # pointeur de compression : inutile pour une requête simple
            break
        labels.append(p[i + 1:i + 1 + p[i]].decode("ascii", "replace"))
        i += 1 + p[i]
    return ".".join(labels).lower()


def _sni(p):
    """Nom du site demandé dans un ClientHello TLS (extension SNI), ou None."""
    try:
        if p[0] != 0x16 or p[5] != 1:
            return None
        i = 43
        i += 1 + p[i]                                        # session id
        i += 2 + struct.unpack("!H", p[i:i + 2])[0]          # suites de chiffrement
        i += 1 + p[i]                                        # compression
        end = i + 2 + struct.unpack("!H", p[i:i + 2])[0]
        i += 2
        while i + 4 <= min(end, len(p)):
            kind, length = struct.unpack("!HH", p[i:i + 4])
            i += 4
            if kind == 0:
                size = struct.unpack("!H", p[i + 3:i + 5])[0]
                return p[i + 5:i + 5 + size].decode("ascii", "replace").lower() or None
            i += length
    except (IndexError, struct.error):
        pass
    return None


def _service_port(sport, dport):
    for port in (dport, sport):
        if port in PORTS:
            return port
    return min(sport, dport)


def _credential(port, payload):
    """Type d'identifiant visible en clair dans ce paquet (sans sa valeur), ou None."""
    head = payload[:400]
    upper = head.upper()
    if port in (21, 110) and (upper.startswith(b"USER ") or upper.startswith(b"PASS ")):
        return "mot de passe" if upper.startswith(b"PASS ") else "identifiant"
    if port == 143 and b" LOGIN " in upper:
        return "identifiant et mot de passe"
    if port in (25, 587) and upper.startswith(b"AUTH "):
        return "authentification"
    if b"\r\nAUTHORIZATION: BASIC " in upper:
        return "identifiant et mot de passe (HTTP Basic)"
    if b"\r\nAUTHORIZATION: BEARER " in upper:
        return "jeton d'accès"
    return None


# ---------------------------------------------------------------------
# Analyse
# ---------------------------------------------------------------------
def analyze(path, focus=None):
    """Analyse complète d'une capture. `focus` = ne garder que le trafic d'une adresse IP."""
    if focus:
        focus = str(ipaddress.ip_address(focus.strip()))
    r = {"file": path, "packets": 0, "bytes": 0, "first": None, "last": None, "read": 0, "truncated": False,
         "protocols": Counter(), "sent": Counter(), "recv": Counter(), "pkts": Counter(),
         "convs": defaultdict(lambda: [0, 0, set()]), "services": Counter(), "dns": Counter(), "resolvers": Counter(),
         "sni": Counter(), "http": Counter(), "clear": Counter(), "creds": {}, "syn": defaultdict(set), "rst": 0,
         "arp": defaultdict(set)}
    for ts, linktype, data, orig in _packets(path):
        r["read"] += 1
        if r["read"] > MAX_PACKETS:
            r["truncated"] = True
            break
        layer = _l3(linktype, data)
        if layer is None:
            continue
        et, p, frame = layer
        if et == 0x0806 and len(p) >= 28:  # ARP : qui annonce quelle adresse
            sender = socket.inet_ntoa(p[14:18])
            if sender != "0.0.0.0":
                r["arp"][sender].add(p[8:14].hex(":"))
            if not focus or focus == sender:
                r["protocols"]["ARP"] += 1
                r["packets"] += 1
            continue
        ip = _ip(et, p)
        if ip is None:
            continue
        src, dst, proto, l4 = ip
        if focus and focus not in (src, dst):
            continue
        size = orig or len(data)
        r["packets"] += 1
        r["bytes"] += size
        if ts:
            r["first"] = ts if r["first"] is None else min(r["first"], ts)
            r["last"] = ts if r["last"] is None else max(r["last"], ts)
        r["sent"][src] += size
        r["recv"][dst] += size
        r["pkts"][src] += 1
        r["pkts"][dst] += 1
        conv = r["convs"][tuple(sorted((src, dst)))]
        conv[0] += 1
        conv[1] += size

        if proto == 6 and len(l4) >= 20:
            sport, dport = struct.unpack("!HH", l4[:4])
            flags, payload = l4[13], l4[(l4[12] >> 4) * 4:]
            port = _service_port(sport, dport)
            r["protocols"]["TCP"] += 1
            r["services"][("TCP", port)] += 1
            conv[2].add(PORTS.get(port, f"tcp/{port}"))
            if flags & 0x02 and not flags & 0x10:
                r["syn"][(src, dst)].add(dport)
            if flags & 0x04:
                r["rst"] += 1
            if payload:
                if port in CLEARTEXT:
                    r["clear"][CLEARTEXT[port]] += len(payload)
                    what = _credential(port, payload) or ("session Telnet" if port == 23 else None)
                    if what:
                        r["creds"].setdefault((CLEARTEXT[port], src, dst, what), ts)
                if payload.startswith(_HTTP_METHODS):
                    _http(r, payload)
                    if port not in CLEARTEXT:
                        r["clear"]["HTTP"] += len(payload)
                        what = _credential(80, payload)
                        if what:
                            r["creds"].setdefault(("HTTP", src, dst, what), ts)
                elif payload[:1] == b"\x16":
                    name = _sni(payload)
                    if name:
                        r["sni"][name] += 1
        elif proto == 17 and len(l4) >= 8:
            sport, dport = struct.unpack("!HH", l4[:4])
            payload, port = l4[8:], _service_port(sport, dport)
            r["protocols"]["UDP"] += 1
            r["services"][("UDP", port)] += 1
            conv[2].add(PORTS.get(port, f"udp/{port}"))
            if dport in (53, 5353, 5355) and len(payload) > 12 and not payload[2] & 0x80:
                name = _qname(payload, 12)
                if name:
                    r["dns"][name] += 1
                    if dport == 53:
                        r["resolvers"][dst] += 1
            if port == 161 and payload:
                r["clear"]["SNMP"] += len(payload)
        elif proto in (1, 58):
            r["protocols"]["ICMP"] += 1
        else:
            r["protocols"][f"IP proto {proto}"] += 1
    return r


def _http(r, payload):
    line, _, rest = payload[:2048].partition(b"\r\n")
    parts = line.decode("latin-1").split(" ")
    if len(parts) < 2:
        return
    host = ""
    for header in rest.split(b"\r\n"):
        if header[:5].lower() == b"host:":
            host = header[5:].strip().decode("latin-1")
            break
    r["http"][f"{parts[0]} {host}{parts[1]}"[:160]] += 1


# ---------------------------------------------------------------------
# Présentation
# ---------------------------------------------------------------------
def size(n):
    for unit in ("o", "Ko", "Mo", "Go"):
        if n < 1024 or unit == "Go":
            return f"{n:.0f} {unit}" if unit == "o" else f"{n:.1f} {unit}"
        n /= 1024


def findings(r):
    notes = []
    for (svc, src, dst, what) in r["creds"]:
        notes.append(["bad", f"{what[0].upper()}{what[1:]} {svc} visible en clair : {src} → {dst} (valeur masquée)"])
    for ip, macs in r["arp"].items():
        if len(macs) > 1:
            notes.append(["bad", f"Conflit ARP : {ip} annoncée par {len(macs)} cartes réseau ({', '.join(sorted(macs))}). "
                                 "Possible usurpation (ARP spoofing) ou adresse en double."])
    for (src, dst), ports in r["syn"].items():
        if len(ports) >= SCAN_THRESHOLD:
            notes.append(["bad", f"Balayage de ports probable : {src} a sondé {len(ports)} ports de {dst}"])
    for name, nbytes in r["clear"].most_common():
        notes.append(["warn", f"Protocole non chiffré : {name} ({size(nbytes)} lisibles par quiconque est sur le chemin)"])
    if r["packets"] > 100 and r["rst"] > r["packets"] * 0.2:
        notes.append(["warn", f"{r['rst']} connexions TCP refusées ou coupées (RST) : services fermés ou filtrés"])
    if r["truncated"]:
        notes.append(["warn", f"Capture trop grande : seuls les {MAX_PACKETS} premiers paquets ont été analysés"])
    return notes or [["ok", "Aucun constat particulier"]]


def _top(counter, n=25):
    return counter.most_common(n)


def blocks(r):
    duration = (r["last"] - r["first"]) if r["first"] is not None else 0
    stamp = lambda t: time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t)) if t else "inconnu"  # noqa: E731
    hosts = set(r["pkts"])
    total = sum(r["protocols"].values()) or 1
    out = [
        {"notes": findings(r)},
        {"title": "Résumé", "kv": [
            ["Fichier", r["file"]], ["Paquets", f"{r['packets']} (sur {r['read']} lus)"], ["Volume", size(r["bytes"])],
            ["Début", stamp(r["first"])], ["Fin", stamp(r["last"])], ["Durée", f"{duration:.1f} s"],
            ["Débit moyen", f"{size(r['bytes'] / duration)}/s" if duration > 0 else "—"],
            ["Machines", str(len(hosts))], ["Conversations", str(len(r["convs"]))]]},
        {"title": "Protocoles", "cols": ["Protocole", "Paquets", "Part"],
         "rows": [[k, v, f"{v * 100 / total:.1f} %"] for k, v in r["protocols"].most_common()]},
        {"title": "Machines les plus actives", "cols": ["Adresse", "Paquets", "Envoyé", "Reçu"],
         "rows": [[ip, n, size(r["sent"][ip]), size(r["recv"][ip])] for ip, n in _top(r["pkts"], 20)]},
        {"title": "Conversations", "cols": ["Machine A", "Machine B", "Paquets", "Volume", "Services"],
         "rows": [[a, b, c[0], size(c[1]), ", ".join(sorted(c[2])[:6])]
                  for (a, b), c in sorted(r["convs"].items(), key=lambda kv: -kv[1][1])[:25]]},
        {"title": "Services", "cols": ["Port", "Service", "Paquets"],
         "rows": [[f"{proto.lower()}/{port}", PORTS.get(port, ""), n] for (proto, port), n in _top(r["services"], 20)]},
        {"title": "Domaines demandés (DNS)", "cols": ["Nom", "Requêtes"], "rows": _top(r["dns"])},
        {"title": "Sites HTTPS (nom demandé en clair dans TLS)", "cols": ["Nom", "Connexions"], "rows": _top(r["sni"])},
        {"title": "Requêtes HTTP en clair", "cols": ["Requête", "Nombre"], "rows": _top(r["http"])},
    ]
    if r["resolvers"]:
        out.append({"title": "Serveurs DNS utilisés", "cols": ["Adresse", "Requêtes"], "rows": _top(r["resolvers"], 10)})
    return [b if "rows" not in b else {**b, "rows": [[str(c) for c in row] for row in b["rows"]]} for b in out]


def compare(path_a, path_b):
    """Ce qui apparaît ou disparaît entre deux captures (avant / après une modification, par ex.)."""
    a, b = analyze(path_a), analyze(path_b)

    def facts(r):
        return ({("Machine", ip) for ip in r["pkts"]} | {("Domaine DNS", n) for n in r["dns"]}
                | {("Site HTTPS", n) for n in r["sni"]} | {("Protocole en clair", n) for n in r["clear"]}
                | {("Service", f"{p.lower()}/{port} {PORTS.get(port, '')}".strip()) for p, port in r["services"]})

    fa, fb = facts(a), facts(b)
    new, gone = sorted(fb - fa), sorted(fa - fb)
    notes = [["warn" if new else "ok", f"{len(new)} éléments apparus"], ["ok", f"{len(gone)} éléments disparus"]]
    new_clear = [v for k, v in new if k == "Protocole en clair"]
    if new_clear:
        notes.insert(0, ["bad", f"Nouveau protocole non chiffré : {', '.join(new_clear)}"])
    return [{"notes": notes},
            {"title": "Résumé", "cols": ["", "Avant", "Après"],
             "rows": [["Paquets", str(a["packets"]), str(b["packets"])], ["Volume", size(a["bytes"]), size(b["bytes"])],
                      ["Machines", str(len(a["pkts"])), str(len(b["pkts"]))]]},
            {"title": "Apparu dans la 2ᵉ capture", "cols": ["Type", "Valeur"], "rows": [list(x) for x in new]},
            {"title": "Disparu", "cols": ["Type", "Valeur"], "rows": [list(x) for x in gone]}]
