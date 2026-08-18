"""The source registry.

A source is only admissible if an anonymous client can retrieve it: no account,
no API key, no subscription, no cookie. Each entry records the licence and the
role it plays, so a run can be audited without reading the code.

Access status for every entry was verified on 17 August 2026; see research/.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Role = Literal["place_spine", "entity_spine", "domain"]
Fmt = Literal["csv", "json", "geojson", "zip-csv", "zip-shp", "xml"]


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    publisher: str
    url: str
    fmt: Fmt
    role: Role
    licence: str
    cadence: str
    # What a healthy response looks like. Used to catch the trap case where a
    # publisher returns HTTP 200 and a sign-in page instead of the data.
    expect_content: tuple[str, ...] = ("text/csv",)
    # Member to read from inside an archive, if the payload is zipped.
    member_glob: str | None = None
    systems: tuple[str, ...] = ()
    notes: str = ""
    # For Ordnance Survey products whose filenames are versioned per release,
    # the concrete file is resolved at fetch time. See resolve.py.
    os_product: str | None = None
    os_file_pattern: str | None = None
    # Set when a source is known to fail the anonymous test. Kept in the registry
    # deliberately: a platform that silently drops unreachable sources cannot be
    # trusted on coverage.
    blocked: str | None = None

    @property
    def admissible(self) -> bool:
        return self.blocked is None


OS_DOWNLOADS = "https://api.os.uk/downloads/v1/products/{p}/downloads?area=GB&format={f}&redirect"

REGISTRY: tuple[Source, ...] = (
    # ---------------- place spine ----------------
    Source(
        id="os_open_uprn",
        name="OS Open UPRN",
        publisher="Ordnance Survey",
        url=OS_DOWNLOADS.format(p="OpenUPRN", f="CSV"),
        fmt="zip-csv",
        role="place_spine",
        licence="OS OpenData (OGL v3 with attribution)",
        cadence="monthly",
        expect_content=("application/zip", "application/octet-stream"),
        member_glob="*.csv",
        systems=("catchment", "ledger", "highwater", "lastmile", "bulwark"),
        notes="Every property reference in GB with coordinates. ~618 MB zipped.",
    ),
    Source(
        id="os_lids_uprn_usrn",
        name="OS Linked Identifiers -- property to street",
        publisher="Ordnance Survey",
        url=OS_DOWNLOADS.format(p="LIDS", f="CSV"),
        fmt="zip-csv",
        role="place_spine",
        licence="OS OpenData (OGL v3 with attribution)",
        cadence="monthly",
        expect_content=("application/zip", "application/octet-stream"),
        member_glob="*.csv",
        os_product="LIDS",
        os_file_pattern="BLPU-UPRN-Street-USRN",
        systems=("catchment", "ledger", "highwater", "lastmile", "bulwark"),
        notes=(
            "The crosswalk that lets a property reference reach a street. "
            "LIDS ships one file per identifier pair, versioned by month, so the "
            "exact file is resolved at fetch time rather than hardcoded."
        ),
    ),
    Source(
        id="os_lids_uprn_toid",
        name="OS Linked Identifiers -- property to building",
        publisher="Ordnance Survey",
        url=OS_DOWNLOADS.format(p="LIDS", f="CSV"),
        fmt="zip-csv",
        role="place_spine",
        licence="OS OpenData (OGL v3 with attribution)",
        cadence="monthly",
        expect_content=("application/zip", "application/octet-stream"),
        member_glob="*.csv",
        os_product="LIDS",
        os_file_pattern="BLPU-UPRN-TopographicArea-TOID",
        systems=("bulwark", "ledger", "lastmile"),
        notes="Property reference to topographic identifier -- the building footprint join.",
    ),
    Source(
        id="os_open_usrn",
        name="OS Open USRN",
        publisher="Ordnance Survey",
        url=OS_DOWNLOADS.format(p="OpenUSRN", f="GeoPackage"),
        fmt="zip-csv",
        role="place_spine",
        licence="OS OpenData (OGL v3 with attribution)",
        cadence="monthly",
        expect_content=("application/zip", "application/octet-stream"),
        notes="Street references. GeoPackage only.",
    ),
    Source(
        id="os_code_point_open",
        name="Code-Point Open",
        publisher="Ordnance Survey",
        url=OS_DOWNLOADS.format(p="CodePointOpen", f="CSV"),
        fmt="zip-csv",
        role="place_spine",
        licence="OS OpenData (OGL v3 with attribution)",
        cadence="quarterly",
        expect_content=("application/zip", "application/octet-stream"),
        member_glob="Data/CSV/*.csv",
        notes="Postcode centroids. ~14.5 MB zipped -- the cheap way to smoke-test the loader.",
    ),
    Source(
        id="ons_lad_boundaries",
        name="ONS Local Authority Districts (May 2024, ultra generalised)",
        publisher="Office for National Statistics",
        url=(
            "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
            "LAD_MAY_2024_EW_BUC_RUC/FeatureServer/0/query"
            "?where=1%3D1&outFields=LAD24CD,LAD24NM&returnGeometry=true&f=geojson"
            "&resultRecordCount=400&outSR=4326"
        ),
        fmt="geojson",
        role="place_spine",
        licence="OGL v3",
        cadence="annual",
        expect_content=("application/json", "text/plain"),
        notes="Administrative geography for aggregation and mapping.",
    ),
    # ---------------- entity spine ----------------
    Source(
        id="gazette_insolvency",
        name="The Gazette insolvency notices",
        publisher="The Gazette",
        url="https://www.thegazette.co.uk/insolvency/notice/data.json?results-page-size=100",
        fmt="json",
        role="entity_spine",
        licence="OGL v3",
        cadence="realtime",
        expect_content=("application/json",),
        systems=("watchman", "bellwether", "sentinel"),
        notes="Notices carry a structured company number, so no name matching is required.",
    ),
    Source(
        id="companies_house_bulk_index",
        name="Companies House bulk product index",
        publisher="Companies House",
        url="https://download.companieshouse.gov.uk/en_output.html",
        fmt="csv",
        role="entity_spine",
        licence="OGL v3",
        cadence="daily",
        expect_content=("text/html",),
        systems=("sentinel", "watchman", "bellwether"),
        notes="Index page listing the daily bulk snapshot parts; parsed to find the real files.",
    ),
    # ---------------- domain ----------------
    Source(
        id="gias_establishments",
        name="Get Information About Schools -- all establishments",
        publisher="Department for Education",
        url=(
            "https://ea-edubase-api-prod.azurewebsites.net/edubase/downloads/public/"
            "edubasealldata{date}.csv"
        ),
        fmt="csv",
        role="domain",
        licence="OGL v3",
        cadence="daily",
        expect_content=("text/csv", "application/octet-stream"),
        systems=("catchment", "compass", "bellwether"),
        notes=(
            "Carries UPRN and trust identifier, so it measures both spines directly. "
            "The download *page* blocks automation; this direct URL does not. "
            "{date} is substituted as YYYYMMDD."
        ),
    ),
    Source(
        id="planning_developer_contributions",
        name="Developer agreement contributions",
        publisher="MHCLG",
        url="https://www.planning.data.gov.uk/entity.json?dataset=developer-agreement-contribution&limit=500",
        fmt="json",
        role="domain",
        licence="OGL v3",
        cadence="daily",
        expect_content=("application/json",),
        systems=("ledger",),
        notes="39,325 records, GBP 1.49bn. Property reference populated on 0.0% -- the gap Ledger fills.",
    ),
    Source(
        id="ea_flood_assets",
        name="Environment Agency asset management",
        publisher="Environment Agency",
        url="https://environment.data.gov.uk/asset-management/id/asset?_limit=500",
        fmt="json",
        role="domain",
        licence="OGL v3",
        cadence="quarterly",
        expect_content=("application/json",),
        systems=("bulwark",),
        notes="Condition, last inspection date, purpose and protection type per asset.",
    ),
    Source(
        id="ea_rainfall_stations",
        name="Environment Agency rainfall stations",
        publisher="Environment Agency",
        url="https://environment.data.gov.uk/flood-monitoring/id/stations?parameter=rainfall&_limit=500",
        fmt="json",
        role="domain",
        licence="OGL v3",
        cadence="15 minutes",
        expect_content=("application/json",),
        systems=("baseline",),
        notes="1,044 stations. The weather normaliser for sewage spill statistics.",
    ),
    # ---------------- known-blocked, kept visible ----------------
    Source(
        id="epc_domestic",
        name="Energy Performance Certificate register",
        publisher="MHCLG",
        url="https://epc.opendatacommunities.org/api/v1/domestic/search?size=2",
        fmt="json",
        role="domain",
        licence="OGL v3",
        cadence="daily",
        expect_content=("application/json",),
        blocked=(
            "Returns HTTP 200 with a sign-in page to an anonymous client. Advertised "
            "as open; is not. Lastmile uses Price Paid Data instead."
        ),
    ),
    Source(
        id="cqc_syndication",
        name="CQC syndication API",
        publisher="Care Quality Commission",
        url="https://api.service.cqc.org.uk/public/v1/locations?perPage=3",
        fmt="json",
        role="domain",
        licence="OGL v3",
        cadence="daily",
        expect_content=("application/json",),
        blocked="HTTP 401 -- requires a subscription key. The published location file is still free.",
    ),
)

BY_ID: dict[str, Source] = {s.id: s for s in REGISTRY}


def get(source_id: str) -> Source:
    try:
        return BY_ID[source_id]
    except KeyError:
        raise KeyError(
            f"unknown source {source_id!r}; known: {', '.join(sorted(BY_ID))}"
        ) from None


def by_role(role: Role) -> tuple[Source, ...]:
    return tuple(s for s in REGISTRY if s.role == role)


def admissible() -> tuple[Source, ...]:
    return tuple(s for s in REGISTRY if s.admissible)
