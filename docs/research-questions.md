# What this archive is for

Written before the second capture, so the questions are honest about what the
data can and cannot reach.

## Is there a commercial need

Yes, and it is well funded — which cuts both ways. Mine status feeds commodity
traders, battery supply chains, critical-minerals policy and mining investors,
and several companies sell exactly that: **S&P Global Market Intelligence**
(Capital IQ Pro Metals & Mining, mine-level cost and asset analysis), Wood
Mackenzie, CRU, Benchmark Mineral Intelligence and Fastmarkets. Academic
snapshots exist too — one study tracked 289 nickel and cobalt projects
including 43 in care and maintenance.

So the *analysis* is not novel. The demand is proven by people paying for it.

## What is not already covered

The gap is narrow and specific, and it is worth stating precisely rather than
claiming more:

- The paid services are **subscription and proprietary**. Their history is not
  auditable and cannot be cited in public work.
- The academic snapshots are **one-off**. The 289-project study is a point in
  time, not a series.
- WA's own **"Operating Mines"** dataset is a filtered extract of this same
  MINEDEX, restricted to *operating* and *under development*. It excludes care
  and maintenance — the state this repository exists to watch — and it is
  overwritten in place, so it is not an archive either.
- The US **MSHA** dataset does carry mine status publicly, but for a different
  jurisdiction.

What does not appear to exist is a **free, public, machine-readable time
series of Western Australian mine stage transitions**. That is the whole claim.
It is a modest one.

## Is the source reliable

Measured, not assumed. Twelve samples of a real partition request, three
seconds apart: **all HTTP 200, median 1.13s, max 1.52s**, and one identical
payload size throughout — so byte-stable when nothing changes, which is what
makes change detection meaningful.

**But it is not stable in content.** Hours after the first capture the layer
was rebuilt from 10,004 rows to 48,414, with every `gid` reassigned and no
announcement. Treat schema and key stability as something to verify each run,
not to assume — that is exactly what the truncation gate is for, and it is why
partitions key on `site_code` rather than a surrogate id.

One caveat that shaped the registry: a separate probe returned in **29.2s**,
against the engine's 30s default. The tail is rare but real, so every endpoint
sets `timeout_seconds: 90`.

## The questions

### Answerable from this repository alone

| # | question | needs |
| --- | --- | --- |
| 1 | Which mines changed stage, in which direction, and when? | 2 captures |
| 2 | Mothball rate against restart rate, by commodity | 2+ |
| 3 | How long does a mine sit in care and maintenance before restarting — or before being written off as Shut? | many months |
| 4 | Do restarts arrive singly or in clusters? Clustering implies a price signal rather than site-specific decisions | 12+ |
| 5 | What share of *Proposed* mines ever reach *Under Development*, and how long does it take? | years |
| 6 | Does the registry move often enough to justify monthly capture? | 2 captures |

Question 6 is the one that validates the design, so it ships as a query from
day one. If most months show near-zero movement, widen the cadence; if a lot
moves every month, narrow it.

### Answerable only with something this fleet will not capture

**Lead and lag against commodity prices** — does WA nickel mothball before or
after the LME price breaks? This is the most valuable question here and the
archive cannot answer it alone. Prices are exactly the kind of perishable state
that is already commercially occupied, so the fleet's own screen says cite them
rather than capture them. Join to a published price series at analysis time.

### Blocked

- **Ownership consolidation** — see [ownership-is-blocked.md](ownership-is-blocked.md).
- **Joining a mine to the tenement beneath it.** MINEDEX carries no tenement
  id and the tenement layer carries no site code, so the only route is spatial.
  Site coordinates are requested into the raw archive for exactly this reason,
  but tenement geometry is not captured, so the join needs a one-off download.

### Not answerable from this source at all

- **Why** a mine was mothballed. MINEDEX has no reason code for a stage change.
  The dead-tenement layer has twelve reason categories on 100% of records;
  `site_stage` has none. This archive will show *when*, never *why*.
- Production volumes, employment, capital spend, reserves — none are in
  MINEDEX. Do not imply them.

## Can the crawl actually answer these

Verified against the first capture, through the shipped sqlite loader:

```
commodity | operating | idle | pipeline
NICKEL    |         8 |  117 |       81
GOLD      |       538 |  568 |      725
```

The transition and supply-response queries execute and correctly return no
rows on a single capture. `examples/whats_changed.py` was tested against a
synthetic second month and reported the flips it was given, so the listening
path works before the real second capture arrives.
