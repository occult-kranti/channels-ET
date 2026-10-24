#!/usr/bin/env python3
"""Build the verified expansion, then stage the complete static release.

The source-only bootstrap is used once when committed expansion inputs are absent.
It downloads public research source (no credentials, media, or transcript bodies),
verifies the archive and every source-file hash, then builds the public artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = (
    "index.html", ".nojekyll", "dist/index.html", "dist/expansion/index.html",
    "dist/research/index.html", "dist/research/app.js", "dist/research/data.json",
    "dist/research/paper.pdf", "dist/research/source.zip",
    "dist/research/qwen-digest-lora-pilot.zip", "dist/research/qa-candidates.sqlite",
)
GOFILE_DL_COMMIT = "372c99e13b2f897c5c856c5321896eb7f1b35e0b"
GOFILE_DL_ZIP_SHA256 = "3a6861329730726ccba0bdb33f5a2c86a88e0061c7925b1965ce341ee7a009cc"
TECTONIC_SHA256 = "1a715688baf591e650c8aeb160ae934e181685eecbb38b317de30b269ac5d606"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: list[str], *, cwd: Path = ROOT, env: dict | None = None) -> None:
    print("+", " ".join(str(a) for a in args), flush=True)
    subprocess.run([str(a) for a in args], cwd=cwd, env=env, check=True)


def download(url: str, target: Path) -> None:
    run(["curl", "-fLsS", url, "-o", target])


def source_release() -> dict:
    return json.loads((ROOT / "scripts/pages/source-release.json").read_text())


def bootstrap_source(work: Path) -> None:
    marker = ROOT / "research/expansion-2026/non-bashar-analysis/analysis.json"
    if marker.exists():
        print("Committed expansion source is present; skipping external bootstrap.")
        return
    release = source_release()
    run(["python3", "-m", "pip", "install", "pathvalidate==3.3.1", "curl_cffi==0.16.3"])
    downloader_zip = work / "gofile-dl.zip"
    download(f"https://codeload.github.com/martadams89/gofile-dl/zip/{GOFILE_DL_COMMIT}", downloader_zip)
    if sha256(downloader_zip) != GOFILE_DL_ZIP_SHA256:
        raise ValueError("Pinned gofile-dl archive hash mismatch")
    with zipfile.ZipFile(downloader_zip) as archive:
        archive.extractall(work / "gofile-dl-src")
    run([sys_executable(), str(work / "gofile-dl-src" / f"gofile-dl-{GOFILE_DL_COMMIT}" / "run.py"),
         release["downloadPage"], "-d", work / "source-download"])
    candidates = list((work / "source-download").rglob("source-bootstrap.tar.xz"))
    if len(candidates) != 1:
        raise ValueError(f"Expected one source archive, found {len(candidates)}")
    archive_path = candidates[0]
    if sha256(archive_path) != release["archiveSha256"]:
        raise ValueError("Expansion source archive hash mismatch")
    with tarfile.open(archive_path, "r:xz") as archive:
        archive.extractall(ROOT)
    manifest_path = ROOT / "source-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for row in manifest["files"]:
        relative = Path(row["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe source path: {relative}")
        data = (ROOT / relative).read_bytes()
        if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ValueError(f"Source hash mismatch: {relative}")
    print(f"Verified {len(manifest['files'])} source files from {manifest['sourceCommit']}")
    manifest_path.unlink()
    for obsolete in ("part-00.b64", "part-01.b64"):
        (ROOT / "research/expansion-2026/patch/parts" / obsolete).unlink(missing_ok=True)


def sys_executable() -> str:
    return shutil.which("python3") or "python3"


def ensure_system_tools() -> None:
    missing = [tool for tool in ("rsvg-convert", "pdfinfo", "zip") if not shutil.which(tool)]
    if missing:
        run(["sudo", "apt-get", "update"])
        run(["sudo", "apt-get", "install", "-y", "--no-install-recommends",
             "poppler-utils", "librsvg2-bin", "zip"])


def ensure_tectonic(work: Path) -> None:
    if shutil.which("tectonic"):
        return
    archive = work / "tectonic.tar.gz"
    download("https://github.com/tectonic-typesetting/tectonic/releases/download/"
             "tectonic%400.17.0/tectonic-0.17.0-x86_64-unknown-linux-gnu.tar.gz", archive)
    if sha256(archive) != TECTONIC_SHA256:
        raise ValueError("Tectonic archive hash mismatch")
    with tarfile.open(archive, "r:gz") as source:
        source.extractall(work)
    binary = work / "tectonic"
    if not binary.is_file():
        raise ValueError("Tectonic binary missing after extraction")
    os.environ["PATH"] = str(work) + os.pathsep + os.environ.get("PATH", "")


def ensure_dashboard_assets(work: Path) -> None:
    npm = work / "channels-et-npm"
    run(["npm", "install", "--prefix", npm, "echarts@6.1.0",
         "@fontsource-variable/inter@5.3.0", "@fontsource-variable/jetbrains-mono@5.3.0",
         "@fontsource-variable/space-grotesk@5.3.0"])
    vendor, fonts = ROOT / "dist/research/vendor", ROOT / "dist/research/fonts"
    vendor.mkdir(parents=True, exist_ok=True)
    fonts.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(npm / "node_modules/echarts/dist/echarts.min.js", vendor / "echarts.min.js")
    shutil.copyfile(npm / "node_modules/echarts/LICENSE", vendor / "echarts-LICENSE.txt")
    font_files = {
        "inter": "inter-latin-wght-normal.woff2",
        "jetbrains-mono": "jetbrains-mono-latin-wght-normal.woff2",
        "space-grotesk": "space-grotesk-latin-wght-normal.woff2",
    }
    for family, filename in font_files.items():
        source = npm / "node_modules/@fontsource-variable" / family / "files" / filename
        shutil.copyfile(source, fonts / filename.replace("-normal", ""))
        shutil.copyfile(npm / "node_modules/@fontsource-variable" / family / "LICENSE",
                        fonts / f"{family}-LICENSE.txt")


def build_expansion() -> None:
    with tempfile.TemporaryDirectory(prefix="channels-et-build-") as temp:
        work = Path(temp)
        bootstrap_source(work)
        ensure_system_tools()
        ensure_tectonic(work)
        run([sys_executable(), "-m", "pip", "install", "-r", ROOT / "research/expansion-2026/requirements.txt"])
        run([sys_executable(), "research/expansion-2026/acquisition/verify.py"])
        run([sys_executable(), "research/expansion-2026/inventory/build.py"])
        run([sys_executable(), "research/expansion-2026/inventory/verify.py"])
        run([sys_executable(), "research/expansion-2026/qa/build.py"])
        run([sys_executable(), "research/expansion-2026/qa/verify.py"])
        run([sys_executable(), "scripts/expansion/rebuild_public_sqlite.py"])
        run([sys_executable(), "scripts/expansion/render_public_figures.py"])
        run([sys_executable(), "research/expansion-2026/non-bashar-analysis/verify_public.py"])
        if os.environ.get("CHANNELS_ET_SKIP_PAPER_BUILD") == "1":
            run([sys_executable(), "research/expansion-2026/paper/verify.py"])
        else:
            run(["bash", "research/expansion-2026/paper/build.sh"])
        ensure_dashboard_assets(work)
        run([sys_executable(), "research/expansion-2026/dashboard/build_data.py"])
        run([sys_executable(), "scripts/expansion/prepare_release.py", "all", "--pdf-name",
             "draft-expansion-paper.pdf"])
        run([sys_executable(), "research/expansion-2026/dashboard/build_data.py"])
        run([sys_executable(), "research/expansion-2026/dashboard/verify.py"])
        run(["node", "--check", ROOT / "dist/research/app.js"])
        if os.environ.get("CHANNELS_ET_BROWSER") == "1":
            run([sys_executable(), "-m", "pip", "install", "playwright==1.62.0"])
            run([sys_executable(), "-m", "playwright", "install", "--with-deps", "chromium"])
            run([sys_executable(), "research/expansion-2026/dashboard/browser_check.py"])


def stage(output: Path) -> dict:
    output = output.resolve()
    if output == ROOT or output in ROOT.parents or output.is_relative_to(ROOT / "dist"):
        raise ValueError("Output must not replace the repository or its dist sources")
    if output.exists():
        raise ValueError("Output directory already exists; choose a fresh path")
    sources = [ROOT / "index.html", ROOT / ".nojekyll", *sorted((ROOT / "dist").rglob("*"))]
    for source in sources:
        if source.is_symlink():
            raise ValueError(f"Static artifact must not contain symlinks: {source.relative_to(ROOT)}")
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            raise ValueError(f"Missing static release file: {relative}")
    output.mkdir(parents=True)
    files = []
    for source in sources:
        if not source.is_file():
            continue
        relative = source.relative_to(ROOT).as_posix()
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        files.append({"path": relative, "bytes": target.stat().st_size, "sha256": sha256(target)})
    commit = os.environ.get("GITHUB_SHA") or subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    static_inputs_dirty = bool(subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", "index.html", ".nojekyll", "dist"],
        cwd=ROOT, text=True).strip())
    manifest = {
        "schema_version": 1,
        "repository": "occult-kranti/channels-ET",
        "source_commit": commit,
        "static_inputs_dirty": static_inputs_dirty,
        "commit_scope": "Checkout HEAD plus verified source/bootstrap and generated artifacts; per-file hashes bind all static outputs",
        "base_path": "/channels-ET/",
        "entry": "index.html",
        "current_dashboard": "dist/research/",
        "legacy_dashboard": "dist/",
        "method": "Build verified expansion source, then copy the complete retained dist tree",
        "manifest_self_excluded": True,
        "files": files,
        "file_count": len(files),
        "total_bytes": sum(x["bytes"] for x in files),
    }
    (output / "deployment-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("CHANNELS_ET_BUILD_EXPANSION", "1") == "1":
        try:
            build_expansion()
        except Exception as exc:
            import traceback
            traceback.print_exc()
            print(f"::error title=Expansion build failed::{type(exc).__name__}: {exc}")
            raise
    manifest = stage(args.output)
    print(json.dumps({k: manifest[k] for k in ("source_commit", "file_count", "total_bytes")}))


if __name__ == "__main__":
    main()
