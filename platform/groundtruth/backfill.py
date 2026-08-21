"""Fetching everything, not just a sample.

Several sources were originally taken in part: one BDUK region of ten, one EDM
year of six, three weeks of procurement notices, and four Ordnance Survey
products capped mid-download when disk was short. Partial inputs produce
findings that look national and are not, so this module completes them.

Three shapes of incompleteness, handled differently:

  * **Split by region or year.** BDUK and EDM publish one archive per slice.
    Discover the slices from the publisher's own index, then fetch each.
  * **Paged behind a cursor.** Contracts Finder pages on `publishedTo`, the
    Gazette on a page number. Walk backwards until the publisher stops giving
    new records or a depth limit is reached.
  * **One large file.** Companies House and the OS products are single
    downloads that were previously truncated; they just need fetching whole.

Everything is written into the same bronze directory the loaders already read,
and every fetch is recorded, so a source stops being "in use with no
provenance" once it has been through here.
"""
from __future__ import annotations

import json
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

import requests

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
GOVUK_CONTENT = "https://www.gov.uk/api/content"
CKAN = "https://ckan.publishing.service.gov.uk/api/3/action/package_search"


@dataclass
class Result:
    name: str
    ok: bool
    detail: str
    bytes: int = 0


def _session() -> requests.Session:
    s = requests.Session()
    s.trust_env = False           # never pick up proxy or netrc credentials
    s.headers.update(UA)
    return s


