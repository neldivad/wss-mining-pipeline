# Why ownership is not captured

`wa.tenements.live` is written, validated and **paused**. It is blocked on a
policy decision, not a technical one, and this file exists so the decision is
recorded rather than quietly forgotten.

## What it would answer

Holder identity is the whole point of the tenement layer. Ownership is
overwritten in place, so consolidation is invisible after the fact:

- Is ground concentrating or dispersing? (top-10 share of hectares over time)
- Which companies are accumulating, which are shedding?
- Do holders shed ground before or after mothballing their mines?
- At first capture, three of the ten largest holders were nickel companies
  while nickel ran one operating mine — are they still holding a year later?

None of that is answerable from a single download, and none of it is
recoverable later.

## Why it is blocked

Two engine contracts collide on this source.

1. **Capture stores raw bytes verbatim.** Nothing is parsed, filtered or
   redacted at capture time — that is what makes the archive trustworthy.
2. **`personal_data: present` is rejected outright.** `wss validate` fails the
   registry; the fleet declares that it does not collect personal data.

At first capture, **1,446 of 3,604 holders (40%) were named individuals** in
`SURNAME, FORENAME` form, holding 4,280 tenements — 14% of the register.
Western Australia publishes them because a tenement register is a public
record. That makes republishing lawful, but it does not make the fleet's
`personal_data: none` declaration true.

Pseudonymising in the parser does not resolve it. The parser (`_holder` in
`parsers/mining_v1.py`, kept for this reason) reduces natural persons to a
stable digest so holdings can still be followed across captures, and that
fixes the *derived* table. The raw archive still mirrors the register as
served, because contract 1 says it must.

## The options, for whoever decides

| option | ownership analysis | `personal_data: none` stays true |
| --- | --- | --- |
| leave paused **(current)** | lost | yes |
| request `holder1`, pseudonymise in parser | full | **no** — raw holds the names |
| filter to corporate holders server-side | biased: drops 14% of tenements and distorts area totals | yes |
| relax the engine rule to allow `present` with stated obligations | full | the rule changes instead |

The last row is a change to the fleet's architecture, not to this repository,
which is why it is not taken here unilaterally.

## Note on the history

An earlier local commit of this repository captured the tenement layer with
holder names in `raw/`. It was never pushed, and the git history was
reinitialised before publication, so no commit in this repository has ever
contained them.
