#!/usr/bin/env python3

import json
import unittest
from pathlib import Path


GENERATOR_DIR = Path(__file__).resolve().parents[1]
COMMON_DIR = GENERATOR_DIR.parent
WORKFLOW_DIR = COMMON_DIR / "risk-radar-testcase-workflow"


class RadarResultAdapterTests(unittest.TestCase):
    def test_minimal_workflow_uses_isolated_generator_and_reviewer(self):
        entrypoint = (WORKFLOW_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("This skill orchestrates isolated radar-only dependencies", entrypoint)
        self.assertIn("Give the same requirement artifact", entrypoint)
        self.assertIn("Give the original requirement plus that radar result", entrypoint)
        self.assertIn("invoke `qa-testcase-reviewer-radar`", entrypoint)
        self.assertIn("`qa-testcase-generator-radar`", entrypoint)
        for legacy_term in (
            "prepare_generation_packets.py",
            "assemble_lean_run.py",
            "stage_timing.py",
            "audited-workflow.md",
        ):
            self.assertNotIn(legacy_term, entrypoint)

    def test_radar_result_contract_is_small(self):
        schema_path = WORKFLOW_DIR / "schemas" / "radar-result.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        risk = schema["$defs"]["risk"]
        self.assertEqual(schema["properties"]["schema_version"]["const"], "1.0")
        self.assertIn("test_points", risk["required"])
        for legacy_field in (
            "requirement_fingerprint",
            "coverage_key",
            "obligation_id",
            "decision_ids",
        ):
            self.assertNotIn(legacy_field, schema.get("required", []))
            self.assertNotIn(legacy_field, risk.get("properties", {}))

    def test_generator_keeps_one_plan_and_normal_export(self):
        adapter = (GENERATOR_DIR / "references" / "radar_integration.md").read_text(encoding="utf-8")
        skill = (GENERATOR_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Build one coverage plan", adapter)
        self.assertIn("Do not generate a radar-blind core first", adapter)
        self.assertIn("python scripts/export_excel.py", skill)
        self.assertNotIn("obligation_id", skill)
        self.assertNotIn("radar_handoff", skill)


if __name__ == "__main__":
    unittest.main()
