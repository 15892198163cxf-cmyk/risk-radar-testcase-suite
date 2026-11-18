#!/usr/bin/env python3
"""Exercise the PDF adapter through its CLI without contacting the OCR service."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("parse_pdf.py").resolve()


class PdfAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dependency = self.root / "custom-ocr"
        self.write_library(self.dependency)

    def write_library(self, root, ok=True):
        lib = root / "scripts" / "lib.py"
        lib.parent.mkdir(parents=True, exist_ok=True)
        lib.write_text(
            "import os\n"
            "def parse_document(**kwargs):\n"
            f"    return {{'ok': {ok!r}, 'text': 'fixture result', 'inputs': kwargs, "
            "'legacy_token_present': 'PADDLEOCR_ACCESS_TOKEN' in os.environ}\n",
            encoding="utf-8",
        )

    def run_adapter(self, *args, script=SCRIPT, configured=True, token=None, bootstrap=None):
        env = dict(os.environ)
        for key in ("PADDLEOCR_SKILL_DIR", "PADDLEOCR_API_TOKEN", "PADDLEOCR_ACCESS_TOKEN"):
            env.pop(key, None)
        if configured:
            env["PADDLEOCR_SKILL_DIR"] = str(self.dependency)
        if token:
            env["PADDLEOCR_API_TOKEN"] = token
        command = [sys.executable, "-X", "utf8"]
        command += ["-c", bootstrap] if bootstrap else [str(script)]
        return subprocess.run(
            command + list(args), cwd=self.root, env=env,
            capture_output=True, text=True, encoding="utf-8", timeout=15,
        )

    def test_explicit_dependency_url_stdout_and_no_default_credential(self):
        result = self.run_adapter("--file-url", "https://example.invalid/prd.pdf", "--stdout")
        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("fixture result", payload["text"])
        self.assertEqual("https://example.invalid/prd.pdf", payload["inputs"]["file_url"])
        self.assertIsNone(payload["inputs"]["file_path"])
        self.assertFalse(payload["legacy_token_present"])

    def test_local_input_and_json_file_output(self):
        source = self.root / "需求.pdf"
        source.write_bytes(b"fixture")
        output = self.root / "nested" / "parsed.json"
        result = self.run_adapter("--file-path", str(source), "--output", str(output))
        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(str(source.resolve()), payload["inputs"]["file_path"])
        self.assertIsNone(payload["inputs"]["file_url"])

    def test_ocr_failure_keeps_result_and_nonzero_exit(self):
        self.write_library(self.dependency, ok=False)
        result = self.run_adapter("--file-url", "https://example.invalid/prd.pdf", "--stdout")
        self.assertEqual(1, result.returncode)
        self.assertFalse(json.loads(result.stdout)["ok"])

    def test_invalid_explicit_dependency_does_not_silently_fall_back(self):
        self.dependency = self.root / "missing-custom-install"
        result = self.run_adapter("--file-url", "https://example.invalid/prd.pdf", "--stdout")
        self.assertEqual(1, result.returncode)
        self.assertIn(str(self.dependency), result.stderr)
        self.assertIn("PADDLEOCR_SKILL_DIR", result.stderr)

    def test_missing_input_file_stops_before_loading_dependency(self):
        result = self.run_adapter("--file-path", str(self.root / "missing.pdf"), "--stdout")
        self.assertEqual(1, result.returncode)
        self.assertIn("文件不存在", result.stderr)

    def test_standalone_sibling_dependency(self):
        script = self.root / "skills" / "qa-testcase-generator-radar" / "scripts" / "parse_pdf.py"
        script.parent.mkdir(parents=True)
        shutil.copyfile(SCRIPT, script)
        self.write_library(script.parents[2] / "paddleocr-doc-parsing")
        result = self.run_adapter("--file-url", "https://example.invalid/prd.pdf", "--stdout", script=script, configured=False)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])

    def test_nested_suite_uses_common_dependency(self):
        script = self.root / "common" / "risk-radar-testcase-suite" / "qa-testcase-generator-radar" / "scripts" / "parse_pdf.py"
        script.parent.mkdir(parents=True)
        shutil.copyfile(SCRIPT, script)
        self.write_library(self.root / "common" / "paddleocr-doc-parsing")
        result = self.run_adapter("--file-url", "https://example.invalid/prd.pdf", "--stdout", script=script, configured=False)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])

    def test_missing_dependency_reports_configuration_help(self):
        script = self.root / "skills" / "qa-testcase-generator-radar" / "scripts" / "parse_pdf.py"
        script.parent.mkdir(parents=True)
        shutil.copyfile(SCRIPT, script)
        result = self.run_adapter("--file-url", "https://example.invalid/prd.pdf", "--stdout", script=script, configured=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("PADDLEOCR_SKILL_DIR", result.stderr)

    def test_real_dependency_rejects_missing_token_without_network(self):
        bootstrap = (
            "import runpy\nfrom unittest.mock import patch\n"
            "with patch('requests.post', side_effect=AssertionError('unexpected network')):\n"
            f"    runpy.run_path({str(SCRIPT)!r}, run_name='__main__')\n"
        )
        result = self.run_adapter("--file-url", "https://example.invalid/prd.pdf", "--stdout", configured=False, bootstrap=bootstrap)
        self.assertEqual(1, result.returncode, result.stderr)
        self.assertEqual("CONFIG_ERROR", json.loads(result.stdout)["error"]["code"])

    def test_real_dependency_uses_runtime_token_without_network(self):
        bootstrap = (
            "import runpy\nfrom unittest.mock import patch, Mock\n"
            "with patch('requests.post', return_value=Mock(status_code=503, text='fixture unavailable')) as request:\n"
            "    try:\n"
            f"        runpy.run_path({str(SCRIPT)!r}, run_name='__main__')\n"
            "    finally:\n"
            "        assert request.call_args.kwargs['headers']['Authorization'] == 'bearer fixture-token'\n"
        )
        result = self.run_adapter("--file-url", "https://example.invalid/prd.pdf", "--stdout", configured=False, token="fixture-token", bootstrap=bootstrap)
        self.assertEqual(1, result.returncode, result.stderr)
        self.assertNotIn("AssertionError", result.stderr)
        self.assertEqual("API_ERROR", json.loads(result.stdout)["error"]["code"])


if __name__ == "__main__":
    unittest.main()
