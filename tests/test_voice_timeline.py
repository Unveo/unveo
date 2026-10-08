import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
import voice, plan_timeline  # noqa: E402

KOKORO = Path(os.environ.get("UNVEO_HOME", Path.home() / ".unveo")) / "models/kokoro/kokoro-v1.0.int8.onnx"

SCRIPT = """# Script: T
## s01 · context · anim:title · 2.5 s
(no narration)

## s02 · context · anim:context · target 4 s
Narration: MPLADS funds local works. [src: README.md:1]

## s03 · product · capture · target 4 s · steps: s03
Narration: Pick a state to see the risk. [src: README.md:1]

## s04 · close · anim:close · target 4 s
Narration: Now anyone can check. [brief: close.impact_line]
"""


def brief(limit=60, lang="en", provider="kokoro"):
    return {"version": 1, "limit_s": limit, "language": lang,
            "voice": {"provider": provider, "voice_id": "en-IN-NeerjaNeural", "rate": "+0%",
                      "say_as": {"MPLADS": "M P lads"}}}


def run(script_name, out, *args):
    p = subprocess.run([sys.executable, str(SCRIPTS / script_name), *args, "--out", str(out)],
                       capture_output=True, text=True, timeout=300)
    return p.returncode, json.loads(p.stdout.strip().splitlines()[-1])


class UnitTest(unittest.TestCase):
    def test_say_as_only_replaces_whole_words(self):
        self.assertEqual(voice.say_as("MPLADS and MPLADSX", {"MPLADS": "M P lads"}), "M P lads and MPLADSX")

    def test_estimated_word_timings_cover_the_clip_in_order(self):
        words = voice.estimate_words("one three fifteen", 3.0)
        self.assertEqual([w["w"] for w in words], ["one", "three", "fifteen"])
        self.assertAlmostEqual(words[-1]["t1"], 3.0, places=2)
        self.assertTrue(all(a["t1"] <= b["t0"] + 1e-9 for a, b in zip(words, words[1:])))

    def test_timeline_durations_frames_and_starts(self):
        scenes = [{"id": "s01", "segment": "context", "visual": "anim", "template": "title", "narration": ""},
                  {"id": "s02", "segment": "product", "visual": "capture", "template": None, "narration": "x"},
                  {"id": "s03", "segment": "close", "visual": "anim", "template": "close", "narration": "y"}]
        clips = {"s02": {"file": "voice/s02.mp3", "dur_s": 4.0}, "s03": {"file": "voice/s03.mp3", "dur_s": 2.0}}
        tl = plan_timeline.build(scenes, clips, limit_s=60)
        d = {s["id"]: s for s in tl["scenes"]}
        self.assertEqual(d["s01"]["dur_s"], 2.5)
        self.assertAlmostEqual(d["s02"]["dur_s"], 0.3 + 4.0 + 0.5, places=2)
        self.assertAlmostEqual(d["s03"]["dur_s"], 0.3 + 2.0 + 0.4 + 1.5, places=2)  # the close holds 1.5 s (docs/16 S4)
        self.assertEqual(d["s02"]["start_s"], 2.5)
        for s in tl["scenes"]:
            self.assertAlmostEqual(s["dur_s"] * 30, round(s["dur_s"] * 30), places=6)  # whole frames
        self.assertAlmostEqual(tl["total_s"], sum(s["dur_s"] for s in tl["scenes"]), places=3)


class MissingKokoroTest(unittest.TestCase):
    def test_the_offline_voice_missing_asks_for_the_install_not_a_traceback(self):
        out = Path(tempfile.mkdtemp())
        (out / "script.md").write_text(SCRIPT)
        (out / "brief.json").write_text(json.dumps(brief()))
        p = subprocess.run([sys.executable, str(SCRIPTS / "voice.py"), "--provider", "kokoro", "--out", str(out)], capture_output=True,
                           text=True, timeout=120, env={**os.environ, "UNVEO_HOME": str(out / "home")})
        res = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(p.returncode, 2, res)
        self.assertIn("--with-kokoro", res["fix"])


@unittest.skipUnless(KOKORO.exists(), "Kokoro model not installed")
class EndToEndTest(unittest.TestCase):
    def setUp(self):
        self.out = Path(tempfile.mkdtemp())
        (self.out / "script.md").write_text(SCRIPT)
        (self.out / "brief.json").write_text(json.dumps(brief()))

    def test_voice_then_timeline(self):
        code, res = run("voice.py", self.out)
        self.assertEqual(code, 0, res)
        vj = json.loads((self.out / "voice/voice.json").read_text())
        self.assertEqual(vj["provider"], "kokoro")
        self.assertEqual([c["scene"] for c in vj["clips"]], ["s02", "s03", "s04"])
        self.assertTrue(all(c["dur_s"] > 0.5 and (self.out / c["file"]).exists() for c in vj["clips"]))
        # unchanged text is not re-voiced
        code, res = run("voice.py", self.out)
        self.assertEqual(res["voiced"], [])
        code, res = run("plan_timeline.py", self.out)
        self.assertEqual(code, 0, res)
        tl = json.loads((self.out / "timeline.json").read_text())
        self.assertEqual([s["id"] for s in tl["scenes"]], ["s01", "s02", "s03", "s04"])

    def test_samples_make_one_short_clip_per_voice_style(self):
        code, res = run("voice.py", self.out, "samples", "--provider", "kokoro")
        self.assertEqual(code, 0, res)
        self.assertGreaterEqual(len(res["samples"]), 2)
        self.assertTrue(all((self.out / s["file"]).exists() for s in res["samples"]))

    def test_over_the_limit_needs_the_agent(self):
        (self.out / "brief.json").write_text(json.dumps(brief(limit=30)))
        long = SCRIPT.replace("Pick a state to see the risk.", " ".join(["Pick a state to see the risk."] * 16))
        (self.out / "script.md").write_text(long)
        run("voice.py", self.out)
        code, res = run("plan_timeline.py", self.out)
        self.assertEqual(code, 2)
        self.assertGreater(res["over_by_s"], 0)
        self.assertEqual(res["longest_product_scenes"][0], "s03")


if __name__ == "__main__":
    unittest.main()
