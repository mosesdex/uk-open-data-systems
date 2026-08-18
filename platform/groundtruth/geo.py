"""Coordinate conversion.

Ordnance Survey publishes eastings and northings on the British National Grid
(OSGB36 / Airy 1830). Web maps need WGS84. The conversion is a full datum shift,
not a reprojection, so a naive formula is out by roughly 100 metres -- enough to
put a property on the wrong side of a street, which defeats the point of a
place spine.

Implemented as: grid -> Airy 1830 lat/lon, then a Helmert transformation onto
WGS84. Verified against the worked example in the Ordnance Survey guide.
"""
from __future__ import annotations

import math

# Airy 1830 (OSGB36) and the National Grid projection
A_AIRY, B_AIRY = 6377563.396, 6356256.909
F0 = 0.9996012717
LAT0, LON0 = math.radians(49.0), math.radians(-2.0)
E0, N0 = 400000.0, -100000.0

# WGS84
A_WGS, B_WGS = 6378137.000, 6356752.3141

# Helmert, OSGB36 -> WGS84
TX, TY, TZ = 446.448, -125.157, 542.060
RXS, RYS, RZS = 0.1502, 0.2470, 0.8421          # arc-seconds
S_PPM = -20.4894


def _ecc_sq(a: float, b: float) -> float:
    return (a * a - b * b) / (a * a)


def grid_to_airy(easting: float, northing: float) -> tuple[float, float]:
    """National Grid easting/northing to OSGB36 latitude/longitude, in radians."""
    a, b = A_AIRY, B_AIRY
    e2 = _ecc_sq(a, b)
    n = (a - b) / (a + b)
    n2, n3 = n * n, n * n * n

    lat = LAT0
    m = 0.0
    for _ in range(100):
        lat = (northing - N0 - m) / (a * F0) + lat
        ma = (1 + n + 1.25 * n2 + 1.25 * n3) * (lat - LAT0)
        mb = (3 * n + 3 * n2 + 2.625 * n3) * math.sin(lat - LAT0) * math.cos(lat + LAT0)
        mc = (1.875 * n2 + 1.875 * n3) * math.sin(2 * (lat - LAT0)) * math.cos(2 * (lat + LAT0))
        md = (35 / 24) * n3 * math.sin(3 * (lat - LAT0)) * math.cos(3 * (lat + LAT0))
        m = b * F0 * (ma - mb + mc - md)
        if abs(northing - N0 - m) < 1e-5:
            break

    sin_lat = math.sin(lat)
    nu = a * F0 / math.sqrt(1 - e2 * sin_lat ** 2)
    rho = a * F0 * (1 - e2) / (1 - e2 * sin_lat ** 2) ** 1.5
    eta2 = nu / rho - 1

    tan_lat = math.tan(lat)
    t2, t4, t6 = tan_lat ** 2, tan_lat ** 4, tan_lat ** 6
    sec_lat = 1 / math.cos(lat)
    nu3, nu5, nu7 = nu ** 3, nu ** 5, nu ** 7

    vii = tan_lat / (2 * rho * nu)
    viii = tan_lat / (24 * rho * nu3) * (5 + 3 * t2 + eta2 - 9 * t2 * eta2)
    ix = tan_lat / (720 * rho * nu5) * (61 + 90 * t2 + 45 * t4)
    x = sec_lat / nu
    xi = sec_lat / (6 * nu3) * (nu / rho + 2 * t2)
    xii = sec_lat / (120 * nu5) * (5 + 28 * t2 + 24 * t4)
    xiia = sec_lat / (5040 * nu7) * (61 + 662 * t2 + 1320 * t4 + 720 * t6)

    de = easting - E0
    de2, de3, de4, de5, de6, de7 = de**2, de**3, de**4, de**5, de**6, de**7

    out_lat = lat - vii * de2 + viii * de4 - ix * de6
    out_lon = LON0 + x * de - xi * de3 + xii * de5 - xiia * de7
    return out_lat, out_lon


def _to_cartesian(lat: float, lon: float, h: float, a: float, b: float):
    e2 = _ecc_sq(a, b)
    nu = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    x = (nu + h) * math.cos(lat) * math.cos(lon)
    y = (nu + h) * math.cos(lat) * math.sin(lon)
    z = ((1 - e2) * nu + h) * math.sin(lat)
    return x, y, z


def _from_cartesian(x: float, y: float, z: float, a: float, b: float):
    e2 = _ecc_sq(a, b)
    lon = math.atan2(y, x)
    p = math.sqrt(x * x + y * y)
    lat = math.atan2(z, p * (1 - e2))
    for _ in range(20):
        nu = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
        new = math.atan2(z + e2 * nu * math.sin(lat), p)
        if abs(new - lat) < 1e-12:
            lat = new
            break
        lat = new
    return lat, lon


def airy_to_wgs84(lat: float, lon: float) -> tuple[float, float]:
    """Helmert datum shift from OSGB36 to WGS84."""
    x, y, z = _to_cartesian(lat, lon, 0.0, A_AIRY, B_AIRY)
    s = 1 + S_PPM * 1e-6
    rx, ry, rz = (math.radians(v / 3600) for v in (RXS, RYS, RZS))
    x2 = TX + s * x - rz * y + ry * z
    y2 = TY + rz * x + s * y - rx * z
    z2 = TZ - ry * x + rx * y + s * z
    return _from_cartesian(x2, y2, z2, A_WGS, B_WGS)


def bng_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """British National Grid to WGS84 (latitude, longitude) in degrees."""
    lat, lon = grid_to_airy(easting, northing)
    lat, lon = airy_to_wgs84(lat, lon)
    return math.degrees(lat), math.degrees(lon)
