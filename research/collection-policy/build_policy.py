#!/usr/bin/env python3
"""Offline selection and accounting; never downloads or changes source inventories."""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
INVENTORY = HERE.parent / "harvest" / "inventory"
BASHAR_RE = re.compile(r"\bbashar\b|\bdarr?yl\s*anka\b", re.I)
BASHAR_ROUTE_RE = re.compile(r"bashar|darr?yl.?anka", re.I)
SHORTS_RE = re.compile(r"https?://(?:(?:www|m)\.)?youtube\.com/shorts/([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])", re.I)
TITLE_SHORTS_RE = re.compile(r"(?:^|\s)#shorts?(?:\s|$)|\[shorts?\]|\(shorts?\)", re.I)
ID_RE = re.compile(r"[A-Za-z0-9_-]{11}\Z")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strings(values):
    return [v for v in values or [] if isinstance(v, str)]


def dump_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def dump_jsonl(path, values):
    path.write_text("".join(json.dumps(v, ensure_ascii=False, sort_keys=True) + "\n" for v in values), encoding="utf-8")


def dump_csv(path, rows, columns):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(row.get(k), ensure_ascii=False, sort_keys=True) if isinstance(row.get(k), (list, dict)) else row.get(k) for k in columns})


def walk_strings(value, pointer=""):
    if isinstance(value, str):
        yield pointer or "/", value
    elif isinstance(value, dict):
        for key, child in value.items():
            token = str(key).replace("~", "~0").replace("/", "~1")
            yield from walk_strings(child, pointer + "/" + token)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_strings(child, pointer + "/" + str(index))


def walk_objects(value, pointer=""):
    if isinstance(value, dict):
        yield pointer or "/", value
        for key, child in value.items():
            token = str(key).replace("~", "~0").replace("/", "~1")
            yield from walk_objects(child, pointer + "/" + token)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_objects(child, pointer + "/" + str(index))


def explicit_short_objects(parsed):
    """Only explicit fields tied to a literal ID; never infer format from length."""
    for pointer, value in walk_objects(parsed):
        flags = [key for key in ["is_short", "isShort"] if value.get(key) is True]
        flags += [key for key in ["media_type", "format_type"] if str(value.get(key, "")).casefold() in {"short", "shorts"}]
        ids = {value[key] for key in ["id", "video_id", "videoId"] if isinstance(value.get(key), str) and ID_RE.fullmatch(value[key])}
        if flags:
            for vid in sorted(ids):
                yield vid, pointer, flags


def duration_details(video, minimum):
    values = []
    observations = []
    invalid = False
    for field, value, ref in [
        ("duration_seconds", video.get("duration_seconds"), video.get("duration_source_ref")),
        *[("duration_conflict_values", v, None) for v in video.get("duration_conflict_values", [])],
        *[(o.get("duration_field") or "duration_seconds", o.get("duration_seconds"), o.get("source_ref")) for o in video.get("metadata_observations", [])],
    ]:
        if isinstance(value, bool) or isinstance(value, (int, float)) and not math.isfinite(value):
            invalid = True
            observations.append({"field": field, "seconds": None, "invalid_value": repr(value), "source_ref": ref})
        elif isinstance(value, (int, float)) and value > 0:
            values.append(float(value))
            observations.append({"field": field, "seconds": float(value), "source_ref": ref})
    unique = sorted(set(values))
    state = "invalid" if invalid else "unknown" if not unique else "conflicting" if len(unique) > 1 else "under_minimum" if unique[0] < minimum else "eligible_duration"
    return state, unique, observations


def alias_components(routes):
    parents = {r["route_id"]: r["route_id"] for r in routes}

    def find(key):
        while parents[key] != key:
            parents[key] = parents[parents[key]]
            key = parents[key]
        return key

    for route in routes:
        for alias in route.get("explicit_aliases", []):
            if alias in parents:
                a, b = find(route["route_id"]), find(alias)
                parents[max(a, b)] = min(a, b)
    return {key: find(key) for key in sorted(parents)}


