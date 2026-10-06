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

    def test_records_each_scene_paced_to_the_voice(self):
        out = Path(tempfile.mkdtemp())
        (out / "capture").mkdir()
        (out / "voice").mkdir()
        (out / "capture/steps.json").write_text(json.dumps({"version": 1, "base_url": self.base, "scenes": {
            "s05": {"start": {"do": "goto", "url": "/"}, "steps": [
                {"do": "type", "target": {"label": "Search"}, "text": "road", "say": "road"},
                {"do": "click", "target": {"role": "button", "name": "Search"}, "say": "open"}]},
            "s06": {"steps": [{"do": "click", "target": {"role": "link", "name": "Open report"}, "say": "report"}]}}}))
        (out / "voice/voice.json").write_text(json.dumps({"version": 1, "provider": "edge", "clips": [
            {"scene": "s05", "file": "voice/s05.mp3", "dur_s": 3.0, "words": ScheduleTest.WORDS},
            {"scene": "s06", "file": "voice/s06.mp3", "dur_s": 2.0, "words": [{"w": "report", "t0": 0.8, "t1": 1.2}]}]}))
        (out / "timeline.json").write_text(json.dumps({"version": 1, "fps": 30, "scenes": [
            {"id": "s05", "visual": "capture", "lead_s": 0.3, "voice_s": 3.0, "dur_s": 3.8, "start_s": 0},
            {"id": "s06", "visual": "capture", "lead_s": 0.3, "voice_s": 2.0, "dur_s": 2.8, "start_s": 3.8}]}))
        p = subprocess.run([sys.executable, str(SCRIPTS / "capture.py"), "record", "--out", str(out)],
                           capture_output=True, text=True, timeout=300)
        res = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(p.returncode, 0, res)
        by = {s["scene"]: s for s in res["scenes"]}
        for sid, want in (("s05", 3.8), ("s06", 2.8)):
            f = out / f"capture/{sid}.mp4"
            self.assertTrue(f.exists(), sid)
            self.assertAlmostEqual(duration(f), want, delta=0.35)
        typed = by["s05"]["actions"][0]
        self.assertAlmostEqual(typed["at_s"], 0.7, delta=0.35)   # 0.3 lead + 0.7 word - 0.3 early


if __name__ == "__main__":
    unittest.main()
