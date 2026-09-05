import pytest

from groundtruth.geo import ngr_to_bng, ngr_to_wgs84


class TestGridReferences:
    """An outlet placed in the wrong 100 km square is worse than one with no
    location at all, so a malformed reference must return None, not a guess."""

    @pytest.mark.parametrize("ref,expect", [
        ("TQ 30000 80000", (530000, 180000)),
        ("TQ3000080000", (530000, 180000)),
        ("tq 30000 80000", (530000, 180000)),
        ("SU 12345 67890", (412345, 167890)),
        ("NT 25000 73000", (325000, 673000)),
        ("SX 1234 5678", (212340, 56780)),
    ])
    def test_valid_references(self, ref, expect):
        assert ngr_to_bng(ref) == expect

    @pytest.mark.parametrize("ref", [
        "", None, "BAD", "TQ", "TQ 300 8000", "TQ 12345",
        "II 12345 67890", "TQ ABCDE FGHIJ", "TQ 123456789012",
    ])
    def test_malformed_references_return_none(self, ref):
        assert ngr_to_bng(ref) is None

    def test_precision_scales_with_digit_count(self):
        # Fewer digits means a coarser square, not a different place.
        assert ngr_to_bng("TQ 3 8") == (530000, 180000)
        assert ngr_to_bng("TQ 30 80") == (530000, 180000)

    def test_converts_to_wgs84(self):
        lat, lon = ngr_to_wgs84("TQ 30000 80000")
        assert 51.4 < lat < 51.6 and -0.3 < lon < 0.0


class TestAvailabilityAdjustment:
    """A monitor that was off for half the year under-reports by half."""

    def test_half_watched_outlet_doubles_when_adjusted(self, tmp_path):
        from groundtruth import store
        con = store.connect(tmp_path / "db")
        con.execute("""CREATE TABLE silver.storm_overflow (
            year INTEGER, unique_id VARCHAR, company VARCHAR, site_name VARCHAR,
            permit VARCHAR, asset_type VARCHAR, ngr VARCHAR, easting INTEGER,
            northing INTEGER, latitude DOUBLE, longitude DOUBLE,
            receiving_water VARCHAR, bathing_water VARCHAR, spills DOUBLE,
            long_term_average DOUBLE, operational_pct DOUBLE)""")
        con.execute("""INSERT INTO silver.storm_overflow VALUES
            (2025,'A','Co','Site A',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,10,NULL,50),
            (2025,'B','Co','Site B',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,10,NULL,100)""")
        from groundtruth.systems import baseline as BL
        BL.build(con)
        rows = {r[0]: r[1] for r in con.execute(
            "SELECT unique_id, spills_full_year_equivalent FROM gold.baseline_outlet").fetchall()}
        assert rows["A"] == 20.0, "a half-watched outlet must adjust upward"
        assert rows["B"] == 10.0, "a fully watched outlet must not move"
        con.close()

    def test_zero_availability_does_not_divide_by_zero(self, tmp_path):
        from groundtruth import store
        from groundtruth.systems import baseline as BL
        con = store.connect(tmp_path / "db")
        con.execute("""CREATE TABLE silver.storm_overflow (
            year INTEGER, unique_id VARCHAR, company VARCHAR, site_name VARCHAR,
            permit VARCHAR, asset_type VARCHAR, ngr VARCHAR, easting INTEGER,
            northing INTEGER, latitude DOUBLE, longitude DOUBLE,
            receiving_water VARCHAR, bathing_water VARCHAR, spills DOUBLE,
            long_term_average DOUBLE, operational_pct DOUBLE)""")
        con.execute("""INSERT INTO silver.storm_overflow VALUES
            (2025,'A','Co','Dark',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0,NULL,0)""")
        BL.build(con)
        assert con.execute(
            "SELECT spills_full_year_equivalent FROM gold.baseline_outlet").fetchone()[0] is None
        con.close()


