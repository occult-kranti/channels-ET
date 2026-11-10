#!/usr/bin/env python3
"""Build a public catalogue from tracked static artifacts; optionally audit live URLs.

The catalogue indexes public metadata and derived research. It never follows media
URLs, reads private source bodies, or changes historical study denominators.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html import escape, unescape
import json
from pathlib import Path
import re
import subprocess
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://occult-kranti.github.io/channels-ET/"
REPOSITORY = "https://github.com/occult-kranti/channels-ET"
GROUPS = {
    "dashboards": "Dashboards & research pages",
    "reports": "Research papers · PDF",
    "bundles": "Dataset, analysis & source bundles · ZIP",
    "databases": "Public research databases · SQLite",
    "metadata": "Data & release manifests",
    "repository": "Repository & version history",
}
PAGE_DESCRIPTIONS = {
    "dist/index.html": "Atlas of people, attributed speakers, sessions and source records.",
    "dist/dataset-submission/index.html": "Dataset workbench, publisher contexts, publication explorer and working paper.",
    "dist/youtube-archive/index.html": "Collection ledger: account identities, indexed videos and retained-artifact receipts.",
    "dist/transcript-knowledge/index.html": "Searchable source profiles, question candidates, curated answers and graph.",
    "dist/channel-lab/index.html": "Source inventory, recording comparisons and recognition-edition sensitivity.",
    "dist/knowledge-bank/index.html": "Source-bound knowledge, retrieval experiments and speech-recognition studies.",
    "dist/council-study/index.html": "Council-name registers, message comparisons and collection records.",
    "dist/channeling-network/index.html": "Attributed relationships, repeated labels, source coverage and study supplements.",
    "dist/bashar-ra/index.html": "Bashar and Ra source comparisons, questions, topics and research paper.",
    "dist/subscription-audit/index.html": "Subscription screening and publisher text, video and audio inventories.",
    "dist/transcripts/index.html": "Historical transcript study, reading candidates, maps and storage distributions.",
    "dist/research/index.html": "Living research workspace with historical study outputs and collection diagnostics.",
    "dist/expansion/index.html": "Historical evidence explorer, practitioner coverage and question-pair analysis.",
    "dist/schumann-crosslinks/index.html": "Schumann cross-link evidence review, synthetic checks and prospective protocol.",
}
WORKSPACES = {
    "analysis": "Atlas analysis", "bashar-ra": "Bashar & Ra",
    "channel-lab": "Channel & Recording Lab", "channeling-network": "Channeling relationships",
    "council-study": "Council names & messages", "dataset-submission": "Dataset workbench",
    "expansion": "Evidence explorer", "exports": "Atlas exports",
    "knowledge-bank": "Knowledge bank", "research": "Living research",
    "schumann-crosslinks": "Schumann cross-links", "subscription-audit": "Subscription screening",
    "transcript-knowledge": "Transcript knowledge", "transcripts": "Transcript study",
    "youtube-archive": "YouTube archive",
}
LABELS = {
    "dist/analysis/channeling-atlas-paper.pdf": "Atlas analysis paper",
    "dist/analysis/channeling-analysis-bundle.zip": "Atlas analysis bundle",
    "dist/analysis/channeling-atlas-overleaf.zip": "Atlas paper · Overleaf source",
    "dist/dataset-submission/channeling-discourse-metadata-2026-11-08.zip": "Dataset metadata release · 2026-11-08",
    "dist/dataset-submission/paper/overleaf-source.zip": "Dataset paper · Overleaf source",
    "dist/exports/channeling-research-csv.zip": "Atlas research tables · CSV bundle",
    "dist/knowledge-bank/project-skills.zip": "Knowledge bank · project method skills",
    "dist/research/qwen-digest-lora-pilot.zip": "Living research · Qwen digest LoRA pilot",
    "dist/transcript-knowledge/database-public.sqlite": "Transcript knowledge · public database",
    "dist/analysis/report.html": "Atlas analysis · HTML report",
}
NOTES = [
    "Public downloads contain metadata, derived outputs and research source packages. Original audio and complete source texts are not included in these public downloads; consult the dataset archive status for actual retention and transfer receipts.",
    "Historical studies keep their original sampling dates, inputs and denominators. A later site deployment does not make those collections newly acquired or complete.",
    "The 2026-11-08 dataset is a working research release. A dataset DOI, human authorship and final institutional/rights determinations remain unfinished; no conference submission or acceptance is claimed.",
]


def tracked_files() -> set[str]:
    return set(subprocess.check_output(
        ["git", "ls-files", "-z", "dist", "index.html"], cwd=ROOT
    ).decode().split("\0")) - {""}


def title(path: Path) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", path.read_text(), re.I | re.S)
    return unescape(re.sub(r"\s+", " ", match.group(1))).strip() if match else path.stem


def workspace(path: str) -> str:
    parts = Path(path).parts
    return WORKSPACES.get(parts[1], "Channeling Atlas") if len(parts) > 2 else "Channeling Atlas"


def label(path: str) -> str:
    if path in LABELS:
        return LABELS[path]
    name = Path(path).name
    if name in {"paper.pdf", "report.pdf"}:
        return workspace(path) + " · research paper"
    if name == "source.zip":
        return workspace(path) + " · paper source package"
    return workspace(path) + " · " + name


def local_entry(path: str, category: str, description: str = "") -> dict:
    file = ROOT / path
    if not file.is_file() or file.is_symlink():
        raise ValueError(f"Catalogue target is not a regular file: {path}")
    url_path = path.removesuffix("index.html") if file.name == "index.html" else path
    return {
        "label": title(file) if file.suffix == ".html" else label(path),
        "category": category,
        "description": description,
        "path": path,
        "url": BASE + quote(url_path, safe="/"),
        "bytes": file.stat().st_size,
        "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
    }


def catalogue() -> dict:
    tracked = tracked_files()
    entries: dict[str, dict] = {}

    def add(path: str, category: str, description: str = "") -> None:
        if path not in tracked:
            raise ValueError(f"Catalogue target is not tracked: {path}")
        entries[path] = local_entry(path, category, description)

    for path in sorted(tracked):
        if path.startswith("dist/releases/"):
            continue
        file = Path(path)
        if file.name == "index.html":
            add(path, "dashboards", PAGE_DESCRIPTIONS.get(path, "Project landing page and research entrypoints."))
        elif file.suffix == ".pdf" and not any("figure" in p or p == "generated" for p in file.parts):
            add(path, "reports", "Published study artifact; retain its stated source frame and limitations.")
        elif file.suffix == ".zip":
            add(path, "bundles", "Public downloadable package; consult its included documentation and rights statement.")
        elif file.suffix in {".sqlite", ".sqlite3", ".db"}:
            add(path, "databases", "Public research database; source records and model outputs retain their stated evidence status.")

    # Include the data needed to enter each workspace without enumerating thousands
    # of per-source records or repeating figures already linked from the dashboards.
    for path in sorted(tracked):
        file = Path(path)
        if len(file.parts) == 3 and file.name == "manifest.json":
            manifest = json.loads((ROOT / path).read_text())
            add(path, "metadata", manifest.get("scope", "Workspace artifact manifest."))
            for module in manifest.get("modules", {}).values():
                add((file.parent / module["file"]).as_posix(), "metadata", "Workspace data module listed in " + path + ".")
        elif len(file.parts) <= 3 and file.name in {"data.json", "analysis.json", "evidence.json"}:
            add(path, "metadata", "Public metadata and derived analysis for this workspace.")
    for path in ("dist/dataset-submission/metadata-release-2026-11-08.json",
                 "dist/dataset-submission/schema.json", "dist/dataset-submission/archive.json"):
        add(path, "metadata", "Versioned dataset metadata, schema or archive status; see the dataset release notes.")
    if "dist/analysis/report.html" in tracked:
        add("dist/analysis/report.html", "dashboards", "Historical Atlas analysis report and downloadable study artifacts.")
        entries["dist/analysis/report.html"]["label"] = LABELS["dist/analysis/report.html"]

    records = sorted(entries.values(), key=lambda row: (list(GROUPS).index(row["category"]), row["path"]))
    records.extend([
        {"label": "Public repository", "category": "repository", "url": REPOSITORY,
         "description": "Code, research documentation and committed artifacts."},
        {"label": "GitHub release history", "category": "repository", "url": REPOSITORY + "/releases",
         "description": "Published GitHub release records; separate from a DOI repository deposit."},
        {"label": "Dataset release notes · 2026-11-08", "category": "repository",
         "url": REPOSITORY + "/tree/main/dataset/releases/2026-11-08",
         "description": "Frozen source-frame date, public package hashes and unfinished submission requirements."},
    ])
    return {
        "schema_version": 1,
        "title": "Channeling Atlas · published links",
        "base_url": BASE,
        "scope": "Tracked dashboard entrypoints, complete report PDFs, ZIP bundles, public SQLite databases and workspace data entrypoints. Individual figures and per-record data remain accessible through their workspaces.",
        "provenance": "Generated by scripts/pages/build_link_catalog.py from git ls-files and local file bytes. File hashes describe catalogue build inputs; live HTTP checks are recorded separately.",
        "notes": NOTES,
        "counts": dict(Counter(row["category"] for row in records)),
        "entries": records,
    }


def human_size(size: int) -> str:
    return f"{size / 1048576:.1f} MB" if size >= 1048576 else f"{size / 1024:.0f} KB"


def html_page(data: dict) -> str:
    sections = []
    for category, heading in GROUPS.items():
        rows = [row for row in data["entries"] if row["category"] == category]
        items = []
        for row in rows:
            size = f'<span class="size">{human_size(row["bytes"])}</span>' if "bytes" in row and category != "dashboards" else ""
            path = f'<code>{escape(row["path"])}</code>' if "path" in row else ""
            items.append(f'<li data-entry><div class="entry-title"><a href="{escape(row["url"], quote=True)}">{escape(row["label"])}</a>{size}</div><p>{escape(row["description"])}</p>{path}</li>')
        sections.append(f'<section id="{category}" aria-labelledby="heading-{category}" data-group><h2 id="heading-{category}">{escape(heading)} <span>{len(rows)}</span></h2><ul class="entries {category}">{"".join(items)}</ul></section>')
    nav = "".join(f'<a href="#{key}">{escape(value.split(" · ")[0])}</a>' for key, value in GROUPS.items())
    return '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#183d32"><meta name="description" content="All Channeling Atlas workspaces, research papers, public data downloads and source packages in one place.">
<title>Published links · Channeling Atlas</title>
<style>
:root{color-scheme:light;--paper:#f4f3ec;--surface:#fffef9;--ink:#203d35;--muted:#52665e;--line:#cbd3c9;--green:#285b49;--focus:#a24a17}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 Arial,Helvetica,sans-serif}a{color:var(--green);text-underline-offset:4px}a:hover{color:#28677f}:focus-visible{outline:3px solid var(--focus);outline-offset:4px}.wrap{width:min(1160px,calc(100% - 40px));margin:auto}.skip{position:absolute;top:-80px;left:20px;padding:12px;background:var(--surface)}.skip:focus{top:10px}header{border-bottom:1px solid var(--line);padding:22px 0}header .wrap{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}.brand{font-size:.85rem;letter-spacing:.1em;font-weight:700;text-decoration:none}main{padding:48px 0 64px}h1,h2{font-family:Georgia,'Times New Roman',serif;font-weight:400;line-height:1.15}h1{font-size:clamp(2.5rem,6vw,4.3rem);margin:10px 0 22px;letter-spacing:-.035em}h2{font-size:1.85rem;margin:0 0 20px}h2 span{font:400 .85rem Arial,sans-serif;color:var(--muted);margin-left:8px}.eyebrow{font-size:.75rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}.lede{max-width:820px;font-size:1.1rem}.context{max-width:900px;border-left:3px solid var(--line);padding-left:20px;margin:26px 0;font-size:.93rem;color:var(--muted)}.context p{margin:8px 0}.jump{display:flex;gap:10px 22px;flex-wrap:wrap;padding:20px 0;border-block:1px solid var(--line);margin:28px 0}.filter{max-width:600px;margin:28px 0}label{font-weight:700;font-size:.9rem}input{display:block;width:100%;min-height:48px;border:1px solid #8ca18f;border-radius:3px;background:var(--surface);color:var(--ink);font:inherit;padding:11px 13px;margin:8px 0}.status{font-size:.9rem;color:var(--muted)}section{margin-top:44px}.entries{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 28px}.entries li{min-width:0;padding:18px 0;border-top:1px solid var(--line)}.entry-title{display:flex;align-items:baseline;justify-content:space-between;gap:12px}.entry-title a{font-weight:700}.entries p{font-size:.91rem;color:var(--muted);margin:7px 0}.size{font-size:.75rem;white-space:nowrap;color:var(--muted)}code{font:12px/1.5 ui-monospace,monospace;overflow-wrap:anywhere;color:var(--muted)}footer{border-top:1px solid var(--line);padding:24px 0;color:var(--muted);font-size:.9rem}footer .wrap{display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap}[hidden]{display:none!important}@media(max-width:680px){.wrap{width:calc(100% - 32px)}main{padding-top:32px}.entries{grid-template-columns:1fr}.jump{gap:12px 18px}h2{font-size:1.6rem}.entry-title{align-items:flex-start}}
</style></head><body>
<a class="skip" href="#main">Skip to published links</a>
<header><div class="wrap"><a class="brand" href="../">CHANNELING ATLAS</a><a href="../dataset-submission/">Open dataset workbench →</a></div></header>
<main id="main" class="wrap" tabindex="-1"><p class="eyebrow">Research collection</p><h1>Published links</h1>
<p class="lede">Explore every research workspace, then open its papers, public data and source packages. This catalogue brings the project’s main published artifacts together.</p>
<div class="context">''' + "".join(f"<p>{escape(note)}</p>" for note in NOTES) + '''</div>
<nav class="jump" aria-label="Catalogue sections">''' + nav + '''</nav>
<div class="filter" id="filter" hidden><label for="search">Find a workspace or download</label><input id="search" type="search" placeholder="Try transcript, paper, dataset or SQLite" autocomplete="off"><p id="results" class="status" role="status" aria-live="polite"></p></div>
''' + "\n".join(sections) + r'''
<p id="empty" hidden>No matching links. Try a broader word or clear the search.</p>
</main><footer><div class="wrap"><span>Public metadata · Derived research · Historical study frames</span><a href="links.json">Download catalogue JSON with file hashes</a></div></footer>
<script>
(() => {const input=document.querySelector('#search'),rows=[...document.querySelectorAll('[data-entry]')],groups=[...document.querySelectorAll('[data-group]')];document.querySelector('#filter').hidden=false;function filter(){const words=input.value.toLowerCase().trim().split(/\s+/).filter(Boolean);let count=0;for(const row of rows){row.hidden=!words.every(word=>row.textContent.toLowerCase().includes(word));if(!row.hidden)count++;}for(const group of groups)group.hidden=![...group.querySelectorAll('[data-entry]')].some(row=>!row.hidden);document.querySelector('#results').textContent=`${count} of ${rows.length} links shown`;document.querySelector('#empty').hidden=count>0;}input.addEventListener('input',filter);document.querySelector('.jump').addEventListener('click',event=>{if(event.target.closest('a')){input.value='';filter();}});filter();})();
</script></body></html>
'''


def markdown(data: dict) -> str:
    lines = ["# Deployed links", "", f"[Open the complete published catalogue]({BASE}dist/releases/) · [Machine-readable catalogue]({BASE}dist/releases/links.json)", ""]
    lines.extend(note + "\n" for note in NOTES)
    lines.extend(["This index is generated from tracked static files. Individual figures and per-source records are linked from the relevant workspaces. Rebuild with `python scripts/pages/build_link_catalog.py`.", ""])
    for category, heading in GROUPS.items():
        lines.extend(["## " + heading, ""])
        for row in data["entries"]:
            if row["category"] == category:
                lines.append(f'- [{row["label"]}]({row["url"]})' + (f' — {row["description"]}' if category in {"dashboards", "repository"} else ""))
        lines.append("")
    return "\n".join(lines)


def audit_entry(row: dict) -> dict:
    result = {"url": row["url"], "label": row["label"], "category": row["category"]}
    if "path" in row:
        result["path"] = row["path"]
    try:
        with urlopen(Request(row["url"], headers={"User-Agent": "channels-ET-link-audit/1.0"}), timeout=30) as response:
            sample = response.read(16384)
            suffix = Path(row.get("path", "")).suffix
            expected = {".pdf": b"%PDF-", ".zip": b"PK", ".sqlite": b"SQLite format 3", ".sqlite3": b"SQLite format 3", ".db": b"SQLite format 3"}.get(suffix)
            if expected:
                signature_ok = sample.startswith(expected)
            elif suffix == ".json":
                signature_ok = sample.lstrip().startswith((b"{", b"["))
            else:
                signature_ok = b"<html" in sample.lower()
            result.update(status=response.status, final_url=response.url,
                          content_type=response.headers.get("Content-Type"),
                          content_length=response.headers.get("Content-Length"),
                          sampled_bytes=len(sample), signature_ok=signature_ok,
                          ok=response.status == 200 and signature_ok)
    except HTTPError as error:
        result.update(status=error.code, error=str(error), ok=False)
    except (URLError, TimeoutError, OSError) as error:
        result.update(error=str(error), ok=False)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify generated files without writing them")
    parser.add_argument("--audit-live", action="store_true", help="Check actual public URLs, using at most four workers")
    parser.add_argument("--audit-output", type=Path, help="Write an HTTP receipt outside this public repository")
    args = parser.parse_args()
    if args.audit_live and not args.audit_output:
        parser.error("--audit-live requires --audit-output outside this public repository")
    if args.audit_output and args.audit_output.resolve().is_relative_to(ROOT):
        parser.error("HTTP audit receipts belong outside the public repository")
    data = catalogue()
    outputs = {ROOT / "dist/releases/index.html": html_page(data),
               ROOT / "dist/releases/links.json": json.dumps(data, indent=2, ensure_ascii=False) + "\n",
               ROOT / "DEPLOYED-LINKS.md": markdown(data)}
    for path, content in outputs.items():
        if args.check:
            if not path.is_file() or path.read_text() != content:
                raise SystemExit(f"Catalogue needs rebuilding: {path.relative_to(ROOT)}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    print(json.dumps({"catalogue_entries": len(data["entries"]), "counts": data["counts"], "check": args.check}))
    if args.audit_live:
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(audit_entry, data["entries"]))
        receipt = {"checked_at": datetime.now(timezone.utc).isoformat(), "workers": 4,
                   "scope": "HTTP GET status and first 16 KiB content signatures. Does not validate browser rendering, full file hashes, historical collection freshness or private media retention.",
                   "total": len(results), "passed": sum(row["ok"] for row in results), "results": results}
        args.audit_output.parent.mkdir(parents=True, exist_ok=True)
        args.audit_output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps({"audit_total": receipt["total"], "audit_passed": receipt["passed"], "receipt": str(args.audit_output)}))
        if receipt["passed"] != receipt["total"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
