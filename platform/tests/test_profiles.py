"""Place and organisation profiles.

The rule under test: a profile assembles what the systems already wrote, and a
system that has not run is reported as unavailable rather than as zero.
"""
import pytest

from groundtruth import profiles as P
from groundtruth import store


@pytest.fixture
def con(tmp_path):
    c = store.connect(tmp_path / "db")
    for s in ("silver", "gold"):
        c.execute(f"CREATE SCHEMA IF NOT EXISTS {s}")
    c.execute("CREATE TABLE silver.lad (lad_code VARCHAR, lad_name VARCHAR)")
    c.execute("INSERT INTO silver.lad VALUES ('E07000223','Adur')")
    yield c
    c.close()


def _catchment(con):
    con.execute("""CREATE TABLE gold.catchment_district (
        lad_code VARCHAR, lad_name VARCHAR, schools INTEGER,
        utilisation_pct DOUBLE, measured_pct DOUBLE)""")
    con.execute("INSERT INTO gold.catchment_district VALUES ('E07000223','Adur',24,89.6,97.2)")


class TestPlaceProfile:
    def test_absent_system_is_unavailable_not_zero(self, con):
        """'No flood defences here' and 'Bulwark has not run' are different
        answers, and the difference is why the platform reports coverage."""
        prof = P.place_profile(con, "gt:place:lad:E07000223")
        bulwark = next(s for s in prof["sections"] if s["system"] == "bulwark")
        assert bulwark["available"] is False
        assert bulwark["facts"] == {}
        assert "not run" in bulwark["note"]

    def test_assembles_what_a_system_wrote(self, con):
        _catchment(con)
        prof = P.place_profile(con, "gt:place:lad:E07000223")
        sec = next(s for s in prof["sections"] if s["system"] == "catchment")
        assert sec["available"] and sec["match"] == "identifier"
        assert sec["facts"]["utilisation_pct"] == 89.6
        assert sec["table"] == "gold.catchment_district", "a fact names its table"

    def test_name_matched_section_is_labelled_a_name_match(self, con):
        _catchment(con)
        con.execute("""CREATE TABLE gold.plumbline_authority (
            lpa VARCHAR, major_decisions INTEGER, headline_pct DOUBLE)""")
        con.execute("INSERT INTO gold.plumbline_authority VALUES ('Adur District Council',12,88.0)")
        prof = P.place_profile(con, "gt:place:lad:E07000223")
        sec = next(s for s in prof["sections"] if s["system"] == "plumbline")
        assert sec["match"] == "name", "matched on a spelling, and says so"
        assert prof["by_name"] == 1 and prof["by_identifier"] == 1

    def test_postcode_resolves_to_its_district_and_says_so(self, con):
        _catchment(con)
        con.execute("""CREATE TABLE silver.place_postcode (
            postcode_key VARCHAR, postcode VARCHAR, positional_quality INTEGER,
            easting INTEGER, northing INTEGER, lad_code VARCHAR,
            ward_code VARCHAR, country_code VARCHAR)""")
        con.execute("INSERT INTO silver.place_postcode VALUES "
                    "('BN431AA','BN431AA',10,0,0,'E07000223','W1','E92')")
        prof = P.place_profile(con, "gt:place:postcode:BN43 1AA")
        assert prof["lad_code"] == "E07000223"
        assert prof["resolved_from"] == "gt:place:postcode:BN431AA"

    def test_unknown_postcode_is_unresolved_not_empty(self, con):
        con.execute("""CREATE TABLE silver.place_postcode (
            postcode_key VARCHAR, postcode VARCHAR, positional_quality INTEGER,
            easting INTEGER, northing INTEGER, lad_code VARCHAR,
            ward_code VARCHAR, country_code VARCHAR)""")
        prof = P.place_profile(con, "gt:place:postcode:ZZ99 9ZZ")
        assert prof["resolved"] is False and "place spine" in prof["reason"]

    def test_wrong_kind_is_refused_with_a_reason(self, con):
        prof = P.place_profile(con, "gt:entity:company:01234567")
        assert prof["resolved"] is False


