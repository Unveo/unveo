import json, subprocess, sys, tempfile, unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
import voice  # noqa: E402
from common import ffmpeg_exe  # noqa: E402


class CatalogueTest(unittest.TestCase):
    def test_every_accent_has_voices_and_multilingual_comes_first_in_us(self):
        for accent in ("us", "uk", "in", "au", "hi"):
            self.assertTrue(voice.VOICES[accent], accent)
        self.assertIn("Multilingual", voice.VOICES["us"][0][0])

    def test_accent_follows_the_system_region_not_a_fixed_country(self):
        self.assertEqual(voice.accent_for_locale("en_GB.UTF-8"), "uk")
        self.assertEqual(voice.accent_for_locale("en_IN"), "in")
        self.assertEqual(voice.accent_for_locale("en-AU"), "au")
        self.assertEqual(voice.accent_for_locale("de_DE"), "us")  # unknown English region -> US
        self.assertEqual(voice.accent_for_locale(None), "us")


class DeliveryTest(unittest.TestCase):
    def test_sentences_split_on_end_punctuation_only(self):
        self.assertEqual(voice.split_sentences("It works. Does it scale? Yes, it does! Done"),
                         ["It works.", "Does it scale?", "Yes, it does!", "Done"])

    def test_pauses_vary_within_bounds_and_are_repeatable(self):
        ps = [voice.pause_after(s, "s05", i) for i, s in enumerate(["Short one.", "A much longer sentence with many more words in it.", "Why?"])]
        self.assertTrue(all(0.28 <= p <= 0.55 for p in ps), ps)
        self.assertGreater(len(set(ps)), 1)
        self.assertEqual(ps, [voice.pause_after(s, "s05", i) for i, s in enumerate(["Short one.", "A much longer sentence with many more words in it.", "Why?"])])

    def test_rate_varies_a_little_around_the_chosen_pace(self):
        rates = [int(voice.vary_rate("+10%", "s05", i).rstrip("%")) for i in range(8)]
        self.assertTrue(all(7 <= r <= 13 for r in rates), rates)
        self.assertGreater(len(set(rates)), 1)

    def test_join_offsets_word_timings_and_length_is_the_sum(self):
        sr = 24000
        a, b = np.ones(sr), np.ones(sr // 2)
        audio, words = voice.join_sentences([a, b], [[{"w": "Hi", "t0": 0.1, "t1": 0.5}], [{"w": "There", "t0": 0.0, "t1": 0.3}]], [0.4], sr)
        self.assertEqual(len(audio), sr + int(0.4 * sr) + sr // 2)
        self.assertAlmostEqual(words[1]["t0"], 1.4, places=3)
        self.assertLess(words[0]["t1"], words[1]["t0"])

    def test_trim_edges_cuts_leading_and_trailing_silence(self):
        sr = 24000
        x = np.concatenate([np.zeros(sr // 2), np.full(sr, 0.3), np.zeros(sr)])
        y, lead = voice.trim_edges(x, sr)
        self.assertAlmostEqual(lead, 0.45, delta=0.06)  # keeps ~50 ms
        self.assertLess(len(y), len(x) - sr)


class TightenTest(unittest.TestCase):
    def test_mic_hiss_edges_and_long_pauses_are_cut(self):
        sr = 24000
        rng = np.random.default_rng(1)
        hiss = lambda s: rng.normal(0, 0.012, int(s * sr))  # about -38 dB, a laptop mic in a quiet room
        speech = lambda s: np.sin(np.arange(int(s * sr)) * 2 * np.pi * 200 / sr) * 0.3
        x = np.concatenate([hiss(1.0), speech(2.0), hiss(1.5), speech(2.0), hiss(2.0)])
        y = voice.tighten(x, sr)
        self.assertAlmostEqual(len(y) / sr, 2.0 + 0.45 + 2.0 + 0.1, delta=0.15)

    def test_natural_short_pauses_are_kept(self):
        sr = 24000
        speech = np.full(sr, 0.3)
        x = np.concatenate([speech, np.zeros(int(0.35 * sr)), speech])
        self.assertAlmostEqual(len(voice.tighten(x, sr)) / sr, 2.35, delta=0.05)  # nothing to cut


class OwnVoiceTest(unittest.TestCase):
    def test_own_provider_builds_voice_json_from_approved_takes(self):
        o = Path(tempfile.mkdtemp())
        (o / "your-voice").mkdir(parents=True)
        (o / "script.md").write_text("# S\n## s01 · context · anim:title · 2.5 s\n(no narration)\n\n"
                                     "## s02 · context · anim:context · target 3 s\nNarration: Hello there. [brief: limit_s]\n\n"
                                     "## s03 · close · anim:close · target 3 s\nNarration: Bye now. [brief: limit_s]\n")
        (o / "brief.json").write_text(json.dumps({"version": 1, "language": "en", "voice": {"provider": "own"}}))
        for sid in ("s02", "s03"):
            subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono:d=0.3", "-f", "lavfi",
                            "-i", "sine=f=220:d=1.2", "-filter_complex", "[0][1][0]concat=n=3:v=0:a=1", str(o / f"your-voice/{sid}.wav")], check=True)
        p = subprocess.run([sys.executable, str(SCRIPTS / "voice.py"), "--out", str(o)], capture_output=True, text=True, timeout=120)
        res = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(p.returncode, 0, res)
        vj = json.loads((o / "voice/voice.json").read_text())
        self.assertEqual(vj["provider"], "own")
        self.assertEqual([c["scene"] for c in vj["clips"]], ["s02", "s03"])
        self.assertTrue(all(1.1 < c["dur_s"] < 1.5 for c in vj["clips"]), vj["clips"])  # edge silence trimmed

    def test_missing_takes_are_listed(self):
        o = Path(tempfile.mkdtemp())
        (o / "your-voice").mkdir(parents=True)
        (o / "script.md").write_text("# S\n## s02 · context · anim:context · target 3 s\nNarration: Hello. [brief: limit_s]\n")
        (o / "brief.json").write_text(json.dumps({"version": 1, "language": "en", "voice": {"provider": "own"}}))
        p = subprocess.run([sys.executable, str(SCRIPTS / "voice.py"), "--out", str(o)], capture_output=True, text=True, timeout=60)
        res = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(p.returncode, 2)
        self.assertEqual(res["missing"], ["s02"])


if __name__ == "__main__":
    unittest.main()
