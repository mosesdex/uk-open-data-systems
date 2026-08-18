"""The entity spine.

The rule under test throughout: an identifier beats a name, a name match is
scored rather than silent, and ambiguity is reported rather than guessed.
"""
import pytest

from groundtruth import entity as E


class TestCompanyNumbers:
    @pytest.mark.parametrize("raw,expect", [
        ("1234567", "01234567"), ("01234567", "01234567"),
        ("SC123456", "SC123456"), ("  12345678 ", "12345678"),
    ])
    def test_normalises_to_eight_characters(self, raw, expect):
        assert E.normalise_company_number(raw) == expect

    @pytest.mark.parametrize("raw", ["abc", "123", "", None, "SW1A 1AA"])
    def test_rejects_things_that_are_not_company_numbers(self, raw):
        assert E.normalise_company_number(raw) is None


class TestNameNormalisation:
    def test_collapses_the_many_spellings_of_one_company(self):
        variants = ["SOFTCAT PLC - FCA", "Softcat plc",
                    "SOFTCAT PUBLIC LIMITED COMPANY", "  softcat  "]
        assert len({E.normalise_name(v) for v in variants}) == 1

    def test_does_not_merge_group_and_holdings_entities(self):
        # "X Group Ltd" and "X Holdings Ltd" are routinely separate companies
        # with separate numbers. Collapsing them would be a false merge.
        assert E.normalise_name("Softcat Group Limited") != E.normalise_name("Softcat plc")
        assert E.normalise_name("Northern Care Group Ltd") != \
               E.normalise_name("Northern Care Holdings Ltd")
        assert E.normalise_name("Acme UK Ltd") != E.normalise_name("Acme Ltd")

    def test_strips_regulator_decoration(self):
        assert E.normalise_name("ACME LTD - FCA") == E.normalise_name("Acme Limited")

    def test_keeps_genuinely_different_names_apart(self):
        assert E.normalise_name("United Learning") != E.normalise_name("Delta Academies")


class TestResolution:
    def test_an_identifier_wins_and_needs_no_matching(self):
        ref = E.resolve(company_number="SC776044", name="DGS DUNDEE LTD")
        assert ref.method == "identifier" and ref.confidence == 1.0
        assert ref.company_number == "SC776044"

    def test_exact_name_match_is_high_but_not_certain(self):
        index = E.build_index([("12602755", "MAJESTIC TRANSPORT LTD")])
        ref = E.resolve(name="Majestic Transport Limited", index=index)
        assert ref.resolved and ref.method == "name"
        assert ref.confidence < 1.0, "only an identifier may score 1.0"

    def test_two_companies_sharing_a_name_is_ambiguous_not_a_guess(self):
        index = E.build_index([("11111111", "ACME LTD"), ("22222222", "Acme Limited")])
        ref = E.resolve(name="ACME", index=index)
        assert not ref.resolved
        assert len(ref.candidates) == 2 and "ambiguous" in ref.note

    def test_a_fuzzy_match_never_auto_accepts(self):
        index = E.build_index([("11111111", "NORTHERN CARE SERVICES LTD")])
        ref = E.resolve(name="Northern Care Services Yorkshire", index=index)
        assert ref.confidence < E.ACCEPT, "a name match must never auto-accept"
        if ref.resolved:
            assert ref.needs_review

    def test_no_candidate_resolves_to_nothing(self):
        index = E.build_index([("11111111", "ACME LTD")])
        ref = E.resolve(name="Totally Unrelated Business", index=index)
        assert not ref.resolved

    def test_a_name_with_no_index_cannot_resolve(self):
        assert not E.resolve(name="ACME LTD").resolved


class TestGazette:
    def test_extracts_number_and_postcode(self, tmp_path):
        import json
        from groundtruth.gazette import parse
        doc = {"entry": [
            {"id": "1", "title": "DGS DUNDEE LTD",
             "category": {"@term": "Appointment of Liquidators"},
             "content": "<div><p>DGS DUNDEE LTD ( SC776044 ) Address, Dundee, DD1 4AA</p></div>"},
            {"id": "2", "title": "BOOKER COMMERCIAL LIMITED",
             "category": {"@term": "Notices to Creditors"},
             "content": "<div><p>Company Address Unit 18, Barnsley, S75 3LS</p></div>"},
        ]}
        p = tmp_path / "g.json"; p.write_text(json.dumps(doc))
        notices = parse(p)
        assert notices[0].identified and notices[0].company_number == "SC776044"
        # Measured on the live feed: notices to creditors omit the number, but
        # still print an address -- so the place spine can locate what the
        # entity spine cannot identify.
        assert not notices[1].identified
        assert notices[1].locatable and notices[1].postcode == "S75 3LS"
