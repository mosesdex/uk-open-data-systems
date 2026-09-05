"""Evidence bundles.

The rule under test: a bundle exports results *and their defences*. It states
where its own provenance is missing rather than presenting a clean list.
"""
import json

import pytest

from groundtruth import bundles as B
from groundtruth import investigations as I
from groundtruth import store


@pytest.fixture
def con(tmp_path):
    c = store.connect(tmp_path / "db")
    for s in ("silver", "gold"):
        c.execute(f"CREATE SCHEMA IF NOT EXISTS {s}")
    c.execute("""CREATE TABLE gold.entity (
        company_number VARCHAR, name VARCHAR, status VARCHAR, post_town VARCHAR,
        incorporated VARCHAR, sic_1 VARCHAR, brand VARCHAR,
        care_locations INTEGER, care_beds INTEGER, care_authorities INTEGER,
        proc_awards INTEGER, proc_value DOUBLE, proc_buyers INTEGER,
        in_care BOOLEAN, in_proc BOOLEAN)""")
    c.execute("INSERT INTO gold.entity VALUES ('01234567','ACME LTD','Active','LONDON',"
              "'2001-01-01','8710',NULL,4,120,2,7,50000.0,3,TRUE,TRUE)")
    yield c
    c.close()


@pytest.fixture
def inv(con):
    i = I.create(con, "Riverside", question="Who is behind the site?")
    I.add(con, i.id, "gt:entity:company:01234567", why="named on the agreement")
    return i


class TestContent:
    def test_records_name_the_table_they_came_from(self, con, inv):
        b = B.build(con, inv.id)
        tables = [r["table"] for s in b["subjects"] for r in s["records"]]
        assert "gold.entity" in tables

    def test_the_reason_each_subject_is_present_survives_into_the_bundle(self, con, inv):
        b = B.build(con, inv.id)
        assert b["subjects"][0]["why"] == "named on the agreement"

    def test_ruled_out_items_are_exported_not_dropped(self, con, inv):
        I.add(con, inv.id, "gt:entity:company:09999999", why="shared director")
        I.remove(con, inv.id, "gt:entity:company:09999999",
                 because="different person, same name")
        b = B.build(con, inv.id)
        assert len(b["ruled_out"]) == 1
        assert "same name" in b["ruled_out"][0]["ruled_out_because"]

    def test_limitations_carry_the_corrected_claims(self, con, inv):
        b = B.build(con, inv.id)
        ids_ = {c["id"] for c in b["limitations"]["corrected_claims"]}
        assert "epc-two-hundred-is-not-data" in ids_, "platform claims always apply"

    def test_limitations_carry_the_national_data_gaps(self, con, inv):
        b = B.build(con, inv.id)
        gaps = b["limitations"]["evidence_gaps"]["not_published_anywhere"]
        assert gaps and all(g["reason"] for g in gaps)

    def test_standing_caveats_state_the_gb_scope(self, con, inv):
        b = B.build(con, inv.id)
        assert any("Great Britain" in c
                   for c in b["limitations"]["standing_caveats"])


class TestProvenanceHonesty:
    def test_a_source_with_no_retrieval_record_is_marked_as_such(self, con, inv):
        """A bundle that lists a source without saying it cannot vouch for when
        the data arrived is worse than one that omits it."""
        b = B.build(con, inv.id)
        assert b["sources"]
        assert all("retrieval_recorded" in s for s in b["sources"])
        unrecorded = [s for s in b["sources"] if not s["retrieval_recorded"]]
        assert unrecorded, "this fixture has no fetch log, so all are unrecorded"

    def test_markdown_warns_about_unrecorded_retrievals(self, con, inv):
        md = B.to_markdown(B.build(con, inv.id))
        assert "no recorded retrieval" in md


class TestRendering:
    def test_markdown_leads_with_the_question_and_ends_with_limitations(self, con, inv):
        md = B.to_markdown(B.build(con, inv.id))
        assert md.startswith("# Riverside")
        assert "Who is behind the site?" in md
        assert md.index("## Limitations") > md.index("## Subjects")

    def test_json_round_trips(self, con, inv):
        assert json.loads(B.to_json(B.build(con, inv.id)))["bundle"]["investigation"] == inv.id

    def test_write_produces_the_three_formats(self, con, inv, tmp_path):
        out = B.write(con, inv.id, tmp_path / "pack")
        names = set(out["files"])
        assert {"bundle.json", "README.md", "sources.csv", "subjects.csv"} <= names
        assert (tmp_path / "pack" / "README.md").read_text().startswith("# Riverside")
        assert out["sources_without_retrieval_record"] > 0

    def test_record_csvs_are_written_per_table(self, con, inv, tmp_path):
        B.write(con, inv.id, tmp_path / "pack")
        files = list((tmp_path / "pack" / "records").glob("*.csv"))
        assert files and any("gold_entity" in f.name for f in files)
        assert "company_number" in files[0].read_text()


class TestOrganisationSubjects:
    def test_an_authority_carries_its_own_row_and_what_it_collected(self, con, inv):
        con.execute("CREATE TABLE silver.planning_authority (entity BIGINT, name VARCHAR)")
        con.execute("INSERT INTO silver.planning_authority VALUES (382,'Worthing Borough Council')")
        con.execute("""CREATE TABLE gold.ledger_authority (
            authority VARCHAR, contributions INTEGER, with_amount INTEGER,
            total_amount DOUBLE, amount_coverage_pct DOUBLE, with_location INTEGER)""")
        con.execute("INSERT INTO gold.ledger_authority VALUES "
                    "('Worthing Borough Council',64,50,1000000.0,78.1,0)")
        I.add(con, inv.id, "gt:entity:organisation:382", why="collected the contribution")
        b = B.build(con, inv.id)
        sub = next(s for s in b["subjects"] if s["identifier"] == "gt:entity:organisation:382")
        tables = [r["table"] for r in sub["records"]]
        assert tables == ["silver.planning_authority", "gold.ledger_authority"]
