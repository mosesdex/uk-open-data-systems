"""The corrected-claims archive.

The rule under test: a correction stays visible, names how it was caught, and
says honestly whether anything now stops it recurring.
"""
from groundtruth import claims as C


class TestArchive:
    def test_every_entry_says_what_was_believed_and_what_is_true(self):
        for c in C.ARCHIVE:
            assert c.believed and c.actually, f"{c.id} is missing one half"
            assert c.believed != c.actually
            assert c.how_caught, f"{c.id} does not say how it was caught"

    def test_identifiers_are_unique(self):
        assert len({c.id for c in C.ARCHIVE}) == len(C.ARCHIVE)

    def test_unguarded_corrections_are_reported_not_hidden(self):
        """A correction with no test behind it can happen again tomorrow, and
        saying so is more useful than leaving the field blank."""
        s = C.summary()
        assert s["guarded"] + s["unguarded"] == s["total"]

    def test_the_ledger_overclaim_is_recorded(self):
        entry = next(c for c in C.ARCHIVE if c.id == "ledger-fills-the-gap")
        assert "0.16%" in entry.actually
        assert entry.guarded

    def test_payload_is_serialisable_for_the_site(self):
        import json
        json.dumps(C.as_payload())
