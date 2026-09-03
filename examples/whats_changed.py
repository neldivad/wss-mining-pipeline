#!/usr/bin/env python3
"""What moved since the previous capture — the point of running this monthly.

    python examples/whats_changed.py            # human readable
    python examples/whats_changed.py --markdown # for a GitHub job summary

Reads derived/observations/*.csv only. Stdlib. Prints nothing alarming when
nothing moved, which is itself the answer on most months.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def latest_by_date(metric: str) -> dict[str, dict[str, str]]:
    """{observed_at: {entity_id: value}}, deduplicated on newest captured_at."""
    seen: dict[tuple[str, str], tuple[str, str]] = {}
    for part in sorted((REPO / "derived" / "observations").glob("*.csv")):
        with part.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                if row["metric"] != metric:
                    continue
                key = (row["observed_at"], row["entity_id"])
                prev = seen.get(key)
                if prev is None or row["captured_at"] > prev[0]:
                    seen[key] = (row["captured_at"], row["value"])
    out: dict[str, dict[str, str]] = defaultdict(dict)
    for (observed_at, entity), (_, value) in seen.items():
        out[observed_at][entity] = value
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args()

    stages = latest_by_date("stage")
    commodity = latest_by_date("commodity")
    dates = sorted(stages)
    if len(dates) < 2:
        print(f"Only {len(dates)} capture so far — nothing to compare yet.")
        return 0

    prev, now = dates[-2], dates[-1]
    moves = [
        (e, stages[prev][e], v, commodity.get(now, {}).get(e, "?"))
        for e, v in stages[now].items()
        if e in stages[prev] and stages[prev][e] != v
    ]
    gone = set(stages[prev]) - set(stages[now])
    new = set(stages[now]) - set(stages[prev])

    head = f"{prev[:10]} → {now[:10]}"
    if args.markdown:
        print(f"### Mine stage changes, {head}\n")
        if not moves and not gone and not new:
            print("No site changed stage. The registry is unchanged.")
            return 0
        print(f"**{len(moves)} moved · {len(new)} added · {len(gone)} removed**\n")
        if moves:
            print("| site | commodity | was | now |")
            print("| --- | --- | --- | --- |")
            for e, was, now_v, com in sorted(moves, key=lambda m: (m[3], m[0]))[:60]:
                print(f"| `{e.split(':')[-1]}` | {com} | {was} | **{now_v}** |")
            if len(moves) > 60:
                print(f"\n…and {len(moves) - 60} more.")
    else:
        print(f"Mine stage changes, {head}")
        print(f"  {len(moves)} moved, {len(new)} added, {len(gone)} removed")
        for e, was, now_v, com in sorted(moves, key=lambda m: (m[3], m[0]))[:40]:
            print(f"  {e.split(':')[-1]:12} {com[:22]:24} {was} -> {now_v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
