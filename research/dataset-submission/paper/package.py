"""Package only explicitly admitted manuscript inputs; never source media/text."""
import hashlib
import json
import pathlib
import subprocess
import zipfile

PAPER = pathlib.Path(__file__).resolve().parent
INPUTS = [
    "paper.tex", "body.tex", "checklist.tex", "related-work.bib",
    "generated/counts.tex", "generated/origin-table.tex",
    "generated/analysis-results.tex", "generated/frame-binding.json",
    "vendor/aaai2027.sty", "vendor/aaai2027.bst",
    "vendor/upstream-source-manifest.json", "compute-context.json",
]
FIGURES = [
    "corpus-profile.pdf", "topic-contexts.pdf", "similarity-contexts.pdf",
    "sensitivity.pdf", "network.pdf", "projection.pdf",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    inputs = INPUTS + ["generated/" + name for name in FIGURES if (PAPER / "generated" / name).is_file()]
    with zipfile.ZipFile(PAPER / "overleaf-source.zip", "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in inputs:
            target = name.removeprefix("vendor/")
            bundle.write(PAPER / name, target)
        bundle.writestr("README.txt", "Compile paper.tex using PDFLaTeX and BibTeX. Working draft; human authorship, DOI, final rights and ethics review pending. This ZIP contains manuscript inputs, not source media/transcripts.\n")
    pages = subprocess.check_output(["pdftotext", "-layout", str(PAPER / "paper.pdf"), "-"], text=True).split("\f")
    checklist_page = next((index + 1 for index, page in enumerate(pages) if "Paper Checklist" in page), None)
    total_pages = len(pages) - (not pages[-1].strip())
    receipt = {
        "status": "working_draft_built_not_submitted",
        "total_pages": total_pages,
        "checklist_starts_page": checklist_page,
        "body_and_references_pages": checklist_page - 1 if checklist_page else None,
        "within_10_page_body_reference_target": checklist_page is not None and checklist_page - 1 <= 10,
        "official_style_unchanged": digest(PAPER / "vendor/aaai2027.sty") == "391bce82815bf698b8e382dd3ae7e30c75d7ab46df140cb295b1266016bc8623",
        "artifacts": [{"path": name, "bytes": (PAPER / name).stat().st_size, "sha256": digest(PAPER / name)} for name in inputs + ["paper.pdf", "overleaf-source.zip"]],
    }
    (PAPER / "build-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: value for key, value in receipt.items() if key != "artifacts"}, indent=2))


if __name__ == "__main__":
    main()
