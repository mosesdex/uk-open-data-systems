import pytest

from groundtruth.systems.catchment import is_mainstream, Coverage


class TestProvisionSplit:
    """Specialist provision reports capacity on a different basis.

    Measured on the live register: 12.5% of pupil referral units and 5.1% of
    special academies record more pupils than places, against 0.1-0.4% of
    mainstream schools. Blending them produces a utilisation figure that means
    nothing, so the split has to hold.
    """

    @pytest.mark.parametrize("t", [
        "Community school", "Academy converter", "Voluntary aided school",
        "Free schools", "Academy sponsor led", "Foundation school",
    ])
    def test_mainstream_types(self, t):
        assert is_mainstream(t) is True

    @pytest.mark.parametrize("t", [
        "Community special school", "Academy special converter",
        "Pupil referral unit", "Academy alternative provision converter",
        "Hospital school", "Non-maintained special school",
    ])
    def test_specialist_types(self, t):
        assert is_mainstream(t) is False

    def test_unknown_type_defaults_to_mainstream(self):
        # Safer to under-claim specialist pressure than to inflate it.
        assert is_mainstream("") is True
        assert is_mainstream(None) is True


class TestCoverage:
    def test_percentages(self):
        c = Coverage(total=100, resolved=97, with_capacity=88)
        assert c.resolved_pct == 97.0
        assert c.capacity_pct == 88.0

    def test_empty_input_does_not_divide_by_zero(self):
        c = Coverage(0, 0, 0)
        assert c.resolved_pct == 0.0 and c.capacity_pct == 0.0


class TestUnplacedReason:
    """A school with no district is explained from the register's own fields.
    Calling all of them out of scope was the first answer given, and it hid 18
    English schools; the classifier exists so the reason is read, not assumed."""

    @staticmethod
    def _r(*a, **k):
        from groundtruth.systems.catchment import unplaced_reason
        return unplaced_reason(*a, **k)

    def test_overseas_offshore_and_service_schools_are_outside_great_britain(self):
        for t in ("British schools overseas", "Offshore schools", "Service children's education"):
            assert self._r(t, "") == "outside_great_britain"

    def test_an_offshore_school_is_outside_even_with_a_postcode(self):
        # Jersey, Guernsey and Isle of Man postcodes are not in a GB register.
        assert self._r("Offshore schools", "JE2 7XB") == "outside_great_britain"

    def test_online_and_welsh(self):
        assert self._r("Online provider", "") == "online_only"
        assert self._r("Welsh establishment", "NP20 1AA") == "in_wales"

    def test_an_english_school_is_never_called_out_of_scope(self):
        assert self._r("Free schools", "BS1 1AA") == "postcode_not_in_register"
        assert self._r("Sixth form centres", "") == "no_location_in_record"
        assert self._r("Academy converter", "BB1 1AA", located=True) == "located_no_district"

    def test_a_curly_apostrophe_still_classifies(self):
        # cp1252 read as latin-1 turns U+2019 into \x92; both must match.
        assert self._r("Service children\u2019s education", "") == "outside_great_britain"
        assert self._r("Service children\x92s education", "") == "outside_great_britain"

