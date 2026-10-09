"""The submission kit (docs/16 OUT1–OUT4): chapters, images, the vertical cut and the Devpost draft."""
import json, re, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
import kit  # noqa: E402
import script as scriptmod  # noqa: E402
from common import ffmpeg_exe, streams  # noqa: E402

FF = ffmpeg_exe()


def timeline(spec):
    """[(id, segment, visual, template, dur)] -> timeline.json's scenes."""
    out, t = [], 0.0
    for sid, seg, vis, tpl, dur in spec:
        out.append({"id": sid, "segment": seg, "visual": vis, "template": tpl, "start_s": t, "dur_s": dur})
        t += dur
    return {"scenes": out}


SPEC = [("s01", "hook", "capture", None, 4), ("s02", "context", "anim", "title", 2.5), ("s03", "problem", "anim", "compose", 6),
        ("s04", "product", "capture", None, 9), ("s05", "product", "anim", "explainer-pipeline-flow", 9),
        ("s06", "product", "anim", "terminal", 12), ("s07", "product", "capture", None, 8), ("s08", "close", "anim", "close", 4.5)]
BRIEF = {"project": {"name": "Field Scan"}, "palette": {"tokens": {"bg": "#0f1115"}},
         "understanding": {"journey": ["Open the map → every report pinned", "Run the scan → three findings", "Open a finding → its fix"],
                           "hidden_logic": [{"id": "H1", "title": "The nightly pipeline"}]},
         "close": {"links": [{"label": "Live app", "url": "https://fieldscan.app"}]}}


def work(spec=SPEC):
    o = Path(tempfile.mkdtemp())
    (o / "script.md").write_text("".join(f"## {sid} · {seg} · {'anim:' + tpl if tpl else vis} · target {d} s"
                                         + (" · logic: H1" if tpl and tpl.startswith("explainer") else "") + "\nNarration: x\n\n"
                                         for sid, seg, vis, tpl, d in spec))
    return o


class ChaptersTest(unittest.TestCase):
    def test_follows_youtubes_rules_and_names_chapters_from_the_journey(self):
        ch = kit.chapters(work(), BRIEF, timeline(SPEC)).splitlines()
        self.assertEqual(ch, ["0:00 Intro & The problem", "0:12 Open the map & How it works: The nightly pipeline",
                              "0:30 Run the scan", "0:42 Open a finding & Wrap-up"])  # each under 10 s takes in the next
        starts = [int(c.split()[0].split(":")[0]) * 60 + int(c.split()[0].split(":")[1]) for c in ch]
        total = sum(x[-1] for x in SPEC)
        self.assertTrue(all(b - a >= 10 for a, b in zip(starts, starts[1:] + [total])))

    def test_a_short_video_gets_none(self):
        spec = [("s01", "context", "anim", "title", 3), ("s02", "product", "capture", None, 8), ("s03", "close", "anim", "close", 4)]
        self.assertIsNone(kit.chapters(work(spec), BRIEF, timeline(spec)))


class VerticalPlanTest(unittest.TestCase):
    def test_the_opening_ends_on_a_scene_boundary_and_the_close_fits_in_45_s(self):
        a_end, c_start, total = kit.vertical_plan(timeline(SPEC))
        self.assertEqual((a_end, c_start, total), (30.5, 50.5, 55.0))
        self.assertLessEqual(a_end - kit.JOIN_S + (total - c_start), 45)

    def test_a_short_video_is_used_whole(self):
        spec = SPEC[:3] + SPEC[-1:]
        self.assertEqual(kit.vertical_plan(timeline(spec)), (17.0, None, 17.0))

    def test_captions_move_below_the_picture_and_across_the_cut(self):
        o = Path(tempfile.mkdtemp())
        (o / "captions.ass").write_text(
            "[Script Info]\nPlayResX: 1920\nPlayResY: 1080\nWrapStyle: 2\n\n[V4+ Styles]\n"
            "Style: Default,Geist SemiBold,44,&H00FFFFFF,&H80FFFFFF,&HFF000000,&H4D000000,0,0,0,0,100,100,0,0,4,12,0,2,160,160,26,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            "Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,first\n"
            "Dialogue: 0,0:00:40.00,0:00:42.00,Default,,0,0,0,,cut away\n"
            "Dialogue: 0,0:00:51.00,0:00:53.00,Default,,0,0,0,,the close\n")
        text = kit.vertical_captions(o, 30.5, 50.5).read_text()
        self.assertIn("PlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0", text)
        self.assertIn(",44,&H00FFFFFF,", text)
        self.assertTrue(re.search(r",2,70,70,520,1$", text, re.M))
        self.assertIn("0:00:01.00,0:00:03.00,Default,,0,0,0,,first", text)
        self.assertNotIn("cut away", text)
        self.assertIn("0:00:30.70,0:00:32.70,Default,,0,0,0,,the close", text)  # 51 - (50.5 - 30.2)


