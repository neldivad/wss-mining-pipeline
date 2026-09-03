# What this repository deliberately does not capture

The rule: **capture perishable state, cite everything else.** A source that
keeps its own history needs no archive, and duplicating it would be noise. Each
of the following was screened and rejected on that basis, not overlooked.

## WA dead tenements — `DMIRS-026`

**422,194 records, deaths back to 1883, a reason on 100% of them across 12
categories.** Surrendered 48.7%, Expired 15.0%, Withdrawn 13.7%, Forfeited
10.9%. This is a better graveyard than almost any jurisdiction publishes and it
is complete — so survival curves, cohort analysis and the shift from forfeiture
to voluntary surrender can be rebuilt from one download at any time.

Three traps if you use it:

- **One row per holder, not per tenement.** 422,194 rows are 376,733 tenements.
- **`grantdate = 2999-12-31` is a sentinel for "never granted."** 55,444 records
  are refused, withdrawn or lapsed *applications*. Counting them as dead
  tenements understates survival — 17.3% instead of the correct 21.0%.
- **Abolished instruments show 0% survival by construction.** Gold Mining Lease,
  Prospecting Area and Mineral Claim account for 234,042 deaths. The Mining Act
  1978 retired them; they did not fail.

## WA exploration reports — WAMEX `DMIRS-033`

118,705 reports with a target commodity and a date. Historical and complete,
but released on roughly a **five-year embargo** — 2,831 reports for 2019
against 79 for 2025. Any recent time series built from it is an artefact of the
embargo, not of activity. Usable only across fully-released windows.

## British Columbia

BC publishes `MTA_ACQUIRED_TENURE_SVW` **and**
`MTA_ACQUIRED_TENURE_HISTORY_SP`, which carries a `REVISION_NUMBER`. It
versions its own tenure changes, which is exactly what a `wss-*` repo exists to
do for publishers who don't. Cite BC; do not mirror it.

## What is left, and why it is here

| kept | why |
| --- | --- |
| MINEDEX `site_stage` | overwritten in place; no `timeInfo`, no historic-moment support, no dated snapshots. The date a mine was mothballed exists nowhere. |
| Live tenement `holder` | ownership of ground is overwritten, so consolidation is invisible afterwards. |

Static properties — titles, coordinates, tenement type, survey status — are not
emitted into the observation table either. They cannot change in a way worth a
time series. The raw archive keeps every field the endpoints request — including site
coordinates, which exist only to make a later spatial join to tenements
possible — so a new parser version can surface them without re-fetching.

See also [pagination.md](pagination.md) for why Brazil is not here yet.
