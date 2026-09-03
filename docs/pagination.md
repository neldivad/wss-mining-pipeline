# Why the endpoints look like that

Every source here is one ArcGIS feature service, and ArcGIS caps a response at
`maxRecordCount` — 10,000 for both WA layers. Ask for 30,463 tenements and the
server returns 5,000 or 10,000 of them, with **HTTP 200**. Nothing about that
response looks wrong.

That is the one failure this repository cannot tolerate: gates pass, the
manifest looks healthy, and four fifths of the state quietly vanishes.

## The shape used here

Each source declares several endpoints, one per **`site_code` range**:

```
where=site_code<'S0005000'
where=site_code>='S0005000' AND site_code<'S0010000'
...
where=site_code>='S0245000'
```

Twelve partitions holding roughly 2,000–5,000 rows each against a 10,000 cap,
so about 2× headroom.

### Why not `gid`

The first version partitioned on `gid`, which looked ideal: dense, sequential,
10,004 sites across ids 11226143–11236146. It survived one day.

On 3 September 2026 the layer was refreshed from **10,004 rows to 48,414** and
**every `gid` was reassigned** — site `S0000013` moved from the low range to
11273060. The open-ended top partition suddenly held 41,657 rows, the server
truncated it at 10,000, and the gate quarantined the source.

`gid` is a surrogate key that does not survive a rebuild. `site_code` is the
business identity and does, which is the only property a partition key needs.

Two properties matter:

- **The first partition is open at the bottom and the last is open at the top.**
  New records get new high `gid`s, so they always land in the final partition.
  Nothing can be issued into a gap.
- **Every partition is complete**, so the truncation guard below can apply to
  all of them at once.

## The guard

```yaml
must_not_contain: ['exceededTransferLimit":true', "Access Denied"]
```

A truncated ArcGIS response contains that literal; a complete one omits the key
entirely. Because no partition is *meant* to be truncated, this gate is a
straightforward assertion of completeness.

**When it fires, the data has outgrown its ranges.** That is not a bug to work
around — it is the design working. Re-split:

1. `.../query?where=1=1&outStatistics=[{"statisticType":"max","onStatisticField":"gid","outStatisticFieldName":"hi"}]&f=json`
2. Pick new cuts so each partition sits near 3,000–4,000 rows.
3. Edit the registry, `wss validate`, `wss doctor <source_id>`.

Offsets (`resultOffset`) were rejected for this: pages 1..n-1 are *legitimately*
truncated, so a source-level gate cannot tell a normal page from a lost one,
and gates in this engine are per source rather than per endpoint.

## What this does not solve — a note for whoever forks this

Brazil's ANM registry (`geo.anm.gov.br`, SIGMINE `dados_anm` layer 0) is the
obvious next jurisdiction and it **cannot be expressed this way**. It holds
269,427 active mining processes with a `FASE` field that is a genuine funnel —
*requerimento de pesquisa → autorização de pesquisa → requerimento de lavra →
concessão de lavra* — plus `SUBS`, the commodity per process, which the WA
tenement layers do not carry. It is active-only: when a process dies it simply
disappears, so both the transitions **and** the deaths are unrecoverable. On
the filing rule it is a stronger capture target than WA, which at least keeps
its graveyard.

The obstacles are mechanical:

- `resultRecordCount` is rejected outright — *"Pagination is not supported."*
- `ANO` comparisons return error 400, so no date partition.
- `UF` (state) partitions do not go fine enough: Minas Gerais alone holds
  51,146 processes, and its largest single `FASE` is 24,601.
- The route that does work is two-phase: `returnIdsOnly=true` per state
  (verified — MG returned all 51,146 ids), then fetch by `objectIds` in
  batches of 1,000 (verified — 1,000 of 1,000 returned). About 27 + 270
  requests for a full pass.

Those batch URLs are **computed from the previous response**, and a registry
endpoint is a static string. So Brazil needs an engine capability that does not
exist yet: a declared pagination strategy, something like

```yaml
paginate:
  strategy: arcgis_ids     # or: offset
  partition_field: UF
  batch_size: 1000
```

with truncation treated as a hard failure rather than a gate. If you are
picking this up: that feature is the unlock, and Brazil is the reason to build
it. Until then, this repository covers Western Australia only, and says so.
