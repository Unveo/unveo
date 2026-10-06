import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills/unveo/scripts/check_setup.py"


def run(home, *args):
    env = {**os.environ, "UNVEO_HOME": str(home)}
    p = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env, timeout=120)
    return p.returncode, json.loads(p.stdout.strip().splitlines()[-1])


class CheckSetupTest(unittest.TestCase):
    def test_empty_home_reports_missing_venv_with_fix_and_exits_2(self):
        with tempfile.TemporaryDirectory() as home:
            code, out = run(home)
        self.assertEqual(code, 2)
        self.assertFalse(out["ok"])
        self.assertEqual(out["step"], "setup")
        self.assertFalse(out["checks"]["venv"]["ok"])
        self.assertIn("venv", out["checks"]["venv"]["fix"])
        self.assertTrue(out["checks"]["python"]["ok"])
        self.assertTrue(Path(out["skill_dir"], "SKILL.md").exists())

    def test_output_names_every_check(self):
        with tempfile.TemporaryDirectory() as home:
            _, out = run(home)
        self.assertLessEqual({"python", "venv", "packages", "chromium", "ffmpeg"}, set(out["checks"]))
        self.assertIn("py", out)

    def test_real_home_passes_once_installed(self):
        real = Path(os.environ.get("UNVEO_HOME", Path.home() / ".unveo"))
        if not (real / "setup.json").exists():
            self.skipTest("unveo not installed on this machine")
        code, out = run(real)
        self.assertEqual(code, 0, out)
        self.assertTrue(out["ok"])


if __name__ == "__main__":
    unittest.main()
