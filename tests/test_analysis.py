"""tracewave (captures fabriquées) et reqforge (serveur HTTP local). Aucun accès Internet."""
import contextlib
import http.server
import io
import json
import shutil
import socket
import struct
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from Tools import reqforge as rf
from Tools import tracewave as tw
from terminal import events, mission
from terminal.context import default_context
from terminal.registry import build_registry

MAC_A, MAC_B = b"\xaa" * 6, b"\xbb" * 6


# ---------------------------------------------------------------------
# Fabrication de paquets
# ---------------------------------------------------------------------
def eth(ethertype, payload, src=MAC_A):
    return b"\x11" * 6 + src + struct.pack("!H", ethertype) + payload


def ipv4(src, dst, proto, payload):
    return struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(payload), 1, 0, 64, proto, 0,
                       socket.inet_aton(src), socket.inet_aton(dst)) + payload


def tcp(src, dst, sport, dport, payload=b"", flags=0x18):
    seg = struct.pack("!HHIIBBHHH", sport, dport, 1, 0, 5 << 4, flags, 65535, 0, 0) + payload
    return eth(0x0800, ipv4(src, dst, 6, seg))


def udp(src, dst, sport, dport, payload):
    return eth(0x0800, ipv4(src, dst, 17, struct.pack("!HHHH", sport, dport, 8 + len(payload), 0) + payload))


def arp(ip, mac):
    return eth(0x0806, struct.pack("!HHBBH", 1, 0x0800, 6, 4, 2) + mac + socket.inet_aton(ip) + b"\x00" * 6 + b"\x00" * 4, mac)


def dns_query(name):
    q = b"".join(bytes([len(l)]) + l.encode() for l in name.split(".")) + b"\x00"
    return struct.pack("!HHHHHH", 0x1234, 0x0100, 1, 0, 0, 0) + q + struct.pack("!HH", 1, 1)


def client_hello(name):
    n = name.encode()
    ext = struct.pack("!HH", 0, len(n) + 5) + struct.pack("!HBH", len(n) + 3, 0, len(n)) + n
    body = b"\x03\x03" + b"\x00" * 32 + b"\x00" + struct.pack("!H", 2) + b"\x13\x01" + b"\x01\x00" + struct.pack("!H", len(ext)) + ext
    hs = b"\x01" + len(body).to_bytes(3, "big") + body
    return b"\x16\x03\x01" + struct.pack("!H", len(hs)) + hs


def write_pcap(path, frames):
    with open(path, "wb") as f:
        f.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        for i, frame in enumerate(frames):
            f.write(struct.pack("<IIII", 1700000000 + i, 0, len(frame), len(frame)) + frame)


def write_pcapng(path, frames):
    def block(btype, body):
        body += b"\x00" * (-len(body) % 4)
        return struct.pack("<II", btype, len(body) + 12) + body + struct.pack("<I", len(body) + 12)

    with open(path, "wb") as f:
        f.write(block(0x0A0D0D0A, struct.pack("<IHHq", 0x1A2B3C4D, 1, 0, -1)))
        f.write(block(1, struct.pack("<HHI", 1, 0, 65535)))
        for frame in frames:
            ts = 1700000000 * 10**6
            f.write(block(6, struct.pack("<IIIII", 0, ts >> 32, ts & 0xFFFFFFFF, len(frame), len(frame)) + frame))


def sample_frames():
    frames = [
        tcp("192.168.1.10", "10.0.0.5", 50000, 21, b"USER robin\r\n"),
        tcp("192.168.1.10", "10.0.0.5", 50000, 21, b"PASS hunter2\r\n"),
        tcp("192.168.1.10", "10.0.0.8", 50001, 80,
            b"GET /admin HTTP/1.1\r\nHost: intranet.test\r\nAuthorization: Basic cm9iaW46aHVudGVyMg==\r\n\r\n"),
        udp("192.168.1.10", "192.168.1.1", 53000, 53, dns_query("secret.example.org")),
        tcp("192.168.1.10", "93.184.216.34", 50002, 443, client_hello("www.example.com")),
        arp("192.168.1.1", MAC_A),
        arp("192.168.1.1", MAC_B),
    ]
    frames += [tcp("192.168.1.66", "192.168.1.20", 40000, port, flags=0x02) for port in range(1, 21)]
    return frames


class TracewaveTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_full_analysis(self):
        path = self.dir / "cap.pcap"
        write_pcap(path, sample_frames())
        r = tw.analyze(str(path))
        self.assertEqual(r["packets"], 27)
        self.assertIn("secret.example.org", r["dns"])
        self.assertIn("www.example.com", r["sni"])
        self.assertIn("GET intranet.test/admin", r["http"])
        notes = " | ".join(t for _, t in tw.findings(r))
        for expected in ("Mot de passe FTP", "HTTP Basic", "Conflit ARP", "a sondé 20 ports", "Protocole non chiffré : FTP"):
            self.assertIn(expected, notes)
        dump = json.dumps(tw.blocks(r), ensure_ascii=False)
        self.assertNotIn("hunter2", dump)          # jamais de valeur sensible affichée
        self.assertNotIn("cm9iaW46aHVudGVyMg", dump)

    def test_pcapng_focus_and_compare(self):
        a, b = self.dir / "a.pcapng", self.dir / "b.pcapng"
        write_pcapng(a, [tcp("10.0.0.1", "10.0.0.2", 5000, 443, client_hello("site.test"))])
        write_pcapng(b, [tcp("10.0.0.1", "10.0.0.2", 5000, 443, client_hello("site.test")),
                         tcp("10.0.0.1", "10.0.0.9", 5001, 23, b"login\r\n")])
        rb = tw.analyze(str(b))
        self.assertEqual((rb["packets"], rb["sni"]["site.test"]), (2, 1))
        self.assertEqual(tw.analyze(str(b), focus="10.0.0.9")["packets"], 1)
        text = json.dumps(tw.compare(str(a), str(b)), ensure_ascii=False)
        self.assertIn("10.0.0.9", text)
        self.assertIn("Nouveau protocole non chiffré : Telnet", text)

    def test_bad_files(self):
        bad = self.dir / "x.pcap"
        bad.write_bytes(b"pas une capture du tout")
        with self.assertRaises(ValueError):
            tw.analyze(str(bad))
        bad.write_bytes(b"")
        with self.assertRaises(ValueError):
            tw.analyze(str(bad))
        cut = self.dir / "cut.pcap"
        write_pcap(cut, sample_frames())
        cut.write_bytes(cut.read_bytes()[:-10])  # capture coupée en cours d'écriture
        self.assertEqual(tw.analyze(str(cut))["packets"], 26)
        with self.assertRaises(ValueError):
            tw.analyze(str(cut), focus="pas-une-ip")

    def test_cli(self):
        path = self.dir / "cap one.pcap"
        write_pcap(path, sample_frames())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            build_registry().dispatch(default_context(), f'tracewave "{path}"')
        self.assertIn("Conflit ARP", out.getvalue())
        self.assertIn("secret.example.org", out.getvalue())


