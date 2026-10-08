"""Record once, edit later: a take's recording is retimed so each action lands on its voice word."""
import json, subprocess, sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_audio_stitch_qa import FF, SCRIPTS, info, project, run  # noqa: E402

sys.path.insert(0, str(SCRIPTS))
import stitch  # noqa: E402


def played(segs):
    return sum((b - a) / s + h for a, b, s, h in segs)


class RetimePlanTest(unittest.TestCase):
    def test_early_action_waits_on_a_frame_for_its_word(self):
        segs = stitch.retime_plan(4.0, [(1.0, 2.5)], 6.0)
        self.assertEqual(segs[0], (0.0, 1.0, 1.0, 1.5))   # real time, then hold 1.5 s before the click
        self.assertEqual(segs[1][:3], (1.0, 4.0, 1.0))

    def test_late_action_plays_faster_but_never_past_the_cap(self):
        segs = stitch.retime_plan(8.0, [(5.0, 2.0)], 6.0)
        self.assertAlmostEqual(segs[0][2], 2.5)            # wanted 5/2 = 2.5x: exactly the cap
        segs = stitch.retime_plan(8.0, [(6.0, 1.0)], 6.0)
        self.assertAlmostEqual(segs[0][2], 2.5)            # 6x wanted: capped, the click lands a little late

    def test_too_long_a_take_is_sped_up_then_trimmed_to_fit(self):
        segs = stitch.retime_plan(20.0, [], 4.0)
        self.assertAlmostEqual(played(segs), 4.0, places=3)
        self.assertAlmostEqual(segs[-1][2], 2.5)
        self.assertAlmostEqual(segs[-1][1], 10.0)          # 4 s at 2.5x covers the first 10 s

    def test_after_the_last_action_only_its_settle_must_fit(self):
        segs = stitch.retime_plan(5.0, [(1.0, 1.8)], 3.0, keep_until=2.0)
        self.assertEqual(segs[-1][2], 1.0)                 # 1 s of settle fits in the 1.2 s left: real time
        self.assertAlmostEqual(segs[-1][1], 2.2)           # and the idle tail is cut

    def test_never_slower_than_real_time(self):
        self.assertTrue(all(s >= 1.0 for _, _, s, _ in stitch.retime_plan(3.0, [(1.0, 2.0), (2.0, 4.0)], 6.0)))


class IdleAndSlowTest(unittest.TestCase):
    def test_idle_time_is_cut_before_anything_speeds_up(self):
        segs = stitch.retime_plan(8.0, [(6.0, 4.0)], 6.0, idle=[(2.0, 4.5)])
        self.assertTrue(all(sp == 1.0 for _, _, sp, _ in segs))      # 2 s of the waiting is cut: all real time
        self.assertAlmostEqual(played(segs), 6.0, places=3)
        self.assertAlmostEqual(segs[0][1], 2.5, places=3)            # 0.5 s of the idle stretch is left, then a cut
        self.assertAlmostEqual(segs[1][0], 4.5, places=3)

    def test_a_glide_or_typing_is_never_sped_past_1_6x(self):
        segs = stitch.retime_plan(10.0, [(8.0, 4.0)], 6.0, slow=[(1.0, 3.0)])
        speeds = {round(a, 2): sp for a, _, sp, _ in segs}
        self.assertEqual(speeds[1.0], stitch.SLOW_SPEED)
        self.assertGreater(speeds[0.0], stitch.SLOW_SPEED)          # the rest makes up the time

    def test_no_idle_or_slow_keeps_the_old_plan(self):
        self.assertEqual(stitch.retime_plan(8.0, [(5.0, 2.0)], 6.0, idle=[], slow=[]), stitch.retime_plan(8.0, [(5.0, 2.0)], 6.0))


class RetimeIngestTest(unittest.TestCase):
    def test_ingest_moves_the_click_onto_its_word(self):
        o, _ = project()
        # s02's take: 5 s of gray with a white flash at 1.0 s (the click); the voice says "here" at 1.8 s
        subprocess.run([FF, "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:s=1920x1080:r=30:d=5",
                        "-vf", "drawbox=c=white:t=fill:enable='between(t,1.0,1.4)'", "-pix_fmt", "yuv420p", "-c:v", "libx264",
                        str(o / "capture/s02.mp4")], check=True)
        (o / "capture/steps.json").write_text(json.dumps({"version": 1, "base_url": "http://x", "scenes": {
            "s02": {"steps": [{"do": "click", "target": {"text": "Go"}, "say": "here"}]}}}))
        (o / "capture/record.json").write_text(json.dumps({"s02": {"recorded_s": 5.0, "need_s": 2.0, "zooms": [],
                                                                   "actions": [{"step": 0, "at_s": 1.0, "do": "click", "say": "here"}]}}))
        v = json.loads((o / "voice/voice.json").read_text())
        v["clips"][0]["words"] = [{"w": "Look", "t0": 0.0, "t1": 0.4}, {"w": "here.", "t0": 1.8, "t1": 2.2}]
        (o / "voice/voice.json").write_text(json.dumps(v))
        code, res = run("stitch.py", o, "ingest")
        self.assertEqual(code, 0, res)
        timed = o / "capture/s02-timed.mp4"
        self.assertTrue(timed.exists())
        want = 0.3 + 1.8 - 0.3                              # lead + word - a moment early
        self.assertLess(brightness(timed, want - 0.3), 160)  # still waiting
        self.assertGreater(brightness(timed, want + 0.15), 200)  # the flash now lands on "here"
        d, _ = info(o / "render/segments/s02.mp4")
        self.assertAlmostEqual(d, 3.0, delta=0.07)          # the scene keeps its timeline length


def brightness(path, t):
    raw = subprocess.run([FF, "-v", "quiet", "-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1", "-vf", "scale=32:18",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    return sum(raw) / len(raw)


if __name__ == "__main__":
    unittest.main()
