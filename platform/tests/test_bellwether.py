import pytest

from groundtruth import store, entity
from groundtruth.systems import bellwether as B


def _seed(con, rows):
    con.execute("""CREATE TABLE IF NOT EXISTS silver.care_location (
        location VARCHAR, local_authority VARCHAR, sector VARCHAR, beds INTEGER,
        company_number VARCHAR, provider VARCHAR, provider_key VARCHAR, brand VARCHAR)""")
    con.executemany("INSERT INTO silver.care_location VALUES (?,?,?,?,?,?,?,?)", rows)


class TestConcentration:
    def test_group_view_catches_what_the_entity_view_misses(self, tmp_path):
        """The Care UK case, reduced.

        One operator running homes through two numbered companies looks like
        two modest providers by legal entity, and one large one by group.
        """
        con = store.connect(tmp_path / "t.duckdb")
        _seed(con, [
            ("H1", "Islington", "care", 100, "02571516", "Care UK Care Services Ltd",
             entity.normalise_name("Care UK Care Services Ltd"), "BRAND Care UK"),
            ("H2", "Islington", "care", 100, "02644862", "Care UK Community Partnerships Ltd",
             entity.normalise_name("Care UK Community Partnerships Ltd"), "BRAND Care UK"),
            ("H3", "Islington", "care", 200, "09999999", "Someone Else Ltd",
             entity.normalise_name("Someone Else Ltd"), "-"),
        ])
        B.build(con); B.build_groups(con)

        entity_top = con.execute("""SELECT max(share_pct) FROM gold.bellwether_care
                                    WHERE local_authority='Islington'""").fetchone()[0]
        group_top = con.execute("""SELECT max(share_pct) FROM gold.bellwether_group
                                   WHERE local_authority='Islington'""").fetchone()[0]
        assert entity_top == pytest.approx(50.0)   # 200 of 400, the unbranded one
        assert group_top == pytest.approx(50.0)    # Care UK group is also 200 of 400
        care_uk = con.execute("""SELECT beds FROM gold.bellwether_group
            WHERE local_authority='Islington' AND group_name LIKE '%Care UK%'""").fetchone()[0]
        assert care_uk == 200, "the group view must sum both companies"
        con.close()

    def test_unbranded_providers_are_not_pooled_into_one_group(self, tmp_path):
        """'-' means no group, not the same group."""
        con = store.connect(tmp_path / "t.duckdb")
        _seed(con, [
            ("A", "Leeds", "care", 50, "11111111", "Alpha Ltd", "alpha", "-"),
            ("B", "Leeds", "care", 50, "22222222", "Beta Ltd", "beta", "-"),
        ])
        B.build_groups(con)
        rows = con.execute("""SELECT count(*) FROM gold.bellwether_group
                              WHERE local_authority='Leeds'""").fetchone()[0]
        assert rows == 2, "two unbranded providers must stay separate"
        con.close()

    def test_unbranded_share_is_reported(self, tmp_path):
        con = store.connect(tmp_path / "t.duckdb")
        _seed(con, [
            ("A", "Leeds", "care", 75, "11111111", "Alpha Ltd", "alpha", "-"),
            ("B", "Leeds", "care", 25, "22222222", "Beta Ltd", "beta", "BRAND Beta"),
        ])
        # The group view cannot see 75% of these beds, and must say so.
        assert B.unbranded_share(con) == pytest.approx(75.0)
        con.close()

    def test_systemic_ranking_counts_authorities_not_just_beds(self, tmp_path):
        con = store.connect(tmp_path / "t.duckdb")
        _seed(con, [
            ("A", "Leeds",  "care", 100, "1", "X Ltd", "x", "BRAND Wide"),
            ("B", "York",   "care", 100, "2", "Y Ltd", "y", "BRAND Wide"),
            ("C", "Leeds",  "care", 300, "3", "Z Ltd", "z", "BRAND Narrow"),
        ])
        rows = {r[0]: r for r in B.systemic(con)}
        assert rows["BRAND Wide"][1] == 2, "spans two authorities"
        assert rows["BRAND Narrow"][1] == 1
        assert rows["BRAND Wide"][2] == 2, "two distinct companies"
        con.close()
