import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
COMMON = REPO_ROOT / "common"
SUITE = "common/risk-radar-testcase-suite"


class SkillIsolationTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (REPO_ROOT / relative_path).read_text(encoding="utf-8")

    def test_standalone_skill_entrypoints_keep_original_names(self):
        generator = self.read("common/qa-testcase-generator/SKILL.md")
        reviewer = self.read("common/qa-testcase-reviewer/SKILL.md")
        self.assertIn("name: qa-testcase-generator\n", generator)
        self.assertIn("name: qa-testcase-reviewer\n", reviewer)

    def test_radar_variants_are_distinct_and_explicit_only(self):
        for name in ("qa-testcase-generator-radar", "qa-testcase-reviewer-radar"):
            skill = self.read(f"{SUITE}/{name}/SKILL.md")
            agent = self.read(f"{SUITE}/{name}/agents/openai.yaml")
            self.assertIn(f"name: {name}\n", skill)
            self.assertIn("allow_implicit_invocation: false", agent)

    def test_workflow_routes_radar_path_only_to_isolated_variants(self):
        workflow = self.read(f"{SUITE}/risk-radar-testcase-workflow/SKILL.md")
        self.assertIn("`qa-testcase-generator-radar`", workflow)
        self.assertIn("`qa-testcase-reviewer-radar`", workflow)
        self.assertIn("unchanged no-radar compatibility path", workflow)

    def test_radar_generator_owns_radar_specific_assets(self):
        generator = COMMON / "risk-radar-testcase-suite" / "qa-testcase-generator-radar"
        required = (
            "references/radar_integration.md",
            "scripts/validate_testcase_quality.py",
            "scripts/test_radar_result_adapter.py",
        )
        for relative in required:
            self.assertTrue((generator / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
