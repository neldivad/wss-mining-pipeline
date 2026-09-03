#!/usr/bin/env python3
"""Render charts from derived/observations/*.csv as SVG.

    python examples/visualize.py

Written to examples/charts/:

  fleet-state.svg        what is running and what is idle, by commodity
  pipeline-depth.svg     which commodities are proposing rather than producing
  stage-transitions.svg  which mines moved, and where — the point of the archive
  restart-clock.svg      how long a mothballed mine waits before it restarts

This repository is longitudinal. The last two cannot be drawn from a single
capture, so they render as placeholders that say what they need and how far
off it is. That is deliberate: a chart that quietly invents a trend from one
observation is worse than no chart.

Stdlib only. Deterministic: the same observations produce the same bytes.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "examples" / "charts"

SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, BASE = "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'
STAGES = ("Operating", "Under Development", "Proposed",
          "Care and Maintenance", "Shut", "Undeveloped")


def T(x, y, s, size=12, fill=INK, anchor="start", weight="normal", tab=False):
    st = "font-variant-numeric: tabular-nums;" if tab else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family=\'{FONT}\' font-size="{size}" '
            f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}" '
            f'style="{st}">{escape(str(s))}</text>')


def R(x, y, w, h, fill):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,0):.1f}" height="{max(h,0):.1f}" fill="{fill}"/>'


def L(x1, y1, x2, y2, c=GRID, w=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{c}" stroke-width="{w}"{d}/>'


def head(W, H, title, sub, note=""):
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         R(0, 0, W, H, SURFACE), T(38, 46, title, 20, INK, weight="600"),
         T(38, 70, sub, 13, INK2)]
    if note:
        p.append(T(38, 90, note, 11.5, MUTED))
    return p


def save(parts, name):
    parts.append("</svg>")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text("\n".join(parts), encoding="utf-8")
    print(f"  wrote examples/charts/{name}")


def load():
    """{observed_at: {entity: {metric: value}}}, deduplicated on captured_at."""
    seen = {}
    for part in sorted((REPO / "derived" / "observations").glob("*.csv")):
        with part.open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                k = (r["observed_at"], r["entity_id"], r["metric"])
                if k not in seen or r["captured_at"] > seen[k][0]:
                    seen[k] = (r["captured_at"], r["value"])
    out = defaultdict(lambda: defaultdict(dict))
    for (obs, ent, metric), (_, val) in seen.items():
        out[obs][ent][metric] = val
    return out


def mines(snapshot):
    return {e: a for e, a in snapshot.items() if a.get("site_type") == "Mine"}


def by_commodity(snap):
    g = defaultdict(lambda: defaultdict(int))
    for a in mines(snap).values():
        g[a.get("commodity", "?")][a.get("stage", "?")] += 1
    return g


def placeholder(name, title, sub, needs, have, shows, last):
    """A chart that has not got enough captures yet, and says so."""
    W, H = 900, 400
    p = head(W, H, title, sub)
    x0, y0, w, h = 60, 120, W - 120, 210
    p.append(R(x0, y0, w, h, "#f4f3ef"))
    for i in range(1, 4):
        p.append(L(x0, y0 + h * i / 4, x0 + w, y0 + h * i / 4, "#e7e5df"))
    cx = x0 + w / 2
    p.append(T(cx, y0 + 78, f"{have} of {needs} captures", 26, INK, anchor="middle", weight="600", tab=True))
    p.append(T(cx, y0 + 106, shows, 13.5, INK2, anchor="middle"))
    # projected from the latest capture, not from today, so output stays
    # byte-identical for a given set of observations
    months = max(needs - have, 0)
    y, m = int(last[:4]), int(last[5:7]) + months
    y, m = y + (m - 1) // 12, (m - 1) % 12 + 1
    when = "ready now — re-run this script" if months == 0 else \
        f"first renderable around {date(y, m, 1).strftime('%B %Y')} at monthly capture"
    p.append(T(cx, y0 + 134, when, 12, ORANGE, anchor="middle"))
    p.append(T(38, H - 30, "This repository is longitudinal. Drawing a trend from one observation "
                           "would be worse than drawing nothing.", 11.5, MUTED))
    save(p, name)


def chart_fleet_state(snap, as_of):
    g = by_commodity(snap)
    rows = []
    for k, c in g.items():
        op, cm = c["Operating"], c["Care and Maintenance"]
        pipe = c["Proposed"] + c["Under Development"]
        if op + cm >= 4:
            rows.append((k, op, cm, pipe))
    rows.sort(key=lambda r: -r[2] / (r[1] + r[2]))
    W, H = 900, 150 + 26 * len(rows) + 58
    p = head(W, H, "What is running, and what is switched off",
             f"Western Australian mine fleet by commodity, {as_of}. "
             "Bar is the idled share of the developed fleet.",
             "Care and maintenance restarts in months. Proposed capacity arrives in years.")
    x0, bw = 250, 300
    p += [T(x0, 124, "IDLED SHARE", 10, MUTED, weight="600"),
          T(x0 + bw + 86, 124, "OPERATING", 10, BLUE, anchor="end", weight="600"),
          T(x0 + bw + 156, 124, "IDLE", 10, ORANGE, anchor="end", weight="600"),
          T(x0 + bw + 246, 124, "PIPELINE", 10, AQUA, anchor="end", weight="600")]
    y = 132
    for pct in (0, 50, 100):
        p.append(L(x0 + bw * pct / 100, y, x0 + bw * pct / 100, y + 26 * len(rows) + 4, GRID))
    for k, op, cm, pipe in rows:
        idle = cm / (op + cm) * 100
        p.append(T(x0 - 14, y + 16, k.title()[:30], 12.5, INK, anchor="end"))
        p.append(R(x0, y + 5, bw * idle / 100, 15, ORANGE if idle >= 50 else BLUE))
        p.append(T(x0 + bw * idle / 100 + 7, y + 16.5, f"{idle:.0f}%", 11.5,
                   ORANGE if idle >= 50 else INK2, weight="600", tab=True))
        p.append(T(x0 + bw + 86, y + 16.5, f"{op:,}", 12, INK2, anchor="end", tab=True))
        p.append(T(x0 + bw + 156, y + 16.5, f"{cm:,}", 12, INK2, anchor="end", tab=True))
        p.append(T(x0 + bw + 246, y + 16.5, f"{pipe:,}" if pipe else "—", 12,
                   AQUA if pipe >= 5 else INK2, anchor="end", tab=True))
        y += 26
    p.append(T(38, y + 34, "Every number here is a stock. When it moved, and how fast, is what "
                           "repeated capture adds.", 11.5, MUTED))
    save(p, "fleet-state.svg")


def chart_pipeline_depth(snap, as_of):
    g = by_commodity(snap)
    rows = []
    for k, c in g.items():
        pipe = c["Proposed"] + c["Under Development"]
        built = c["Operating"] + c["Care and Maintenance"] + c["Shut"]
        if pipe >= 3:
            rows.append((k, pipe, built, c["Shut"]))
    rows.sort(key=lambda r: -(r[1] / max(r[2], 1)))
    W, H = 900, 150 + 26 * len(rows) + 78
    p = head(W, H, "Which commodities are proposing rather than producing",
             f"Proposed and under-development mines against everything ever developed, {as_of}.",
             "A high ratio with no shut mines is a commodity arriving; with many shut mines it is one trying to return.")
    x0, bw = 250, 330
    mx = max(r[1] / max(r[2], 1) for r in rows)
    p += [T(x0, 124, "PIPELINE PER DEVELOPED MINE", 10, MUTED, weight="600"),
          T(x0 + bw + 96, 124, "PIPELINE", 10, AQUA, anchor="end", weight="600"),
          T(x0 + bw + 186, 124, "EVER BUILT", 10, INK2, anchor="end", weight="600"),
          T(x0 + bw + 266, 124, "SHUT", 10, MUTED, anchor="end", weight="600")]
    y = 132
    for k, pipe, built, shut in rows:
        ratio = pipe / max(built, 1)
        p.append(T(x0 - 14, y + 16, k.title()[:30], 12.5, INK, anchor="end"))
        p.append(R(x0, y + 5, bw * ratio / mx, 15, AQUA if shut <= 2 else BLUE))
        p.append(T(x0 + bw * ratio / mx + 7, y + 16.5, f"{ratio:.1f}×", 11.5, INK2, weight="600", tab=True))
        for dx, v in ((96, pipe), (186, built), (266, shut)):
            p.append(T(x0 + bw + dx, y + 16.5, f"{v:,}", 12, INK2, anchor="end", tab=True))
        y += 26
    p.append(T(38, y + 34, "Green marks commodities with two or fewer shut mines — pre-production, "
                           "not recovering.", 11.5, MUTED))
    p.append(T(38, y + 54, "Whether these proposals convert is question 5, and it needs years of "
                           "capture to answer.", 11.5, MUTED))
    save(p, "pipeline-depth.svg")


def main():
    data = load()
    dates = sorted(data)
    if not dates:
        print("  no observations yet — run wss capture && wss derive")
        return
    snap, as_of = data[dates[-1]], dates[-1][:10]
    chart_fleet_state(snap, as_of)
    chart_pipeline_depth(snap, as_of)
    placeholder("stage-transitions.svg",
                "Which mines moved, and where",
                "Every stage change between consecutive captures, by commodity and direction.",
                needs=2, have=len(dates), last=as_of,
                shows="Mothballs, restarts and permanent write-offs — the fact the registry overwrites")
    placeholder("restart-clock.svg",
                "How long a mothballed mine waits",
                "Months between entering care and maintenance and restarting — or being written off.",
                needs=12, have=len(dates), last=as_of,
                shows="Distribution of dwell time, and whether restarts cluster on a price signal")


if __name__ == "__main__":
    main()
