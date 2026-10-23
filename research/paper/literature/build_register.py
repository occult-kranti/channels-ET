"""Regenerate readable literature exports from the audited source register."""
from pathlib import Path
import csv
import json
import re

BASE = Path(__file__).resolve().parent
rows = json.loads((BASE / "source-register.json").read_text())
bibkeys = set(re.findall(r"^\s*@\w+\{([^,]+),", (BASE.parent / "references.bib").read_text(), re.M))
keys = [row["key"] for row in rows]
assert len(keys) == len(set(keys)), "Duplicate source-register keys"
assert set(keys) == bibkeys, "Bibliography/register keys disagree"
with (BASE / "source-register.csv").open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

lines = [
    "# Targeted primary-source register", "",
    "Verified 23 October 2026. Targeted review, not a systematic review. "
    "Metadata are in `../references.bib`. Access depth is recorded per source; "
    "retrieval alone is not a claim that every page was read. None of these "
    "sources establishes the origin or truth of communications in our dataset.", "",
]
for row in rows:
    lines += [
        f"## {row['title']} ({row['year']})", "",
        f"Key: `{row['key']}`. {row['publication_class']}.", "",
        f"Primary source: {row['primary_url']}", "",
        f"Access source: {row['access_url']}", "",
        f"Access depth: {row['access_depth']}", "",
        f"Locator: {row['reading_locators']}", "",
        f"Use: {row['supported_use']}", "",
        f"Boundary: {row['limits_and_nontransfer']}", "",
    ]
(BASE / "annotated-bibliography.md").write_text("\n".join(lines))
print(f"Regenerated {len(rows)} source cards; all BibTeX keys accounted for.")
