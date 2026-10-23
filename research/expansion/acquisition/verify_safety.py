#!/usr/bin/env python3
"""Local safety/control tests; provider responses are fixtures, not research data."""
import contextlib
import datetime as dt
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("collector", HERE / "collect.py")
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class SafetyTests(unittest.TestCase):
    def invoke(self, args):
        with patch.object(sys, "argv", ["collect.py"] + args), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return collector.main()

    def test_block_stops_and_nonzero(self):
        with tempfile.TemporaryDirectory() as folder:
            output = pathlib.Path(folder) / "run.json"
            with patch.object(collector, "discover", return_value={"status": "blocked", "error": "fixture HTTP 403"}) as client:
                code = self.invoke(["search", "--max-jobs", "4", "--output", str(output)])
            result = json.loads(output.read_text())
            self.assertEqual(code, 2)
            self.assertEqual(client.call_count, 1)
            self.assertTrue(result["blocked"])
            self.assertEqual(len(result["records"]), 1)
            self.assertIn("query", result["records"][0]["input_provenance"])

    def test_resume_keeps_prior_record_and_skips_job(self):
        with tempfile.TemporaryDirectory() as folder:
            output = pathlib.Path(folder) / "run.json"
            with patch.object(collector, "discover", return_value={"status": "success", "rows": []}), patch.object(collector.time, "sleep"):
                self.assertEqual(self.invoke(["search", "--max-jobs", "1", "--output", str(output)]), 0)
                initial = json.loads(output.read_text())["records"][0]
                self.assertEqual(self.invoke(["search", "--max-jobs", "2", "--resume", "--output", str(output)]), 0)
            result = json.loads(output.read_text())
            self.assertEqual(result["records"][0], initial)
            self.assertEqual(len({r["job_id"] for r in result["records"]}), 3)
            self.assertEqual(result["attempted_this_run"], 2)

    def test_person_filter_and_overwrite_protection(self):
        data = collector.read(HERE / "collection-plan.json")
        person = data["searches"][0]["person_id"]
        with tempfile.TemporaryDirectory() as folder:
            output = pathlib.Path(folder) / "run.json"
            with patch.object(collector, "discover", return_value={"status": "success", "rows": []}), patch.object(collector.time, "sleep"):
                self.invoke(["search", "--person-id", person, "--max-jobs", "2", "--output", str(output)])
                with self.assertRaises(SystemExit):
                    self.invoke(["search", "--output", str(output)])
            result = json.loads(output.read_text())
            self.assertTrue(all(r["input_provenance"]["person_id"] == person for r in result["records"]))

    def test_caption_inside_git_refused_before_provider(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(collector, "captions") as client:
                with self.assertRaises(SystemExit):
                    self.invoke(["captions", "--raw-dir", str(collector.ATLAS / "unsafe-fixture"), "--output", str(pathlib.Path(folder) / "run.json")])
                client.assert_not_called()
            outside = pathlib.Path(folder) / "external-raw"
            outside.mkdir()
            (pathlib.Path(folder) / ".git").mkdir()
            self.assertFalse(collector.inside_git(outside), "empty reserved .git must not forbid external storage")
            (pathlib.Path(folder) / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
            self.assertTrue(collector.inside_git(outside), "real repository metadata must forbid raw storage")

    def test_nested_discovery_input_ids_deduplicate(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "fixture.json"
            collector.write(path, {"records": [{"rows": [{"video_id": "abcdefghijk"}, {"video_id": "abcdefghijk"}, {"video_id": "bad"}]}]})
            self.assertEqual([r["video_id"] for r in collector.input_video_jobs(path)], ["abcdefghijk"])

    def test_round_robin_broadens_prefix(self):
        jobs = [{"person_id": "a", "id": "a1"}, {"person_id": "a", "id": "a2"}, {"person_id": "b", "id": "b1"}]
        self.assertEqual([r["id"] for r in collector.round_robin(jobs)], ["a1", "b1", "a2"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SafetyTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    receipt = {"checked_at": dt.datetime.now(dt.timezone.utc).isoformat(), "tests": result.testsRun,
               "failures": len(result.failures), "errors": len(result.errors), "status": "PASS" if result.wasSuccessful() else "FAIL",
               "network_requests": 0, "basis": "Mocked provider responses test collection controls, not actual YouTube access or empirical findings."}
    collector.write(HERE / "safety-verification.json", receipt)
    sys.exit(not result.wasSuccessful())
