"""Verify the official-question transcription and a clean manuscript ZIP build."""
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile
import zipfile

PAPER = pathlib.Path(__file__).resolve().parent
REPO = PAPER.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    original = (REPO / "research/paper/reviews/design/icwsm-checklist-working.tex").read_text()
    current = (PAPER / "checklist.tex").read_text()
    old = [line.split("\\ChecklistTBD")[0].strip() for line in original.splitlines() if "\\item" in line and "\\ChecklistTBD" in line]
    new = [line.split("\\textbf{")[0].strip() for line in current.splitlines() if "\\item" in line and "\\textbf{" in line]
    assert len(old) == len(new) == 35 and old == new
    with tempfile.TemporaryDirectory(prefix="channels-et-overleaf-") as tmp:
        with zipfile.ZipFile(PAPER / "overleaf-source.zip") as bundle:
            for name in bundle.namelist():
                assert not pathlib.PurePosixPath(name).is_absolute() and ".." not in pathlib.PurePosixPath(name).parts
            bundle.extractall(tmp)
        env = os.environ.copy()
        if not env.get("TEXMFHOME") and pathlib.Path("/workspace/channels-et-tex/texmf").is_dir():
            env.update(TEXMFHOME="/workspace/channels-et-tex/texmf", TEXMFVAR="/workspace/channels-et-tex/var", TEXMFCONFIG="/workspace/channels-et-tex/config")
        commands = [
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"],
            ["bibtex", "paper"],
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"],
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"],
        ]
        for command in commands:
            result = subprocess.run(command, cwd=tmp, env=env, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stdout[-3000:] + result.stderr[-1000:])
        text = subprocess.check_output(["pdftotext", "-layout", str(PAPER / "paper.pdf"), "-"], text=True)
        rebuilt = subprocess.check_output(["pdftotext", "-layout", str(pathlib.Path(tmp) / "paper.pdf"), "-"], text=True)
        assert text == rebuilt
        log = (pathlib.Path(tmp) / "paper.log").read_text()
        assert not any(term in log for term in ["Overfull", "undefined references", "undefined citations"])
    receipt = {
        "status": "passed", "question_count": 35,
        "question_text_matches_retained_official_transcription": True,
        "clean_overleaf_zip_compilation": True,
        "clean_rebuild_extracted_text_identical": True,
        "unresolved_references": False, "overfull_boxes": False,
        "official_checklist_pdf_sha256": "f40129bc2a84ff3a4e7e91aae15df8269aeb7928e9feaf304e92bfe87eb658dc",
        "pdf_sha256": sha(PAPER / "paper.pdf"), "zip_sha256": sha(PAPER / "overleaf-source.zip"),
        "note": "Build/integrity validation only. Working answers still require human authorship, release/ethics decisions and final venue review.",
    }
    (PAPER / "verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
