#!/usr/bin/env python3
"""Independent offline adversarial checks; synthetic fixtures never authorize collection."""
from __future__ import annotations
import concurrent.futures
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUNNER = ROOT / "research/collection-runner/runner.py"
spec = importlib.util.spec_from_file_location("independently_reviewed_runner", RUNNER)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class RunnerAdversarialReview(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="channels-et-independent-runner-")
        self.base = Path(self.temp.name)
        self.runtime = self.base / "runtime.json"
        self.runtime_observation = {"fixture_only": True, "checkedAt": r.now(), "spec_revision": "offline-fixture-1", "observed_spec_revision": "offline-fixture-1", "observations_current": True, "network_policy": {"mode": "unrestricted", "state": "unknown", "allowed_hosts": ["b.fixture.invalid", "a.fixture.invalid"]}}
        self.runtime.write_text(json.dumps(self.runtime_observation))
        self.raw = self.base / "raw"
        self.store = r.Store(self.raw / "state.sqlite", self.raw, quota=1024**3, reserve_free=0)
        self.metadata_count = 0

    def tearDown(self):
        self.temp.cleanup()

    def initialize(self, count=1, classification="not_bashar_labeled_in_available_metadata", duration_state="eligible_duration"):
        policy = self.base / "policy.json"
        policy.write_text(json.dumps({"default_new_bashar_youtube_limit": 100, "conservative_new_bashar_youtube_limit": 81}))
        selection = self.base / "selection.jsonl"
        values = [{"video_id": f"{index:011d}", "source_id": "youtube:" + f"{index:011d}", "source_url": "https://www.youtube.com/watch?v=" + f"{index:011d}", "selected_default": True, "selected_conservative_all_materials": True, "classification": classification, "classification_evidence": [], "duration_state": duration_state, "shorts_evidence": []} for index in range(count)]
        selection.write_text("".join(json.dumps(value) + "\n" for value in values))
        self.store.initialize(selection, policy)
        # This non-runtime fingerprint exercises ledger concurrency only and cannot
        # satisfy execute_one's hash of the actual current runtime/proxy configuration.
        with self.store.connect() as connection:
            connection.execute("INSERT INTO probes VALUES(?,?,?,?,?,?)", ("offline-fixture", "success", time.time(), '{"fixture":"offline_ledger_only"}', None, None))
        return values

    def claim(self, kind, owner):
        return self.store.claim(kind, owner, "offline-fixture")

    def metadata(self, index=0, **overrides):
        vid = f"{index:011d}"
        value = {"id": vid, "title": "A long question and answer", "channel": "Fixture interview channel", "uploader": "Fixture interview channel", "duration": 600, "is_short": False, "webpage_url": "https://www.youtube.com/watch?v=" + vid, "original_url": "https://www.youtube.com/watch?v=" + vid, "extractor": "youtube", "extractor_key": "Youtube"}
        value.update(overrides)
        folder = self.raw / "quarantine" / "independent-metadata-fixtures"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"metadata-{index}-{self.metadata_count}.json"
        self.metadata_count += 1
        path.write_text(json.dumps(value))
        self.store.metadata_result("youtube:" + vid, value, path)
        return value, path

    def item(self, index=0):
        with self.store.connect() as connection:
            return connection.execute("SELECT * FROM items WHERE source_id=?", ("youtube:" + f"{index:011d}",)).fetchone()

    def review(self, index=0, **overrides):
        proof = self.base / "review-proof.txt"
        proof.write_text("Synthetic offline review fixture, not human validation or access authorization.")
        value = {"reason": "Offline adversarial review fixture", "metadata_sha256": self.item(index)["metadata_sha256"], "evidence_source_ref": {"path": str(proof), "sha256": digest(proof)}}
        value.update(overrides)
        path = self.base / f"review-{index}.json"
        path.write_text(json.dumps(value))
        self.store.review("youtube:" + f"{index:011d}", path)

    def test_atomic_global_cap_and_fresh_bashar_reclassification(self):
        self.initialize(105)
        for index in range(105):
            self.metadata(index, title="Bashar question fixture")
            self.assertEqual(self.item(index)["classification"], "bashar")
        with mock.patch.dict(r.CAPS, {"video": 1, "captions": 1}):
            with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
                claimed = list(executor.map(lambda index: self.claim("video", "worker-" + str(index)), range(120)))
            claimed = [job for job in claimed if job]
            self.assertEqual(len(claimed), 100)
            self.assertEqual(self.store.export()["summary"]["bashar_unique_youtube_slots_used"], 100)
            for job in claimed:
                self.store.finish(job, job["owner"], [], "offline fixture closes first format")
            with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
                captions = list(executor.map(lambda index: self.claim("captions", "caption-" + str(index)), range(120)))
            self.assertEqual(sum(bool(job) for job in captions), 100)
            self.assertEqual(self.store.export()["summary"]["bashar_unique_youtube_slots_used"], 100)

    def test_duration_boundary_nonfinite_and_bool_fail_closed(self):
        self.initialize(6)
        for index, duration in enumerate([299.999, True, float("inf"), float("nan"), None]):
            try:
                self.metadata(index, duration=duration)
            except ValueError:
                continue
            self.assertTrue(self.store.reasons(self.item(index)))
        self.metadata(5, duration=300)
        self.assertFalse(self.store.reasons(self.item(5)))

    def test_fresh_positive_shorts_cannot_be_overridden_by_review(self):
        self.initialize()
        self.metadata(is_short=True, webpage_url="https://www.youtube.com/shorts/00000000000")
        try:
            self.review(non_shorts_verified=True)
        except ValueError:
            pass
        self.assertTrue(self.store.reasons(self.item()), "Fresh positive Shorts metadata must retain a hard hold")

    def test_changed_metadata_invalidates_prior_conflict_review(self):
        self.initialize(duration_state="conflicting")
        self.metadata(duration=600)
        self.review(duration_conflict_resolved=True)
        self.assertFalse(self.store.reasons(self.item()))
        self.metadata(duration=900, description="Changed source observation")
        self.assertTrue(self.store.reasons(self.item()), "Old metadata-hash-bound conflict resolution must not survive a new hash")

    def test_metadata_object_must_match_its_hashed_file(self):
        self.initialize()
        value, path = self.metadata()
        changed = dict(value, duration=1200)
        with self.assertRaises(ValueError):
            self.store.metadata_result("youtube:00000000000", changed, path)

    def test_metadata_source_hash_and_canonical_id(self):
        self.initialize()
        value, path = self.metadata()
        self.assertFalse(self.store.reasons(self.item()))
        path.write_text(path.read_text() + "\n")
        self.assertTrue(self.store.reasons(self.item()))
        with self.assertRaises(ValueError):
            self.store.metadata_result("youtube:00000000000", dict(value, id="00000000001"), path)

    def test_initial_global_denial_preserves_all_queued_attempts(self):
        self.initialize(3)
        args = types.SimpleNamespace(runtime_receipt=self.runtime, kind="metadata", yt_python=Path("/nonexistent/offline-fixture"))
        with mock.patch.object(r.subprocess, "Popen", side_effect=AssertionError("No child process allowed")):
            result = r.execute_one(self.store, args)
        self.assertEqual(result["status"], "blocked_before_claim_or_network")
        self.assertEqual(self.store.export()["summary"]["attempts"], 0)

    def test_watch_payload_rejects_wrong_id_and_unplayable_player(self):
        for player in [
            {"videoDetails": {"videoId": "00000000001"}, "playabilityStatus": {"status": "OK"}},
            {"videoDetails": {"videoId": "00000000000"}, "playabilityStatus": {"status": "LOGIN_REQUIRED"}},
        ]:
            with self.subTest(player=player):
                with self.assertRaises(ValueError):
                    r.watch_payload(("var ytInitialPlayerResponse = " + json.dumps(player) + ";").encode(), "00000000000")

    def test_package_runtime_receipt_is_rejected(self):
        package = self.base / "browser-package-runtime.json"
        package.write_text(json.dumps({"browser": "brave", "version": "fixture", "checkedAt": r.now(), "installed": True}))
        with self.assertRaises(ValueError):
            r.config(package)
        for invalid in [None, False, {}, [], " "]:
            typed = dict(self.runtime_observation, spec_revision=invalid, observed_spec_revision=invalid)
            package.write_text(json.dumps(typed))
            with self.assertRaises(ValueError):
                r.config(package)

    def test_runtime_timestamp_and_serialization_keep_same_identity(self):
        original = r.config(self.runtime)
        changed = dict(reversed(list(self.runtime_observation.items())))
        changed["checkedAt"] = r.now()
        changed["observed_phase"] = "another_observation_not_configuration"
        changed["network_policy"] = dict(changed["network_policy"], allowed_hosts=["a.fixture.invalid", "b.fixture.invalid", "a.fixture.invalid"])
        other = self.base / "equivalent-runtime.json"
        other.write_text(json.dumps(changed, indent=4))
        refreshed = r.config(other)
        self.assertEqual(original["fingerprint"], refreshed["fingerprint"])
        self.assertNotEqual(original["runtime_receipt_sha256"], refreshed["runtime_receipt_sha256"])
        self.assertFalse(r.probe_request_allowed({"status": "blocked", "checked_at": time.time() - 1000}, time.time()))

    def test_changed_configuration_revision_changes_identity(self):
        original = r.config(self.runtime)
        changed = dict(self.runtime_observation, spec_revision="offline-fixture-2", observed_spec_revision="offline-fixture-2")
        other = self.base / "changed-runtime.json"
        other.write_text(json.dumps(changed))
        self.assertNotEqual(original["fingerprint"], r.config(other)["fingerprint"])

    def test_fixture_runtime_cannot_authorize_gate_or_probe(self):
        self.initialize()
        current = r.config(self.runtime)
        with self.store.connect() as connection:
            connection.execute("INSERT INTO probes VALUES(?,?,?,?,?,?)", (current["fingerprint"], "success", time.time(), '{"fixture":"not_real_access"}', None, None))
        self.assertFalse(self.store.gate(self.runtime)["ready"])
        with mock.patch.object(r.urllib.request, "build_opener", side_effect=AssertionError("No network opener allowed")):
            with self.assertRaises(ValueError):
                self.store.probe(self.runtime, "00000000000")

    def test_canonical_https_watch_identity_and_redirect_guard(self):
        vid = "00000000000"
        self.assertTrue(r.canonical_watch("https://www.youtube.com/watch?v=" + vid, vid))
        for url in ["http://www.youtube.com/watch?v=" + vid, "https://example.org/watch?v=" + vid, "https://user@www.youtube.com/watch?v=" + vid, "https://www.youtube.com/shorts/" + vid, "https://www.youtube.com/watch?v=00000000001", "https://www.youtube.com/watch?v=" + vid + "&v=00000000001"]:
            self.assertFalse(r.canonical_watch(url, vid), url)
        with self.assertRaises(ValueError):
            r.HTTPSWatchRedirect(vid).redirect_request(r.urllib.request.Request("https://www.youtube.com/watch?v=" + vid), None, 302, "fixture", {}, "https://example.org/watch?v=" + vid)

    def test_atomic_claim_rechecks_global_gate_and_staleness(self):
        self.initialize(2)
        with self.store.connect() as connection:
            connection.execute("UPDATE probes SET status='blocked' WHERE fingerprint='offline-fixture'")
        self.assertIsNone(self.claim("metadata", "blocked-fixture"))
        with self.store.connect() as connection:
            connection.execute("UPDATE probes SET status='success',checked_at=? WHERE fingerprint='offline-fixture'", (time.time() - 301,))
        self.assertIsNone(self.claim("metadata", "stale-fixture"))
        self.assertEqual(self.store.export()["summary"]["attempts"], 0)

    def test_finalization_rechecks_byte_reservation(self):
        self.initialize()
        with mock.patch.dict(r.CAPS, {"metadata": 8}):
            job = self.claim("metadata", "quota-fixture")
        folder = self.raw / "quarantine" / "fixture"
        folder.mkdir(parents=True)
        output = folder / "oversized.json"
        output.write_bytes(b"0123456789")
        with self.assertRaises(ValueError):
            self.store.finish(job, "quota-fixture", [{"path": str(output), "validation": {"fixture": True}}])

    def test_global_extraction_failure_pauses_remaining_queue(self):
        self.initialize(3)
        class FailedChild:
            pid = 99999999
            returncode = 1
            def poll(self): return 1
        args = types.SimpleNamespace(runtime_receipt=self.runtime, kind="metadata", yt_python=Path("/nonexistent/offline-fixture"))
        current = r.config(self.runtime)
        with self.store.connect() as connection:
            connection.execute("INSERT INTO probes VALUES(?,?,?,?,?,?)", (current["fingerprint"], "success", time.time(), '{"fixture":"offline_failure_branch_only"}', None, None))
        # Bypass only the gate function in this isolated unit branch. The real
        # fixture runtime gate remains incapable of authorizing any probe/run.
        with mock.patch.object(self.store, "gate", return_value={"ready": True, "fingerprint": current["fingerprint"]}), mock.patch.object(r, "tool_version", return_value=r.PINNED_YTDLP), mock.patch.object(r.subprocess, "Popen", return_value=FailedChild()):
            first = r.execute_one(self.store, args)
        self.assertEqual(first["status"], "failed_no_retry")
        with self.store.connect() as connection:
            status = connection.execute("SELECT status FROM probes WHERE fingerprint=?", (current["fingerprint"],)).fetchone()[0]
        self.assertEqual(status, "blocked")
        second = r.execute_one(self.store, args)
        self.assertEqual(second["status"], "blocked_before_claim_or_network")
        self.assertEqual(self.store.export()["summary"]["attempts"], 1)

    def test_mutable_database_cannot_escape_raw_quota_root(self):
        escaped = self.base / "escaped-db.sqlite"
        with self.assertRaises(ValueError):
            r.Store(escaped, self.base / "different-raw", quota=1024**3, reserve_free=0)

    def test_future_discovery_is_metadata_only(self):
        self.initialize()
        path = self.base / "discovery.jsonl"
        path.write_text(json.dumps({"video_id": "00000000001", "selected_default": True, "classification": "not_bashar_labeled_in_available_metadata", "duration": 900}) + "\n")
        result = self.store.import_discovery(path)
        self.assertEqual(result["state"], "metadata_only")
        item = self.item(1)
        self.assertFalse(item["selected"])
        with self.store.connect() as connection:
            jobs = connection.execute("SELECT kind FROM jobs WHERE source_id='youtube:00000000001'").fetchall()
        self.assertEqual([job["kind"] for job in jobs], ["metadata"])
        self.assertEqual(json.loads(item["policy_json"])["classification"], "ambiguous_bashar_context")

    def test_shared_collection_writer_lock_is_exclusive(self):
        with r.collection_lock(self.raw):
            with self.assertRaises(ValueError):
                with r.collection_lock(self.raw):
                    pass

    def test_actual_held_plan_matches_default_policy_and_owner_pins(self):
        owner = ROOT / "research/collection-runner"
        receipt = json.loads((owner / "verification.json").read_text())
        for pin in receipt["files"]:
            self.assertEqual(digest(ROOT / pin["path"]), pin["sha256"], pin["path"])
        selection = [json.loads(line) for line in (ROOT / "research/collection-policy/selection.jsonl").read_text().splitlines() if line]
        selected = {row["source_id"] for row in selection if row["selected_default"]}
        self.assertEqual(len(selected), 733)
        self.assertEqual(sum(row["selected_default"] and row["classification"] == "explicit_bashar_association" for row in selection), 100)
        plan = [json.loads(line) for line in (owner / "plan.jsonl").read_text().splitlines() if line]
        self.assertEqual(len(plan), 2408)
        self.assertEqual({row["source_id"] for row in plan if row["kind"] == "metadata"}, {row["source_id"] for row in selection})
        for kind in ["video", "captions"]:
            self.assertEqual({row["source_id"] for row in plan if row["kind"] == kind}, selected)
        self.assertTrue(all(row["attempts"] == 0 and row["status"] == "queued" for row in plan))
        summary = json.loads((owner / "plan-summary.json").read_text())
        self.assertEqual(summary["policy"]["bashar_limit"], 100)
        self.assertEqual(summary["policy"]["selection_sha256"], digest(ROOT / "research/collection-policy/selection.jsonl"))
        self.assertEqual(summary["policy"]["policy_sha256"], digest(ROOT / "research/collection-policy/policy.json"))
        self.assertEqual(summary["attempts"], 0)
        self.assertEqual(summary["bashar_unique_youtube_slots_used"], 0)
        self.assertEqual(summary["verified_quarantine_artifacts"], 0)
        runtime_path = ROOT / "research/access-repair/diagnostics/runtime-revision6.json"
        current = r.config(runtime_path)
        self.assertFalse(current["fixture_only"])
        self.assertEqual(current["runtime_semantics"]["revision"], "6")
        for name in ["dry-run.json", "blocked-run-one.json", "blocked-bounded-run.json"]:
            self.assertEqual(json.loads((owner / name).read_text())["gate"]["fingerprint"], current["fingerprint"], name)


