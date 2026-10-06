import json, re, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class VersionsTest(unittest.TestCase):
    def test_all_manifests_and_skill_md_share_one_version(self):
        versions = {p: json.loads((ROOT / p).read_text())["version"]
                    for p in [".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "plugin.json"]}
        m = re.search(r"unveo v(\S+)", (ROOT / "skills/unveo/SKILL.md").read_text())
        self.assertIsNotNone(m, "SKILL.md needs a 'unveo v<version>' line")
        versions["SKILL.md"] = m.group(1)
        self.assertEqual(len(set(versions.values())), 1, versions)

    def test_skill_name_matches_folder(self):
        text = (ROOT / "skills/unveo/SKILL.md").read_text()
        self.assertRegex(text, r"(?m)^name: unveo$")

    def test_agent_folders_point_at_the_skill(self):
        for p in [".claude/skills/unveo", ".agents/skills/unveo", ".opencode/skills/unveo"]:
            self.assertTrue((ROOT / p / "SKILL.md").exists(), p)


if __name__ == "__main__":
    unittest.main()
