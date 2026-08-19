import pytest

from groundtruth import store, chains


class TestChainsAreHonest:
    """A chain runs against real tables. Where a system has produced nothing,
    the step must be absent rather than narrated."""

    def test_empty_database_produces_no_steps(self, tmp_path):
        con = store.connect(tmp_path / "db")
        for ch in chains.run_all(con):
            assert ch.steps == [], f"{ch.name} invented a step with no data"
            assert ch.systems_touched == 0
        con.close()

    def test_a_step_appears_only_when_its_table_exists(self, tmp_path):
        con = store.connect(tmp_path / "db")
        con.execute("""CREATE TABLE silver.contribution (
            entity BIGINT, reference VARCHAR, organisation_entity BIGINT,
            agreement VARCHAR, purpose VARCHAR, amount DOUBLE, units DOUBLE,
            start_date VARCHAR, has_geometry BOOLEAN)""")
        con.execute("INSERT INTO silver.contribution VALUES (1,'r',1,'a','p',1000,NULL,'2026',FALSE)")
        ch = chains.chain_development_approved(con)
        systems = [s.system for s in ch.steps]
        assert systems == ["Ledger"], "only the system with data should speak"
        assert "1,000" in ch.steps[0].answer
        con.close()

    def test_chain_metadata_is_stable(self, tmp_path):
        con = store.connect(tmp_path / "db")
        names = {c.name for c in chains.run_all(con)}
        assert names == {"A company goes bust", "A council approves housing",
                         "A regulator reissues its reference numbers"}
        con.close()


class TestReuseSummary:
    def test_counts_only_systems_that_produced_output(self, tmp_path):
        con = store.connect(tmp_path / "db")
        assert chains.reuse_summary(con)["systems_built"] == 0
        con.execute("CREATE TABLE gold.catchment_district (x INTEGER)")
        con.execute("CREATE TABLE gold.watchman_exposure (x INTEGER)")
        r = chains.reuse_summary(con)
        assert r["systems_built"] == 2
        assert r["place_spine_users"] == ["catchment"]
        assert r["entity_spine_users"] == ["watchman"]
        con.close()

    def test_every_system_is_assigned_to_a_spine(self):
        """No system may quietly belong to neither."""
        import inspect
        src = inspect.getsource(chains.reuse_summary)
        assigned = set()
        for line in src.splitlines():
            if line.strip().startswith(("place =", "entity =", "both =")):
                assigned |= set(eval(line.split("=", 1)[1].strip()))
        expected = {"catchment", "sentinel", "highwater", "plumbline", "junction",
                    "ledger", "bellwether", "sightline", "lastmile", "bulwark",
                    "watchman", "compass", "baseline"}
        assert assigned == expected