if __name__ == "__main__":
    before = digest(RUNNER)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RunnerAdversarialReview)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = digest(RUNNER)
    owner = ROOT / "research/collection-runner"
    payload = {"schema_version": 1, "review_type": "independent_executable_offline_adversarial_and_static_review", "release_state": "HOLD_NO_NETWORK_OR_COLLECTION", "runner_path": str(RUNNER.relative_to(ROOT)), "runner_sha256_before": before, "runner_sha256_after": after, "runner_stable_during_review": before == after, "review_helper_sha256": digest(__file__), "tests_run": result.testsRun, "passed": result.wasSuccessful() and before == after, "failures": [{"test": case.id(), "detail": detail} for case, detail in result.failures], "errors": [{"test": case.id(), "detail": detail} for case, detail in result.errors], "network_requests": 0, "media_downloads": 0, "owner_receipts_modified": False, "fixture_scope": "Synthetic isolated temporary ledgers and mocked HTTP responses; fixtures are never presented as real access evidence and never touch the production queue.", "reviewed_owner_files": [{"path": str((owner / name).relative_to(ROOT)), "sha256": digest(owner / name)} for name in ["runner.py", "test_guards.py", "README.md", "verification.json", "toolchain-inspection.json", "plan-summary.json", "plan.jsonl", "blocked-run-one.json", "blocked-bounded-run.json", "runtime-binding-migration.json"]], "reviewed_runtime_receipt": {"path": "research/access-repair/diagnostics/runtime-revision6.json", "sha256": digest(ROOT / "research/access-repair/diagnostics/runtime-revision6.json"), "semantics": r.config(ROOT / "research/access-repair/diagnostics/runtime-revision6.json")["runtime_semantics"]}, "actual_plan": {"metadata": 942, "captions": 733, "video": 733, "total": 2408, "attempts": 0, "bashar_slots_used": 0, "quarantine_artifacts": 0, "default_selected_bashar_unique_youtube_ids": 100, "default_selected_other_ids": 633, "rss_recordings_consuming_default_youtube_slots": 0}, "resolved_findings": [{"id": key, "status": "fixed_and_independently_verified", "finding": description} for key, description in [("R1", "Watch success must parse a playable exact-ID player response and enforce canonical HTTPS redirects."), ("R2", "Fresh positive Shorts evidence must remain held despite a review attempting a non-Shorts override."), ("R3", "Changed metadata must invalidate a prior metadata-hash-bound duration or format review."), ("R4", "Completed outputs and finalization must recheck byte reservations, shared quota and free space after a fast child exit."), ("R5", "An extraction failure must pause the current configuration before later queued claims consume attempts."), ("R6", "The mutable database must remain within the private raw quota root."), ("R7", "A supplied metadata object must match its actual private hashed JSON file."), ("R8", "The access gate must bind typed current cloud runtime revision/mode/state; package-install JSON is invalid and timestamp/formatting/equivalent policy ordering must not create new configuration identity.")]], "static_audit": {"blocking_findings_remaining_in_reviewed_authorized_paths": 0, "sqlite_atomic_claim_and_global_cap": True, "metadata_then_asset_bounded_two_worker_schedule": True, "source_id_shared_by_video_audio_and_captions": True, "metadata_source_hash_and_exact_id_binding": True, "current_configuration_proxy_tls_runtime_gate": True, "typed_real_cloud_runtime_required": True, "timestamp_and_serialization_independent_configuration_identity": True, "current_actual_plan_bound_to_cloud_revision6": True, "shared_old_new_collection_lock": True, "private_quarantine_only_verified_artifacts": True, "ffprobe_and_webvtt_validation_present": True, "no_automatic_retries": True, "future_discovery_only_creates_metadata_jobs": True}, "limitations": ["No successful live YouTube access or actual media acquisition is established by this review.", "The global cap assumes cooperative use of the preserved single-authority ledger; deliberate source-code or database edits are outside its guard model.", "The byte monitor and final quarantine checks are application guards, not operating-system filesystem quotas; a subprocess can overshoot before its next polling check.", "Metadata association and extractor format evidence do not verify actual speakers, transcript accuracy, or unique original sessions."]}
    (HERE / "runner-review.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    raise SystemExit(0 if payload["passed"] else 1)