class TestOrganisationProfile:
    def _entity(self, con):
        con.execute("""CREATE TABLE gold.entity (
            company_number VARCHAR, name VARCHAR, status VARCHAR,
            post_town VARCHAR, incorporated VARCHAR, sic_1 VARCHAR, brand VARCHAR,
            care_locations INTEGER, care_beds INTEGER, care_authorities INTEGER,
            proc_awards INTEGER, proc_value DOUBLE, proc_buyers INTEGER,
            in_care BOOLEAN, in_proc BOOLEAN)""")
        con.execute("INSERT INTO gold.entity VALUES ('01234567','ACME LTD','Active',"
                    "'LONDON','2001-01-01','8710',NULL,4,120,2,7,50000.0,3,TRUE,TRUE)")

    def test_unbuilt_spine_says_so_rather_than_returning_nothing(self, con):
        prof = P.organisation_profile(con, "gt:entity:company:01234567")
        assert prof["resolved"] is False and "gold.entity" in prof["reason"]

    def test_unknown_company_is_distinguished_from_an_unbuilt_spine(self, con):
        self._entity(con)
        prof = P.organisation_profile(con, "gt:entity:company:09999999")
        assert prof["resolved"] is False and "no organisation" in prof["reason"]

    def test_assembles_identity_and_activity(self, con):
        self._entity(con)
        prof = P.organisation_profile(con, "gt:entity:company:01234567")
        assert prof["resolved"] and prof["name"] == "ACME LTD"
        assert prof["care_beds"] == 120 and prof["procurement_awards"] == 7

    def test_padded_company_number_finds_the_same_organisation(self, con):
        self._entity(con)
        assert P.organisation_profile(con, "gt:entity:company:1234567")["name"] == "ACME LTD"

    def test_footprint_is_read_from_a_table_not_asserted(self, con):
        self._entity(con)
        con.execute("""CREATE TABLE gold.bellwether_care (
            local_authority VARCHAR, provider VARCHAR, company_number VARCHAR,
            locations INTEGER, beds INTEGER, la_beds INTEGER, share_pct DOUBLE)""")
        con.execute("INSERT INTO gold.bellwether_care VALUES "
                    "('Adur','ACME LTD','01234567',2,60,600,10.0),"
                    "('Worthing','ACME LTD','01234567',2,60,900,6.7)")
        prof = P.organisation_profile(con, "gt:entity:company:01234567")
        assert prof["authorities_operated_in"] == ["Adur", "Worthing"]


class TestGeographyLevels:
    def test_upper_tier_system_explains_itself_rather_than_reading_as_empty(self, con):
        """Worthing has no care row; West Sussex has 238. An empty section would
        read as 'no care homes in Worthing', which is the opposite of the truth."""
        _catchment(con)
        con.execute("""CREATE TABLE gold.bellwether_care (
            local_authority VARCHAR, provider VARCHAR, company_number VARCHAR,
            locations INTEGER, beds INTEGER, la_beds INTEGER, share_pct DOUBLE)""")
        con.execute("INSERT INTO gold.bellwether_care VALUES "
                    "('West Sussex','ACME LTD','01234567',2,60,600,10.0)")
        prof = P.place_profile(con, "gt:place:lad:E07000223")
        sec = next(s for s in prof["sections"] if s["system"] == "bellwether")
        assert sec["available"] is True and sec["facts"] == {}
        assert "upper-tier" in sec["note"]
        assert "not that there is nothing to report" in sec["note"]

    def test_a_unitary_authority_does_match_its_care_rows(self, con):
        con.execute("""CREATE TABLE gold.catchment_district (
            lad_code VARCHAR, lad_name VARCHAR, schools INTEGER,
            utilisation_pct DOUBLE, measured_pct DOUBLE)""")
        con.execute("INSERT INTO gold.catchment_district VALUES ('E08000025','Birmingham',459,90.0,95.0)")
        con.execute("""CREATE TABLE gold.bellwether_care (
            local_authority VARCHAR, provider VARCHAR, company_number VARCHAR,
            locations INTEGER, beds INTEGER, la_beds INTEGER, share_pct DOUBLE)""")
        con.execute("INSERT INTO gold.bellwether_care VALUES "
                    "('Birmingham','ACME LTD','01234567',3,90,900,10.0)")
        prof = P.place_profile(con, "gt:place:lad:E08000025")
        sec = next(s for s in prof["sections"] if s["system"] == "bellwether")
        assert sec["facts"]["count"] == 1
