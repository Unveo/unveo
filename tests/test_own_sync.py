"""Own voice in sync: the studio's word timings reach voice.json, and explainers follow the voice (docs/15 round 3)."""
import json, subprocess, sys, tempfile, time, unittest, urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
import render, voice  # noqa: E402
from common import ffmpeg_exe  # noqa: E402

SR = 24000


def take():
    """1 s hiss, 1 s speech, 1.5 s hiss, 1 s speech, 1 s hiss."""
    rng = np.random.default_rng(2)
    hiss = lambda s: rng.normal(0, 0.012, int(s * SR))
    speech = lambda s: np.sin(np.arange(int(s * SR)) * 2 * np.pi * 200 / SR) * 0.3
    return np.concatenate([hiss(1.0), speech(1.0), hiss(1.5), speech(1.0), hiss(1.0)])


class TimeMapTest(unittest.TestCase):
    def test_times_follow_the_cuts(self):
        y, segs = voice.tighten(take(), SR, with_map=True)
        self.assertAlmostEqual(voice.remap(1.0, segs), 0.05, delta=0.06)   # start of speech 1, after the cut lead-in
        self.assertAlmostEqual(voice.remap(1.5, segs), 0.55, delta=0.06)
        self.assertAlmostEqual(voice.remap(3.5, segs), 1.5, delta=0.08)    # speech 2: 1 s + 0.45 s pause later
        self.assertAlmostEqual(voice.remap(2.5, segs), voice.remap(3.5, segs), delta=0.08)  # inside a cut pause: snaps to what follows
        self.assertAlmostEqual(len(y) / SR, 2.55, delta=0.1)


class SpokenWordsTest(unittest.TestCase):
    def test_studio_word_times_become_voice_json_words(self):
        o = Path(tempfile.mkdtemp())
        (o / "your-voice").mkdir(parents=True)
        (o / "script.md").write_text("# S\n## s02 · context · anim:context · target 3 s\nNarration: Hello there. Bye now. [brief: limit_s]\n")
        (o / "brief.json").write_text(json.dumps({"version": 1, "language": "en", "voice": {"provider": "own"}}))
        import soundfile as sf
        sf.write(str(o / "your-voice/s02.wav"), take(), SR)
        lag = voice.RECOGNITION_LAG_S
        (o / "your-voice/s02.words.json").write_text(json.dumps({"words": [
            {"w": "Hello", "t": 1.0 + lag}, {"w": "there", "t": 1.5 + lag}, {"w": "Bye", "t": 3.5 + lag}, {"w": "now", "t": 4.0 + lag}]}))
        p = subprocess.run([sys.executable, str(SCRIPTS / "voice.py"), "--out", str(o)], capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        clip = json.loads((o / "voice/voice.json").read_text())["clips"][0]
        self.assertEqual(clip["timing"], "spoken")
        t0 = [w["t0"] for w in clip["words"]]
        for got, want in zip(t0, [0.05, 0.55, 1.5, 2.0]):
            self.assertAlmostEqual(got, want, delta=0.12)
        self.assertTrue(all(w["t1"] > w["t0"] for w in clip["words"]))

    def test_without_studio_words_estimates_never_land_in_a_pause(self):
        y, segs = voice.tighten(take(), SR, with_map=True)
        words = voice.spread_over_speech("Hello there. Bye now.", segs)
        gap = (segs[0][1] - segs[0][0] + segs[0][2], segs[1][2])  # the kept 0.45 s pause, in output time
        for w in words:
            self.assertFalse(gap[0] + 0.06 < w["t0"] < gap[1] - 0.06, (w, gap))


class ExplainerBeatsTest(unittest.TestCase):
    WORDS = [{"w": "What", "t0": 0.0, "t1": 0.3}, {"w": "Google's", "t0": 2.2, "t1": 2.8}, {"w": "token,", "t0": 6.6, "t1": 7.0}]

    def test_beats_can_name_the_word_they_land_on(self):
        d = render.resolve_word_times({"beats": [0, "word:google", "word:token"]}, self.WORDS, 0.3)
        self.assertEqual(d["beats"], [0, 2.35, 6.75])

    def test_a_voiced_explainer_without_beats_is_a_blocking_issue(self):
        scenes = [{"id": "s06", "visual": "anim", "template": "explainer-system-map", "voice": "voice/s06.mp3"},
                  {"id": "s07", "visual": "anim", "template": "explainer-system-map", "voice": None}]
        issues = render.sync_issues(scenes, {"s06": {"nodes": []}, "s07": {}})
        self.assertEqual([i["scene"] for i in issues], ["s06"])
        self.assertEqual(render.sync_issues(scenes[:1], {"s06": {"beats": [0, 2.3]}}), [])


SCRIPT = ("# S\n## s02 · context · anim:context · target 3 s\nNarration: Developers now code with AI. [brief: limit_s]\n\n"
          "## s03 · close · anim:close · target 3 s\nNarration: Thanks for watching. [brief: limit_s]\n")


class StudioSyncTest(unittest.TestCase):
    def setUp(self):
        self.o = Path(tempfile.mkdtemp())
        (self.o / "script.md").write_text(SCRIPT)
        (self.o / "brief.json").write_text(json.dumps({"version": 1, "language": "en", "voice": {"provider": "own", "rate": "+10%"}}))
        self.p = subprocess.Popen([sys.executable, str(SCRIPTS / "studio.py"), "serve", "--no-open", "--out", str(self.o)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for _ in range(100):
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

    def test_lines_carry_the_pace_and_a_target_length(self):
        lines = json.loads(urllib.request.urlopen(self.url + "/lines", timeout=5).read())
        self.assertAlmostEqual(lines[0]["wps"], 2.42, places=2)  # 2.2 words/s × 1.10
        self.assertAlmostEqual(lines[0]["target_s"], 5 / 2.42, delta=0.05)

    def test_word_timings_are_saved_next_to_the_take(self):
        req = urllib.request.Request(self.url + "/words/s02", data=json.dumps({"words": [{"w": "Developers", "t": 0.9}]}).encode(), method="POST")
        self.assertTrue(json.loads(urllib.request.urlopen(req, timeout=5).read())["ok"])
        self.assertEqual(json.loads((self.o / "your-voice/s02.words.json").read_text())["words"][0]["w"], "Developers")

    def test_logo_is_served(self):
        r = urllib.request.urlopen(self.url + "/logo.png", timeout=5)
        self.assertEqual(r.headers["Content-Type"], "image/png")

    def test_pace_highlight_moves_while_recording(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch(args=["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"])
            page = b.new_page()
            page.goto(self.url)
            page.wait_for_selector("#read .w")
            page.click("#record")
            page.wait_for_timeout(1600)
            pace = page.evaluate("document.querySelectorAll('#read .w.pace, #read .w.paced').length")
            readout = page.text_content("#clock")
            page.click("#record")
            b.close()
        self.assertGreaterEqual(pace, 2)
        self.assertRegex(readout, r"\d\.\d s")


if __name__ == "__main__":
    unittest.main()
