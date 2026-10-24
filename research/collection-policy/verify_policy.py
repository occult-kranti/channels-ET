#!/usr/bin/env python3
"""Validate real policy exports, input pins, boundary behavior and deterministic rebuild."""
import collections
import json
import tempfile
import unittest
from pathlib import Path

from build_policy import HERE, INVENTORY, build, classify, duration_details, explicit_short_objects, read_json, round_robin, sha


class PolicyVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [json.loads(line) for line in (HERE / "selection.jsonl").read_text().splitlines() if line]
        cls.summary = read_json(HERE / "summary.json")
        cls.routes = read_json(HERE / "route-inventory.json")["records"]

    def test_json_schema_all_records(self):
        import jsonschema
        validator = jsonschema.Draft202012Validator(read_json(HERE / "schema.json"))
        for row in self.rows:
            validator.validate(row)

    def test_pinned_inputs_unchanged(self):
        manifest = read_json(HERE / "input-manifest.json")
        for pin in manifest["files"] + manifest["sourcepins"] + manifest["policy_files"]:
            path = HERE / pin["path"]
            self.assertEqual(sha(path), pin["sha256"], str(path))
            self.assertEqual(path.stat().st_size, pin["bytes"])

    def test_id_uniqueness_and_disjoint_duration_accounting(self):
        self.assertEqual(len(self.rows), 942)
        self.assertEqual(len({r["video_id"] for r in self.rows}), 942)
        source_rows = {r["video_id"]: r for r in [json.loads(line) for line in (INVENTORY / "videos.jsonl").read_text().splitlines() if line]}
        self.assertEqual(set(source_rows), {r["video_id"] for r in self.rows})
        self.assertEqual(collections.Counter(r["duration_state"] for r in self.rows), {"eligible_duration": 748, "under_minimum": 123, "unknown": 61, "conflicting": 10})
        for row in self.rows:
            self.assertEqual(row["source_id"], "youtube:" + row["video_id"])
            self.assertEqual(row["source_url"], "https://www.youtube.com/watch?v=" + row["video_id"])
            self.assertTrue(row["metadata_refresh_required"])
            self.assertEqual(row["source_refs"], source_rows[row["video_id"]]["source_refs"])
            self.assertEqual(row["channel_route_ids"], source_rows[row["video_id"]]["channel_route_ids"])

    def test_duration_threshold_unknown_and_conflicts(self):
        def state(value, conflicts=()):
            return duration_details({"duration_seconds": value, "duration_conflict_values": conflicts}, 300)[0]
        self.assertEqual(state(299.999), "under_minimum")
        self.assertEqual(state(300), "eligible_duration")
        self.assertEqual(state(None), "unknown")
        self.assertEqual(state(0), "unknown")
        self.assertEqual(state(True), "invalid")
        self.assertEqual(state(float("inf")), "invalid")
        self.assertEqual(state(float("nan")), "invalid")
        self.assertEqual(state(300, [float("inf")]), "invalid")
        self.assertEqual(state(300, [300, 301]), "conflicting")
        self.assertEqual(state(299, [300]), "conflicting")

    def test_shorts_are_explicit_and_overlap_duration_exclusion(self):
        shorts = [r for r in self.rows if r["shorts_evidence"]]
        self.assertEqual([r["video_id"] for r in shorts], ["eKRwhz2gAzw"])
        self.assertEqual(shorts[0]["duration_seconds"], 155)
        self.assertFalse(shorts[0]["selected_default"])
        self.assertTrue(all(not e["live_platform_verified"] for e in shorts[0]["shorts_evidence"]))
        self.assertEqual(list(explicit_short_objects({"id": "ABCDEFGHIJK", "duration": 15})), [])
        self.assertEqual(list(explicit_short_objects({"id": "ABCDEFGHIJK", "is_short": True})), [("ABCDEFGHIJK", "/", ["is_short"])])

    def test_ambiguous_context_and_mixed_interview_routes_not_speakers(self):
        counts = collections.Counter(r["classification"] for r in self.rows)
        self.assertEqual(counts, {"explicit_bashar_association": 173, "ambiguous_bashar_context": 15, "not_bashar_labeled_in_available_metadata": 754})
        for row in self.rows:
            if row["classification"] == "ambiguous_bashar_context":
                self.assertFalse(row["selected_default"])
                self.assertFalse(row["selected_conservative_all_materials"])
        synthetic = {"source_refs": [{"source_id": "channels-ET:test", "locator": "/"}], "channel_route_ids": ["mixed"], "entity_labels": ["Other"], "title": "Other guest"}
        result, _ = classify(synthetic, {"mixed": {"url": "https://www.youtube.com/@interviews"}}, set())
        self.assertEqual(result, "not_bashar_labeled_in_available_metadata")

    def test_global_caps_and_uncapped_others(self):
        b = [r for r in self.rows if r["classification"] == "explicit_bashar_association"]
        other = [r for r in self.rows if r["classification"] == "not_bashar_labeled_in_available_metadata"]
        self.assertEqual(sum(r["selected_default"] for r in b), 100)
        self.assertEqual(sum(r["selected_conservative_all_materials"] for r in b), 81)
        reservation = read_json(HERE / "retained-bashar-reservation.json")
        self.assertEqual(len({r["source_id"] for r in reservation["records"]}), 19)
        self.assertEqual(19 + sum(r["selected_conservative_all_materials"] for r in b), 100)
        self.assertEqual(sum(r["selected_default"] for r in other), 633)
        self.assertTrue(all(r["selected_default"] == r["eligible_on_inherited_metadata"] for r in other))
        self.assertTrue({r["video_id"] for r in self.rows if r["selected_conservative_all_materials"]} <= {r["video_id"] for r in self.rows if r["selected_default"]})
        for name, field, size in [("selected-default.jsonl", "selected_default", 733), ("selected-conservative-all-materials.jsonl", "selected_conservative_all_materials", 714)]:
            exported = [json.loads(line) for line in (HERE / name).read_text().splitlines() if line]
            self.assertEqual(len(exported), size)
            self.assertEqual({r["video_id"] for r in exported}, {r["video_id"] for r in self.rows if r[field]})
        for row in self.rows:
            if row["selected_default"] or row["selected_conservative_all_materials"]:
                self.assertTrue(row["eligible_on_inherited_metadata"])
                self.assertGreaterEqual(row["duration_seconds"], 300)
                self.assertFalse(row["shorts_evidence"])

    def test_route_overlap_not_double_counted(self):
        relevant = read_json(HERE / "bashar-routes.json")["records"]
        self.assertEqual(len(self.routes), 362)
        self.assertEqual(len(relevant), 68)
        self.assertEqual(sum(bool(r["indexed_bashar_count"]) for r in relevant), 62)
        self.assertEqual(sum(r["indexed_bashar_count"] for r in self.routes), 247)
        routed_ids = set().union(*(set(r["known_bashar_video_ids"]) for r in relevant))
        self.assertEqual(len(routed_ids), 162)
        self.assertEqual(sum(r["classification"] == "explicit_bashar_association" and not r["channel_route_ids"] for r in self.rows), 11)
        self.assertTrue(all(r["whole_channel_lifetime_video_count"] is None for r in self.routes))
        self.assertIsNone(self.summary["whole_channel_lifetime_bashar_upload_count"])
        by_id = {r["video_id"]: r for r in self.rows}
        for route in self.routes:
            self.assertEqual(route["indexed_video_count"], len(set(route["known_video_ids"])))
            self.assertEqual(route["indexed_bashar_count"], len(set(route["known_bashar_video_ids"])))
            for vid in route["known_video_ids"]:
                self.assertIn(route["route_id"], by_id[vid]["channel_route_ids"])

    def test_sampling_is_deterministic_and_input_order_independent(self):
        candidates = [r for r in self.rows if r["bashar_eligible_rank"] is not None]
        forward = [r["video_id"] for r in round_robin(candidates)]
        backward = [r["video_id"] for r in round_robin(list(reversed(candidates)))]
        self.assertEqual(forward, backward)
        self.assertEqual(forward, [r["video_id"] for r in sorted(candidates, key=lambda r: r["bashar_eligible_rank"])])

    def test_publication_dates_do_not_become_original_session_dates(self):
        self.assertTrue(any(r["historical_upload_date_observations"] for r in self.rows))
        self.assertTrue(all(r["original_session_date"] is None and r["original_session_identity"] is None for r in self.rows))

    def test_deterministic_rebuild_all_exports(self):
        with tempfile.TemporaryDirectory(prefix=".verify-", dir=HERE) as temp:
            build(Path(temp))
            for path in sorted(Path(temp).iterdir()):
                self.assertEqual(path.read_bytes(), (HERE / path.name).read_bytes(), path.name)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PolicyVerification)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    receipt = {"schema_version": 1, "passed": result.wasSuccessful(), "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "scope": "metadata schema, source hashes, accounting, cap invariants, threshold boundaries, explicit Shorts evidence, route overlap, ambiguity, sampling determinism, and byte-identical offline rebuild", "release_state": "HOLD_METADATA_ONLY_NO_DOWNLOADS", "network_requests": 0, "downloads": 0, "validator": "jsonschema.Draft202012Validator plus unittest assertions", "verified_files": [{"path": p.name, "sha256": sha(p), "bytes": p.stat().st_size} for p in sorted(HERE.iterdir()) if p.is_file() and p.name != "verification.json"]}
    (HERE / "verification.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
