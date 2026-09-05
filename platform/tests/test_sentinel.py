import json

import pytest

from groundtruth import store
from groundtruth.systems import sentinel as S


def _ocds(tmp_path, releases, name="o.json"):
    p = tmp_path / name
    p.write_text(json.dumps({"releases": releases}))
    return p


def _release(ocid, buyer, supplier, value=1000, method="open", number=None):
    parties = [{"id": "S1", "name": supplier}]
    if number:
        parties[0]["identifier"] = {"scheme": "GB-COH", "id": number}
    return {"ocid": ocid, "buyer": {"id": "B1", "name": buyer},
            "tender": {"procurementMethod": method}, "parties": parties,
            "awards": [{"id": "1", "date": "2026-01-01", "value": {"amount": value},
                        "suppliers": [{"id": "S1", "name": supplier}]}]}


class TestWhatCannotBeComputed:
    """Two standard screens are impossible in UK data. The system must report
    that rather than implying it ran them."""

    def test_bidder_counts_are_absent(self, tmp_path):
        p = _ocds(tmp_path, [_release("a", "Council", "Acme Ltd")])
        con = store.connect(tmp_path / "db")
        cov = S.load(con, p)
        assert cov.with_tenderer_count == 0
        con.close()

    def test_supplier_identification_is_partial_and_measured(self, tmp_path):
        p = _ocds(tmp_path, [
            _release("a", "Council", "Acme Ltd", number="07654321"),
            _release("b", "Council", "Beta Ltd"),
        ])
        con = store.connect(tmp_path / "db")
        cov = S.load(con, p)
        assert cov.awards == 2 and cov.suppliers_identified == 1
        con.close()


class TestConcentration:
    def test_repeated_awards_to_one_supplier_are_surfaced(self, tmp_path):
        p = _ocds(tmp_path, [
            _release("a", "Council", "Acme Ltd", number="07654321"),
            _release("b", "Council", "Acme Ltd", number="07654321"),
            _release("c", "Council", "Acme Ltd", number="07654321"),
            _release("d", "Council", "Other Ltd", number="09999999"),
        ])
        con = store.connect(tmp_path / "db")
        S.load(con, p); S.build(con)
        row = con.execute("""SELECT top_supplier_award_share FROM gold.sentinel_buyer
                             WHERE buyer='Council'""").fetchone()
        assert row[0] == pytest.approx(75.0)
        rep = con.execute("SELECT awards FROM gold.sentinel_repeat").fetchall()
        assert rep and rep[0][0] == 3
        con.close()

    def test_one_company_under_two_names_is_counted_once(self, tmp_path):
        """The entity spine is what makes concentration measurable at all."""
        p = _ocds(tmp_path, [
            _release("a", "Council", "Acme Limited", number="07654321"),
            _release("b", "Council", "ACME LTD", number="07654321"),
            _release("c", "Council", "Other Ltd", number="09999999"),
        ])
        con = store.connect(tmp_path / "db")
        S.load(con, p); S.build(con)
        suppliers = con.execute("""SELECT suppliers FROM gold.sentinel_buyer
                                   WHERE buyer='Council'""").fetchone()[0]
        assert suppliers == 2, "two spellings of one company number are one supplier"
        con.close()

    def test_uncompeted_share_counts_direct_and_limited(self, tmp_path):
        p = _ocds(tmp_path, [
            _release("a", "Council", "A Ltd", method="direct"),
            _release("b", "Council", "B Ltd", method="limited"),
            _release("c", "Council", "C Ltd", method="open"),
            _release("d", "Council", "D Ltd", method="selective"),
        ])
        con = store.connect(tmp_path / "db")
        S.load(con, p); S.build(con)
        n, total, pct = S.uncompeted_share(con)
        assert n == 2 and total == 4 and pct == 50.0
        con.close()


