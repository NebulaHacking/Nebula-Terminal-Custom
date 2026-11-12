"""Tests des outils crypto et reconnaissance. Aucun accès Internet : serveurs locaux uniquement."""
import contextlib
import functools
import http.server
import io
import socket
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from Tools import cryptokit as ck
from Tools import recon
from terminal.context import default_context
from terminal.registry import build_registry


def _run(line, ctx=None, stdin=""):
    buf = io.StringIO()
    ctx = ctx or default_context()
    with contextlib.redirect_stdout(buf), mock.patch("builtins.input", side_effect=stdin.splitlines()):
        build_registry().dispatch(ctx, line)
    return buf.getvalue()


class CryptoKitTest(unittest.TestCase):
    def test_encode_decode_roundtrip(self):
        text = "Nébula & <test> 100%"
        for fmt in ck.FORMATS:
            self.assertEqual(ck.decode(fmt, ck.encode(fmt, text)), text, fmt)
        self.assertEqual(ck.encode("-b64", "Bonjour"), "Qm9uam91cg==")
        self.assertEqual(ck.decode("b64", "Qm9uam91cg"), "Bonjour")  # padding manquant toléré
        with self.assertRaises(ValueError):
            ck.decode("hex", "zz")
        with self.assertRaises(ValueError):
            ck.encode("nope", "x")
        self.assertIn(("hex", "Nebula"), ck.decode_auto("4e6562756c61"))

    def test_hash(self):
        h = ck.hash_text("abc")
        self.assertEqual(h["md5"], "900150983cd24fb0d6963f7d28e17f72")
        self.assertEqual(h["sha256"], "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "a b.bin"
            f.write_bytes(b"abc")
            self.assertEqual(ck.hash_file(str(f)), h)
            self.assertIn("OK", _run(f'hash -c {h["sha1"]} "{f}"'))
            self.assertIn("DIFFERENT", _run(f'hash -c {"0" * 40} {f}'))

    def test_hashid(self):
        self.assertEqual(ck.hashid("5f4dcc3b5aa765d61d8327deb882cf99")[0], "MD5")
        self.assertEqual(ck.hashid("a" * 64)[0], "SHA-256")
        self.assertEqual(ck.hashid("$2b$12$" + "a" * 53), ["bcrypt"])
        self.assertEqual(ck.hashid("$6$salt$hash"), ["sha512crypt (Unix)"])
        self.assertEqual(ck.hashid("pas un hash"), [])

    def test_ipcalc(self):
        info = ck.ipcalc("192.168.1.10/24")
        self.assertEqual((info["Réseau"], info["Broadcast"], info["Hôtes utilisables"]),
                         ("192.168.1.0/24", "192.168.1.255", "254"))
        self.assertEqual(ck.ipcalc("10.0.0.1 255.255.0.0")["Réseau"], "10.0.0.0/16")
        self.assertEqual(ck.ipcalc("10.0.0.0/31")["Hôtes utilisables"], "2")
        self.assertEqual(ck.ipcalc("2001:db8::1/64")["Réseau"], "2001:db8::/64")
        with self.assertRaises(ValueError):
            ck.ipcalc("999.1.1.1/24")

    def test_jwt(self):
        token = "eyJhbGciOiJub25lIn0.eyJzdWIiOiJyb2JpbiIsImV4cCI6MTcwMDAwMDAwMH0."
        res = ck.jwt_decode(token)
        self.assertEqual(res["payload"]["sub"], "robin")
        self.assertTrue(any("alg=none" in w for w in res["warnings"]))
        self.assertTrue(any("expiré" in w for w in res["warnings"]))
        with self.assertRaises(ValueError):
            ck.jwt_decode("pas.un")

    def test_passwords(self):
        pw = ck.pwgen(24)
        self.assertEqual(len(pw), 24)
        self.assertNotEqual(pw, ck.pwgen(24))
        with self.assertRaises(ValueError):
            ck.pwgen(3)
        self.assertEqual(ck.pwstrength("password")["verdict"], "très faible")
        self.assertIn(ck.pwstrength(pw)["verdict"], ("fort", "très fort"))

    def test_pwstrength_never_stored_in_history(self):
        ctx = default_context()
        out = _run("pwstrength MonSecret123", ctx, stdin="MonSecret123")
        self.assertIn("Entropie", out)
        self.assertNotIn("MonSecret123", " ".join(ctx.history))

    def test_ts(self):
        self.assertEqual(ck.ts_convert("1700000000")["UTC"], "2023-11-14 22:13:20")
        self.assertEqual(ck.ts_convert("1700000000000")["Timestamp"], "1700000000")  # millisecondes
        back = ck.ts_convert(ck.ts_convert("1700000000")["Local"])
        self.assertEqual(back["Timestamp"], "1700000000")
        with self.assertRaises(ValueError):
            ck.ts_convert("demain")

    def test_files(self):
        self.assertEqual(ck.file_type(b"\x89PNG\r\n\x1a\n...."), "Image PNG")
        self.assertEqual(ck.file_type(b"MZ\x90\x00"), "Exécutable Windows (PE : .exe / .dll)")
        self.assertEqual(ck.file_type(b"bonjour"), "Texte (UTF-8)")
        self.assertEqual(ck.strings(b"\x00\x01hello\x00ab\x00world!!\xff"), ["hello", "world!!"])
        self.assertEqual(ck.entropy(b"aaaa"), 0.0)
        self.assertAlmostEqual(ck.entropy(bytes(range(256))), 8.0)
        self.assertIn("introuvable", _run("fileinfo nope-nope.bin"))


class ReconTest(unittest.TestCase):
    def test_clean_host(self):
        self.assertEqual(recon.clean_host("https://Example.com:8443/a?b"), "example.com")
        self.assertEqual(recon.clean_host("10.0.0.1"), "10.0.0.1")
        for bad in ("-oProxyCommand=x", "a b", "", "ex.com; rm -rf"):
            with self.assertRaises(ValueError, msg=bad):
                recon.clean_host(bad)
        with self.assertRaises(ValueError):
            recon.dns_query("example.com", "AXFR; x")

    def test_banner_and_portscan_on_local_server(self):
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(5)
        port = srv.getsockname()[1]

        def serve():
            while True:
                try:
                    conn, _ = srv.accept()
                except OSError:
                    return
                conn.sendall(b"220 nebula-test FTP ready\r\n")
                conn.close()

        threading.Thread(target=serve, daemon=True).start()
        try:
            self.assertEqual(recon.grab_banner("127.0.0.1", port), "220 nebula-test FTP ready")
            from Tools.portscan import scan_ports
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(scan_ports("127.0.0.1", "normal", port, port), [port])
                with self.assertRaises(ValueError):
                    scan_ports("127.0.0.1", "normal", 0, 70000)
        finally:
            srv.close()

    def test_subdomain_wildcard_is_filtered(self):
        def fake(name):
            if name.startswith("vpn."):
                return name, ["10.0.0.9"]
            return name, ["1.2.3.4"]  # tout le reste résout : wildcard

        with mock.patch.object(recon, "_resolve", side_effect=fake):
            res = recon.enum_subdomains("corp.test", ["www", "vpn", "mail"])
        self.assertEqual(res["found"], [("vpn.corp.test", ["10.0.0.9"])])
        self.assertEqual(res["wildcard"], ["1.2.3.4"])

    def test_hostscan_limits_and_sweep(self):
        with self.assertRaises(ValueError):
            recon.host_sweep("10.0.0.0/8")
        with mock.patch.object(recon, "_ping", side_effect=lambda ip, t: ip.endswith(".2")), \
                mock.patch.object(recon, "_name_of", return_value="box"):
            self.assertEqual(recon.host_sweep("192.168.50.0/29"), [("192.168.50.2", "box")])

    def test_headers_and_dirb_on_local_http_server(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "admin").write_text("secret")
            (Path(d) / "words.txt").write_text("nope\nadmin\nadmin\n# commentaire\n")
            class Quiet(http.server.SimpleHTTPRequestHandler):
                def log_message(self, *args):
                    pass

            handler = functools.partial(Quiet, directory=d)
            httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            url = f"http://127.0.0.1:{httpd.server_address[1]}"
            try:
                res = recon.http_headers(url)
                self.assertEqual(res["status"], 200)
                self.assertEqual(len(res["missing"]), len(recon.SECURITY_HEADERS))
                self.assertIn("Server", res["leaks"])

                from Tools.dirb import dirb
                with contextlib.redirect_stdout(io.StringIO()):
                    found = dirb(url, wordlist=str(Path(d) / "words.txt"))
                self.assertEqual(found, [f"{url}/admin"])
            finally:
                httpd.shutdown()
                httpd.server_close()


class HelpTest(unittest.TestCase):
    def test_help_filter(self):
        out = _run("help crypto")
        self.assertIn("hashid", out)
        self.assertNotIn("netstorm", out)
        self.assertIn("Aucune commande", _run("help zzzz"))


if __name__ == "__main__":
    unittest.main()