def classify(video, route_map, darryl_ids):
    evidence = []
    for label in strings(video.get("entity_labels")):
        if label.casefold() == "bashar":
            evidence.append({"kind": "explicit_entity_label", "value": label, "source_refs": video["source_refs"]})
    for person_id in video.get("person_ids", []):
        if person_id in darryl_ids:
            evidence.append({"kind": "practitioner_record_named_darryl_anka", "value": person_id, "source_refs": video["source_refs"]})
    for field in ["title", "publisher_labels"]:
        values = [video.get(field)] if field == "title" else strings(video.get(field))
        for value in values:
            if isinstance(value, str) and BASHAR_RE.search(value):
                evidence.append({"kind": "explicit_" + field, "value": value, "source_refs": video["source_refs"]})
    for observation in video.get("metadata_observations", []):
        for field in ["practitioner_labels", "publisher_labels", "entity_labels"]:
            for value in strings(observation.get(field)):
                if BASHAR_RE.search(value):
                    evidence.append({"kind": "observation_" + field, "value": value, "source_refs": [observation["source_ref"]]})
    for rid in video.get("channel_route_ids", []):
        route = route_map[rid]
        if BASHAR_ROUTE_RE.search(route["url"]):
            evidence.append({"kind": "explicit_branded_route_association", "value": route["url"], "source_refs": route["source_refs"]})
    if evidence:
        return "explicit_bashar_association", evidence
    contextual = [ref for ref in video["source_refs"] if ref["source_id"].startswith("bashar-index:")]
    if contextual:
        return "ambiguous_bashar_context", [{"kind": "contextual_link_only_not_speaker_evidence", "source_refs": contextual}]
    return "not_bashar_labeled_in_available_metadata", []


def sample_group(video, components):
    accounts = sorted(video.get("publisher_account_ids", []))
    routes = sorted({components[r] for r in video.get("channel_route_ids", [])})
    if accounts:
        return "inherited_publisher_group", accounts[0]
    if routes:
        return "inherited_route_alias_component", routes[0]
    return "unresolved_upload_id", video["video_id"]


def round_robin(rows):
    groups = collections.defaultdict(list)
    for row in sorted(rows, key=lambda r: r["video_id"]):
        groups[(row["sampling_group_kind"], row["sampling_group_id"])].append(row)
    selected = []
    index = 0
    while True:
        level = [groups[key][index] for key in sorted(groups) if len(groups[key]) > index]
        if not level:
            break
        selected.extend(level)
        index += 1
    return selected


