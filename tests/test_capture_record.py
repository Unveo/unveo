import functools, http.server, json, re, subprocess, sys, tempfile, threading, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
import capture  # noqa: E402
from common import ffmpeg_exe  # noqa: E402

SITE = ROOT / "tests/fixtures/mini-web"


def duration(p):
    err = subprocess.run([ffmpeg_exe(), "-i", str(p)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


class ScheduleTest(unittest.TestCase):
    WORDS = [{"w": "Search", "t0": 0.2, "t1": 0.6}, {"w": "road,", "t0": 0.7, "t1": 1.0},
             {"w": "and", "t0": 1.1, "t1": 1.2}, {"w": "open", "t0": 2.0, "t1": 2.3}, {"w": "the", "t0": 2.3, "t1": 2.4},
             {"w": "report.", "t0": 2.5, "t1": 3.0}]

    def test_actions_land_just_before_their_word_in_order(self):
        steps = [{"do": "type", "say": "road"}, {"do": "wait"}, {"do": "click", "say": "open the report"}]
        at = capture.schedule(steps, self.WORDS, lead_s=0.3)
        self.assertAlmostEqual(at[0], 0.3 + 0.7 - 0.3)
        self.assertIsNone(at[1])                     # no 'say': runs right after the previous step
        self.assertAlmostEqual(at[2], 0.3 + 2.0 - 0.3)

    def test_unknown_say_word_is_none(self):
        self.assertEqual(capture.schedule([{"do": "click", "say": "banana"}], self.WORDS, 0.3), [None])


class RecordTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
        handler.log_message = lambda *a: None
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_records_every_scene_in_one_take_at_a_natural_pace(self):
        out = Path(tempfile.mkdtemp())
        (out / "capture").mkdir()
        (out / "capture/steps.json").write_text(json.dumps({"version": 1, "base_url": self.base, "scenes": {
            "s05": {"start": {"do": "goto", "url": "/"}, "steps": [
                {"do": "type", "target": {"label": "Search"}, "text": "road", "say": "road"},
                {"do": "click", "target": {"role": "button", "name": "Search"}, "say": "open"}]},
            "s06": {"steps": [{"do": "click", "target": {"role": "link", "name": "Open report"}, "say": "report"}]}}}))
        p = subprocess.run([sys.executable, str(SCRIPTS / "capture.py"), "record", "--out", str(out)],  # no voice, no timeline
                           capture_output=True, text=True, timeout=300)
        res = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(p.returncode, 0, res)
        by = {s["scene"]: s for s in res["scenes"]}
        take = json.loads((out / "capture/record.json").read_text())
        for sid in ("s05", "s06"):
            self.assertAlmostEqual(duration(out / f"capture/{sid}.mp4"), by[sid]["recorded_s"], delta=0.1)
            self.assertGreaterEqual(by[sid]["recorded_s"], by[sid]["actions"][-1]["at_s"] + capture.SETTLE_S - 0.05)
            self.assertAlmostEqual(take[sid]["need_s"], take[sid]["recorded_s"] / capture.MAX_SPEED, delta=0.02)
        self.assertAlmostEqual(by["s05"]["actions"][0]["at_s"], capture.LEAD_S, delta=0.25)  # a natural beat, not the voice
        self.assertEqual(by["s05"]["actions"][1]["say"], "open")
        self.assertTrue((out / "capture/take/sheet.png").exists())

    def test_a_failing_scene_stops_the_take_with_evidence(self):
        out = Path(tempfile.mkdtemp())
        (out / "capture").mkdir()
        (out / "capture/steps.json").write_text(json.dumps({"version": 1, "base_url": self.base, "scenes": {
            "s05": {"start": {"do": "goto", "url": "/"}, "steps": [{"do": "click", "target": {"role": "button", "name": "Serch"}, "timeout_ms": 1500}]},
            "s06": {"steps": [{"do": "click", "target": {"role": "link", "name": "Open report"}}]}}}))
        p = subprocess.run([sys.executable, str(SCRIPTS / "capture.py"), "record", "--out", str(out)],
                           capture_output=True, text=True, timeout=300)
        res = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(p.returncode, 2, res)
        self.assertEqual([f["scene"] for f in res["failures"]], ["s05"])
        self.assertNotIn("s06", [s["scene"] for s in res["scenes"]])  # later scenes depend on s05's page
        self.assertIn("Search", res["failures"][0]["closest"])
        self.assertTrue(Path(res["failures"][0]["screenshot"]).exists())

if __name__ == "__main__":
    unittest.main()
