#!/usr/bin/env python3
"""Materialize the public SQLite and PNG figures from committed text artifacts.

The repository stores source-bound SVG/CSV/JSON; GitHub Actions renders the PNGs
and builds the public database so binary artifacts never need review in Git.
"""
from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
PUBLIC_SQLITE_SEED = ROOT / "analysis/non-bashar-public-seed.sqlite"
PUBLIC_SQLITE_OUT = ROOT / "analysis/non-bashar-public.sqlite"
FIGURE_INPUTS = {
    "fig1-acquisition-funnel": "analysis/fig1-funnel.svg",
    "fig2-asr-coverage": "analysis/fig2-asr-coverage.svg",
    "fig3-entity-heatmap": "analysis/fig3-entity-heatmap.svg",
    "fig4-tfidf-similarity": "analysis/fig4-tfidf-similarity.svg",
    "fig5-question-types": "analysis/fig5-question-types.svg",
    "fig6-network": "analysis/fig6-network.svg",
}


def build_public_sqlite() -> None:
    if not PUBLIC_SQLITE_SEED.exists():
        print(f"Seed SQLite absent; skipping public database materialization: {PUBLIC_SQLITE_SEED.name}")
        return
    script = ROOT / "analysis/build_public_sqlite.py"
    subprocess.run(["python3", str(script), str(PUBLIC_SQLITE_SEED), str(PUBLIC_SQLITE_OUT)],
                   check=True)
    print(f"Materialized {PUBLIC_SQLITE_OUT.name} from {PUBLIC_SQLITE_SEED.name}")


def render_pngs() -> None:
    for name, source_name in FIGURE_INPUTS.items():
        svg = ROOT / source_name
        png = svg.with_suffix(".png")
        subprocess.run(["rsvg-convert", "-w", "1600", "-o", str(png), str(svg)], check=True)
        print(f"Rendered {png.name} from {svg.name}")


def main() -> None:
    build_public_sqlite()
    render_pngs()


if __name__ == "__main__":
    main()