def build(out=HERE, inventory=INVENTORY):
    policy = read_json(HERE / "policy.json")
    reservation = read_json(HERE / "retained-bashar-reservation.json")
    if len(reservation["records"]) != policy["already_retained_bashar_podcast_audio_reservation"]:
        raise ValueError("Retained-material budget reservation differs from policy")
    videos = [json.loads(line) for line in (inventory / "videos.jsonl").read_text().splitlines() if line]
    routes = read_json(inventory / "channel-routes.json")["records"]
    persons = read_json(inventory / "practitioner-candidates.json")["records"]
    publishers = read_json(inventory / "publisher-accounts.json")["records"]
    manifest = read_json(inventory / "source-manifest.json")
    route_map = {r["route_id"]: r for r in routes}
    components = alias_components(routes)
    darryl_ids = {p["id"] for p in persons if re.fullmatch(r"Darr?yl Anka", p["name"], re.I)}
    pins = []
    shorts = collections.defaultdict(list)
    upload_dates = collections.defaultdict(list)
    for pin in manifest["files"]:
        source = inventory / pin["snapshot_path"]
        actual_sha = sha(source)
        if actual_sha != pin["sha256"]:
            raise ValueError("Source snapshot hash mismatch: " + pin["source_id"])
        pins.append({"source_id": pin["source_id"], "path": "../harvest/inventory/" + pin["snapshot_path"], "sha256": actual_sha, "bytes": source.stat().st_size})
        raw = source.read_text(encoding="utf-8")
        try:
            parsed = json.loads(raw)
            values = walk_strings(parsed)
        except (json.JSONDecodeError, UnicodeDecodeError):
            parsed = None
            values = (("/line/" + str(i), value) for i, value in enumerate(raw.splitlines(), 1))
        for pointer, value in values:
            for match in SHORTS_RE.finditer(value):
                shorts[match[1]].append({"kind": "inherited_shorts_url", "url": match[0], "source_id": pin["source_id"], "locator": pointer, "sha256": actual_sha, "live_platform_verified": False})
        for vid, pointer, flags in explicit_short_objects(parsed):
            shorts[vid].append({"kind": "inherited_explicit_short_format_flag", "fields": flags, "source_id": pin["source_id"], "locator": pointer, "sha256": actual_sha, "live_platform_verified": False})
        if pin["source_id"] == "channels-ET:dist/analysis/data.json":
            for index, video in enumerate(parsed.get("videos", [])):
                if video.get("date") or video.get("publishedTimestamp"):
                    upload_dates[video["id"]].append({"date": video.get("date"), "published_timestamp": video.get("publishedTimestamp"), "date_source": video.get("dateSource"), "interpretation": "historical_upload_metadata" if video.get("dateSource") == "fresh_watch_metadata_UTC" else "inherited_date_semantics_unverified", "source_id": pin["source_id"], "locator": "/videos/" + str(index), "sha256": actual_sha})
    rows = []
    for video in sorted(videos, key=lambda v: v["video_id"]):
        classification, evidence = classify(video, route_map, darryl_ids)
        state, durations, observations = duration_details(video, policy["minimum_duration_seconds"])
        short_evidence = list(shorts.get(video["video_id"], []))
        for title in [video.get("title"), *[o.get("title") for o in video.get("metadata_observations", [])]]:
            if isinstance(title, str) and TITLE_SHORTS_RE.search(title):
                marker = {"kind": "title_marker_heuristic", "title": title, "live_platform_verified": False}
                if marker not in short_evidence:
                    short_evidence.append(marker)
        reasons = []
        if classification == "ambiguous_bashar_context":
            reasons.append("ambiguous_bashar_context_requires_verification")
        if state != "eligible_duration":
            reasons.append({"unknown": "duration_unknown_requires_metadata", "conflicting": "duration_conflicting_requires_metadata", "invalid": "duration_invalid_requires_metadata", "under_minimum": "duration_below_300_seconds"}[state])
        if short_evidence:
            reasons.append("shorts_historical_url_or_title_marker")
        eligible = not reasons
        kind, group = sample_group(video, components)
        rows.append({
            "schema_version": 1, "source_id": video["source_id"], "video_id": video["video_id"], "source_url": video["source_url"], "title": video.get("title"),
            "classification": classification, "classification_evidence": evidence, "actual_speaker_status": "unknown_not_audio_verified", "source_refs": video["source_refs"],
            "publisher_account_ids": video.get("publisher_account_ids", []), "publisher_labels": video.get("publisher_labels", []), "channel_route_ids": video.get("channel_route_ids", []),
            "duration_state": state, "duration_seconds": durations[0] if len(durations) == 1 else None, "duration_values_seconds": durations, "duration_observations": observations,
            "shorts_evidence": short_evidence, "live_platform_format_verified": False,
            "historical_upload_date_observations": upload_dates.get(video["video_id"], []), "original_session_date": None, "original_session_identity": None, "repost_status": "unresolved_distinct_uploads_may_repeat_original_sessions",
            "eligible_on_inherited_metadata": eligible, "metadata_refresh_required": True, "hold_or_exclusion_reasons": reasons,
            "sampling_group_kind": kind, "sampling_group_id": group, "bashar_eligible_rank": None,
            "selected_default": False, "selected_conservative_all_materials": False, "default_decision": "held_or_excluded", "conservative_decision": "held_or_excluded", "acquisition_status": "not_downloaded_by_this_layer",
        })
    bashar_candidates = [r for r in rows if r["eligible_on_inherited_metadata"] and r["classification"] == "explicit_bashar_association"]
    for rank, row in enumerate(round_robin(bashar_candidates), 1):
        row["bashar_eligible_rank"] = rank
    for row in rows:
        if not row["eligible_on_inherited_metadata"]:
            continue
        is_bashar = row["classification"] == "explicit_bashar_association"
        for suffix, limit in [("default", policy["default_new_bashar_youtube_limit"]), ("conservative_all_materials", policy["conservative_new_bashar_youtube_limit"])]:
            row["selected_" + suffix] = not is_bashar or row["bashar_eligible_rank"] <= limit
        row["default_decision"] = "selected_pending_access_and_metadata_refresh" if row["selected_default"] else "held_bashar_global_cap"
        row["conservative_decision"] = "selected_pending_access_and_metadata_refresh" if row["selected_conservative_all_materials"] else "held_bashar_global_cap"
    by_id = {r["video_id"]: r for r in rows}
    route_rows = []
    for route in sorted(routes, key=lambda r: r["route_id"]):
        associated = [by_id[i] for i in sorted(set(route["known_video_ids"]))]
        b = [r for r in associated if r["classification"] == "explicit_bashar_association"]
        branded = bool(BASHAR_ROUTE_RE.search(route["url"]))
        route_rows.append({
            "route_id": route["route_id"], "url": route["url"], "route_type": route["route_type"], "enumeration_status": "not_live_enumerated", "identity_status": route["identity_status"],
            "inherited_alias_component": components[route["route_id"]], "explicit_alias_route_ids": route.get("explicit_aliases", []),
            "bashar_relevant": bool(b) or branded, "bashar_branded_url_evidence": branded, "source_refs": route["source_refs"],
            "indexed_video_count": len(associated), "indexed_eligible_count": sum(r["eligible_on_inherited_metadata"] for r in associated),
            "indexed_bashar_count": len(b), "indexed_bashar_eligible_count": sum(r["eligible_on_inherited_metadata"] for r in b),
            "indexed_bashar_under_minimum_count": sum(r["duration_state"] == "under_minimum" for r in b),
            "indexed_bashar_unknown_duration_count": sum(r["duration_state"] == "unknown" for r in b),
            "indexed_bashar_conflicting_duration_count": sum(r["duration_state"] == "conflicting" for r in b),
            "indexed_bashar_shorts_evidence_count": sum(bool(r["shorts_evidence"]) for r in b),
            "indexed_bashar_multi_route_count": sum(len(r["channel_route_ids"]) > 1 for r in b),
            "selected_default_count": sum(r["selected_default"] for r in associated), "selected_default_bashar_count": sum(r["selected_default"] for r in b),
            "selected_conservative_bashar_count": sum(r["selected_conservative_all_materials"] for r in b),
            "known_video_ids": [r["video_id"] for r in associated], "known_bashar_video_ids": [r["video_id"] for r in b],
            "whole_channel_lifetime_video_count": None, "whole_channel_eligible_video_count": None,
            "count_scope": "inherited_index_associations_only_not_live_channel_upload_total",
        })
    explicit = [r for r in rows if r["classification"] == "explicit_bashar_association"]
    ambiguous = [r for r in rows if r["classification"] == "ambiguous_bashar_context"]
    other = [r for r in rows if r["classification"] == "not_bashar_labeled_in_available_metadata"]

    def counts(group):
        return {"indexed": len(group), "eligible": sum(r["eligible_on_inherited_metadata"] for r in group), "under_minimum": sum(r["duration_state"] == "under_minimum" for r in group), "unknown_duration": sum(r["duration_state"] == "unknown" for r in group), "conflicting_duration": sum(r["duration_state"] == "conflicting" for r in group), "shorts_historical_evidence": sum(bool(r["shorts_evidence"]) for r in group)}

    relevant = [r for r in route_rows if r["bashar_relevant"]]
    publisher_rows = []
    publisher_map = {p["publisher_account_id"]: p for p in publishers}
    for publisher_id in sorted({pid for row in explicit for pid in row["publisher_account_ids"]}):
        publisher = publisher_map[publisher_id]
        items = [r for r in explicit if publisher_id in r["publisher_account_ids"]]
        publisher_rows.append({"publisher_account_id": publisher_id, "name": publisher["name"], "identity_status": publisher["identity_status"], "channel_route_ids": publisher["channel_route_ids"], "source_ref": publisher["source_ref"], "indexed_bashar_count": len(items), "indexed_bashar_eligible_count": sum(r["eligible_on_inherited_metadata"] for r in items), "indexed_bashar_under_minimum_count": sum(r["duration_state"] == "under_minimum" for r in items), "indexed_bashar_unknown_duration_count": sum(r["duration_state"] == "unknown" for r in items), "indexed_bashar_conflicting_duration_count": sum(r["duration_state"] == "conflicting" for r in items), "selected_default_bashar_count": sum(r["selected_default"] for r in items), "selected_conservative_bashar_count": sum(r["selected_conservative_all_materials"] for r in items), "known_bashar_video_ids": [r["video_id"] for r in items], "whole_publisher_lifetime_upload_count": None})
    summary = {
        "schema_version": 1, "policy_id": policy["policy_id"], "release_state": policy["release_state"], "scope": "offline_inherited_metadata_selection_no_downloads",
        "inventory_capture_time": manifest["captured_at"], "requested_approximate_video_target": 1000, "all_upload_ids": counts(rows), "explicit_bashar_association": counts(explicit), "ambiguous_bashar_context": counts(ambiguous), "other_not_bashar_labeled": counts(other),
        "explicit_or_ambiguous_bashar_context_ids": len(explicit) + len(ambiguous), "literal_routes_total": len(routes), "playlists_total": sum(1 for line in (inventory / "playlists.jsonl").read_text().splitlines() if line),
        "bashar_relevant_literal_routes": len(relevant), "routes_with_explicit_bashar_indexed_videos": sum(bool(r["indexed_bashar_count"]) for r in relevant), "bashar_branded_routes_with_zero_indexed_videos": sum(r["bashar_branded_url_evidence"] and not r["indexed_video_count"] for r in relevant),
        "bashar_inherited_publisher_groups": len(publisher_rows), "bashar_ids_without_publisher_group": sum(not r["publisher_account_ids"] for r in explicit),
        "bashar_video_route_edges": sum(len(r["channel_route_ids"]) for r in explicit), "bashar_ids_with_any_route": sum(bool(r["channel_route_ids"]) for r in explicit), "bashar_ids_without_route": sum(not r["channel_route_ids"] for r in explicit),
        "bashar_multi_route_upload_ids": sum(len(r["channel_route_ids"]) > 1 for r in explicit), "bashar_extra_route_edges_beyond_unique_routed_ids": sum(len(r["channel_route_ids"]) for r in explicit) - sum(bool(r["channel_route_ids"]) for r in explicit),
        "default": {"new_bashar_youtube_limit": policy["default_new_bashar_youtube_limit"], "new_bashar_selected": sum(r["selected_default"] for r in explicit), "other_selected": sum(r["selected_default"] for r in other), "total_new_youtube_ids_selected": sum(r["selected_default"] for r in rows), "eligible_bashar_held_by_cap": sum(r["eligible_on_inherited_metadata"] and not r["selected_default"] for r in explicit), "independent_retained_podcasts_separate_source_type": 19, "podcasts_consume_youtube_cap": False},
        "conservative_all_materials_alternative": {"new_bashar_youtube_limit": policy["conservative_new_bashar_youtube_limit"], "reserved_existing_bashar_podcast_materials": 19, "new_bashar_selected": sum(r["selected_conservative_all_materials"] for r in explicit), "other_selected": sum(r["selected_conservative_all_materials"] for r in other), "total_new_youtube_ids_selected": sum(r["selected_conservative_all_materials"] for r in rows), "eligible_bashar_held_by_cap": sum(r["eligible_on_inherited_metadata"] and not r["selected_conservative_all_materials"] for r in explicit), "includes_existing_podcast_reservation": True},
        "whole_channel_lifetime_bashar_upload_count": None, "whole_channel_lifetime_all_practitioner_upload_count": None, "lifetime_count_status": "unknown_live_enumeration_blocked_in_parent_acquisition_environment_not_estimated_here",
        "original_session_deduplication": "unresolved_upload_IDs_only", "original_session_dates": "unknown_not_inferred_from_upload_dates_or_titles", "shorts_count_overlap_warning": "Historical Shorts evidence overlaps duration categories; do not add these counts.",
        "downloads_performed_by_this_layer": 0,
    }
    inputs = {"schema_version": 1, "base": "../harvest/inventory", "policy_files": [{"path": name, "sha256": sha(HERE / name), "bytes": (HERE / name).stat().st_size} for name in ["policy.json", "retained-bashar-reservation.json"]], "files": [{"path": "../harvest/inventory/" + name, "sha256": sha(inventory / name), "bytes": (inventory / name).stat().st_size} for name in ["videos.jsonl", "channel-routes.json", "practitioner-candidates.json", "publisher-accounts.json", "playlists.jsonl", "source-manifest.json"]], "sourcepins": pins}
    out.mkdir(parents=True, exist_ok=True)
    dump_jsonl(out / "selection.jsonl", rows)
    dump_jsonl(out / "selected-default.jsonl", [r for r in rows if r["selected_default"]])
    dump_jsonl(out / "selected-conservative-all-materials.jsonl", [r for r in rows if r["selected_conservative_all_materials"]])
    dump_csv(out / "selection.csv", rows, ["video_id", "source_url", "title", "classification", "duration_state", "duration_seconds", "duration_values_seconds", "shorts_evidence", "channel_route_ids", "publisher_account_ids", "eligible_on_inherited_metadata", "bashar_eligible_rank", "sampling_group_kind", "sampling_group_id", "selected_default", "selected_conservative_all_materials", "default_decision", "hold_or_exclusion_reasons"])
    dump_json(out / "route-inventory.json", {"schema_version": 1, "records": route_rows})
    dump_json(out / "bashar-routes.json", {"schema_version": 1, "records": relevant})
    dump_json(out / "bashar-publishers.json", {"schema_version": 1, "records": publisher_rows})
    dump_csv(out / "bashar-publishers.csv", publisher_rows, ["publisher_account_id", "name", "identity_status", "channel_route_ids", "indexed_bashar_count", "indexed_bashar_eligible_count", "indexed_bashar_under_minimum_count", "indexed_bashar_unknown_duration_count", "indexed_bashar_conflicting_duration_count", "selected_default_bashar_count", "selected_conservative_bashar_count", "whole_publisher_lifetime_upload_count"])
    route_columns = ["route_id", "url", "inherited_alias_component", "bashar_relevant", "bashar_branded_url_evidence", "indexed_video_count", "indexed_eligible_count", "indexed_bashar_count", "indexed_bashar_eligible_count", "indexed_bashar_under_minimum_count", "indexed_bashar_unknown_duration_count", "indexed_bashar_conflicting_duration_count", "indexed_bashar_shorts_evidence_count", "indexed_bashar_multi_route_count", "selected_default_bashar_count", "selected_conservative_bashar_count", "whole_channel_lifetime_video_count", "whole_channel_eligible_video_count", "count_scope"]
    dump_csv(out / "route-inventory.csv", route_rows, route_columns)
    dump_csv(out / "bashar-routes.csv", relevant, route_columns)
    dump_json(out / "input-manifest.json", inputs)
    dump_json(out / "summary.json", summary)
    return rows, route_rows, summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE)
    args = parser.parse_args()
    _, _, summary = build(args.output)
    print(json.dumps(summary, indent=2, sort_keys=True))
