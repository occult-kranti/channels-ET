"""Offline planner invariants; no fixture is a successful platform retrieval."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("batch_selection", HERE / "selection.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def upload(vid="abcdefghijk", duration=300):
    return {"video_id": vid, "source_url": "https://www.youtube.com/watch?v="+vid,
            "source_id": "youtube:"+vid, "duration_seconds": duration,
            "selected_default": True, "eligible_on_inherited_metadata": True,
            "duration_state": "eligible_duration", "shorts_evidence": [],
            "hold_or_exclusion_reasons": [], "classification": "not_bashar_labeled_in_available_metadata",
            "publisher_account_ids": ["atlas_analysis:publisher"], "historical_upload_date_observations": []}


def fixture(relationship="official", direct=False):
    person = {"practitioner_id": "person-test", "name": "Test Person",
              "account_urls_inherited": ["https://www.youtube.com/@test-person"],
              "video_urls_inherited": ["https://www.youtube.com/watch?v=abcdefghijk"] if direct else []}
    return {"people": {"records": [person]}, "links": {"records": [{"practitioner_id": "person-test",
            "publisher_matches": [{"publisher_group_id": "publisher", "inherited_account_url": "https://www.youtube.com/@test-person"}]}]},
            "analysis": {"channels": [{"id": "publisher", "relationship": relationship, "name": "Test"}]},
            "selection": [upload()], "leads": {"records": []}, "metrics": {"channels": []}}


class SelectionTests(unittest.TestCase):
    def test_exact_five_minute_boundary_and_unknowns(self):
        self.assertTrue(module.eligible(upload(duration=300)))
        for value in [299.999, None, True, float("nan"), float("inf"), -1, "600"]:
            self.assertFalse(module.eligible(upload(duration=value)), repr(value))

    def test_selection_and_all_holds_fail_closed(self):
        for field, value in [("selected_default", False), ("selected_default", 1),
                             ("eligible_on_inherited_metadata", False), ("duration_state", "conflicting"),
                             ("shorts_evidence", ["literal shorts URL"]),
                             ("hold_or_exclusion_reasons", ["unresolved"]),
                             ("source_url", "https://www.youtube.com/watch?v=XXXXXXXXXXX")]:
            row = upload(); row[field] = value
            self.assertFalse(module.eligible(row), field)

    def test_url_identity_and_non_youtube_rejection(self):
        self.assertEqual(module.video_id("https://youtu.be/abcdefghijk"), "abcdefghijk")
        self.assertEqual(module.video_id("https://music.youtube.com/podcast/abcdefghijk"), "abcdefghijk")
        self.assertIsNone(module.video_id("https://evil.example/watch?v=abcdefghijk"))
        self.assertIsNone(module.video_id("https://www.youtube.com/shorts/abcdefghijk"))
        self.assertIsNone(module.video_id("https://www.youtube.com/watch?v=too-short"))

    def test_mixed_publisher_does_not_infer_all_guest_appearances(self):
        self.assertEqual(len(module.proposal(fixture("interview/publisher"))["records"]), 0)
        self.assertEqual(len(module.proposal(fixture("community/reupload"))["records"]), 0)
        self.assertEqual(len(module.proposal(fixture("official"))["records"]), 1)

    def test_direct_link_remains_candidate_without_claiming_speaker(self):
        record = module.proposal(fixture("interview/publisher", True))["records"][0]
        self.assertEqual(record["actual_speaker_status"], "unknown_not_audio_verified")
        self.assertEqual(record["stage"], "metadata_only_proposal")
        self.assertFalse(record["downloaded"])

    def test_global_upload_dedup_and_shared_associations(self):
        data = fixture(direct=True)
        second = copy.deepcopy(data["people"]["records"][0]); second.update(practitioner_id="person-second", name="Second Person")
        data["people"]["records"].append(second)
        result = module.proposal(data)
        self.assertEqual(len(result["records"]), 1)
        self.assertEqual(len(result["records"][0]["context_associations"]), 2)
        self.assertEqual(result["summary"]["cap_slots_consumed"], 0)

    def test_joint_contexts_do_not_multiply_individual_completion(self):
        data = fixture(direct=True)
        data["people"]["records"][0]["name"] = "Caroline (Calenara; surname unresolved)"
        second = copy.deepcopy(data["people"]["records"][0]); second.update(practitioner_id="person-leo", name="Leo (Calenara; surname unresolved)")
        data["people"]["records"].append(second)
        result = module.proposal(data)
        self.assertEqual(len(result["contexts"]), 1)
        self.assertEqual(result["contexts"][0]["context_kind"], "joint_named_context")
        self.assertEqual(len(result["contexts"][0]["person_names"]), 2)
        self.assertEqual(result["summary"]["proposed_context_video_associations"], 1)

    def test_publisher_outlet_and_unmeasured_lead_stay_separate(self):
        data = fixture()
        data["leads"]["records"] = [{"name": "GFL Station", "channel_url": "https://www.youtube.com/@gflstation",
                                     "example_videos": [{"url": "https://www.youtube.com/watch?v=LMNOPQRSTUV"}]}]
        result = module.proposal(data)
        outlet = next(c for c in result["contexts"] if c["name"] == "GFL Station")
        self.assertEqual(outlet["context_kind"], "publishing_outlet")
        self.assertEqual(outlet["pilot_target"], 0)
        self.assertEqual(result["discovery_only"][0]["stage"], "unmeasured_discovery_only")

    def test_quota_bounded_and_order_deterministic(self):
        data = fixture()
        data["selection"] = [upload(f"video{i:06d}") for i in range(15)]
        first = module.proposal(data)
        data["selection"].reverse()
        self.assertEqual(first, module.proposal(data))
        self.assertEqual(len(first["records"]), 10)
        for n in [True, 0, 11, 2.5]:
            with self.assertRaises(ValueError): module.proposal(data, n)

    def test_current_source_contract_and_counts(self):
        data, hashes = module.load_inputs(module.ROOT)
        result = module.proposal(data)
        self.assertEqual(len(hashes), 6)
        self.assertEqual(result["summary"]["unique_proposed_uploads"], 264)
        self.assertEqual(result["summary"]["classification_counts"]["explicit_bashar_association"], 10)
        self.assertEqual(result["summary"]["contexts_with_full_candidate_quota"], 12)
        self.assertEqual(result["summary"]["context_kinds"]["person_candidate"], 104)
        self.assertEqual(result["summary"]["indexed_publisher_groups"], 256)
        self.assertTrue(all(r["duration_seconds_inherited"] >= 300 for r in result["records"]))
        self.assertTrue(all(not r["downloaded"] and r["metadata_refresh_required"] for r in result["records"]))


if __name__ == "__main__":
    unittest.main()
