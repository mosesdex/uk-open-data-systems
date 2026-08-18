"""Guards on the no-registration rule.

These tests are the reason the rule is real rather than aspirational.
"""
import pytest

from groundtruth.fetch import (CredentialLeak, _assert_anonymous, _clean_session,
                               payload_problem)
from groundtruth import sources as S


class TestAnonymity:
    @pytest.mark.parametrize("header", [
        "Authorization", "Cookie", "X-API-Key", "api-key",
        "Ocp-Apim-Subscription-Key", "Proxy-Authorization",
    ])
    def test_rejects_every_form_of_credential(self, header):
        with pytest.raises(CredentialLeak):
            _assert_anonymous({header: "secret"})

    def test_allows_ordinary_headers(self):
        _assert_anonymous({"User-Agent": "groundtruth/0.1", "Accept": "*/*"})

    def test_session_carries_no_credentials(self):
        s = _clean_session()
        assert s.auth is None
        assert len(s.cookies) == 0
        assert s.trust_env is False          # ignores netrc and proxy credentials
        _assert_anonymous(s.headers)


class TestPayloadCheck:
    def test_matching_content_type_is_fine(self):
        assert payload_problem(b'{"items":[]}', "application/json", ("application/json",)) is None
        assert payload_problem(b"UPRN,X\n1,2", "text/csv;charset=utf-8", ("text/csv",)) is None

    def test_html_where_json_promised_is_rejected(self):
        # Regression: the energy certificate register answers 200 and serves an
        # ordinary GOV.UK landing page from another host -- no login form at all.
        # An earlier detector looked for sign-in wording and passed it through.
        body = (b"<!DOCTYPE html><html><head><title>Get energy performance of "
                b"buildings data</title></head><body>Cookies on this service "
                b"We use some essential cookies to make this service work.</body></html>")
        problem = payload_problem(body, "text/html;charset=utf-8", ("application/json",))
        assert problem is not None
        assert "not data" in problem

    def test_sign_in_wording_gives_a_more_specific_reason(self):
        body = b"<html><body>Please sign in with your password</body></html>"
        problem = payload_problem(body, "text/html", ("application/json",))
        assert problem is not None and "sign-in" in problem

    def test_undeclared_content_type_is_accepted(self):
        assert payload_problem(b"data", "", ("text/csv",)) is None

    def test_zip_accepted_for_archive_sources(self):
        assert payload_problem(b"PK\x03\x04", "application/zip",
                               ("application/zip", "application/octet-stream")) is None


class TestRegistry:
    def test_every_source_declares_a_licence(self):
        assert all(s.licence for s in S.REGISTRY)

    def test_blocked_sources_stay_in_the_registry(self):
        # Coverage figures are only trustworthy if unreachable sources are visible.
        assert any(s.blocked for s in S.REGISTRY)
        assert set(S.admissible()).issubset(set(S.REGISTRY))

    def test_ids_are_unique(self):
        ids = [s.id for s in S.REGISTRY]
        assert len(ids) == len(set(ids))

    def test_spines_are_populated(self):
        assert S.by_role("place_spine") and S.by_role("entity_spine")

    def test_unknown_source_names_the_alternatives(self):
        with pytest.raises(KeyError, match="unknown source"):
            S.get("nope")


class TestResolution:
    """Late-binding URLs. These hit the network, so they are marked."""

    @pytest.mark.network
    def test_resolves_versioned_os_filenames(self):
        from groundtruth.resolve import os_download_url
        url = os_download_url("LIDS", "BLPU-UPRN-Street-USRN")
        assert "BLPU-UPRN-Street-USRN" in url and url.startswith("https://api.os.uk/")

    @pytest.mark.network
    def test_unresolvable_pattern_lists_what_is_available(self):
        from groundtruth.resolve import os_download_url, ResolutionError
        with pytest.raises(ResolutionError, match="Available:"):
            os_download_url("LIDS", "no-such-pair")

    def test_date_substitution(self):
        from groundtruth.resolve import resolve
        url = resolve(S.get("gias_establishments"))
        assert "{date}" not in url and "edubasealldata20" in url