class WriteupTest(unittest.TestCase):
    GOOD = ("## Inspiration\n_(Your team's words: what made you build this?)_\n\n"
            "## What it does\nIt pins every report on a map. [src: README.md:1]\n\n"
            "## How we built it\n- A nightly job fetches the CSVs. [src: README.md:2]\n\n"
            "## Challenges we ran into\n_(Your team's words)_\n\n## Accomplishments that we're proud of\n_(Your team's words)_\n\n"
            "## What we learned\n_(Your team's words)_\n\n## What's next\n_(Your team's words)_\n")

    def out(self, text):
        o = Path(tempfile.mkdtemp())
        (o / "README.md").write_text("Field Scan pins reports.\nA nightly job.\n")
        (o / "brief.json").write_text(json.dumps({**BRIEF, "project": {"name": "Field Scan", "source": {"path": str(o)}}}))
        (o / "writeup.md").write_text(text)
        return o

    def test_a_cited_draft_with_prompts_for_the_team_passes_and_publishes_clean(self):
        o = self.out(self.GOOD)
        self.assertEqual(scriptmod.writeup_check(o)["errors"], [])
        root = Path(tempfile.mkdtemp())
        text = kit.devpost(o, json.loads((o / "brief.json").read_text()), root).read_text()
        self.assertNotIn("[src", text)
        self.assertIn("It pins every report on a map.\n", text)
        self.assertIn("_(Your team's words: what made you build this?)_", text)
        self.assertTrue(text.endswith("## Links\n- Live app: https://fieldscan.app\n"))

    def test_invented_facts_missing_sections_and_bad_sources_fail(self):
        errs = scriptmod.writeup_check(self.out(self.GOOD.replace(" [src: README.md:1]", "")))["errors"]
        self.assertTrue(any("What it does: no source tag" in e for e in errs), errs)
        errs = scriptmod.writeup_check(self.out(self.GOOD.replace("It pins every report on a map. [src: README.md:1]",
                                                                  "_(Your team's words)_")))["errors"]
        self.assertTrue(any("the repo answers this one" in e for e in errs), errs)
        errs = scriptmod.writeup_check(self.out(self.GOOD.replace("## What we learned\n_(Your team's words)_\n\n", "")))["errors"]
        self.assertTrue(any("exactly, in order" in e for e in errs), errs)
        errs = scriptmod.writeup_check(self.out(self.GOOD.replace("README.md:2]", "README.md:9]")))["errors"]
        self.assertTrue(any("past the end" in e for e in errs), errs)
        self.assertIsNone(kit.devpost(self.out(self.GOOD.replace(" [src: README.md:1]", "")), BRIEF, Path(tempfile.mkdtemp())))


class PublishTest(unittest.TestCase):
    def test_images_and_the_vertical_cut_from_the_clean_film(self):
        o, root = work(), Path(tempfile.mkdtemp())
        total = sum(x[-1] for x in SPEC)
        subprocess.run([FF, "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=s=1920x1080:r=30:d={total}", "-f", "lavfi", "-i",
                        f"sine=frequency=440:duration={total}", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "ultrafast",
                        "-c:a", "aac", "-shortest", str(o / "final-clean.mp4")], check=True)
        done, notes = kit.publish(o, BRIEF, timeline(SPEC), root)
        self.assertTrue((root / "chapters.txt").exists())
        gallery = sorted(p.name for p in (root / "images").glob("gallery-*.jpg"))
        self.assertEqual(gallery, ["gallery-01-s04.jpg", "gallery-02-s05.jpg", "gallery-03-s06.jpg", "gallery-04-s07.jpg"])
        self.assertIn("1800x1200", subprocess.run([FF, "-i", str(root / "images" / gallery[0])], capture_output=True, text=True).stderr)
        self.assertIn("1280x720", subprocess.run([FF, "-i", str(root / "images/thumbnail.jpg")], capture_output=True, text=True).stderr)
        v = streams(root / "vertical.mp4")
        self.assertAlmostEqual(v["video_s"], 30.5 - kit.JOIN_S + 4.5, delta=0.1)
        self.assertAlmostEqual(v["audio_s"], v["video_s"], delta=0.1)
        self.assertIn("1080x1920", subprocess.run([FF, "-i", str(root / "vertical.mp4")], capture_output=True, text=True).stderr)
        self.assertIn("no devpost.md", " ".join(notes))


if __name__ == "__main__":
    unittest.main()
