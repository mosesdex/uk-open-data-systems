"""The investigation workspace.

The rule under test: nothing enters or leaves the collection without a stated
reason, and ruling something out is preserved rather than deleted.
"""
import pytest

from groundtruth import investigations as I
from groundtruth import store


@pytest.fixture
def con(tmp_path):
    c = store.connect(tmp_path / "db")
    c.execute("CREATE SCHEMA IF NOT EXISTS silver")
    yield c
    c.close()


@pytest.fixture
def inv(con):
    return I.create(con, "Riverside Development",
                    question="Who is behind the site and what was promised?")


class TestCreating:
    def test_name_becomes_a_stable_slug(self, con):
        assert I.create(con, "Riverside Development").id == "riverside-development"

    def test_duplicate_name_is_refused(self, con, inv):
        with pytest.raises(I.InvestigationError):
            I.create(con, "Riverside  Development")

    def test_a_name_with_no_letters_is_refused(self, con):
        with pytest.raises(I.InvestigationError):
            I.create(con, "   ---   ")


class TestItems:
    def test_an_item_needs_a_reason(self, con, inv):
        """An unexplained item is indistinguishable from an accident three
        weeks later, and this collection is meant to be handed on."""
        with pytest.raises(I.InvestigationError):
            I.add(con, inv.id, "gt:entity:company:01234567", why="  ")

    def test_adding_records_the_reason_and_the_kind(self, con, inv):
        I.add(con, inv.id, "gt:entity:company:01234567", why="named on the s106")
        item = I.get(con, inv.id).live_items[0]
        assert item["why"] == "named on the s106"
        assert (item["kind"], item["namespace"]) == ("entity", "company")

    def test_adding_twice_does_not_duplicate(self, con, inv):
        I.add(con, inv.id, "gt:entity:company:01234567", why="first")
        out = I.add(con, inv.id, "gt:entity:company:01234567", why="again")
        assert out["added"] is False
        assert len(I.get(con, inv.id).live_items) == 1

    def test_a_malformed_identifier_is_refused(self, con, inv):
        with pytest.raises(Exception):
            I.add(con, inv.id, "not-an-identifier", why="x")

    def test_adding_to_an_unknown_investigation_is_refused(self, con):
        with pytest.raises(I.InvestigationError):
            I.add(con, "nope", "gt:entity:company:01234567", why="x")


class TestRulingOut:
    def test_ruling_out_keeps_the_row_and_the_reason(self, con, inv):
        """'We looked at this and ruled it out' is a finding; deleting the row
        destroys the finding."""
        I.add(con, inv.id, "gt:entity:company:01234567", why="named on the s106")
        I.remove(con, inv.id, "gt:entity:company:01234567",
                 because="dissolved before the agreement was signed")
        got = I.get(con, inv.id)
        assert got.live_items == []
        assert len(got.ruled_out) == 1
        assert "dissolved" in got.ruled_out[0]["removed_because"]

    def test_ruling_out_needs_a_reason(self, con, inv):
        I.add(con, inv.id, "gt:entity:company:01234567", why="x")
        with pytest.raises(I.InvestigationError):
            I.remove(con, inv.id, "gt:entity:company:01234567", because="")

    def test_a_ruled_out_item_can_be_added_again(self, con, inv):
        I.add(con, inv.id, "gt:entity:company:01234567", why="x")
        I.remove(con, inv.id, "gt:entity:company:01234567", because="ruled out")
        assert I.add(con, inv.id, "gt:entity:company:01234567",
                     why="new evidence")["added"] is True


class TestClosing:
    def test_closing_requires_an_outcome(self, con, inv):
        with pytest.raises(I.InvestigationError):
            I.close(con, inv.id, outcome="   ")

    def test_nothing_found_is_a_valid_outcome_and_is_recorded(self, con, inv):
        I.close(con, inv.id, outcome="nothing found: the money is unlocatable")
        got = I.get(con, inv.id)
        assert got.open is False and "nothing found" in got.outcome


class TestExpand:
    def test_traversed_items_record_the_path_that_reached_them(self, con, inv):
        con.execute("""CREATE TABLE silver.contribution (
            entity BIGINT, reference VARCHAR, organisation_entity BIGINT,
            agreement VARCHAR, purpose VARCHAR, amount DOUBLE, units DOUBLE,
            start_date VARCHAR, has_geometry BOOLEAN)""")
        con.execute("""INSERT INTO silver.contribution VALUES
            (1,'C-1',111,'A-1','health',100,NULL,'2019-01-01',FALSE)""")
        out = I.expand(con, inv.id, "gt:event:contribution:111/C-1", depth=2)
        assert out["added"] >= 1
        item = next(i for i in I.get(con, inv.id).live_items
                    if i["identifier"] == "gt:event:agreement:111/A-1")
        assert "agreed_under" in item["found_via"]
        assert "silver.contribution" in item["found_via"], "the path names its table"
