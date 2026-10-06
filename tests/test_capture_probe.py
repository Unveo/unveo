import functools, http.server, json, subprocess, sys, tempfile, threading, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/unveo/scripts/capture.py"
SITE = ROOT / "tests/fixtures/mini-web"


def probe(url):
    with tempfile.TemporaryDirectory() as out:
        p = subprocess.run([sys.executable, str(SCRIPT), "probe", "--url", url, "--out", out],
                           capture_output=True, text=True, timeout=120)
        last = json.loads(p.stdout.strip().splitlines()[-1])
        shot = Path(out, "capture/probe.png")
        return p.returncode, last, shot.exists() and shot.stat().st_size > 1000


class ProbeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        site = Path(cls.tmp.name)
        (site / "index.html").write_text((SITE / "index.html").read_text())
        (site / "login.html").write_text('<!doctype html><title>Sign in</title><form><input name="email">'
                                         '<input type="password" name="pw"><button>Sign in</button></form>')
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
        handler.log_message = lambda *a: None
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.tmp.cleanup()

    def test_loads_page_and_saves_screenshot(self):
        code, out, shot = probe(self.base + "/")
        self.assertEqual(code, 0, out)
        self.assertEqual((out["status"], out["title"], out["login_wall"]), (200, "Mini Risk", False))
        self.assertTrue(shot)

    def test_detects_login_wall(self):
        code, out, _ = probe(self.base + "/login.html")
        self.assertEqual(code, 0, out)
        self.assertTrue(out["login_wall"])

    def test_missing_page_needs_the_user(self):
        code, out, _ = probe(self.base + "/nope.html")
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], 404)

    def test_unreachable_host_needs_the_user(self):
        code, out, _ = probe("http://127.0.0.1:9/")
        self.assertEqual(code, 2)
        self.assertFalse(out["ok"])


if __name__ == "__main__":
    unittest.main()
