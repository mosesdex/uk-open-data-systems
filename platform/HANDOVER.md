# Groundtruth — handover

## What this is

A working platform that resolves two missing joins in UK government data —
**place** (where) and **entity** (who) — and thirteen systems built on top of
them. Everything runs on data an anonymous client can retrieve: no account, no
API key, no subscription, anywhere.

## Where each part lives

| Part | Where |
|---|---|
| **The website** — what Groundtruth is, the thirteen systems, the research | published at <https://mosesdex.github.io/uk-open-data-systems/> |
| **The system** — public, admin and mobile interfaces reading real output | **localhost only** |
| **The engine** — fetchers, spines, systems, database | this directory, on your machine |

The operational interfaces are deliberately not published. The site explains the
platform; it does not run it. Running it locally means the operator holds the
data and can reproduce every number without depending on anyone else hosting it.
A CI check fails the website build if a system file or a link to one ever
reaches the published output.

## Running it

```bash
cd platform
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt

./.venv/bin/python -m groundtruth.cli run --fetch    # everything, ~15 min
./.venv/bin/python -m groundtruth.cli run            # rebuild from what is cached
./.venv/bin/python -m groundtruth.cli serve          # the system, on localhost
```

`serve` binds to `127.0.0.1` and nothing else, so an operator running this on a
laptop on a shared network does not expose a dashboard to it. That is asserted
by a test, and verified in practice: the loopback address answers, the machine's
LAN address refuses the connection.

A stage that fails is recorded and the run continues. A platform that stops at
the first unreachable publisher is useless for a corpus this size, and a test
asserts this by running every stage against an empty directory.

Individual commands: `sources`, `fetch`, `load`, `status`, `place`, `coverage`,
`catchment`, `watchman`, `bellwether`, `bulwark`, `ledger`, `baseline`,
`sentinel`, `highwater`, `plumbline`, `sightline`, `lastmile`, `junction`,
`compass`, `chains`, `publish`.

## What a full run produces

| Stage | Result |
|---|---|
| place spine | 1,749,109 postcodes, 318 districts |
| catchment | 26,605 of 27,167 schools resolved |
| bellwether | 57,867 care locations, 71.5% identified |
| bulwark | 141,468 flood defences |
| ledger | 39,325 contributions, **0 located** |
| baseline | 14,302 storm overflows |
| sentinel | 1,850 awards, 30.9% identified |
| watchman | register of 1,734 awards |
| highwater | 23,336 objections, 70.0% with an outcome |
| plumbline | 68,273 rows, 508 authorities |
| sightline | 180 water quality objections |
| lastmile | 1,423,443 premises, 7,211 new-build sales |
| compass | 163 authorities over 11 years |
| junction | **937 of 6,770** records served |

`publish` writes all of it to `../app/data/platform.json`, which the prototype
reads. Nothing in the prototype is typed in by hand.

## The rules the code enforces

1. **No credentials, ever.** `fetch.py` refuses to send an `Authorization`
   header, cookie or API key and ignores netrc and proxy credentials.
2. **A 200 is not data.** A source promising JSON that returns HTML is rejected,
   because the energy certificate register does exactly that.
3. **Coverage travels with every statistic.** A utilisation figure states the
   share of records it was computed over.
4. **Nothing merges silently.** Name matches are scored; ties are reported as
   ambiguous rather than resolved to whichever sorted first.
5. **Failures are recorded, not hidden.** Blocked sources stay in the registry.

## Things worth knowing before extending it

- **Code-Point Open is Great Britain, not the UK.** Zero Northern Ireland
  postcodes. Any coverage figure must say GB.
- **Publishers change formats without notice.** AIMS dates are `DD/MM/YYYY`;
  planning years switch from `2020-21` to `2021/22` mid-series; the
  "within maximum time" column was discontinued after 2020.
- **Published files carry their own subtotals.** The SEN file is a cube; summing
  across it counted the same children four times over.
- **A blocked endpoint is not a blocked dataset.** The CQC API needs a key while
  a fuller file is published openly; DNO `/records` is 403 while `/exports` is
  200.
- **Row-by-row inserts are the wrong tool.** Hand large CSVs to DuckDB directly:
  1.4m premises took minutes in Python and 0.8 seconds natively.

## Tests

185 offline, 2 network (`-m network`). They exist mainly to pin the mistakes
already made once: the EPC trap, the transposed dates, the cube double-count,
the wrong gigabit column, the sheet that appended itself to another dataset.

## Not built

- The property tier of the place spine (OS Open UPRN) is registered and loads,
  but was not run to completion here for disk reasons. `gt load` handles it.
- Watchman needs a backfill of historic award notices before it produces signal:
  at the current register size the expected hit rate is 0.2 per three weeks.
- Bid prices and single-bidder counts are not in UK data at all, so those
  collusion screens cannot be built by anyone.
