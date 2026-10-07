import json, re, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "tests"))
import captions  # noqa: E402

VOICE_WORDS = [{"w": "Under", "t0": 0.1, "t1": 0.5}, {"w": "M", "t0": 0.55, "t1": 0.7}, {"w": "P", "t0": 0.72, "t1": 0.85},
               {"w": "lads", "t0": 0.88, "t1": 1.3}, {"w": "every", "t0": 1.6, "t1": 1.9}, {"w": "MP", "t0": 1.95, "t1": 2.3},
               {"w": "recommends", "t0": 2.4, "t1": 3.0}, {"w": "works", "t0": 3.1, "t1": 3.5}, {"w": "It", "t0": 4.0, "t1": 4.1},
               {"w": "works", "t0": 4.15, "t1": 4.6}]


class AlignTest(unittest.TestCase):
    def test_real_words_come_back_with_punctuation_and_their_timings(self):
        toks = captions.align("Under MPLADS, every MP recommends works. It works.", VOICE_WORDS, {"MPLADS": "M P lads"}, 5.0)
        self.assertEqual([t["w"] for t in toks], ["Under", "MPLADS,", "every", "MP", "recommends", "works.", "It", "works."])
        mplads = toks[1]
        self.assertEqual((mplads["t0"], mplads["t1"]), (0.55, 1.3))  # spans "M P lads"

    def test_falls_back_to_estimated_timings_when_counts_disagree(self):
        toks = captions.align("Twenty twenty six was big.", [{"w": "2026", "t0": 0.1, "t1": 0.9}], {}, 2.0)
        self.assertEqual(len(toks), 5)
        self.assertTrue(all(a["t1"] <= b["t0"] + 1e-6 for a, b in zip(toks, toks[1:])))


class GroupTest(unittest.TestCase):
    def test_breaks_at_sentence_ends_and_keeps_two_short_lines(self):
        toks = captions.align("Under MPLADS, every MP recommends works. It works.", VOICE_WORDS, {"MPLADS": "M P lads"}, 5.0)
        cues = captions.group(toks, scene_end=5.0)
        self.assertEqual(cues[0]["text"].replace("\n", " "), "Under MPLADS, every MP recommends works.")
        self.assertEqual(cues[1]["text"], "It works.")
        for c in cues:
            self.assertLessEqual(len(c["text"].split("\n")), 2)
            self.assertTrue(all(len(line) <= 42 for line in c["text"].split("\n")))
            self.assertGreaterEqual(c["end"] - c["start"], 1.2 - 1e-6)
            self.assertLessEqual(c["end"], 5.0)

    def test_long_sentence_splits_at_a_comma_not_leaving_one_word_alone(self):
        text = "But feedback on these tools is scattered, and anyone can answer twice whenever they like."
        words = [{"w": w, "t0": i * 0.35, "t1": i * 0.35 + 0.3} for i, w in enumerate(text.replace(",", "").replace(".", "").split())]
        cues = captions.group(captions.align(text, words, {}, 6.0), scene_end=6.0)
        self.assertTrue(cues[0]["text"].replace("\n", " ").endswith("scattered,"), cues)
        self.assertTrue(all(len(c["text"].split()) >= 3 for c in cues), cues)

    def test_srt_time_format(self):
        self.assertEqual(captions.srt_time(3723.456), "01:02:03,456")


class BoxTest(unittest.TestCase):
    def test_a_two_line_caption_sits_in_one_box(self):
        import numpy as np
        from common import ffmpeg_exe
        from PIL import Image
        d = Path(tempfile.mkdtemp())
        (d / "c.ass").write_text(captions.ASS_HEAD + "Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,You sign in with Google, so there's\\Nno password.\n")
        subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=white:s=1920x1080:d=1", "-vf",
                        f"subtitles={d / 'c.ass'}:fontsdir={captions.FONTS}", "-frames:v", "1", str(d / "c.png")], check=True)
        a = np.array(Image.open(d / "c.png").convert("L")).astype(int)
        rows = [r for r in range(700, 1080) if (a[r] < 200).sum() > 50]
        lefts = {int(np.argmax(a[r] < 200)) for r in rows}
        self.assertLessEqual(max(lefts) - min(lefts), 2, lefts)  # one box: every row starts at the same x


class StitchBurnTest(unittest.TestCase):
    def test_burned_captions_change_the_frame_and_srt_is_written(self):
        from test_audio_stitch_qa import project, run, FF  # reuse the tiny finished project
        o, total = project()
        vj = json.loads((o / "voice/voice.json").read_text())
        for c in vj["clips"]:
            c["words"] = [{"w": "Look", "t0": 0.0, "t1": 0.6}, {"w": "here", "t0": 0.7, "t1": 1.2}][: 2]
        (o / "voice/voice.json").write_text(json.dumps(vj))
        run("stitch.py", o, "ingest"); run("score.py", o); run("mix.py", o)
        b = json.loads((o / "brief.json").read_text()); b["captions"] = "off"; (o / "brief.json").write_text(json.dumps(b))
        run("stitch.py", o, "final")
        plain = (o / "final.mp4").read_bytes()
        b["captions"] = "burned"; (o / "brief.json").write_text(json.dumps(b))
        code, res = run("captions.py", o)
        self.assertEqual(code, 0, res)
        self.assertTrue((o / "captions.srt").read_text().startswith("1\n00:00:"))
        code, res = run("stitch.py", o, "final")
        self.assertEqual(code, 0, res)
        self.assertNotEqual(plain, (o / "final.mp4").read_bytes())


if __name__ == "__main__":
    unittest.main()
