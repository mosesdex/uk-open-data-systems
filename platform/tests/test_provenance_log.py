"""A byte in the database carries a record of where it came from.

Backfill steps wrote files with no fetch-log row, so the audit could say the
data was present but not when it arrived or what it was. And the admin looked
for each source's file under one name, so data that arrived under another name
or in parts was reported as absent.
"""
import time
from pathlib import Path
from types import SimpleNamespace

from groundtruth import admin, audit, cli, store
from groundtruth import sources as S


def _res(name, detail="120 stations, 2025", ok=True):
    return SimpleNamespace(name=name, ok=ok, detail=detail, bytes=2)


class TestBackfillIsLogged:
    def test_a_step_is_logged_with_the_files_checksum(self, tmp_path):
        con = store.connect(tmp_path / "db")
        (tmp_path / "rainfall_annual_2025.json").write_text("{}")
        src = next(s for s in S.REGISTRY if s.needs_backfill == "rainfall")
        n = cli._record_backfill(con, "run1", "rainfall", _res("rainfall_annual_2025.json"),
                                 started=time.time(), bronze=tmp_path)
        assert n == 1
        sid, ok, sha, size = con.execute(
            "SELECT source_id, ok, sha256, bytes_len FROM bronze.fetch_log").fetchone()
        assert (sid, ok, size) == (src.id, True, 2) and len(sha) == 64

    def test_a_step_that_found_its_file_complete_records_nothing(self, tmp_path):
        con = store.connect(tmp_path / "db")
        assert cli._record_backfill(con, "run1", "rainfall", _res("x.json", "already complete"),
                                    started=time.time(), bronze=tmp_path) == 0


class TestDataUnderAnotherName:
    def test_a_source_in_several_parts_is_found_and_sized_in_full(self, tmp_path):
        for i in (1, 2):
            (tmp_path / f"psc-snapshot-2026-08-20_{i}of32.zip").write_bytes(b"x" * 10)
        assert admin._on_disk(tmp_path, "ch_psc") == "psc-snapshot-*.zip"
        assert sum(p.stat().st_size for p in Path(tmp_path).glob("psc-snapshot-*.zip")) == 20


class TestWhoServesASource:
    def test_publisher_delegated_and_third_party_are_told_apart(self):
        assert audit.source_authority("https://www.gov.uk/x") == audit.PUBLISHER
        assert audit.source_authority("https://services1.arcgis.com/x") == audit.DELEGATED
        assert audit.source_authority("https://www.planit.org.uk/api") == audit.THIRD_PARTY


class TestWhatAnotherMachineCanReproduce:
    def test_backfill_outputs_are_not_reported_as_hand_fetched(self, tmp_path):
        (tmp_path / "psc-snapshot-2026-08-20_1of32.zip").write_bytes(b"x")
        (tmp_path / "dno_ecr.json").write_text("{}")
        g = admin.registry_gaps(tmp_path)
        assert g["backfilled"] == {"psc": 1}
        assert g["unregistered"] == ["dno_ecr.json"]

    def test_every_file_a_backfill_step_writes_is_accounted_for(self):
        import fnmatch
        import re
        src = (Path(admin.__file__).parent / "backfill.py").read_text()
        ids = {s.id + x for s in S.REGISTRY
               for x in (".csv", ".json", ".geojson", ".zip", ".xml", ".ods", ".bin")}
        for name in re.findall(r'dest = bronze / f?"([^"]+)"', src):
            pat = re.sub(r"\{[^}]*\}", "*", name)
            if pat.startswith("*"):
                continue                     # a stem shared with a registry id
            probe = pat.replace("*", "x")
            assert probe in ids or any(fnmatch.fnmatch(probe, p) for p in admin.BACKFILL_OUTPUTS), name
