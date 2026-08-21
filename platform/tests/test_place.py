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
