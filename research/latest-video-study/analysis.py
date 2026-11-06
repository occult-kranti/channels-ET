#!/usr/bin/env python3
"""Compare locally available video transcripts without publishing their text.

Input: a JSON list or {"records": [...]} with video_id, channel, title,
transcript_path, and transcript_source. Paths are relative to the manifest.
Produces descriptive TF-IDF, cosine and (where possible) exploratory NMF.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path


def transcript_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        obj = json.loads(raw)
        if not isinstance(obj, dict) or not isinstance(obj.get("text"), str):
            raise ValueError("JSON transcript must contain a string 'text'")
        return obj["text"]
    return raw


def analyse(manifest_path: Path, output: Path):
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        from sklearn.decomposition import NMF
        import numpy as np
        import sklearn
    except ImportError as exc:
        raise SystemExit("Install scikit-learn and numpy to run analysis: " + str(exc))
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = data.get("records") if isinstance(data, dict) else data
    if not isinstance(records, list):
        raise ValueError("Manifest must be a JSON list or an object containing records")
    output.mkdir(parents=True, exist_ok=True)
    included, texts, excluded, seen = [], [], [], set()
    for n, item in enumerate(records):
        if not isinstance(item, dict):
            excluded.append({"row": n + 1, "reason": "record is not an object"}); continue
        vid = str(item.get("video_id") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
            excluded.append({"row": n + 1, "video_id": vid, "reason": "invalid video_id"}); continue
        if vid in seen:
            excluded.append({"video_id": vid, "reason": "duplicate video_id"}); continue
        seen.add(vid)
        if not item.get("transcript_path"):
            excluded.append({"video_id": vid, "reason": "missing transcript_path"}); continue
        path = Path(item["transcript_path"])
        if not path.is_absolute(): path = manifest_path.parent / path
        try:
            text = transcript_text(path)
        except (OSError, ValueError, UnicodeError) as exc:
            excluded.append({"video_id": vid, "reason": f"cannot read transcript: {exc}"}); continue
        count = len(re.findall(r"\b\w+\b", text))
        if count < 30:
            excluded.append({"video_id": vid, "reason": "transcript has fewer than 30 tokens"}); continue
        included.append({"video_id": vid, "channel": str(item.get("channel") or "unknown"),
                         "title": str(item.get("title") or ""),
                         "transcript_source": str(item.get("transcript_source") or "unknown"),
                         "transcript_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "word_count": count})
        texts.append(text)
    result = {"manifest": str(manifest_path), "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
              "included": included, "excluded": excluded, "comparison_status": "insufficient_transcripts",
              "limitations": ["One video per channel cannot represent a channel's complete views.",
                  "Transcript errors, hosts, guests, ads, language and video length can confound similarities.",
                  "TF-IDF and NMF reflect word use, not verified claims, semantic equivalence or ET identity.",
                  "Automatic captions and speech-to-text should not be treated as verbatim without checking audio."],
              "methods": {"representation": "word unigram and bigram TF-IDF, English stop words, sublinear TF", "sklearn_version": sklearn.__version__}}
    if len(texts) >= 2:
        try:
            vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True,
                                          min_df=1, max_features=10000, token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z']+\b")
            matrix = vectorizer.fit_transform(texts)
        except ValueError as exc:
            result["comparison_status"] = "vocabulary_error"; result["error"] = str(exc)
        else:
            names = vectorizer.get_feature_names_out()
            sim = cosine_similarity(matrix)
            with (output / "similarity.csv").open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f); writer.writerow(["video_id"] + [x["video_id"] for x in included])
                for row, item in zip(sim, included): writer.writerow([item["video_id"]] + [round(float(x), 5) for x in row])
            result["top_terms"] = {}
            for idx, item in enumerate(included):
                row = matrix.getrow(idx)
                order = np.argsort(row.data)[::-1][:12]
                result["top_terms"][item["video_id"]] = [{"term": str(names[row.indices[j]]), "weight": round(float(row.data[j]), 5)} for j in order]
            result["pairs"] = sorted([{"video_a": included[i]["video_id"], "video_b": included[j]["video_id"],
                                       "cosine_similarity": round(float(sim[i, j]), 5)}
                                      for i in range(len(included)) for j in range(i + 1, len(included))],
                                     key=lambda x: -x["cosine_similarity"])
            result["comparison_status"] = "complete"
            # Small corpora do not support a reliable number of topics. This is descriptive only.
            k = min(3, len(texts) - 1, matrix.shape[1] - 1)
            if len(texts) >= 4 and k >= 2:
                model = NMF(n_components=k, init="nndsvda", random_state=42, max_iter=1000)
                weights = model.fit_transform(matrix)
                result["exploratory_nmf"] = {"n_components": k, "topics": [
                    {"topic": i + 1, "terms": [str(names[j]) for j in np.argsort(component)[::-1][:10]]}
                    for i, component in enumerate(model.components_)],
                    "document_weights": [{"video_id": item["video_id"], "weights": [round(float(x), 5) for x in row]}
                                         for item, row in zip(included, weights)]}
            try:
                import matplotlib
                matplotlib.use("Agg")
                import matplotlib.pyplot as plt
                size = min(16, max(6, len(included) * .55))
                fig, ax = plt.subplots(figsize=(size, size))
                im = ax.imshow(sim, cmap="viridis", vmin=0, vmax=1)
                ids = [x["video_id"] for x in included]
                ax.set_xticks(range(len(ids)), ids, rotation=90, fontsize=7)
                ax.set_yticks(range(len(ids)), ids, fontsize=7)
                ax.set_title("Transcript word-use similarity (TF-IDF cosine)")
                fig.colorbar(im, ax=ax, label="Cosine similarity")
                fig.tight_layout(); fig.savefig(output / "similarity.png", dpi=160); plt.close(fig)
                result["figure"] = {"file": "similarity.png", "caption": "Pairwise lexical similarity of included transcripts; scores do not measure agreement or establish claims."}
            except ImportError:
                result["figure_status"] = "matplotlib unavailable"
    (output / "analysis.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Included {len(included)} transcripts; excluded {len(excluded)}; status: {result['comparison_status']}")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path, help="JSON manifest; transcript paths resolve relative to this file")
    p.add_argument("--output", type=Path, required=True, help="Directory for derived, text-free outputs")
    args = p.parse_args()
    analyse(args.manifest, args.output)


if __name__ == "__main__": main()
