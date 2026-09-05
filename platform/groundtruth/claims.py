"""Claims this platform got wrong, and what the source actually said.

The README already admits that fifteen published claims were corrected during
research, and that roughly half of what sounded solid needed correcting once
someone checked the primary source. That admission sits in a paragraph at the
bottom of a page, which is the wrong place for it: it is the most load-bearing
thing the project can say about its own reliability, and it is invisible.

So the corrections become data. Each entry records what was believed, what the
source actually says, how the error was caught, and which rule or test now
prevents it recurring. A claim only leaves this archive if it turns out the
correction was itself wrong -- in which case it gains a further entry rather
than being deleted.

The entries below are drawn from corrections already recorded in this
repository's handover notes and source registry. An entry is added here only
when the failure is documented somewhere that can be checked; this file is an
index of known errors, not a place to reconstruct them from memory.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Claim:
    """One correction.

    ``guard`` names the test or code rule that now prevents recurrence. An entry
    with no guard is a correction the platform could make again tomorrow, and
    saying so is more useful than leaving the field blank.
    """
    id: str
    system: str
    believed: str
    actually: str
    how_caught: str
    guard: str = ""
    corrected_on: str = ""
    severity: str = "material"          # material | presentational
    tags: tuple[str, ...] = ()

    @property
    def guarded(self) -> bool:
        return bool(self.guard)


ARCHIVE: tuple[Claim, ...] = (
    Claim(
        id="ledger-fills-the-gap",
        system="ledger",
        believed="The developer contributions source note read 'Property reference "
                 "populated on 0.0% -- the gap Ledger fills.' The registry therefore "
                 "asserted that Ledger closed the location gap.",
        actually="Ledger did not close it and could not. The contributions carry no "
                 "geometry, and neither does the parent developer-agreement. A route "
                 "does exist -- 99% of agreements carry a planning-application "
                 "reference, and that dataset holds points -- but the whole "
                 "national planning-application dataset covers 4 authorities, and "
                 "only 2 of the 66 that record contributions. Running the join "
                 "closes the chain for 63 of 39,325 contributions: 0.16%, "
                 "GBP 5.86m of GBP 1.49bn.",
        how_caught="Traced the join upstream dataset by dataset instead of trusting "
                   "the note, then measured per-authority overlap against the live "
                   "API with a guard query proving the filter was applied.",
        guard="tests/test_ledger_location.py::TestLocation",
        corrected_on="2026-09-05",
        severity="material",
        tags=("coverage", "join", "overclaim"),
    ),
    Claim(
        id="ledger-authority-level-estimate",
        system="ledger",
        believed="Measuring which authorities publish planning applications gave an "
                 "expected recovery of 86 contributions and GBP 7.5m.",
        actually="Running the join recovered 63 and GBP 5.86m. The authority-level "
                 "measure is an upper bound: it assumes every agreement in a "
                 "covered authority finds its application, and some references do "
                 "not match. The bound is still useful, and is not the result.",
        how_caught="The join was run rather than left as an estimate, and the two "
                   "numbers were compared instead of the second replacing the first.",
        guard="tests/test_ledger_location.py::TestLocation",
        corrected_on="2026-09-05",
        severity="presentational",
        tags=("estimate", "coverage"),
    ),
    Claim(
        id="catchment-summary-versus-detail",
        system="catchment",
        believed="The first contradiction check compared gold.catchment_district."
                 "schools against every row in gold.catchment_school, and reported "
                 "294 of 317 districts as disagreeing -- 7% agreement across a "
                 "system's own summary and detail.",
        actually="The summary counts mainstream schools; the detail carries "
                 "specialist settings as well. Birmingham reads 459 against 511, "
                 "and 459 is exactly its mainstream count. Filtering the detail to "
                 "mainstream brings the check to 100% agreement across all 317 "
                 "districts. The data never disagreed; the check did.",
        how_caught="The disagreement was too large to be plausible, so the biggest "
                   "case was broken down by hand before the finding was reported.",
        guard="tests/test_contradictions.py::test_specialist_settings_are_not_"
              "counted_as_a_contradiction",
        corrected_on="2026-09-05",
        severity="material",
        tags=("definition", "false-positive"),
    ),
    Claim(
        id="sentinel-buyer-view-is-not-the-corpus",
        system="sentinel",
        believed="Summing gold.sentinel_buyer.awards should reproduce the award "
                 "total, so its shortfall against gold.sentinel_method looked like "
                 "a grouping dropping rows.",
        actually="The method grouping accounts for all 2,203 awards exactly. The "
                 "buyer view holds 190 of 469 buyers and 1,856 awards, because it "
                 "publishes buyers meeting its threshold rather than all of them. "
                 "The 15.8% gap is the view's scope, not a loss.",
        how_caught="Both sides were traced back to silver.procurement_award instead "
                   "of being compared only to each other.",
        guard="tests/test_contradictions.py",
        corrected_on="2026-09-05",
        severity="presentational",
        tags=("definition", "coverage"),
    ),
    Claim(
        id="lastmile-csv-dialect-sniffed-per-archive",
        system="lastmile",
        believed="gold.lastmile_authority and gold.lastmile_postcode are two "
                 "views of one loaded table, so the authority summary should be "
                 "reproducible by summing the postcode detail for that district. "
                 "It was not: three districts disagreed by exactly one premise, "
                 "which read like a rollup dropping a row.",
        actually="Nothing was dropped in the rollup. BDUK writes a blank district "
                 "code as a quoted empty field, and DuckDB sniffs the CSV dialect "
                 "from the first file of the glob and applies it to every other "
                 "member of the archive -- so an archive whose first file happens "
                 "to contain no quoted field at all was read with quoting "
                 "disabled. Three premises in Merton, Lewisham and Tower Hamlets "
                 "took a district code of two literal quote characters, which the "
                 "name-keyed authority table counted and nothing code-keyed could "
                 "reach. The same misparse truncated the only two district names "
                 "containing a comma at that comma: 238,679 rows carried "
                 "'\"Kingston upon Hull' and '\"Herefordshire', splitting Hull "
                 "across two published authority rows, and it rejected 39,303 "
                 "further premises outright for having one field too many. "
                 "Pinning the dialect recovers all of them; the three blank codes "
                 "are then filled from the district name, which the publisher did "
                 "give and which maps to exactly one code.",
        how_caught="The off-by-one was traced to the value rather than the "
                   "aggregation, and once the value proved malformed the whole "
                   "column was profiled for other artefacts of the same parse "
                   "instead of only the three rows that were reported.",
        guard="tests/test_lastmile.py::TestPublisherCsvDialect and "
              "::TestMissingDistrictCode; "
              "tests/test_contradictions.py::TestLastmilePremises",
        corrected_on="2026-09-05",
        severity="material",
        tags=("parsing", "false-absence", "aggregation"),
    ),
    Claim(
        id="care-data-is-upper-tier-not-district",
        system="bellwether",
        believed="A district profile could show its care providers alongside its "
                 "schools and broadband, because both are 'the local authority'.",
        actually="They are different authorities. Catchment is keyed to 317 "
                 "districts; Bellwether is keyed to 152 upper-tier authorities, "
                 "because social care is a county responsibility. Worthing has "
                 "zero care rows and West Sussex has 238. Only the 128 unitary "
                 "authorities appear in both.",
        how_caught="A profile for Worthing returned an empty care section, which "
                   "would have read as 'no care homes here' rather than 'care is "
                   "not published at this level'.",
        guard="tests/test_profiles.py::TestGeographyLevels",
        corrected_on="2026-09-05",
        severity="material",
        tags=("geography", "coverage", "false-absence"),
    ),
    Claim(
        id="cqc-no-longer-anonymous",
        system="bellwether",
        believed="The CQC active-locations file is openly downloadable, and the "
                 "registry lists it as admissible under the access standard: no "
                 "account, no key, no approval.",
        actually="Every path under cqc.org.uk/system/files now returns HTTP 403 to "
                 "an anonymous request, for the August file, the July file and "
                 "three September filenames alike, under two user agents. The "
                 "host still serves its HTML pages with 200, so this is bot "
                 "protection on the file path rather than a rotated filename. "
                 "Bellwether's 57,867 care locations rest on a source that no "
                 "longer meets the platform's own access standard.",
        how_caught="The audit re-requested every registered source anonymously "
                   "rather than trusting the access status recorded in August.",
        guard="audit.check_live_sources; run with: gt audit --network",
        corrected_on="2026-09-05",
        severity="material",
        tags=("access", "regression"),
    ),
    Claim(
        id="catchment-national-stated-no-coverage",
        system="catchment",
        believed="The national utilisation headline of 89.6% described school "
                 "places across England.",
        actually="It is computed over 21,429 of 24,071 schools -- those "
                 "publishing both a roll and a capacity -- and excludes a further "
                 "524 mainstream schools holding 18,597 pupils that the place "
                 "spine could not resolve to a district. Every district row "
                 "already published measured_pct; the national figure alone "
                 "carried no coverage at all.",
        how_caught="The audit reconciled the published national total against the "
                   "school-level detail it is summed from.",
        guard="publish.build_payload now emits measured_pct, schools_unplaced and "
              "pupils_unplaced on the national block",
        corrected_on="2026-09-05",
        severity="material",
        tags=("coverage", "aggregation"),
    ),
    Claim(
        id="retrieval-unrecorded-for-eight-sources",
        system="platform",
        believed="bronze.fetch_log records the retrieval of everything in the "
                 "database, so any figure can be traced to a timestamped, "
                 "checksummed download.",
        actually="Eight of 38 sources have data in the database and no row in the "
                 "fetch log, because backfill steps and hand-placed files write "
                 "to bronze directly. Charity register (357,761 rows), PSC "
                 "(7,971,449 rows) and the planning datasets are all in this "
                 "state: real data, no recorded time, status or checksum.",
        how_caught="The audit compared the registry against the fetch log and "
                   "then checked the bronze directory, rather than concluding "
                   "the sources were missing.",
        guard="audit.check_registry_vs_log",
        corrected_on="2026-09-05",
        severity="material",
        tags=("provenance", "auditability"),
    ),
    Claim(
        id="planning-reference-is-not-nationally-unique",
        system="platform",
        believed="A planning reference identifies a contribution or an agreement, "
                 "so gt:event:contribution:<reference> was a sound identifier and "
                 "the graph could join on the bare reference.",
        actually="Planning references are unique per authority, not nationally. "
                 "24,306 of 39,325 contributions (61.8%) and 5,381 of 12,775 "
                 "agreements (42.1%) share a reference with a record in a "
                 "different council -- CIL-OTH-00023 exists in seven. The "
                 "identifier merged them, and every graph edge keyed on the "
                 "reference could join one council's money to another council's "
                 "site. Keys are now <organisation>/<reference> throughout.",
        how_caught="The audit's duplicate-key check flagged 9,282 repeated "
                   "contribution references. Checking whether they double-counted "
                   "the GBP 1.49bn total showed they did not -- and showed why: "
                   "the reference is only unique with its authority.",
        guard="tests/test_ids.py::TestPlanningReferencesAreNotNationallyUnique",
        corrected_on="2026-09-05",
        severity="material",
        tags=("identifier", "false-join", "self-inflicted"),
    ),
    Claim(
        id="epc-two-hundred-is-not-data",
        system="platform",
        believed="An HTTP 200 from the energy certificate register meant the register "
                 "had returned data.",
        actually="It returns HTML -- a sign-in page -- with a 200 status. Treating the "
                 "status as the test would have loaded a web page as a dataset.",
        how_caught="Content-type and body checked against what the source promised.",
        guard="fetch.py content expectations; tests/test_fetch.py",
        severity="material",
        tags=("access", "validation"),
    ),
    Claim(
        id="sen-cube-double-count",
        system="compass",
        believed="The SEN file could be summed across its rows to get a national total.",
        actually="It is a cube carrying its own subtotals. Summing across it counted "
                 "the same children four times over.",
        how_caught="Totals reconciled against the publisher's own stated figure.",
        guard="tests/test_compass.py",
        severity="material",
        tags=("aggregation", "double-count"),
    ),
    Claim(
        id="aims-transposed-dates",
        system="bulwark",
        believed="Asset dates were ISO formatted, as most government feeds are.",
        actually="AIMS publishes DD/MM/YYYY. Parsed as ISO, days and months transpose "
                 "silently for every date below the thirteenth.",
        how_caught="Date distribution checked; no day above twelve appeared.",
        guard="tests/test_bulwark.py",
        severity="material",
        tags=("parsing", "dates"),
    ),
    Claim(
        id="codepoint-is-gb-not-uk",
        system="place",
        believed="Code-Point Open covers the United Kingdom.",
        actually="It covers Great Britain. There are zero Northern Ireland postcodes "
                 "in it, so any coverage figure derived from it must say GB.",
        how_caught="Postcode areas enumerated against the UK list.",
        guard="place.py coverage reporting; HANDOVER.md",
        severity="material",
        tags=("coverage", "geography"),
    ),
    Claim(
        id="planning-year-format-switch",
        system="plumbline",
        believed="The planning performance series used one year format throughout.",
        actually="It switches from '2020-21' to '2021/22' mid-series, and the "
                 "'within maximum time' column was discontinued after 2020.",
        how_caught="Series continuity checked across the join rather than assumed.",
        guard="tests/test_plumbline.py",
        severity="material",
        tags=("parsing", "series"),
    ),
    Claim(
        id="blocked-endpoint-is-not-blocked-dataset",
        system="platform",
        believed="A 403 from a publisher's API meant the dataset was unavailable "
                 "without credentials.",
        actually="The endpoint was blocked, not the data. CQC needs a key on its API "
                 "while publishing a fuller file openly; the DNO '/records' path "
                 "returns 403 while '/exports' returns 200.",
        how_caught="Alternative paths tested before recording a source as blocked.",
        guard="sources.py blocked entries carry the reason and stay in the registry",
        severity="material",
        tags=("access",),
    ),
)


def by_system(system: str) -> list[Claim]:
    return [c for c in ARCHIVE if c.system == system]


def unguarded() -> list[Claim]:
    """Corrections with nothing stopping them recurring."""
    return [c for c in ARCHIVE if not c.guarded]


def summary() -> dict:
    systems: dict[str, int] = {}
    tags: dict[str, int] = {}
    for c in ARCHIVE:
        systems[c.system] = systems.get(c.system, 0) + 1
        for t in c.tags:
            tags[t] = tags.get(t, 0) + 1
    return {
        "total": len(ARCHIVE),
        "guarded": sum(1 for c in ARCHIVE if c.guarded),
        "unguarded": len(unguarded()),
        "by_system": dict(sorted(systems.items())),
        "by_tag": dict(sorted(tags.items(), key=lambda kv: -kv[1])),
    }


def as_payload() -> list[dict]:
    """Shape for the published site, so the archive is visible rather than
    mentioned in a closing paragraph."""
    return [{"id": c.id, "system": c.system, "believed": c.believed,
             "actually": c.actually, "how_caught": c.how_caught,
             "guard": c.guard, "guarded": c.guarded,
             "corrected_on": c.corrected_on, "severity": c.severity,
             "tags": list(c.tags)} for c in ARCHIVE]
