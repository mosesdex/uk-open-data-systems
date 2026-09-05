"""Universal search.

The rule under test: the plan is visible before the answer, a question the
corpus cannot support is refused with a reason, and nothing is resolved by
guessing.
"""
import pytest

from groundtruth import search as S
from groundtruth import store


@pytest.fixture
def con(tmp_path):
    c = store.connect(tmp_path / "db")
    c.execute("CREATE SCHEMA IF NOT EXISTS gold")
    c.execute("""CREATE TABLE gold.catchment_district (
        lad_code VARCHAR, lad_name VARCHAR, schools INTEGER,
        utilisation_pct DOUBLE)""")
    c.execute("INSERT INTO gold.catchment_district VALUES "
              "('E07000223','Adur',24,89.6),('E07000229','Worthing',31,92.1)")
    yield c
    c.close()


class TestPlan:
    def test_resolves_a_district_named_in_the_question(self, con):
        p = S.plan(con, "how many school places are there in Adur")
        assert [h["lad_code"] for h in p.places] == ["E07000223"]
        assert "catchment" in p.systems

    def test_does_not_match_a_district_inside_another_word(self, con):
        # 'Adur' must not fire on 'adurations'. A search box is not the place to
        # relax the matching rules the spines enforce.
        p = S.plan(con, "adurations and other nonsense")
        assert p.places == []

    def test_names_the_tables_it_would_read(self, con):
        p = S.plan(con, "school capacity in Worthing")
        assert "gold.catchment_district" in p.tables

    def test_a_system_that_has_not_run_is_blocked_with_a_reason(self, con):
        p = S.plan(con, "sewage spills in Adur")
        assert "baseline" in p.systems
        assert any("has not run" in b for b in p.blocked)
        assert p.answerable == "partial"

    def test_known_unanswerable_question_is_refused_with_the_reason(self, con):
        p = S.plan(con, "which tenders had a single bidder")
        assert p.answerable in ("no", "partial")
        assert any("not published in UK procurement data" in b for b in p.blocked)

    def test_northern_ireland_is_refused_because_the_spine_is_gb(self, con):
        p = S.plan(con, "school places in Northern Ireland")
        assert any("Great Britain" in b for b in p.blocked)

    def test_words_it_could_not_resolve_are_listed(self, con):
        p = S.plan(con, "school places in Adur and quantumfoobar")
        assert "quantumfoobar" in p.unresolved


class TestAnswer:
    def test_refuses_rather_than_inventing_when_nothing_matches(self, con):
        out = S.answer(con, "what is the airspeed of a swallow")
        assert out["answer"] is None and out["why_not"]

    def test_answers_a_place_question_from_the_profile(self, con):
        out = S.answer(con, "school capacity in Adur")
        assert out["results"] and out["results"][0]["subject"] == "Adur"
        section = out["results"][0]["sections"][0]
        assert section["facts"]["utilisation_pct"] == 89.6

    def test_the_plan_is_returned_alongside_the_answer(self, con):
        out = S.answer(con, "school capacity in Adur")
        assert out["plan"]["tables"] == ["gold.catchment_district"]
        assert out["plan"]["joins"], "the joins used are stated, not hidden"

    def test_national_question_answers_without_a_named_place(self, con):
        out = S.answer(con, "school capacity")
        assert out["results"][0]["table"] == "gold.catchment_district"
        assert out["results"][0]["rows_total"] == 2

    def test_coverage_travels_with_the_answer(self, con):
        out = S.answer(con, "school capacity in Adur")
        assert out["coverage"]["places_resolved"] == 1
        assert "words_not_understood" in out["coverage"]
