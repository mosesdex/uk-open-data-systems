"""Every headline can say where it came from.

The evidence layer existed and held nothing, so `gt why` answered for no figure
on the site. These pin the three ways a recorded headline could mislead: a value
that differs from the one published, a source the system does not actually
read, and a figure that claims to be traced while naming no retrieval.
"""
from groundtruth import admin, evidence, ids, provenance as P, store
from groundtruth import sources as S


class TestEveryHeadlineIsCovered:
    def test_every_system_has_a_headline_and_a_source_it_actually_reads(self):
        assert set(evidence.FIGURES) == set(admin.SYSTEM_TABLES)
        reg = {s.id: s for s in S.REGISTRY}
        for system, sid in evidence.PRIMARY.items():
            assert sid in reg, sid
            assert system in reg[sid].systems, f"{sid} does not feed {system}"

    def test_subjects_are_valid_identifiers(self):
        for system in evidence.FIGURES:
            assert ids.is_valid(evidence.subject(system)), evidence.subject(system)


class TestTheRecordedValueIsThePublishedOne:
    def test_rounding_matches_the_site(self):
        """The site rounds halves up; Python's round() rounds them to even."""
        method = [{"method": "direct", "awards": 1}, {"method": "open", "awards": 39}]
        [f] = evidence._sentinel({"method": method}, None)
        assert f["value_num"] == 2.5                     # 1/40 = 2.5%, exactly
        [c] = evidence._compass({"national": [{"provision": "Education, health and care plan",
                                               "earliest": 236806, "latest": 538547}]}, None)
        assert c["value_text"] == "+127.4%"


class TestAHeadlineIsRecordedAndExplained:
    def test_gt_why_answers_with_source_steps_and_coverage(self, tmp_path):
        con = store.connect(tmp_path / "db")
        con.execute("""INSERT INTO bronze.fetch_log (run_id, source_id, fetched_at, http_status,
                       ok, sha256, bytes_len, content_type, elapsed_ms, path, note, final_url)
                       VALUES ('r1', 'planning_ps2', now(), 200, true, 'ab' || repeat('0', 62),
                               10, 'text/csv', 5, 'x', '', 'u')""")
        payload = {"systems": {"plumbline": {"statutory_pct": 15.9, "headline_pct": 90.4,
                                             "major_decisions": 33058.0}}}
        out = evidence.record_headlines(con, payload)
        assert [h["field"] for h in out["headlines"]["plumbline"]] == ["statutory_pct", "headline_pct"]
        rows = {r["field"]: r for r in P.explain(con, evidence.subject("plumbline"))}
        assert rows["statutory_pct"]["value_num"] == 15.9
        assert rows["statutory_pct"]["source_id"] == "planning_ps2"
        assert rows["statutory_pct"]["source_sha256"].startswith("ab")
        assert rows["statutory_pct"]["transformations"]
        assert rows["headline_pct"]["coverage_pct"] == 100.0
        con.close()

    def test_a_source_with_no_fetch_record_says_so(self, tmp_path):
        con = store.connect(tmp_path / "db")
        payload = {"systems": {"sightline": {"reasons": [{"objections": 180}]}}}
        [h] = evidence.record_headlines(con, payload)["headlines"]["sightline"]
        assert h["sha256"] is None and "no fetch record" in h["note"]
        con.close()
