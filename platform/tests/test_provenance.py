"""The evidence layer.

The rule under test: a stored observation can always answer where it came from.
An observation that cannot is refused, because an untraceable row in a
provenance table is worse than an absent one -- it looks like evidence.
"""
import pytest

from groundtruth import provenance as P
from groundtruth import store


def _con(tmp_path):
    con = store.connect(tmp_path / "db")
    P.init(con)
    return con


def _published(**kw):
    base = dict(subject="gt:entity:company:01234567", field="contracts",
                derivation=P.PUBLISHED, value_num=3.0, source_id="contracts_finder",
                record_ref="OCDS-1")
    base.update(kw)
    return P.Observation(**base)


class TestRefusals:
    def test_published_value_must_name_a_source(self):
        with pytest.raises(P.ProvenanceError):
            _published(source_id=None).validate()

    def test_derived_value_must_record_how_it_was_derived(self):
        # "derived" with no transformation and no join is indistinguishable
        # from a number someone typed in.
        o = P.Observation(subject="gt:place:lad:E06000001", field="total",
                          derivation=P.DERIVED, value_num=1.0)
        with pytest.raises(P.ProvenanceError):
            o.validate()

    def test_unknown_derivation_is_refused(self):
        with pytest.raises(P.ProvenanceError):
            _published(derivation="guessed").validate()

    @pytest.mark.parametrize("c", [-0.1, 1.5])
    def test_confidence_outside_the_unit_interval_is_refused(self, c):
        with pytest.raises(P.ProvenanceError):
            _published(confidence=c).validate()

    def test_nothing_is_stored_when_one_observation_is_invalid(self, tmp_path):
        """Validation happens before any insert, so a bad row cannot leave a
        half-written batch behind."""
        con = _con(tmp_path)
        with pytest.raises(P.ProvenanceError):
            P.record(con, "run-1", [_published(), _published(source_id=None)])
        assert con.execute("SELECT count(*) FROM evidence.observation").fetchone()[0] == 0
        con.close()


class TestExplain:
    def test_returns_the_chain_that_produced_a_number(self, tmp_path):
        con = _con(tmp_path)
        P.record(con, "run-1", [P.Observation(
            subject="gt:place:lad:E06000001", field="contributions_total",
            derivation=P.DERIVED, value_num=4_700_000.0,
            transformations=["normalised organisation", "resolved site"],
            joins=[{"on": "agreement", "to": "planning-application", "confidence": 1.0}],
            confidence=0.987, coverage_n=704, coverage_of=1000)])
        out = P.explain(con, "gt:place:lad:E06000001")
        assert len(out) == 1
        row = out[0]
        assert row["transformations"] == ["normalised organisation", "resolved site"]
        assert row["joins"][0]["to"] == "planning-application"
        assert row["coverage_pct"] == 70.4, "coverage travels with the statistic"
        con.close()

    def test_a_later_run_supersedes_an_earlier_one(self, tmp_path):
        # Append-only: the old row stays, but explain() reports what is believed now.
        con = _con(tmp_path)
        P.record(con, "run-1", [_published(value_num=3.0)])
        P.record(con, "run-2", [_published(value_num=4.0)])
        assert con.execute("SELECT count(*) FROM evidence.observation").fetchone()[0] == 2
        assert P.explain(con, "gt:entity:company:01234567")[0]["value_num"] == 4.0
        con.close()


class TestSummary:
    def test_reports_the_modelled_count_so_the_claim_stays_checkable(self, tmp_path):
        """The platform says it estimates nothing. That is only meaningful if
        the number of modelled observations is visible and equal to zero."""
        con = _con(tmp_path)
        P.record(con, "run-1", [_published()])
        s = P.summary(con)
        assert s["modelled"] == 0
        assert s["by_derivation"]["published"]["observations"] == 1
        con.close()