class TestSharedControl:
    """Two bidders on one contract controlled by the same person. This is the
    collusion signal price and bidder-count screens cannot give, because UK
    data publishes neither. It is a signal to investigate, never a verdict."""

    def _setup(self, con):
        con.execute("""CREATE TABLE silver.psc (
            company_number VARCHAR, kind VARCHAR, name VARCHAR,
            person_key VARCHAR, control VARCHAR)""")

    def _award(self, ocid, company, supplier):
        return (ocid, 'B1', 'A Council', supplier, supplier.lower(), company,
                'open', None, 'services', 100000.0, '2026-01-01')

    def test_shared_controller_between_two_bidders_is_found(self, tmp_path):
        con = store.connect(tmp_path / "db")
        con.execute("""CREATE TABLE silver.procurement_award (
            ocid VARCHAR, buyer_id VARCHAR, buyer VARCHAR, supplier VARCHAR,
            supplier_key VARCHAR, company_number VARCHAR, method VARCHAR,
            method_detail VARCHAR, category VARCHAR, value DOUBLE, award_date VARCHAR)""")
        con.executemany("INSERT INTO silver.procurement_award VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        [self._award('c1', '11111111', 'Alpha Ltd'),
                         self._award('c1', '22222222', 'Beta Ltd')])
        self._setup(con)
        con.executemany("INSERT INTO silver.psc VALUES (?,?,?,?,?)", [
            ('11111111', 'individual-person-with-significant-control', 'Ms Jane Smith', 'jane smith', 'ownership'),
            ('22222222', 'individual-person-with-significant-control', 'Jane Smith', 'jane smith', 'ownership'),
        ])
        S.shared_control(con)
        rows = con.execute("SELECT person FROM gold.sentinel_shared_control").fetchall()
        assert len(rows) == 1 and 'Smith' in rows[0][0]
        con.close()

    def test_different_controllers_are_not_flagged(self, tmp_path):
        con = store.connect(tmp_path / "db")
        con.execute("""CREATE TABLE silver.procurement_award (
            ocid VARCHAR, buyer_id VARCHAR, buyer VARCHAR, supplier VARCHAR,
            supplier_key VARCHAR, company_number VARCHAR, method VARCHAR,
            method_detail VARCHAR, category VARCHAR, value DOUBLE, award_date VARCHAR)""")
        con.executemany("INSERT INTO silver.procurement_award VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        [self._award('c1', '11111111', 'Alpha Ltd'),
                         self._award('c1', '22222222', 'Beta Ltd')])
        self._setup(con)
        con.executemany("INSERT INTO silver.psc VALUES (?,?,?,?,?)", [
            ('11111111', 'individual-person-with-significant-control', 'Jane Smith', 'jane smith', 'ownership'),
            ('22222222', 'individual-person-with-significant-control', 'John Doe', 'john doe', 'ownership'),
        ])
        S.shared_control(con)
        assert con.execute("SELECT count(*) FROM gold.sentinel_shared_control").fetchone()[0] == 0
        con.close()

    def test_framework_co_awards_are_not_flagged(self, tmp_path):
        """A framework awards many suppliers together. Two of them sharing a
        director is coincidence, not collusion, so a large field is excluded."""
        con = store.connect(tmp_path / "db")
        con.execute("""CREATE TABLE silver.procurement_award (
            ocid VARCHAR, buyer_id VARCHAR, buyer VARCHAR, supplier VARCHAR,
            supplier_key VARCHAR, company_number VARCHAR, method VARCHAR,
            method_detail VARCHAR, category VARCHAR, value DOUBLE, award_date VARCHAR)""")
        # ten suppliers on one framework, two sharing a controller
        rows = [self._award('fw', f'{i:08d}', f'Supplier {i}') for i in range(1, 11)]
        con.executemany("INSERT INTO silver.procurement_award VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
        self._setup(con)
        con.executemany("INSERT INTO silver.psc VALUES (?,?,?,?,?)", [
            ('00000001', 'individual-person-with-significant-control', 'Jane Smith', 'jane smith', 'own'),
            ('00000002', 'individual-person-with-significant-control', 'Jane Smith', 'jane smith', 'own'),
        ])
        S.shared_control(con)
        assert con.execute("SELECT count(*) FROM gold.sentinel_shared_control").fetchone()[0] == 0
        con.close()

    def test_corporate_parent_of_a_bidder_is_not_flagged(self, tmp_path):
        """A company controlling its own subsidiary is a group structure, not
        two independent bidders."""
        con = store.connect(tmp_path / "db")
        con.execute("""CREATE TABLE silver.procurement_award (
            ocid VARCHAR, buyer_id VARCHAR, buyer VARCHAR, supplier VARCHAR,
            supplier_key VARCHAR, company_number VARCHAR, method VARCHAR,
            method_detail VARCHAR, category VARCHAR, value DOUBLE, award_date VARCHAR)""")
        con.executemany("INSERT INTO silver.procurement_award VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        [self._award('c1', '11111111', 'Parent Ltd'),
                         self._award('c1', '22222222', 'Sub Ltd')])
        self._setup(con)
        con.executemany("INSERT INTO silver.psc VALUES (?,?,?,?,?)", [
            ('11111111', 'corporate-entity-person-with-significant-control', 'Parent Ltd', 'parent ltd', 'own'),
            ('22222222', 'corporate-entity-person-with-significant-control', 'Parent Ltd', 'parent ltd', 'own'),
        ])
        S.shared_control(con)
        assert con.execute("SELECT count(*) FROM gold.sentinel_shared_control").fetchone()[0] == 0
        con.close()

    def test_missing_psc_table_produces_an_empty_result_not_an_error(self, tmp_path):
        con = store.connect(tmp_path / "db")
        con.execute("""CREATE TABLE silver.procurement_award (
            ocid VARCHAR, buyer_id VARCHAR, buyer VARCHAR, supplier VARCHAR,
            supplier_key VARCHAR, company_number VARCHAR, method VARCHAR,
            method_detail VARCHAR, category VARCHAR, value DOUBLE, award_date VARCHAR)""")
        S.shared_control(con)
        assert con.execute("SELECT count(*) FROM gold.sentinel_shared_control").fetchone()[0] == 0
        con.close()


