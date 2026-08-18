# Groundtruth platform

The engine behind the thirteen systems. Resolves two missing joins in UK
government data: **place** (where) and **entity** (who).

## Setup

```bash
cd platform
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
```

## Use

```bash
./.venv/bin/python -m groundtruth.cli sources            # the registry
./.venv/bin/python -m groundtruth.cli fetch --role place_spine
./.venv/bin/python -m groundtruth.cli fetch --all --max-bytes 20000000
./.venv/bin/python -m groundtruth.cli status             # last outcome per source
```

`--max-bytes` truncates each download, which is how to smoke-test without
pulling 1.3 GB of Ordnance Survey products.

## M1 — ingest framework

**The no-registration rule is enforced in code, not documented.** `fetch.py`
refuses to send an `Authorization` header, a cookie, an API key or a bearer
token, and ignores netrc and proxy credentials. Attempting to send any of them
raises `CredentialLeak`. This matters because the platform's whole proposition
is that a government body can reproduce every number without asking permission;
that is only true if nothing here can quietly acquire credentials.

### The trap case

A source that answers `HTTP 200` is not necessarily serving data. The energy
certificate register answers 200, redirects to a different host, and serves an
ordinary GOV.UK landing page with a cookie banner.

The first version of the check looked for sign-in wording and **passed it
straight through**. The rule is now simpler and decisive: *a source that
promises JSON and returns HTML is not serving data*, whatever the HTML says.
Admissibility is decided on content type; sign-in wording only sharpens the
error message. `tests/test_fetch.py` locks this in as a regression test.

### Design notes

- **Failures are recorded, not raised.** A source that cannot be reached is a
  fact worth storing, because coverage figures are only trustworthy if you can
  see what was missed. `bronze.fetch_log` is append-only.
- **Blocked sources stay in the registry.** A platform that silently drops
  unreachable sources cannot be audited.
- **Content is hashed while streaming**, so a publisher replacing a file without
  a changelog shows up as changed content. The research found this happens.
- **Versioned filenames are resolved at fetch time.** Ordnance Survey splits
  Linked Identifiers into one file per identifier pair, stamped with the month.
  `resolve.py` looks up the current release rather than hardcoding a name that
  breaks in four weeks.
- **Schema changes migrate.** `CREATE TABLE IF NOT EXISTS` will not add a column
  to an existing database, so `store.migrate()` applies them explicitly.

## Layout

```
groundtruth/
  sources.py   the registry: url, licence, role, cadence, expected content
  fetch.py     anonymous fetching, credential guard, payload check
  resolve.py   late-binding URLs for versioned publisher filenames
  store.py     DuckDB: bronze / silver / gold, fetch log, migrations
  cli.py       gt sources | fetch | status
tests/         24 offline tests, 2 network tests (-m network)
```

`data/` holds the database and downloads. It is not committed.

## Status

| Milestone | State |
|---|---|
| M1 ingest framework | **done** — 11 admissible sources, 2 blocked and visible |
| M2 place spine | next |
| M3 entity spine | |
| M4 Catchment end to end | |
