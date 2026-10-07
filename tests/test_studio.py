import json, subprocess, sys, tempfile, time, unittest, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/unveo/scripts"

SCRIPT = ("# S\n## s01 · context · anim:title · 2.5 s\n(no narration)\n\n"
          "## s02 · context · anim:context · target 3 s\nNarration: Developers now code with AI. [brief: limit_s]\n\n"
          "## s03 · close · anim:close · target 3 s\nNarration: Thanks for watching. [brief: limit_s]\n")


class StudioTest(unittest.TestCase):
    def setUp(self):
        self.o = Path(tempfile.mkdtemp())
        (self.o / "script.md").write_text(SCRIPT)
        self.p = subprocess.Popen([sys.executable, str(SCRIPTS / "studio.py"), "serve", "--no-open", "--port", "0", "--out", str(self.o)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for _ in range(100):  # the server writes its address once it's listening
            f = self.o / "voice" / "studio.url"
            if f.exists() and f.read_text().strip():
                self.url = f.read_text().strip()
                break
            time.sleep(0.05)
        else:
            self.fail("studio never started")

    def tearDown(self):
        if self.p.poll() is None:
            self.p.kill()

    def get(self, path):
        return json.loads(urllib.request.urlopen(self.url + path, timeout=5).read())

    def post(self, path, data=b""):
        req = urllib.request.Request(self.url + path, data=data, method="POST")
        return json.loads(urllib.request.urlopen(req, timeout=5).read())

    def test_lines_take_and_finish(self):
        lines = self.get("/lines")
        self.assertEqual([l["id"] for l in lines], ["s02", "s03"])
        self.assertEqual(lines[0]["text"], "Developers now code with AI.")  # tags removed, as it will be spoken
        self.assertFalse(lines[0]["approved"])
        self.assertTrue(self.post("/take/s02", b"FAKEWEBM")["ok"])
        self.assertTrue((self.o / "voice/own/s02.webm").exists())
        self.assertTrue(self.get("/lines")[0]["approved"])
        self.post("/finish")
        out, _ = self.p.communicate(timeout=10)
        res = json.loads(out.strip().splitlines()[-1])
        self.assertEqual((res["approved"], res["missing"]), (["s02"], ["s03"]))

    def test_unknown_scene_is_refused(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.post("/take/..%2F..%2Fevil", b"x")
        self.assertEqual(cm.exception.code, 404)
        self.assertFalse(any(self.o.rglob("evil*")))

    def test_page_is_served(self):
        html = urllib.request.urlopen(self.url + "/", timeout=5).read().decode()
        self.assertIn("Approve", html)


if __name__ == "__main__":
    unittest.main()