class TestControlFootprint:
    """One owner behind several of a buyer's suppliers over time. This is the
    signal PSC actually powers, since award notices name only winners."""

    def test_one_person_two_companies_same_buyer_is_surfaced(self, tmp_path):
        con = store.connect(tmp_path / "db")
        con.execute("""CREATE TABLE silver.procurement_award (
            ocid VARCHAR, buyer_id VARCHAR, buyer VARCHAR, supplier VARCHAR,
            supplier_key VARCHAR, company_number VARCHAR, method VARCHAR,
            method_detail VARCHAR, category VARCHAR, value DOUBLE, award_date VARCHAR)""")
        con.executemany("INSERT INTO silver.procurement_award VALUES (?,?,?,?,?,?,?,?,?,?,?)", [
            ('c1','B','A Council','Alpha','alpha','11111111','open',None,'s',1000.0,'2026-01-01'),
            ('c2','B','A Council','Beta','beta','22222222','open',None,'s',2000.0,'2026-02-01')])
        con.execute("CREATE TABLE silver.psc (company_number VARCHAR, kind VARCHAR, name VARCHAR, person_key VARCHAR, control VARCHAR)")
        con.executemany("INSERT INTO silver.psc VALUES (?,?,?,?,?)", [
            ('11111111','individual','Jo Owner','jo owner','o'),
            ('22222222','individual','Jo Owner','jo owner','o')])
        S.build_footprint(con)
        row = con.execute("SELECT person, companies, awards FROM gold.sentinel_control_footprint").fetchone()
        assert row == ('Jo Owner', 2, 2)
        con.close()

    def test_no_psc_gives_empty_table_not_error(self, tmp_path):
        con = store.connect(tmp_path / "db")
        con.execute("""CREATE TABLE silver.procurement_award (
            ocid VARCHAR, buyer_id VARCHAR, buyer VARCHAR, supplier VARCHAR,
            supplier_key VARCHAR, company_number VARCHAR, method VARCHAR,
            method_detail VARCHAR, category VARCHAR, value DOUBLE, award_date VARCHAR)""")
        S.build_footprint(con)
        assert con.execute("SELECT count(*) FROM gold.sentinel_control_footprint").fetchone()[0] == 0
        con.close()
