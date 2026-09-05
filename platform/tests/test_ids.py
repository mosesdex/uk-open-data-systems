"""Groundtruth identifiers.

The rule under test: an identifier is derived from the publisher's own key, so
the same thing gets the same identifier on any machine, in any order, after any
rebuild. Anything that cannot be quoted is refused rather than minted.
"""
import pytest

from groundtruth import ids


class TestDerivationIsStable:
    def test_same_key_gives_same_identifier(self):
        a = ids.entity_company("01234567")
        b = ids.entity_company("01234567")
        assert str(a) == str(b) == "gt:entity:company:01234567"

    def test_identifier_does_not_depend_on_load_order(self):
        # The reason for deriving rather than allocating: a sequential registry
        # would give these two different identifiers depending on which loaded
        # first, and two operators would disagree about the same property.
        first = [ids.place_uprn(100023336956), ids.place_uprn(200000000001)]
        second = [ids.place_uprn(200000000001), ids.place_uprn(100023336956)]
        assert {str(x) for x in first} == {str(x) for x in second}

    def test_round_trips_through_text(self):
        original = ids.event_contribution("DOV-17-01530-da-con-1", 111)
        assert ids.parse(str(original)) == original


class TestNormalisation:
    def test_company_number_padding_is_one_company(self):
        assert ids.entity_company("1234567") == ids.entity_company("01234567")

    def test_postcode_spacing_and_case_are_one_place(self):
        variants = ["SW1A 1AA", "sw1a1aa", " SW1A  1AA "]
        assert len({str(ids.place_postcode(v)) for v in variants}) == 1

    def test_float_shaped_uprn_is_not_a_second_property(self):
        # JSON hands numeric references back as floats often enough to matter.
        assert ids.place_uprn("100023336956.0") == ids.place_uprn(100023336956)


class TestRefusals:
    @pytest.mark.parametrize("kind,ns", [("place", "company"), ("nonsense", "uprn")])
    def test_unknown_kind_or_namespace_is_refused(self, kind, ns):
        with pytest.raises(ids.IdentifierError):
            ids.mint(kind, ns, "x")

    @pytest.mark.parametrize("key", ["", "   ", None])
    def test_empty_key_is_refused_not_silently_minted(self, key):
        # A minted identifier ends up in an export, and an export is forever.
        with pytest.raises(ids.IdentifierError):
            ids.mint("entity", "company", key)

    @pytest.mark.parametrize("text", ["entity:company:1", "gt:entity:1", "", "gt::x:y"])
    def test_malformed_text_does_not_parse(self, text):
        assert not ids.is_valid(text)


class TestShortForm:
    def test_is_stable_and_fixed_width(self):
        one = ids.short("gt:place:uprn:100023336956")
        assert one == ids.short("gt:place:uprn:100023336956")
        assert len(one) == 16

    def test_distinct_identifiers_do_not_collide_across_a_large_sample(self):
        seen = {ids.short(f"gt:place:uprn:{n}") for n in range(20000)}
        assert len(seen) == 20000


class TestPlanningReferencesAreNotNationallyUnique:
    """24,306 of 39,325 contributions share a reference with a contribution in a
    different council. An identifier on the bare reference merges them."""

    def test_same_reference_in_two_councils_is_two_identifiers(self):
        a = ids.event_contribution("CIL-OTH-00023", 150)
        b = ids.event_contribution("CIL-OTH-00023", 122)
        assert str(a) != str(b)
        assert str(a) == "gt:event:contribution:150/CIL-OTH-00023"

    def test_the_authority_is_required(self):
        with pytest.raises(ids.IdentifierError):
            ids.event_contribution("CIL-OTH-00023", None)

    def test_float_shaped_authority_is_the_same_authority(self):
        # organisation-entity arrives as a float from the publisher's JSON.
        assert ids.event_agreement("A-da", 111.0) == ids.event_agreement("A-da", 111)

    def test_the_two_halves_can_be_read_back(self):
        org, ref = ids.split_qualified(ids.event_contribution("C-1", 111))
        assert (org, ref) == ("111", "C-1")
