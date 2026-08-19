import pytest

from groundtruth import store
from groundtruth.systems import junction as J


def _state(op, fields, rows, catalogue=None, status=200):
    return J.RegisterState(op, f"{op}-ecr", status, tuple(fields), rows, catalogue)


class TestExportParsing:
    def test_semicolon_delimited_export(self):
        fields, rows = J.parse_export("a;b;c\n1;2;3\n")
        assert fields == ["a", "b", "c"] and len(rows) == 1

    def test_header_only_export_is_zero_rows_not_an_error(self):
        """Three of four registers return exactly this: a schema and nothing else."""
        fields, rows = J.parse_export("a;b;c\n")
        assert fields == ["a", "b", "c"] and rows == []

    def test_empty_body(self):
        assert J.parse_export("") == ([], [])

    def test_comma_delimited_falls_back(self):
        fields, rows = J.parse_export("a,b\n1,2\n")
        assert fields == ["a", "b"] and len(rows) == 1


class TestCatalogueGap:
    def test_withheld_counts_records_the_open_route_never_returns(self):
        states = [
            _state("A", ["x"] * 60, 0, catalogue=4496),
            _state("B", ["x"] * 60, 937, catalogue=937),
        ]
        gap = J.catalogue_gap(states)
        assert gap["advertised"] == 5433
        assert gap["returned"] == 937
        assert gap["withheld"] == 4496
        assert gap["operators_serving_data"] == 1

    def test_a_register_serving_everything_withholds_nothing(self):
        assert _state("B", ["x"], 937, catalogue=937).withheld == 0

    def test_missing_catalogue_count_does_not_invent_a_gap(self):
        assert _state("C", ["x"], 0, catalogue=None).withheld == 0


class TestSchemaComparison:
    def test_standardised_registers_show_high_commonality(self):
        """The format is mandated and followed. An earlier version of this
        analysis reported 1.3% commonality because it compared genuine registers
        against an LTDS appendix table, which is a different return entirely."""
        shared = [f"f{i}" for i in range(51)]
        states = [
            _state("A", shared + ["a1", "a2"], 0),
            _state("B", shared + ["b1"], 937),
            _state("C", shared + ["c1", "c2", "c3"], 0),
        ]
        c = J.compare(states)
        assert c["shared_fields"] == 51
        assert c["shared_pct"] > 80

    def test_comparison_needs_at_least_two_schemas(self):
        c = J.compare([_state("A", [], 0)])
        assert c["comparable"] is False

    def test_capacity_fields_are_identified(self):
        fields = ["grid_supply_point", "registered_capacity_mw", "storage_capacity_1_mwh"]
        assert J.capacity_fields(fields) == [
            "registered_capacity_mw", "storage_capacity_1_mwh"]


class TestPersistence:
    def test_states_are_written_with_the_withheld_count(self, tmp_path):
        con = store.connect(tmp_path / "db")
        J.load(con, [_state("A", ["x"] * 60, 0, catalogue=4496)])
        row = con.execute("""SELECT operator, rows, catalogue_records, withheld,
                             publishes_schema, publishes_data
                             FROM gold.junction_register""").fetchone()
        assert row == ("A", 0, 4496, 4496, True, False)
        con.close()