# ---------------------------------------------------------------------
# reqforge
# ---------------------------------------------------------------------
class _Site(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _reply(self, code, body, ctype="text/html"):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Server", "Apache/2.4.1")
        self.send_header("Set-Cookie", "sid=abc; Path=/")
        self.send_header("X-Echo-Lang", self.headers.get("Accept-Language", ""))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/err"):
            return self._reply(500, "Traceback (most recent call last):\n  File app.py")
        q = self.path.partition("q=")[2]
        from urllib.parse import unquote_plus
        self._reply(200, f"<p>Recherche : {unquote_plus(q)}</p><!-- 10.1.2.3 -->")

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
        self._reply(200, f"<p>Reçu {body}</p>")


class ReqforgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Site)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def test_send_and_passive_analysis(self):
        e = rf.send(rf.build("GET", self.base + "/?q=%3Cscript%3Ex", "Accept-Language: fr"))
        self.assertEqual(e["response"]["status"], 200)
        text = " | ".join(t for _, t in e["findings"])
        for expected in ("« q » renvoyé SANS échappement", "Apache/2.4.1", "Cookie sid sans", "10.1.2.3",
                         "En-têtes de sécurité absents"):
            self.assertIn(expected, text)
        self.assertEqual(dict(e["response"]["headers"])["X-Echo-Lang"], "fr")
        err = rf.send(rf.build("GET", self.base + "/err"))
        self.assertIn("erreur technique Python", " ".join(t for _, t in err["findings"]))

    def test_replay_diff_and_exports(self):
        a = rf.send(rf.build("POST", self.base + "/login", "Content-Type: application/x-www-form-urlencoded", "user=robin&pass=x"))
        self.assertIn("sans chiffrement", " ".join(t for _, t in a["findings"]))
        b = rf.send(rf.variant(a, body="user=alice&pass=x", headers="Content-Type: text/plain"))
        self.assertEqual(dict(b["request"]["headers"])["Content-Type"], "text/plain")
        d = json.dumps(rf.diff(a, b), ensure_ascii=False)
        self.assertIn("+<p>Reçu user=alice&pass=x</p>", d)
        self.assertIn("Réponses identiques", json.dumps(rf.diff(a, a), ensure_ascii=False))
        curl = rf.to_curl(a)
        self.assertIn(" -i -X POST", curl)
        self.assertIn("--data-raw", curl)
        compile(rf.to_python(a), "export", "exec")  # le script Python exporté est valide
        self.assertEqual(rf.get(a["n"])["n"], a["n"])
        with self.assertRaises(ValueError):
            rf.get(10**8)

    def test_cors_reflected_origin_with_credentials_is_critical(self):
        req = rf.build("GET", "https://api.test/", "Origin: https://evil.test")
        resp = {"status": 200, "body": "{}", "url": "https://api.test/", "truncated": False,
                "headers": [("Access-Control-Allow-Origin", "https://evil.test"), ("Access-Control-Allow-Credentials", "true")]}
        self.assertIn(["bad", "CORS : l'origine envoyée (https://evil.test) est acceptée AVEC identifiants"], rf.analyze(req, resp))
        resp["headers"] = [("Access-Control-Allow-Origin", "https://evil.test")]
        self.assertEqual(rf.analyze(req, resp)[0][0], "warn")

    def test_parse_raw_and_validation(self):
        req = rf.parse_raw("POST /api?x=1 HTTP/1.1\r\nHost: site.test\r\nContent-Length: 99\r\nCookie: a=b\r\n\r\n{\"k\": 1}")
        self.assertEqual((req["method"], req["url"], req["body"]), ("POST", "https://site.test/api?x=1", '{"k": 1}'))
        self.assertEqual(req["headers"], [("Cookie", "a=b")])
        for bad in (("G ET", "http://x.test"), ("GET", "ftp://x.test"), ("GET", "http://")):
            with self.assertRaises(ValueError):
                rf.build(*bad)
        with self.assertRaises(ValueError):
            rf.parse_headers("pas un en-tête")
        with self.assertRaises(ValueError):
            rf.parse_raw("GET /x HTTP/1.1\r\n\r\n")

    def test_mission_scope_is_enforced(self):
        tmp = Path(tempfile.mkdtemp())
        with mock.patch.object(mission, "ROOT", tmp):
            try:
                mission.new("web", ["127.0.0.1"])
                rf.send(rf.build("GET", self.base + "/"))
                with mock.patch("requests.Session.request") as net:
                    with self.assertRaises(PermissionError):
                        rf.send(rf.build("GET", "http://hors-perimetre.invalid/"))
                    net.assert_not_called()
                out = io.StringIO()
                with contextlib.redirect_stdout(events._Router(out)):
                    build_registry().dispatch(default_context(), "reqforge GET http://hors-perimetre.invalid/")
                self.assertIn("REFUSÉ", out.getvalue())
                self.assertEqual(mission.entries()[-1]["status"], "refusé")
            finally:
                mission.close()
                if mission._record in events.listeners:
                    events.listeners.remove(mission._record)
                shutil.rmtree(tmp, True)

    def test_cli_and_dashboard(self):
        out = io.StringIO()
        reg, ctx = build_registry(), default_context()
        with contextlib.redirect_stdout(out):
            reg.dispatch(ctx, f'reqforge GET {self.base}/?q=bonjour -H "Accept-Language: de"')
            n = rf.HISTORY[-1]["n"]
            reg.dispatch(ctx, f'reqforge replay {n} -H "Accept-Language: it"')
            reg.dispatch(ctx, f"reqforge diff {n} {n + 1}")
            reg.dispatch(ctx, "reqforge list")
        text = out.getvalue()
        self.assertIn("200 OK", text)
        self.assertIn("x-echo-lang", text.lower())
        self.assertIn("it", dict(rf.HISTORY[-1]["response"]["headers"])["X-Echo-Lang"])

        from NebulaGui import server
        server._state.update(ctx=ctx, registry=reg)
        e = server.run_tool("reqforge", {"method": "GET", "target": self.base + "/?q=salut"})
        self.assertEqual(e["status"], "ok")
        self.assertTrue(any(b.get("title", "").startswith("Réponse n°") for b in e["blocks"]))
        hist = server.run_tool("reqforge-history", {})
        self.assertGreaterEqual(len(hist["blocks"][0]["rows"]), 3)


if __name__ == "__main__":
    unittest.main()
