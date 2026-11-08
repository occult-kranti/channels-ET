#!/usr/bin/env python3
"""Independent synthetic publication fixtures; no real collection is performed.

Run: python research/youtube-archive/test_publication.py
The fixtures deliberately contain marker text and fake counts. They never read
retained transcripts, contact a network service or count as acquired media.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "archive_publication_under_test", Path(__file__).with_name("build_public.py"))
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def ref(name, raw):
    return {"file": name, "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


class PublicationMutationTests(unittest.TestCase):
    def test_private_copy_receipt_cannot_enter_public_site(self):
        with self.assertRaisesRegex(ValueError, 'Private copy receipt'):
            BUILDER.build(self.site, [self.producer], self.public / 'copy-receipt.json')
        self.assertFalse((self.public / 'copy-receipt.json').exists())

    def setUp(self):
        # RAM avoids durable test artifacts and has enough space for the reserve
        # check. It does not bypass or mock that production check.
        self.temp = tempfile.TemporaryDirectory(prefix="archive-publication-fixture-",
                                                dir="/dev/shm")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.site = self.base / "synthetic-site"
        self.public = self.site / "dist/youtube-archive"
        self.public.mkdir(parents=True)
        for name, content in (("index.html", "<!doctype html><title>Synthetic fixture</title>"),
                              ("app.js", "/* Synthetic fixture: no collection. */"),
                              ("styles.css", "/* Synthetic fixture. */")):
            (self.public / name).write_text(content)
        self.producer = self.base / "synthetic-producer"
        self.producer.mkdir()
        self.data = {
            "inventory.json": {"fixture_kind": "synthetic_publication_fixture", "accounts": []},
            "collector-status.json": {"fixture_kind": "synthetic_publication_fixture",
                                      "new_media_downloads": 0},
            "publisher-discovery.json": {"fixture_kind": "synthetic_publication_fixture",
                                         "observations": []},
            "reconciliation.json": {
                "fixture_kind": "synthetic_publication_fixture",
                "canonical_frame": {"documents": 2, "words": 12},
                "publisher_contexts": [
                    {"selected_text_units": 1, "selected_words": 5},
                    {"selected_text_units": 1, "selected_words": 7}],
            },
        }
        self.raws = {name: encoded(value) for name, value in self.data.items()}
        self.write_producer()

    def write_producer(self, custom_listing=None):
        for name, raw in self.raws.items():
            (self.producer / name).write_bytes(raw)
        listing = custom_listing if custom_listing is not None else [
            ref(name, raw) for name, raw in self.raws.items()]
        (self.producer / "output-manifest.json").write_bytes(
            encoded({"public_allowlist": listing}))

    def build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            BUILDER.build(self.site, [self.producer], self.base / "private-receipt.json")

    def manifest(self):
        return json.loads((self.public / "manifest.json").read_bytes())

    def write_manifest(self, data):
        (self.public / "manifest.json").write_bytes(encoded(data))

    def reject_build(self):
        with self.assertRaises((ValueError, FileNotFoundError)):
            self.build()

    def reject_verify(self):
        with self.assertRaises((ValueError, FileNotFoundError)):
            BUILDER.verify(self.site)

    def test_valid_synthetic_fixture_roundtrip(self):
        self.build()
        outcome = BUILDER.verify(self.site)
        self.assertEqual(outcome["status"], "passed_metadata_release_checks")
        self.assertEqual(set(outcome["modules"]), BUILDER.REQUIRED)
        manifest = self.manifest()
        self.assertEqual(manifest["builder_sha256"], hashlib.sha256(
            Path(BUILDER.__file__).read_bytes()).hexdigest())
        receipt = json.loads((self.base / "private-receipt.json").read_bytes())
        self.assertEqual(receipt["manifest_sha256"], hashlib.sha256(
            (self.public / "manifest.json").read_bytes()).hexdigest())
        for name, raw in self.raws.items():
            self.assertEqual((self.public / name).read_bytes(), raw)

    def test_unallowlisted_producer_file_is_not_copied(self):
        (self.producer / "unlisted-private.json").write_bytes(
            encoded({"transcript_text": "SYNTHETIC DO NOT PUBLISH"}))
        self.build()
        self.assertFalse((self.public / "unlisted-private.json").exists())

    def test_unsafe_producer_paths(self):
        for name in ("../outside.json", "/absolute.json", "nested/../../escape.json",
                     "C:\\private.json", "https:payload.json", ""):
            with self.subTest(name=name):
                self.write_producer([ref(name, b"{}")])
                self.reject_build()

    def test_producer_symlink_escape(self):
        outside = self.base / "outside.json"
        outside.write_bytes(b"{}")
        (self.producer / "escape.json").symlink_to(outside)
        self.write_producer([ref("escape.json", b"{}")])
        self.reject_build()

    def test_public_target_symlink_escape(self):
        outside = self.base / "outside.json"
        outside.write_bytes(b"{}")
        (self.public / "inventory.json").symlink_to(outside)
        self.reject_build()
        self.assertEqual(outside.read_bytes(), b"{}")

    def test_empty_and_duplicate_producer_allowlists(self):
        first = ref("inventory.json", self.raws["inventory.json"])
        for listing in ([], [first, first]):
            with self.subTest(entries=len(listing)):
                self.write_producer(listing)
                self.reject_build()

    def test_missing_allowlisted_source(self):
        (self.producer / "inventory.json").unlink()
        self.reject_build()

    def test_producer_hash_and_size_mismatch(self):
        for field, value in (("sha256", "0" * 64), ("bytes", 999999)):
            with self.subTest(field=field):
                listing = [ref(name, raw) for name, raw in self.raws.items()]
                listing[0][field] = value
                self.write_producer(listing)
                self.reject_build()

    def test_nonmetadata_artifact_rejected(self):
        (self.producer / "audio.mp3").write_bytes(b"not real media")
        self.write_producer([ref("audio.mp3", b"not real media")])
        self.reject_build()

    def test_nested_raw_text_and_credential_fields_rejected(self):
        for key in sorted(BUILDER.FORBIDDEN):
            with self.subTest(key=key):
                self.raws["inventory.json"] = encoded({"nested": [{key: "SYNTHETIC MARKER"}]})
                self.write_producer()
                self.reject_build()

    def test_plain_private_paths_rejected(self):
        for value in ("/workspace/private-marker", "/dev/shm/private-marker",
                      "channels-et-private/marker"):
            with self.subTest(value=value):
                self.raws["inventory.json"] = encoded({"note": value})
                self.write_producer()
                self.reject_build()

    def test_json_escaped_private_paths_rejected(self):
        for raw in (b'{"note":"\\/workspace\\/private-marker"}',
                    b'{"note":"\\u002fdev\\u002fshm\\u002fprivate-marker"}',
                    b'{"note":"channels-et-\\u0070rivate/marker"}'):
            with self.subTest(raw=raw):
                self.raws["inventory.json"] = raw
                self.write_producer()
                self.reject_build()

    def test_nonfinite_json_values_rejected(self):
        for value in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=str(value)):
                self.raws["inventory.json"] = encoded({"metric": value})
                self.write_producer()
                self.reject_build()

    def test_duplicate_json_object_keys_rejected(self):
        self.raws["inventory.json"] = (
            b'{"nested":{"transcript_text":"SYNTHETIC MARKER"},"nested":{}}')
        self.write_producer()
        self.reject_build()

    def test_missing_required_module(self):
        del self.raws["publisher-discovery.json"]
        self.write_producer()
        self.reject_build()

    def test_reconciliation_count_mismatch(self):
        for field in ("documents", "words"):
            with self.subTest(field=field):
                changed = json.loads(encoded(self.data["reconciliation.json"]))
                changed["canonical_frame"][field] += 1
                self.raws["reconciliation.json"] = encoded(changed)
                self.write_producer()
                self.reject_build()

    def test_stale_public_file_rejected(self):
        self.build()
        (self.public / "stale.json").write_bytes(b"{}")
        self.reject_verify()

    def test_changed_or_missing_public_artifact_rejected(self):
        self.build()
        target = self.public / "inventory.json"
        target.write_bytes(target.read_bytes() + b" ")
        self.reject_verify()
        target.unlink()
        self.reject_verify()

    def test_duplicate_manifest_artifacts_rejected(self):
        self.build()
        manifest = self.manifest()
        manifest["artifacts"].append(manifest["artifacts"][0])
        self.write_manifest(manifest)
        self.reject_verify()

    def test_module_hash_binding_rejected(self):
        self.build()
        manifest = self.manifest()
        manifest["modules"]["inventory"]["sha256"] = "0" * 64
        self.write_manifest(manifest)
        self.reject_verify()

    def test_invalid_module_mapping_rejected(self):
        self.build()
        manifest = self.manifest()
        manifest["modules"]["inventory"]["file"] = "reconciliation.json"
        self.write_manifest(manifest)
        self.reject_verify()

    def test_manifest_private_content_rejected(self):
        self.build()
        for key, value in (("transcript_text", "SYNTHETIC MARKER"),
                           ("note", "/workspace/private-marker")):
            with self.subTest(key=key):
                manifest = self.manifest()
                manifest[key] = value
                self.write_manifest(manifest)
                self.reject_verify()
                del manifest[key]
                self.write_manifest(manifest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
