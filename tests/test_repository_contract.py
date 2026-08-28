import re
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).parents[1]
PROJECTS = (
    "Any-to-OpenCode",
    "Any-to-Grok-Build",
    "Any-to-Kimi-Code",
    "Any-to-ZCode",
    "Any-to-DeepSeek-Harness",
    "Any-to-Codex",
    "Any-to-Claude-Code",
    "Any-to-Pi",
    "Any-to-Antigravity",
)


class RepositoryContractTests(unittest.TestCase):
    def test_required_project_files(self):
        for relative in (
            "SKILL.md",
            "agents/openai.yaml",
            "README.md",
            "README.zh-CN.md",
            "references/defaults.json",
            "references/operation-protocol.md",
            "references/verification.json",
            "assets/readme/hero.svg",
            "assets/readme/hero-mobile.svg",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_skill_frontmatter(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        frontmatter = text.split("---", 2)[1]
        self.assertRegex(frontmatter, r"(?m)^name:\s*[a-z0-9-]+\s*$")
        self.assertRegex(frontmatter, r"(?m)^description:\s*.+$")

    def test_readmes_share_contract_and_matrix(self):
        forbidden = re.compile(r"i[ -]?need[ -]?to", re.IGNORECASE)
        for name in ("README.md", "README.zh-CN.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("schema_version", text)
            self.assertIsNone(forbidden.search(text))
            for project in PROJECTS:
                self.assertIn(project, text)

    def test_heroes_are_valid_svg(self):
        expected = {"hero.svg": "0 0 1200 420", "hero-mobile.svg": "0 0 720 720"}
        for name, viewbox in expected.items():
            root = ET.parse(ROOT / "assets" / "readme" / name).getroot()
            self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
            self.assertEqual(root.attrib.get("viewBox"), viewbox)


if __name__ == "__main__":
    unittest.main()
