#!/usr/bin/env python3
"""Collect the live headline metrics from each Heliosnet repo.

Reads each sibling repo's committed metrics artifact (produced by that repo's
own eval/benchmark command) and prints a single table. It reports only what is
actually on disk: if a repo has not had its eval run, that row is shown as
"not generated" rather than invented. This keeps the meta-repo's metrics table
honest and regenerable rather than hand-maintained.

Usage:
    python3 tools/collect_metrics.py [--root /path/to/workspace]

The default root is the parent directory of this repo, where the sibling repos
live (constellation-vision, groundstation-train, ...).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# repo -> (artifact path under the repo, regen command, extractor)
SOURCES = {
    "groundstation-train": (
        "artifacts/metrics.json",
        "make eval-refs",
        lambda d: f"gate-compliance {d.get('gate_compliance')} (oracle calibration); model headline from a GPU run",
    ),
    "constellation-vision": (
        "artifacts/metrics.json",
        "make eval",
        lambda d: f"mean IoU {round(d['mean_iou'], 4)} on held-out frames",
    ),
    "constellation-stream": (
        "artifacts/bench.json",
        "make bench-big",
        lambda d: (
            f"{round(d['throughput']['throughput_rows_per_s']):,} rec/s, "
            f"p99 {round(d['query_latency']['p99_ms'], 2)} ms "
            f"at {d['throughput']['rows']:,} rows"
        ),
    ),
    "groundstation-rag": (
        "artifacts/metrics.json",
        "make eval",
        lambda d: (
            f"citation-acc {d['citation_accuracy']}, recall@k {d['recall_at_k']}, "
            f"MRR {d['mrr']}, ctx-rel {d['context_relevance']}"
        ),
    ),
}


def collect(root: Path) -> list[tuple[str, str, str]]:
    rows = []
    for repo, (rel, cmd, extract) in SOURCES.items():
        path = root / repo / rel
        if path.exists():
            try:
                data = json.loads(path.read_text())
                summary = extract(data)
            except Exception as exc:  # malformed artifact: say so, do not invent
                summary = f"unreadable artifact ({exc})"
        else:
            summary = "not generated (run the regen command)"
        rows.append((repo, cmd, summary))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = ap.parse_args()
    rows = collect(args.root)
    width = max(len(r[0]) for r in rows)
    print(f"Heliosnet live metrics (root: {args.root})\n")
    for repo, cmd, summary in rows:
        print(f"  {repo.ljust(width)}  | {summary}")
        print(f"  {' '.ljust(width)}  | regen: {cmd}\n")


if __name__ == "__main__":
    main()