def _download(s: requests.Session, url: str, dest: Path, timeout: int = 3600) -> int:
    """Stream to a temporary file, then move into place.

    Writing directly to the destination is how a half-finished download ends up
    looking like a complete one -- which is exactly what produced the four
    truncated Ordnance Survey archives.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    total = 0
    with s.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                if chunk:
                    fh.write(chunk)
                    total += len(chunk)
    tmp.replace(dest)
    return total


# ---------------------------------------------------------------- BDUK
def bduk_regions(s: requests.Session) -> list[tuple[str, str]]:
    url = (f"{GOVUK_CONTENT}/government/publications/"
           "january-2026-omr-and-premises-in-bduk-plans-england-and-wales")
    d = s.get(url, timeout=120).json()
    atts = (d.get("details") or {}).get("attachments") or []
    return [(a["url"].split("/")[-1], a["url"])
            for a in atts if a.get("url", "").endswith(".zip")]


def fetch_bduk(bronze: Path, s: requests.Session | None = None) -> list[Result]:
    s = s or _session()
    out = []
    for name, url in bduk_regions(s):
        region = name.replace("202601_", "").replace(".zip", "")
        dest = bronze / f"bduk_{region}.zip"
        if dest.exists() and dest.stat().st_size > 1_000_000:
            out.append(Result(dest.name, True, "already complete", dest.stat().st_size))
            continue
        try:
            n = _download(s, url, dest)
            out.append(Result(dest.name, True, "fetched", n))
        except Exception as exc:                                  # noqa: BLE001
            out.append(Result(dest.name, False, f"{type(exc).__name__}: {exc}"[:120]))
        time.sleep(0.5)
    return out


# ---------------------------------------------------------------- EDM
def edm_years(s: requests.Session) -> list[tuple[str, str]]:
    r = s.get(CKAN, params={"q": "Event Duration Monitoring Storm Overflows Annual Returns",
                            "rows": 1}, timeout=120).json()
    res = r["result"]["results"][0]["resources"]
    out = []
    for x in res:
        if x.get("format") != "ZIP":
            continue
        name = x.get("name", "")
        if "_Storm_Overflow_Annual_Return" in name:
            year = name.split("_")[1]
            out.append((year, x["url"]))
    return sorted(out)


def fetch_edm(bronze: Path, s: requests.Session | None = None) -> list[Result]:
    s = s or _session()
    out = []
    for year, url in edm_years(s):
        dest = bronze / f"edm_annual_{year}.zip"
        if dest.exists() and dest.stat().st_size > 500_000:
            out.append(Result(dest.name, True, "already complete", dest.stat().st_size))
            continue
        try:
            n = _download(s, url, dest)
            out.append(Result(dest.name, True, f"{year} return", n))
        except Exception as exc:                                  # noqa: BLE001
            out.append(Result(dest.name, False, f"{type(exc).__name__}: {exc}"[:120]))
        time.sleep(0.5)
    return out


# ---------------------------------------------------------------- Companies House
def fetch_companies_house(bronze: Path, s: requests.Session | None = None) -> Result:
    """The single-file basic company data product, ~493 MB."""
    s = s or _session()
    import re
    idx = s.get("https://download.companieshouse.gov.uk/en_output.html", timeout=120)
    links = re.findall(r'href="([^"]*BasicCompanyDataAsOneFile[^"]*\.zip)"', idx.text)
    if not links:
        return Result("companies_house_bulk.zip", False, "no single-file product on the index")
    url = "https://download.companieshouse.gov.uk/" + links[0].lstrip("/")
    dest = bronze / "companies_house_bulk.zip"
    if dest.exists() and dest.stat().st_size > 100_000_000:
        return Result(dest.name, True, "already complete", dest.stat().st_size)
    try:
        n = _download(s, url, dest, timeout=7200)
        return Result(dest.name, True, links[0], n)
    except Exception as exc:                                      # noqa: BLE001
        return Result(dest.name, False, f"{type(exc).__name__}: {exc}"[:120])


# ---------------------------------------------------------------- WFS paging
def fetch_aims(bronze: Path, s: requests.Session | None = None) -> Result:
    """All flood defences, not the first page.

    The registry URL is a WFS GetFeature call, which returns whatever `count`
    asks for and nothing more. Fetching it directly yields 5,000 of 141,468
    assets and looks like a complete file. This walks startIndex to the end.
    """
    s = s or _session()
    BASE = ("https://environment.data.gov.uk/spatialdata/"
            "spatial-flood-defences-including-standardised-attributes/wfs")
    TYPE = ("dataset-8e5be50f-d465-11e4-ba9a-f0def148f590:"
            "Spatial_Flood_Defences_Including_Standardised_Attributes")
    FIELDS = ("asset_id,asset_sub_type,primary_purpose,protection_type,asset_maintainer,"
              "asset_operator,asset_owner,current_condition,target_condition,"
              "last_inspection_date,next_inspection_date,local_authority,"
              "water_management_area,water_course_name,asset_length")
    dest = bronze / "ea_aims_defences.json"
    feats, start, PAGE = [], 0, 5000
    while True:
        r = s.get(BASE, params={"service": "WFS", "version": "2.0.0",
                                "request": "GetFeature", "typeNames": TYPE,
                                "count": PAGE, "startIndex": start,
                                "outputFormat": "application/json",
                                "propertyName": FIELDS}, timeout=600)
        if r.status_code != 200:
            break
        got = r.json().get("features", [])
        if not got:
            break
        feats += [f["properties"] for f in got]
        start += len(got)
        if len(got) < PAGE:
            break
        time.sleep(0.2)
    dest.write_text(json.dumps(feats))
    return Result(dest.name, len(feats) > 100_000, f"{len(feats):,} assets",
                  dest.stat().st_size)


# ---------------------------------------------------------------- gov.uk attachments
def fetch_ps2(bronze: Path, s: requests.Session | None = None) -> Result:
    """The PS2 table itself, not the page that lists it.

    The statistics release carries only a PDF; the data lives in the live-tables
    collection, whose attachment list is reachable through the content API. The
    registry URL is that index, so fetching it directly stores the index.
    """
    s = s or _session()
    d = s.get(f"{GOVUK_CONTENT}/government/statistical-data-sets/"
              "live-tables-on-planning-application-statistics", timeout=120).json()
    atts = (d.get("details") or {}).get("attachments") or []
    hit = [a for a in atts if "PS2_data_-_open_data_table" in (a.get("url") or "")]
    if not hit:
        return Result("planning_ps2.csv", False, "PS2 table not on the live-tables page")
    dest = bronze / "planning_ps2.csv"
    n = _download(s, hit[0]["url"], dest, timeout=900)
    return Result(dest.name, n > 1_000_000, hit[0]["url"].split("/")[-1], n)


# ---------------------------------------------------------------- rainfall totals
def fetch_rainfall(bronze: Path, year: int = 2025,
                          s: requests.Session | None = None,
                          max_stations: int = 400) -> Result:
    """Annual rainfall total per station, for weather-normalising spills.

    The flood-monitoring feed only serves a rolling window; the hydrology API
    serves daily totals with date bounds, which sum to an annual figure. Each
    station carries coordinates and an EA area, so spills can later be adjusted
    against the rainfall that actually fell near them rather than nationally.
    """
    import csv as _csv, io as _io, json as _json, time as _time
    s = s or _session()
    st = s.get("https://environment.data.gov.uk/hydrology/id/stations"
               "?observedProperty=rainfall&_limit=5000", timeout=120).json().get("items", [])
    out = []
    for i, station in enumerate(st[:max_stations]):
        notation = station.get("notation")
        if not notation:
            continue
        meas = f"{notation}-rainfall-t-86400-mm-qualified"
        url = (f"https://environment.data.gov.uk/hydrology/id/measures/{meas}/readings.csv"
               f"?mineq-date={year}-01-01&maxeq-date={year}-12-31")
        try:
            r = s.get(url, timeout=60)
            if r.status_code != 200 or "csv" not in r.headers.get("Content-Type", ""):
                continue
            rows = list(_csv.DictReader(_io.StringIO(r.text)))
            vals = [float(x["value"]) for x in rows if x.get("value")]
            if len(vals) < 300:          # too few days to trust an annual total
                continue
            out.append({"station": notation, "label": station.get("label"),
                        "lat": station.get("lat"), "long": station.get("long"),
                        "easting": station.get("easting"), "northing": station.get("northing"),
                        "days": len(vals), "annual_mm": round(sum(vals), 1)})
        except Exception:                                          # noqa: BLE001
            continue
        if i % 50 == 0:
            _time.sleep(0.3)
    dest = bronze / f"rainfall_annual_{year}.json"
    dest.write_text(_json.dumps(out))
    return Result(dest.name, len(out) > 50, f"{len(out)} stations, {year}", dest.stat().st_size)


# ---------------------------------------------------------------- Companies House PSC
def fetch_psc(bronze: Path, s: requests.Session | None = None) -> Result:
    """All 32 persons-of-significant-control snapshot parts.

    Beneficial ownership is published as a split archive. Missing a part means
    missing whoever it covered, so every part named on the index is fetched;
    parts already complete on disk are skipped.
    """
    import re
    s = s or _session()
    idx = s.get("http://download.companieshouse.gov.uk/en_pscdata.html", timeout=120)
    parts = re.findall(r'(psc-snapshot-[0-9-]+_[0-9]+of[0-9]+\.zip)', idx.text)
    parts = sorted(set(parts))
    if not parts:
        return Result("ch_psc", False, "no PSC snapshot parts on the index")
    got = total = 0
    for part in parts:
        dest = bronze / part
        if dest.exists() and zipfile.is_zipfile(dest):
            got += 1; total += dest.stat().st_size
            continue
        try:
            total += _download(s, "http://download.companieshouse.gov.uk/" + part,
                               dest, timeout=1800)
            got += 1
        except Exception:                                          # noqa: BLE001
            pass
    return Result("ch_psc", got == len(parts),
                  f"{got} of {len(parts)} snapshot parts", total)


# ---------------------------------------------------------------- paged APIs
def fetch_contracts(bronze: Path, pages: int = 200,
                    s: requests.Session | None = None) -> Result:
    """Walk Contracts Finder backwards on its publishedTo cursor."""
    s = s or _session()
    base = ("https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/"
            "Search?limit=100")
    dest = bronze / "contracts_finder_bulk.json"
    seen: dict[str, dict] = {}
    if dest.exists():
        try:
            for x in json.loads(dest.read_text()).get("releases", []):
                if x.get("ocid"):
                    seen[x["ocid"]] = x
        except json.JSONDecodeError:
            pass
    cursor, stalled = None, 0
    for _ in range(pages):
        url = base + (f"&publishedTo={cursor}" if cursor else "")
        try:
            r = s.get(url, timeout=120)
            if r.status_code != 200:
                time.sleep(3); stalled += 1
                if stalled > 5: break
                continue
            rel = r.json().get("releases", [])
        except Exception:                                         # noqa: BLE001
            time.sleep(3); stalled += 1
            if stalled > 5: break
            continue
        if not rel:
            break
        new = sum(1 for x in rel if x.get("ocid") and x["ocid"] not in seen)
        for x in rel:
            if x.get("ocid"):
                seen[x["ocid"]] = x
        dates = [x.get("date", "") for x in rel if x.get("date")]
        if not dates:
            break
        cursor = min(dates)
        stalled = 0 if new else stalled + 1
        if stalled > 3:
            break
        time.sleep(0.4)
    dest.write_text(json.dumps({"releases": list(seen.values())}))
    return Result(dest.name, True, f"{len(seen):,} distinct releases", dest.stat().st_size)


def fetch_gazette(bronze: Path, pages: int = 200,
                  s: requests.Session | None = None) -> Result:
    """Page the insolvency feed until it stops returning new notices."""
    s = s or _session()
    dest = bronze / "gazette_insolvency_bulk.json"
    seen: dict[str, dict] = {}
    if dest.exists():
        try:
            for x in json.loads(dest.read_text()).get("entry", []):
                if x.get("id"):
                    seen[x["id"]] = x
        except json.JSONDecodeError:
            pass
    stalled = 0
    for page in range(1, pages + 1):
        url = ("https://www.thegazette.co.uk/insolvency/notice/data.json"
               f"?results-page-size=100&results-page={page}")
        try:
            r = s.get(url, timeout=120)
            if r.status_code != 200:
                break
            entries = r.json().get("entry", [])
        except Exception:                                         # noqa: BLE001
            time.sleep(2); continue
        if not entries:
            break
        new = sum(1 for e in entries if e.get("id") and e["id"] not in seen)
        for e in entries:
            if e.get("id"):
                seen[e["id"]] = e
        stalled = 0 if new else stalled + 1
        if stalled > 3:
            break
        time.sleep(0.25)
    dest.write_text(json.dumps({"entry": list(seen.values())}))
    return Result(dest.name, True, f"{len(seen):,} distinct notices", dest.stat().st_size)
