# The Bashar Index

An independent research site that indexes the public channeling sessions of **Bashar** (channeled by Darryl Anka): a 684-session catalogue (1984–2027), 75 structured digests of public recordings, a topic analysis with clustering, a glossary, a timeline, 56 redrawn concept diagrams, podcast appearances, and a skeptics section.

**Live site:** served from this repository via GitHub Pages (`index.html` at the root).

## What is here

| Path | Contents |
|---|---|
| `index.html` | The whole site — one self-contained page, no external requests. |
| `data/` | The research data package: digests, catalogue, topic analysis, diagrams (JSON + SVG), glossary, timeline, manifests. See `data/README.md`. |
| `src/` | The Python that builds the page (`build.py`, `css.py`, `js.py`, `svglib.py`, `diagrams_a.py`, `diagrams_b.py`), the analysis pipeline (`topics.py`) and the digest schema (`DIGEST_SPEC.md`). |

## Rebuilding

```
pip install scikit-learn numpy
python3 src/topics.py      # regenerates the analysis from data/digests
python3 src/build.py       # regenerates index.html
```

(`build.py` expects the research files at the paths used during the original build; adjust the constants at the top of the file to point at `data/`.)

## Method and limits

- Digests are AI-generated from auto-transcripts of public YouTube recordings. They are summaries, not transcripts; quotes are limited to 30 words and link back to the original recording.
- Diagrams are original SVG redrawings of concepts described in sessions, each with a confidence grade. No handout artwork is reproduced.
- Upload dates on re-upload channels are unreliable; the site flags these (`~`) and excludes them from year-based views.
- All claims are reported as claims, not endorsed. The site includes critical and skeptical coverage.

## Not affiliated

This project is not affiliated with, endorsed by, or connected to Bashar Communications, Inc. or Darryl Anka. Bashar® session recordings, transcripts and handouts are © Darryl Anka / Bashar Communications, Inc.; none are reproduced here. The code and the derived data in this repository are released under the MIT License (see `LICENSE`).
