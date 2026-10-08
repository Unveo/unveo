"""Cuts that breathe (round 4): transitions between scenes, and a moment to settle after the last click."""
import json, subprocess, sys, unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "tests"))
import looks, plan_timeline  # noqa: E402
from common import ffmpeg_exe  # noqa: E402
from test_audio_stitch_qa import project, run, info  # noqa: E402

SCENES = [{"id": "s01", "visual": "anim", "template": "title"}, {"id": "s02", "visual": "anim", "template": "compose"},
          {"id": "s03", "visual": "anim", "template": "explainer-system-map"}, {"id": "s04", "visual": "capture", "template": None},
          {"id": "s05", "visual": "anim", "template": "close"}]


def rgb_at(path, t):
    raw = subprocess.run([ffmpeg_exe(), "-v", "quiet", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1", "-vf", "scale=64:36",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(float).mean(axis=0)


class CutPlanTest(unittest.TestCase):
    def test_every_boundary_gets_a_transition_from_the_motion_language(self):
        cuts = looks.cuts(SCENES, "swiss")                # swiss moves with snap unless design.json says otherwise
        self.assertEqual(len(cuts), 4)
        self.assertEqual(cuts[0]["type"], "fade")         # out of the title: always a soft fade
        self.assertEqual(cuts[1]["dur"], 0)               # snap: anim -> anim is a hard cut
        self.assertEqual(cuts[2]["type"], "accent-wipe")  # anim -> recording: an accent bar sweeps across
        self.assertEqual(cuts[3]["type"], "fade")         # into the close
        self.assertTrue(all(c["dur"] in (0, looks.T_DEFAULT) for c in cuts))
        self.assertEqual(looks.cuts(SCENES, "swiss", {"motion_style": "glide"})[2]["type"], "card")

    def test_a_recording_into_an_explainer_fades_and_a_flash_is_two_frames(self):
        rec = [{"id": "s05", "visual": "capture", "template": None}, {"id": "s06", "visual": "anim", "template": "explainer-model-io"},
               {"id": "s07", "visual": "capture", "template": None}]
        cuts = looks.cuts(rec, "terminal", {"motion_style": "typewriter"})
        self.assertEqual(cuts[0]["type"], "fade")         # the explainer draws over the recording's last frame
        self.assertEqual((cuts[1]["type"], cuts[1]["dur"]), ("flash", round(looks.T_FLASH, 3)))

    def test_two_recordings_in_a_row_hard_cut_so_the_app_never_ghosts(self):
        scenes = [{"id": "s05", "visual": "capture", "template": None}, {"id": "s06", "visual": "capture", "template": None},
                  {"id": "s07", "visual": "anim", "template": "compose"}]
        cuts = looks.cuts(scenes, "editorial")
        self.assertEqual(cuts[0]["dur"], 0)   # recording -> recording: the app just carries on
        self.assertGreater(cuts[1]["dur"], 0) # recording -> animation still blends

    def test_handles_are_the_outgoing_cut_and_none_after_the_last_scene(self):
        h = looks.handles(SCENES, "editorial")
        self.assertEqual(h["s05"], 0)
        self.assertEqual(h["s01"], looks.T_DEFAULT)

    def test_design_can_turn_transitions_off(self):
        self.assertTrue(all(c["dur"] == 0 for c in looks.cuts(SCENES, "editorial", {"transition": {"dur": 0}})))


class StitchTransitionTest(unittest.TestCase):
    def build(self, design):
        o, total = project()
        (o / "film/design.json").write_text(json.dumps(design))
        for step in (("stitch.py", "ingest"), ("score.py",), ("mix.py",), ("stitch.py", "final")):
            code, res = run(step[0], o, *step[1:])
            self.assertEqual(code, 0, (step, res))
        return o, total

    def test_total_length_is_unchanged_and_the_cut_is_a_blend(self):
        o, total = self.build({"look": "editorial"})
        d, _ = info(o / "final.mp4")
        self.assertAlmostEqual(d, total, delta=0.1)
        navy, gray = rgb_at(o / "final.mp4", 1.0), rgb_at(o / "final.mp4", 3.6)   # inside s01, inside s02
        mid = rgb_at(o / "final.mp4", 2.5 + looks.T_DEFAULT / 2)                     # s01 -> s02, mid-fade
        self.assertGreater(np.abs(mid - navy).sum(), 20)
        self.assertGreater(np.abs(mid - gray).sum(), 20)
        self.assertTrue(np.all(mid >= np.minimum(navy, gray) - 12) and np.all(mid <= np.maximum(navy, gray) + 12))

    def test_drawn_transitions_render_and_keep_the_length(self):
        for kind in ("accent-wipe", "card", "dip-accent"):
            o, total = self.build({"look": "swiss", "transition": {"type": kind, "dur": 0.45}})
            d, _ = info(o / "final.mp4")
            self.assertAlmostEqual(d, total, delta=0.1, msg=kind)
        mid = rgb_at(o / "final.mp4", 2.5 + 0.45 / 2)  # dip-accent: the swiss accent fills the middle of the cut
        self.assertGreater(np.abs(mid - rgb_at(o / "final.mp4", 1.0)).sum(), 30)

    def test_zero_length_transition_is_a_hard_cut(self):
        o, _ = self.build({"look": "editorial", "transition": {"dur": 0}})
        gray = rgb_at(o / "final.mp4", 3.6)
        self.assertLess(np.abs(rgb_at(o / "final.mp4", 2.55) - gray).sum(), 12)


class BeatTest(unittest.TestCase):
    def test_cuts_snap_to_the_beat_only_where_there_is_room(self):
        scenes = [{"id": f"s0{i}", "segment": "product", "visual": "anim", "template": "compose", "narration": "x"} for i in range(1, 4)]
        clips = {s["id"]: {"file": "v.mp3", "dur_s": 3.0} for s in scenes}  # 3.7 s scenes: 0.3 s short of a beat
        tl = plan_timeline.build(scenes, clips, 60)
        snapped = plan_timeline.snap_to_beat(tl, 120, 60)
        for s in snapped["scenes"]:
            end = s["start_s"] + s["dur_s"]
            self.assertAlmostEqual(end / 0.5, round(end / 0.5), delta=0.07)  # every cut on a beat at 120 BPM
        self.assertEqual(plan_timeline.snap_to_beat(tl, 120, tl["total_s"] / 0.98)["total_s"], tl["total_s"])  # no room: unchanged
        self.assertTrue(all(0 <= s["snap_s"] <= 0.35 + 1 / 30 for s in snapped["scenes"]))  # recorded, so QA can allow for it


class SettleTest(unittest.TestCase):
    def test_a_scene_that_needs_to_settle_after_its_last_click_is_lengthened(self):
        scenes = [{"id": "s05", "segment": "product", "visual": "capture", "template": None, "narration": "x"}]
        clips = {"s05": {"file": "voice/s05.mp3", "dur_s": 3.0}}
        plain = plan_timeline.build(scenes, clips, 60)
        needed = plan_timeline.build(scenes, clips, 60, needs={"s05": 4.6})
        self.assertAlmostEqual(plain["scenes"][0]["dur_s"], 3.8, places=2)
        self.assertGreaterEqual(needed["scenes"][0]["dur_s"], 4.6)
        self.assertGreater(needed["scenes"][0]["tail_s"], plain["scenes"][0]["tail_s"])


if __name__ == "__main__":
    unittest.main()
