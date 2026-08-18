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
