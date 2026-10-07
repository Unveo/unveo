import json, subprocess, sys, tempfile, unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/unveo/scripts"
sys.path.insert(0, str(SCRIPTS))
import common  # noqa: E402


def run_emit(code):
    """Run emit() in a child process so we can see its stdout and exit code."""
    p = subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0, {str(SCRIPTS)!r}); import common; {code}"],
                       capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout.strip().splitlines()[-1])


class OutDirTest(unittest.TestCase):
    def test_output_folder_ignores_itself_so_the_users_gitignore_is_never_touched(self):
        with tempfile.TemporaryDirectory() as d:
            o = common.out_dir(Path(d) / "unveo-out")
            self.assertEqual((o / ".gitignore").read_text().strip(), "*")


class PublicFolderTest(unittest.TestCase):
    def test_work_folder_sits_inside_the_users_folder(self):
        with tempfile.TemporaryDirectory() as d:
            o = common.out_dir(Path(d) / "unveo-out" / ".work")
            self.assertEqual(common.public_dir(o), Path(d) / "unveo-out")
            self.assertEqual(common.takes_dir(o), Path(d) / "unveo-out" / "your-voice")
            self.assertEqual(common.clips_dir(o), Path(d) / "unveo-out" / "your-clips")
            self.assertTrue((Path(d) / "unveo-out" / ".gitignore").exists())

    def test_an_old_flat_folder_moves_into_work_once(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "unveo-out"
            (root / "voice" / "own").mkdir(parents=True)
            (root / "brief.json").write_text("{}")
            (root / "voice" / "own" / "s02.webm").write_bytes(b"x")
            (root / "clips").mkdir()
            (root / "clips" / "shot-01.mp4").write_bytes(b"y")
            o = common.out_dir(root / ".work")
            self.assertTrue((o / "brief.json").exists())
            self.assertFalse((root / "brief.json").exists())
            self.assertTrue((root / "your-voice" / "s02.webm").exists())
            self.assertTrue((root / "your-clips" / "shot-01.mp4").exists())


class OutSizeTest(unittest.TestCase):
    def test_2k_is_the_default_and_1080p_is_an_option(self):
        with tempfile.TemporaryDirectory() as d:
            o = Path(d)
            self.assertEqual(common.out_size(o), (2560, 1440))  # no brief yet
            (o / "brief.json").write_text(json.dumps({"resolution": "1080p"}))
            self.assertEqual(common.out_size(o), (1920, 1080))
            (o / "brief.json").write_text(json.dumps({"resolution": "2k"}))
            self.assertEqual(common.out_size(o), (2560, 1440))


class EmitTest(unittest.TestCase):
    def test_ok_prints_json_last_line_and_exits_0(self):
        code, out = run_emit("common.emit('voice', outputs=['a.mp3'])")
        self.assertEqual(code, 0)
        self.assertEqual(out, {"ok": True, "step": "voice", "outputs": ["a.mp3"]})

    def test_user_action_exits_2(self):
        code, out = run_emit("common.emit('stitch', ok=False, user_action=True, message='record shot-01')")
        self.assertEqual(code, 2)
        self.assertFalse(out["ok"])

    def test_error_exits_1(self):
        code, _ = run_emit("common.emit('render', ok=False)")
        self.assertEqual(code, 1)


class JsonTest(unittest.TestCase):
    def test_write_adds_version_and_read_round_trips(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.json"
            common.write_json(p, {"a": 1})
            self.assertEqual(common.read_json(p), {"version": 1, "a": 1})

    def test_read_refuses_unknown_version(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.json"
            p.write_text('{"version": 9}')
            with self.assertRaises(ValueError):
                common.read_json(p)


class HashTest(unittest.TestCase):
    def test_sha1_of_is_stable_and_order_sensitive(self):
        self.assertEqual(common.sha1_of("a", "b"), common.sha1_of("a", "b"))
        self.assertNotEqual(common.sha1_of("a", "b"), common.sha1_of("b", "a"))
        self.assertNotEqual(common.sha1_of("ab"), common.sha1_of("a", "b"))


if __name__ == "__main__":
    unittest.main()
