"""Create an explicit manuscript/venue-only allowlist for the root release builder."""
import hashlib
import json
import pathlib
import shutil

PAPER = pathlib.Path(__file__).resolve().parent
VENUE = PAPER.parent / "venue"
STAGE = pathlib.Path("/workspace/channels-et-private/dataset-submission-2026-11/venue-public")


def main():
    STAGE.mkdir(parents=True, exist_ok=True)
    receipt = json.loads((PAPER / "build-receipt.json").read_text())
    venue = json.loads((VENUE / "requirements.json").read_text())
    venue["paper"].update({
        "pdf": "paper/paper.pdf", "latex_zip": "paper/overleaf-source.zip",
        "tex": "paper/paper.tex", "pdf_built": True,
        "body_and_references_pages": receipt["body_and_references_pages"],
        "total_pages": receipt["total_pages"],
        "checklist_starts_page": receipt["checklist_starts_page"],
        "within_page_target": receipt["within_10_page_body_reference_target"],
        "source_ledger": "docs/venue-sources.json",
    })
    for row in venue["requirements"]:
        if row["id"] == "pages":
            row["status"] = "verified_draft_build" if receipt["within_10_page_body_reference_target"] else "requires_shortening"
            row["evidence"] = f'{receipt["body_and_references_pages"]} pages body/references, followed by checklist; {receipt["total_pages"]} pages total. Working draft only.'
    (VENUE / "requirements.json").write_text(json.dumps(venue, indent=2) + "\n")
    (VENUE / "venue.json").write_text(json.dumps(venue, indent=2) + "\n")
    mapping = {"venue.json": VENUE / "venue.json", "docs/VENUE.md": VENUE / "VENUE.md",
               "docs/venue-sources.json": VENUE / "sources.json", "docs/PAPER.md": PAPER / "README.md"}
    admitted = ["paper.pdf", "overleaf-source.zip", "paper.tex", "body.tex", "checklist.tex",
                "related-work.bib", "build-receipt.json", "compute-context.json", "verification.json"]
    admitted += [a["path"] for a in receipt["artifacts"] if a["path"].startswith("generated/")]
    if (PAPER / "claims.json").exists():
        admitted.append("claims.json")
    for name in sorted(set(admitted)):
        mapping["paper/" + name] = PAPER / name
    rows = []
    for name, source in sorted(mapping.items()):
        target = STAGE / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        rows.append({"file": name, "bytes": target.stat().st_size,
                     "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
    manifest = {"schema_version": 1, "module": "venue", "status": "working_draft_not_submitted",
                "public_allowlist": rows, "source_boundary": "Only manuscript, figures, venue guidance and their receipts; no raw source media or transcript bodies."}
    (STAGE / "output-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (VENUE / "output-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"stage": str(STAGE), "files": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
