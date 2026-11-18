#!/usr/bin/env python3

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


SCRIPT = Path(__file__).with_name("refresh_openviking_bug_cache.ps1")
SKILL_ROOT = SCRIPT.parents[1]
SOURCE_DATA = SKILL_ROOT / "data"
FIXTURE_DATASET = (SCRIPT.parent / "fixtures" / "normalized_bugs.jsonl").read_bytes()


class CacheHandler(BaseHTTPRequestHandler):
    dataset_requests = 0
    payload = FIXTURE_DATASET
    manifest_payload = payload

    @classmethod
    def manifest(cls):
        records = [json.loads(line) for line in cls.manifest_payload.splitlines() if line.strip()]
        current = sum("current_182d" in row.get("view_memberships", []) for row in records)
        historical = sum("historical_view" in row.get("view_memberships", []) for row in records)
        overlap = sum(
            {"current_182d", "historical_view"} <= set(row.get("view_memberships", []))
            for row in records
        )
        archive = sum(not row.get("view_memberships", []) for row in records)
        return {
            "schema_version": "1.1",
            "source_sha256": hashlib.sha256(cls.manifest_payload).hexdigest(),
            "record_count": len(records),
            "current_182d_count": current,
            "historical_view_count": historical,
            "view_overlap_count": overlap,
            "archive_only_count": archive,
            "generated_at": "2026-09-03T00:00:00Z",
        }

    def do_GET(self):
        if self.path.endswith("/manifest.json"):
            body = json.dumps(type(self).manifest()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.endswith("/normalized/normalized_bugs.jsonl"):
            type(self).dataset_requests += 1
            body = self.payload
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def log_message(self, *_args):
        return


class RefreshFastPathTests(unittest.TestCase):
    def run_refresh(self, root, *, require_remote=False):
        CacheHandler.dataset_requests = 0
        server = ThreadingHTTPServer(("127.0.0.1", 0), CacheHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            env = os.environ.copy()
            env["OPENVIKING_KNOWLEDGE_PLUGIN_USER_KEY"] = "test-token"
            env["ZINIAO_LANDMINE_ROOT"] = str(root)
            command = [
                "pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", str(SCRIPT),
                "-BaseUrl", f"http://127.0.0.1:{server.server_port}",
            ]
            if require_remote:
                command.append("-RequireRemote")
            return subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
                timeout=60,
            )
        finally:
            server.shutdown()
            server.server_close()

    def test_matching_manifest_hash_skips_dataset_download(self):
        CacheHandler.payload = b'{"id":"BUG-1","view_memberships":[],"source_view_ids":[]}\n'
        CacheHandler.manifest_payload = CacheHandler.payload
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = root / "data" / "normalized_bugs.jsonl"
            cache.parent.mkdir()
            cache.write_bytes(CacheHandler.payload)
            result = self.run_refresh(root)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("current", result.stdout)
            self.assertIn("DownloadedDataset", result.stdout)
            self.assertEqual(0, CacheHandler.dataset_requests)

    def test_hash_mismatch_downloads_and_rebuilds_in_same_isolated_root(self):
        CacheHandler.payload = FIXTURE_DATASET
        CacheHandler.manifest_payload = CacheHandler.payload
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(SOURCE_DATA, root / "data")
            cache = root / "data" / "normalized_bugs.jsonl"
            cache.write_text('{"id":"STALE","view_memberships":[],"source_view_ids":[]}\n')
            result = self.run_refresh(root, require_remote=True)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("updated", result.stdout)
            self.assertEqual(1, CacheHandler.dataset_requests)
            self.assertEqual(CacheHandler.payload, cache.read_bytes())

    def test_corrupt_download_preserves_existing_cache(self):
        CacheHandler.manifest_payload = b'{"id":"EXPECTED","view_memberships":[],"source_view_ids":[]}\n'
        CacheHandler.payload = b'{"id":"CORRUPT","view_memberships":[],"source_view_ids":[]}\n'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = root / "data" / "normalized_bugs.jsonl"
            cache.parent.mkdir()
            original = b'{"id":"LOCAL","view_memberships":[],"source_view_ids":[]}\n'
            cache.write_bytes(original)
            result = self.run_refresh(root)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("local_fallback", result.stdout)
            self.assertEqual(1, CacheHandler.dataset_requests)
            self.assertEqual(original, cache.read_bytes())

    def test_rebuild_failure_rolls_back_existing_cache(self):
        CacheHandler.payload = FIXTURE_DATASET
        CacheHandler.manifest_payload = CacheHandler.payload
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(SOURCE_DATA, root / "data")
            cache = root / "data" / "normalized_bugs.jsonl"
            original = b'{"id":"LOCAL","view_memberships":[],"source_view_ids":[]}\n'
            cache.write_bytes(original)
            (root / "data" / "landmines.jsonl").unlink()
            result = self.run_refresh(root)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("rolled back", result.stdout)
            self.assertEqual(original, cache.read_bytes())


if __name__ == "__main__":
    unittest.main()
