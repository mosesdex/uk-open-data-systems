import pytest

from groundtruth import store
from groundtruth.run import RunReport, StageResult, _stage, build_everything


class TestStageIsolation:
    """A platform that stops at the first unreachable publisher is useless for a
    corpus this size. A failing stage must be recorded, not raised."""

    def test_a_failing_stage_is_recorded_and_the_run_continues(self):
        r = RunReport()
        _stage(r, "good", lambda: "fine")
        _stage(r, "bad", lambda: (_ for _ in ()).throw(FileNotFoundError("missing.csv")))
        _stage(r, "after", lambda: "still ran")
        assert [s.name for s in r.stages] == ["good", "bad", "after"]
        assert [s.ok for s in r.stages] == [True, False, True]
        assert "FileNotFoundError" in r.stages[1].detail
        assert r.ok is False and len(r.failed) == 1

    def test_a_clean_run_reports_ok(self):
        r = RunReport()
        _stage(r, "a", lambda: "x")
        assert r.ok and r.failed == []

    def test_stage_detail_is_truncated_not_unbounded(self):
        r = RunReport()
        _stage(r, "noisy", lambda: (_ for _ in ()).throw(ValueError("x" * 5000)))
        assert len(r.stages[0].detail) <= 200

    def test_stage_records_elapsed_time(self):
        r = RunReport()
        _stage(r, "timed", lambda: "done")
        assert r.stages[0].seconds >= 0


class TestMissingInputs:
    def test_every_stage_fails_cleanly_with_no_bronze_data(self, tmp_path):
        """With nothing fetched, the run must complete and report each failure
        rather than crashing partway."""
        con = store.connect(tmp_path / "db")
        report = build_everything(con, tmp_path / "empty")
        assert len(report.stages) >= 14
        assert report.failed, "stages with no inputs should be marked failed"
        # chains still runs: it reports zero rather than throwing
        chains = [s for s in report.stages if s.name == "chains"]
        assert chains and chains[0].ok
        con.close()
