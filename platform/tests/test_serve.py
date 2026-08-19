import json

import pytest

from groundtruth import serve


class TestLoopbackOnly:
    """An operator running this on a laptop on a shared network must not find
    they have exposed a dashboard to it."""

    def test_bind_address_is_loopback(self):
        assert serve.LOOPBACK == "127.0.0.1"

    def test_free_port_returns_a_bindable_loopback_port(self):
        import socket
        port = serve.free_port(8899)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((serve.LOOPBACK, port))        # must be free

    def test_free_port_steps_past_a_busy_port(self):
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
            busy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            busy.bind((serve.LOOPBACK, 0))
            taken = busy.getsockname()[1]
            busy.listen(1)
            assert serve.free_port(taken) != taken


class TestPayloadCheck:
    def test_missing_payload_is_reported_not_raised(self, tmp_path):
        ok, detail = serve.check_payload(tmp_path)
        assert ok is False and "gt run" in detail

    def test_unreadable_payload_is_reported(self, tmp_path):
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "platform.json").write_text("{not json")
        ok, detail = serve.check_payload(tmp_path)
        assert ok is False and "unreadable" in detail

    def test_empty_payload_is_not_treated_as_ready(self, tmp_path):
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "platform.json").write_text(json.dumps({"built_systems": []}))
        ok, detail = serve.check_payload(tmp_path)
        assert ok is False and "no system output" in detail

    def test_real_payload_reports_system_count(self, tmp_path):
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "platform.json").write_text(json.dumps(
            {"built_systems": ["catchment", "ledger"], "generated": "2026-08-19T11:00:00+00:00"}))
        ok, detail = serve.check_payload(tmp_path)
        assert ok and "2 systems" in detail


class TestServeGuards:
    def test_missing_interface_directory_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            serve.serve(tmp_path / "nope", open_browser=False)