class TestWeatherNormalisation:
    """Separating what the network did from what the sky did. A fall in spills
    in a drier year tells you less than a fall in a wet one."""

    def _seed(self, con, outlets, stations):
        # build() derives baseline_outlet from silver.storm_overflow, so seed
        # that (the real pipeline shape) and let build compute the rest.
        con.execute("""CREATE TABLE silver.storm_overflow (
            year INTEGER, unique_id VARCHAR, company VARCHAR, site_name VARCHAR,
            permit VARCHAR, asset_type VARCHAR, ngr VARCHAR, easting INTEGER,
            northing INTEGER, latitude DOUBLE, longitude DOUBLE,
            receiving_water VARCHAR, bathing_water VARCHAR, spills DOUBLE,
            long_term_average DOUBLE, operational_pct DOUBLE)""")
        con.executemany("""INSERT INTO silver.storm_overflow VALUES
            (2025,?,?,?,NULL,NULL,NULL,NULL,NULL,?,?,NULL,NULL,?,NULL,100)""",
            [(o[0], o[1], o[2], o[3], o[4], o[5]) for o in outlets])
        con.execute("""CREATE TABLE silver.rainfall_station (
            station VARCHAR, label VARCHAR, lat DOUBLE, long DOUBLE,
            annual_mm DOUBLE, days INTEGER)""")
        con.executemany("INSERT INTO silver.rainfall_station VALUES (?,?,?,?,?,?)", stations)

    def test_rate_uses_the_nearest_station(self, tmp_path):
        from groundtruth import store
        from groundtruth.systems import baseline as BL
        con = store.connect(tmp_path / "db")
        # one outlet at 54,-1 spilling 100; a station beside it at 1000mm and a
        # far one at 100mm. The near station must be used: 100/1000*100 = 10.
        self._seed(con,
            [("o1", "WaterCo", "Site", 54.0, -1.0, 100.0)],
            [("near", "Near", 54.0, -1.0, 1000.0, 365),
             ("far",  "Far",  50.0,  1.0,  100.0, 365)])
        BL.build(con)
        rate = con.execute(
            "SELECT spills_per_100mm_rain FROM gold.baseline_rainfall").fetchone()[0]
        assert rate == 10.0
        con.close()

    def test_wetter_area_gets_a_lower_adjusted_rate_for_equal_spills(self, tmp_path):
        from groundtruth import store
        from groundtruth.systems import baseline as BL
        con = store.connect(tmp_path / "db")
        self._seed(con,
            [("dry", "DryCo", "S", 54.0, -1.0, 100.0),
             ("wet", "WetCo", "S", 50.0,  1.0, 100.0)],
            [("d", "D", 54.0, -1.0,  500.0, 365),
             ("w", "W", 50.0,  1.0, 2000.0, 365)])
        BL.build(con)
        rows = {r[0]: r[4] for r in con.execute(
            "SELECT * FROM gold.baseline_rainfall").fetchall()}
        # same 100 spills, but the wet company's rate is a quarter of the dry one
        assert rows["DryCo"] > rows["WetCo"]
        assert rows["DryCo"] == 20.0 and rows["WetCo"] == 5.0
        con.close()

    def test_no_rainfall_table_gives_empty_result(self, tmp_path):
        from groundtruth import store
        from groundtruth.systems import baseline as BL
        con = store.connect(tmp_path / "db")
        con.execute("""CREATE TABLE silver.storm_overflow (
            year INTEGER, unique_id VARCHAR, company VARCHAR, site_name VARCHAR,
            permit VARCHAR, asset_type VARCHAR, ngr VARCHAR, easting INTEGER,
            northing INTEGER, latitude DOUBLE, longitude DOUBLE,
            receiving_water VARCHAR, bathing_water VARCHAR, spills DOUBLE,
            long_term_average DOUBLE, operational_pct DOUBLE)""")
        con.execute("""INSERT INTO silver.storm_overflow VALUES
            (2025,'o','Co','S',NULL,NULL,NULL,NULL,NULL,54.0,-1.0,NULL,NULL,10,NULL,100)""")
        BL.build(con)
        assert con.execute("SELECT count(*) FROM gold.baseline_rainfall").fetchone()[0] == 0
        con.close()
