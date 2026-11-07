"""Source-pinned, offline ten-per-context planning; never downloads or grants admission.

People, joint practices, archives, institutions and publishing outlets remain
different units. Every selected upload still needs fresh platform metadata and
the existing collection ledger's duration/format/Bashar/storage checks.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
INPUTS = {
    "people": "research/expansion/acquisition/identity-map.json",
    "links": "research/expansion/acquisition/identity-publisher-links.json",
    "selection": "research/collection-policy/selection.jsonl",
    "analysis": "dist/analysis/data.json",
    "leads": "dist/new-round/inventory.json",
    "metrics": "dist/new-round/channel_metrics.json",
}
JOINT = {
    "Caroline (Calenara; surname unresolved)": ("joint-calenara", "Calenara — Caroline and Leo"),
    "Leo (Calenara; surname unresolved)": ("joint-calenara", "Calenara — Caroline and Leo"),
    "Pia Orleane": ("joint-laarkmaa", "Laarkmaa — Pia Orleane and Cullen Baird Smith"),
    "Cullen Baird Smith": ("joint-laarkmaa", "Laarkmaa — Pia Orleane and Cullen Baird Smith"),
}
# Explicit record crosswalk; similar names alone never merge identities.
LEAD_MATCHES = {
    "Christine Nowinski — Coming Out Cosmic": "Christine Nowinski",
    "Sarah Evans — Into the Blue Channeling": "Sarah Evans",
    "Melanie Beckler / Ask Angels": "Melanie Beckler",
}
SAFE_PUBLISHER_RELATIONSHIPS = {"official", "channeler"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def video_id(url):
    if not isinstance(url, str):
        return None
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in {"www.youtube.com", "youtube.com", "music.youtube.com"}:
        value = parse_qs(parsed.query).get("v", [None])[0]
        if value is None and parsed.path.startswith("/podcast/"):
            value = parsed.path.split("/")[2]
    elif host == "youtu.be":
        value = parsed.path.strip("/")
    else:
        return None
    return value if isinstance(value, str) and re.fullmatch(r"[\w-]{11}", value, re.ASCII) else None


def eligible(row):
    duration = row.get("duration_seconds")
    return (row.get("selected_default") is True
            and row.get("eligible_on_inherited_metadata") is True
            and row.get("duration_state") == "eligible_duration"
            and not isinstance(duration, bool) and isinstance(duration, (int, float))
            and math.isfinite(duration) and duration >= 300
            and not row.get("shorts_evidence")
            and not row.get("hold_or_exclusion_reasons")
            and video_id(row.get("source_url")) == row.get("video_id"))


def load_inputs(root):
    loaded, source_hashes = {}, []
    for key, relative in INPUTS.items():
        raw = (root / relative).read_bytes()
        loaded[key] = ([json.loads(line) for line in raw.decode().splitlines() if line]
                       if relative.endswith(".jsonl") else json.loads(raw))
        source_hashes.append({"path": relative, "bytes": len(raw), "sha256": digest(raw)})
    return loaded, source_hashes


def context_kind(name):
    if name.startswith("L/L Research"):
        return "institutional_lineage"
    if name in {"Alice A. Bailey", "George W. Van Tassel (archive)", "Jane Roberts (Seth archive)"}:
        return "historical_author_archive"
    if name == "Paul & Holly":
        return "joint_named_context"
    return "person_candidate"


def build_contexts(data):
    contexts = {}
    links = {r["practitioner_id"]: r for r in data["links"]["records"]}
    channels = {r["id"]: r for r in data["analysis"]["channels"]}
    for index, person in enumerate(data["people"]["records"]):
        name = person["name"]
        key, display = JOINT.get(name, (person["practitioner_id"], name))
        context = contexts.setdefault(key, {
            "context_id": key, "name": display,
            "context_kind": "joint_named_context" if name in JOINT else context_kind(name),
            "person_record_ids": [], "person_names": [], "claimed_entity_labels": [],
            "routes": [], "direct_video_ids": [], "publisher_groups": [], "source_refs": [],
            "identity_status": "inherited_candidate_not_current_identity_or_speaker_verification",
        })
        context["person_record_ids"].append(person["practitioner_id"])
        context["person_names"].append(name)
        context["claimed_entity_labels"].extend(person.get("entity_labels_inherited", []))
        context["direct_video_ids"].extend(filter(None, map(video_id, person.get("video_urls_inherited", []))))
        context["source_refs"].append({"file": INPUTS["people"], "pointer": f"/records/{index}"})
        matches = links.get(person["practitioner_id"], {}).get("publisher_matches", [])
        for url in person.get("account_urls_inherited", []):
            related = [m for m in matches if m["inherited_account_url"] == url]
            context["routes"].append({"url": url, "basis": "inherited_explicit_practitioner_route",
                                      "current_platform_identity_verified": False,
                                      "publisher_group_ids": sorted({m["publisher_group_id"] for m in related})})
        for match in matches:
            channel = channels.get(match["publisher_group_id"], {})
            context["publisher_groups"].append({
                "id": "atlas_analysis:" + match["publisher_group_id"],
                "name": channel.get("name"), "relationship": channel.get("relationship", "unknown"),
                "route": match["inherited_account_url"],
                "can_supply_context_candidates": channel.get("relationship") in SAFE_PUBLISHER_RELATIONSHIPS,
                "status": "inherited_publisher_relationship_not_verified_speech_attribution",
            })
    name_to_context = {name: c for c in contexts.values() for name in c["person_names"]}
    for index, lead in enumerate(data["leads"]["records"]):
        matched = LEAD_MATCHES.get(lead["name"])
        if matched:
            context = name_to_context[matched]
        else:
            key = "lead-" + digest(lead["name"].encode())[:12]
            context = contexts.setdefault(key, {
                "context_id": key, "name": lead["name"],
                "context_kind": "publishing_outlet" if lead["name"] == "GFL Station" else "person_candidate",
                "person_record_ids": [], "person_names": [] if lead["name"] == "GFL Station" else [lead["name"]],
                "claimed_entity_labels": [], "routes": [], "direct_video_ids": [], "publisher_groups": [],
                "source_refs": [], "identity_status": "new_discovery_lead_not_current_identity_or_speaker_verification",
            })
        context["claimed_entity_labels"].extend(lead.get("entity_claims", []))
        context["direct_video_ids"].extend(filter(None, (video_id(v.get("url")) for v in lead.get("example_videos", []))))
        if lead.get("channel_url"):
            context["routes"].append({"url": lead["channel_url"], "basis": "new_round_source_linked_lead",
                                      "current_platform_identity_verified": False, "publisher_group_ids": []})
        context["source_refs"].append({"file": INPUTS["leads"], "pointer": f"/records/{index}"})
    for context in contexts.values():
        for field in ["person_record_ids", "person_names", "claimed_entity_labels", "direct_video_ids"]:
            context[field] = sorted(set(context[field]))
        for field in ["routes", "publisher_groups"]:
            context[field] = list({json.dumps(row, sort_keys=True): row for row in context[field]}.values())
        own = [r["route"] for r in context["publisher_groups"] if r["can_supply_context_candidates"]]
        # This is a preferred inherited route, not a claim that a handle was resolved live.
        routes = own or [r["url"] for r in context["routes"]]
        context["preferred_inherited_route"] = sorted(set(routes), key=lambda u: ("/channel/UC" not in u, u.lower()))[0] if routes else None
        context["preferred_route_scope"] = ("inherited_official_or_channeler_route_not_currently_verified" if own else
            "contextual_or_new_lead_route_requires_video_specific_attribution" if routes else "no_inherited_route")
    return sorted(contexts.values(), key=lambda c: (c["name"].casefold(), c["context_id"]))


def proposal(data, per_context=10):
    if isinstance(per_context, bool) or not isinstance(per_context, int) or not 1 <= per_context <= 10:
        raise ValueError("Pilot quota must be an integer from 1 through 10.")
    contexts = build_contexts(data)
    selected = {r["video_id"]: r for r in data["selection"] if eligible(r)}
    all_ids = {r["video_id"] for r in data["selection"]}
    shared, discoveries = {}, {}
    for context in contexts:
        direct = set(context["direct_video_ids"])
        official = {r["id"] for r in context["publisher_groups"] if r["can_supply_context_candidates"]}
        candidates = []
        for vid, row in selected.items():
            direct_match = vid in direct
            publisher_match = bool(official.intersection(row.get("publisher_account_ids", [])))
            if not (direct_match or publisher_match):
                continue
            dates = sorted(o["date"] for o in row.get("historical_upload_date_observations", []) if o.get("date"))
            evidence = [s for s, yes in [("explicit_inherited_person_video_link", direct_match),
                                         ("inherited_official_or_channeler_publisher_route", publisher_match)] if yes]
            candidates.append({"video_id": vid, "association_basis": evidence,
                               "inherited_upload_date": dates[-1] if dates else None,
                               "priority": 0 if direct_match and publisher_match else 1 if direct_match else 2})
        # Deterministic, nonrandom: evidence tier, then recorded publication date
        # descending, then ID. Missing dates rank last within their tier.
        candidates.sort(key=lambda v: v["video_id"])
        candidates.sort(key=lambda v: v["inherited_upload_date"] or "", reverse=True)
        candidates.sort(key=lambda v: v["priority"])
        chosen = candidates[:per_context] if context["context_kind"] != "publishing_outlet" else []
        context.update(eligible_known_candidates=len(candidates), proposed_video_count=len(chosen),
                       pilot_target=per_context if context["context_kind"] != "publishing_outlet" else 0,
                       still_needed=max(0, per_context-len(chosen)) if context["context_kind"] != "publishing_outlet" else None,
                       proposed_video_ids=[v["video_id"] for v in chosen],
                       selection_status="proposed_pending_access_fresh_metadata_and_cap_ledger" if chosen else "discovery_needed",
                       candidates=candidates)
        for chosen_row in chosen:
            vid = chosen_row["video_id"]; row = selected[vid]
            record = shared.setdefault(vid, {
                "source_id": "youtube:"+vid, "video_id": vid,
                "url": "https://www.youtube.com/watch?v="+vid, "source_url": "https://www.youtube.com/watch?v="+vid,
                "title_inherited": row.get("title"), "duration_seconds_inherited": row["duration_seconds"],
                "classification_inherited": row["classification"],
                "publisher_account_ids": row.get("publisher_account_ids", []),
                "publisher_labels": row.get("publisher_labels", []),
                "channel_route_ids": row.get("channel_route_ids", []),
                "context_associations": [], "source_refs": row.get("source_refs", []),
                "stage": "metadata_only_proposal", "metadata_refresh_required": True,
                "actual_speaker_status": "unknown_not_audio_verified", "downloaded": False,
            })
            record["context_associations"].append({"context_id": context["context_id"], "name": context["name"],
                                                    "context_kind": context["context_kind"],
                                                    "association_basis": chosen_row["association_basis"]})
        for vid in sorted(direct-all_ids):
            record = discoveries.setdefault(vid, {"source_id": "youtube:"+vid, "video_id": vid,
                "url": "https://www.youtube.com/watch?v="+vid, "context_ids": [],
                "stage": "unmeasured_discovery_only", "duration_seconds": None, "platform_format": None})
            record["context_ids"].append(context["context_id"])
    records = sorted(shared.values(), key=lambda r: r["source_id"])
    # The proposal does not allocate a slot; the existing ledger owns all cap admission.
    if sum(r["classification_inherited"] == "explicit_bashar_association" for r in records) > 100:
        raise ValueError("Proposed uploads exceed the global inherited Bashar ceiling.")
    return {"schema_version": 1, "kind": "ten_per_context_metadata_proposal", "records": records,
            "contexts": contexts, "discovery_only": sorted(discoveries.values(), key=lambda r:r["source_id"]),
            "summary": {"raw_practitioner_records": len(data["people"]["records"]),
                "new_round_lead_records": len(data["leads"]["records"]), "contexts_after_explicit_crosswalk": len(contexts),
                "context_kinds": dict(sorted(Counter(c["context_kind"] for c in contexts).items())),
                "contexts_with_full_candidate_quota": sum(c["proposed_video_count"] == per_context for c in contexts),
                "contexts_with_partial_candidate_quota": sum(0 < c["proposed_video_count"] < per_context for c in contexts),
                "contexts_without_known_eligible_selection": sum(c["proposed_video_count"] == 0 for c in contexts),
                "proposed_context_video_associations": sum(c["proposed_video_count"] for c in contexts),
                "unique_proposed_uploads": len(records), "classification_counts": dict(Counter(r["classification_inherited"] for r in records)),
                "unmeasured_discovery_video_ids": len(discoveries), "indexed_publisher_groups": len(data["metrics"].get("channels", [])),
                "downloads_by_this_planner": 0, "network_calls_by_this_planner": 0, "cap_slots_consumed": 0},
            "method": {"quota": per_context, "minimum_duration_seconds": 300,
                "sort": "evidence tier; inherited publication date descending; video ID",
                "global_bashar_limit": 100, "cap_owner": "existing reconciled collection-runner SQLite ledger",
                "deduplication": "exact YouTube upload ID; shared contexts retained; original-session duplicates unresolved",
                "rules": ["Fresh metadata and original collector checks remain mandatory before media admission.",
                    "Account association is not verified speaker identity. Mixed interview outlets do not supply extra candidate videos solely by account.",
                    "Calenara and Laarkmaa each form one joint study context; per-person ten-video completion is not asserted.",
                    "Historical authors, institutional lineages, human candidates and the GFL publishing outlet remain separate.",
                    "A short quota means missing known eligible candidates, not a small or inactive live channel.",
                    "Dates are inherited publication observations, not original performance dates or current latest-upload evidence."]}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--per-context", type=int, default=10)
    args = parser.parse_args()
    data, sources = load_inputs(args.root)
    result = proposal(data, args.per_context)
    result["input_manifest"] = sources
    result["planner_sha256"] = digest(Path(__file__).read_bytes())
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/"proposed-batch.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
    (args.output/"summary.json").write_text(json.dumps(result["summary"], indent=2)+"\n")
    fields = ["context_id", "name", "context_kind", "preferred_inherited_route", "preferred_route_scope", "eligible_known_candidates", "proposed_video_count", "pilot_target", "still_needed", "selection_status"]
    with (args.output/"context-quotas.csv").open("w", newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction="ignore");writer.writeheader();writer.writerows(result["contexts"])
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
