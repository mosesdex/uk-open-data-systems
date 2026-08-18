"""Coordinate conversion.

The datum shift matters: skipping it puts a point ~100 m out, which is enough
to place a property on the wrong side of a street.
"""
import math

import pytest

from groundtruth.geo import bng_to_wgs84, grid_to_airy


def test_matches_the_ordnance_survey_worked_example():
    """OS guide: grid 651409.903 E, 313177.270 N -> OSGB36 52 39 27.2531 N, 1 43 04.5177 E."""
    lat, lon = grid_to_airy(651409.903, 313177.270)
    assert math.degrees(lat) == pytest.approx(52.6575703, abs=1e-6)
    assert math.degrees(lon) == pytest.approx(1.7179215, abs=1e-6)


# Grid references are the real Code-Point Open centroids for these postcodes;
# the expected latitudes and longitudes are independently known locations.
# The authoritative check on the maths is the OS worked example above.
@pytest.mark.parametrize("easting,northing,lat,lon,name", [
    (529090, 179645, 51.5010, -0.1416, "SW1A 1AA, Buckingham Palace"),
    (325597, 673676, 55.9503, -3.1930, "EH1 1YZ, Edinburgh"),
    (384756, 398553, 53.4835, -2.2312, "M1 1AE, Manchester"),
    (412570, 286423, 52.4756, -1.8164, "B33 8TH, Birmingham"),
    (318200, 175860, 51.4758, -3.1792, "CF10 1EP, Cardiff"),
])
def test_known_places_land_where_they_should(easting, northing, lat, lon, name):
    got_lat, got_lon = bng_to_wgs84(easting, northing)
    assert got_lat == pytest.approx(lat, abs=0.002), name
    assert got_lon == pytest.approx(lon, abs=0.002), name


def test_datum_shift_is_actually_applied():
    """WGS84 must differ from raw OSGB36 by roughly 100 m, not be identical."""
    e, n = 651409.903, 313177.270
    airy_lat, airy_lon = (math.degrees(v) for v in grid_to_airy(e, n))
    wgs_lat, wgs_lon = bng_to_wgs84(e, n)
    metres = math.hypot((wgs_lat - airy_lat) * 111_320,
                        (wgs_lon - airy_lon) * 111_320 * math.cos(math.radians(wgs_lat)))
    assert 50 < metres < 200, f"datum shift looks wrong: {metres:.0f} m"
