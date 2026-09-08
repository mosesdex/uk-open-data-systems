import pytest

from groundtruth import place


class TestPostcodeNormalisation:
    @pytest.mark.parametrize("raw,expect", [
        ("SW1A 1AA", "SW1A1AA"), ("sw1a1aa", "SW1A1AA"),
        ("  m1   1ae ", "M11AE"), ("B33 8TH", "B338TH"), ("EH1 1YZ", "EH11YZ"),
    ])
    def test_accepts_real_postcodes_in_any_shape(self, raw, expect):
        assert place.normalise_postcode(raw) == expect

    @pytest.mark.parametrize("raw", [
        "", None, "NOT A PC", "12345", "SW1A", "1AA", "SW1A 1A", "LONDON",
    ])
    def test_rejects_things_that_are_not_postcodes(self, raw):
        # Strictness is the point: near-misses are how a spine starts
        # attributing records to the wrong district.
        assert place.normalise_postcode(raw) is None


class TestPlaceRef:
    def test_unresolved_is_falsy_and_explains_itself(self):
        assert place.UNRESOLVED.resolved is False
        assert place.UNRESOLVED.note

    def test_confidence_follows_the_publisher_quality_flag(self):
        # Best quality must outrank imputed, and nothing may claim certainty
        # that the publisher did not assert.
        assert place.PQ_CONFIDENCE[10] > place.PQ_CONFIDENCE[90]
        assert all(0 < v <= 1 for v in place.PQ_CONFIDENCE.values())
        assert max(place.PQ_CONFIDENCE.values()) < 1.0, "only an exact property is 1.0"


class TestCoverageLimits:
    """Limits worth failing loudly on rather than discovering in production."""

    @pytest.mark.parametrize("postcode", ["BT1 1AA", "BT9 5AA"])
    def test_northern_ireland_is_out_of_scope_for_code_point_open(self, postcode):
        # Code-Point Open covers Great Britain, not the United Kingdom. A NI
        # postcode is well-formed and will normalise, but will not resolve --
        # so any coverage figure must be stated as GB, never UK.
        assert place.normalise_postcode(postcode) is not None


class TestCrossCheck:
    """A published property reference can be wrong. Some in the school register
    point to the opposite end of the country, and a resolver that returns a
    coordinate for one of those has not verified anything."""

    def test_agreement_is_not_a_conflict(self, tmp_path, monkeypatch):
        from groundtruth import place as P
        monkeypatch.setattr(P, "resolve_uprn", lambda c, u:
            P.PlaceRef("uprn", 1.0, None, None, 51.5010, -0.1416, None))
        monkeypatch.setattr(P, "resolve_postcode", lambda c, p:
            P.PlaceRef("postcode", .95, None, None, 51.5012, -0.1418, "E09000033"))
        r = P.cross_check(None, 1, "SW1A 1AA")
        assert r["comparable"] and not r["conflict"] and r["metres"] < 100

    def test_cross_country_disagreement_is_flagged(self, tmp_path, monkeypatch):
        from groundtruth import place as P
        monkeypatch.setattr(P, "resolve_uprn", lambda c, u:
            P.PlaceRef("uprn", 1.0, None, None, 55.9503, -3.1930, None))   # Edinburgh
        monkeypatch.setattr(P, "resolve_postcode", lambda c, p:
            P.PlaceRef("postcode", .95, None, None, 51.5010, -0.1416, "E09000033"))  # London
        r = P.cross_check(None, 1, "SW1A 1AA")
        assert r["conflict"] and r["metres"] > 500_000

    def test_one_tier_alone_is_not_comparable(self, tmp_path, monkeypatch):
        from groundtruth import place as P
        monkeypatch.setattr(P, "resolve_uprn", lambda c, u: P.UNRESOLVED)
        monkeypatch.setattr(P, "resolve_postcode", lambda c, p:
            P.PlaceRef("postcode", .95, None, None, 51.5, -0.14, "E09000033"))
        r = P.cross_check(None, 1, "SW1A 1AA")
        assert r["comparable"] is False and r["conflict"] is False


class TestPropertyTierKeepsDistrict:
    """The property tier gives an exact coordinate but no LAD. If it returns
    without one, property-resolved records fall out of every by-district
    statistic -- which silently cut Catchment from 317 districts to 66."""

    def test_property_result_borrows_the_postcode_district(self, tmp_path, monkeypatch):
        from groundtruth import place as P
        # UPRN resolves to a point but no district; postcode carries the LAD.
        monkeypatch.setattr(P, "resolve_uprn", lambda c, u:
            P.PlaceRef("uprn", 1.0, 529090, 179645, 51.501, -0.142, None))
        monkeypatch.setattr(P, "resolve_postcode", lambda c, p:
            P.PlaceRef("postcode", .95, None, None, 51.5, -0.14, "E09000033", "E05000644"))
        ref = P.resolve(None, uprn=100, postcode="SW1A 1AA")
        assert ref.tier == "uprn"                 # keeps the precise tier
        assert ref.lad_code == "E09000033"        # and gains the district
        assert ref.latitude == 51.501             # coordinate unchanged

    def test_property_without_a_postcode_still_resolves(self, tmp_path, monkeypatch):
        from groundtruth import place as P
        monkeypatch.setattr(P, "resolve_uprn", lambda c, u:
            P.PlaceRef("uprn", 1.0, 1, 2, 51.5, -0.1, None))
        ref = P.resolve(None, uprn=100, postcode=None)
        assert ref.tier == "uprn" and ref.lad_code is None


class TestCoordinateTier:
    """A record with a location and no identifier could not reach a district:
    the UPRN file carries no LAD, so anything without a postcode fell out of
    every by-district statistic. This tier closes that, and must refuse rather
    than guess when nothing is near."""

    @staticmethod
    def _spine():
        import duckdb
        con = duckdb.connect(":memory:")
        con.execute("CREATE SCHEMA silver")
        con.execute("""CREATE TABLE silver.place_postcode(
            postcode_key VARCHAR, postcode VARCHAR, positional_quality INTEGER,
            easting INTEGER, northing INTEGER, lad_code VARCHAR,
            ward_code VARCHAR, country_code VARCHAR)""")
        con.execute("""INSERT INTO silver.place_postcode VALUES
            ('SW1A1AA','SW1A 1AA',10, 529090, 179645,'E09000033','E05013806','E92000001')""")
        return con

    def test_a_grid_reference_resolves_to_a_district(self):
        con = self._spine()
        ref = place.resolve_coordinate(con, 529100, 179650)
        assert ref.resolved and ref.tier == "coordinate"
        assert ref.lad_code == "E09000033"

    def test_it_refuses_beyond_its_radius(self):
        con = self._spine()
        # A point 5 km away. The nearest centroid is not an answer -- returning
        # it would be a fabricated resolution dressed as a real one.
        ref = place.resolve_coordinate(con, 534090, 179645)
        assert not ref.resolved
        assert ref.lad_code is None
        assert "within" in ref.note

    def test_confidence_never_beats_the_postcode_tier(self):
        con = self._spine()
        ref = place.resolve_coordinate(con, 529090, 179645)
        # Sitting exactly on a centroid is still only as good as that centroid.
        assert ref.confidence <= 0.60

    def test_it_survives_no_connection(self):
        assert not place.resolve_coordinate(None, 1, 2).resolved
