"""
Tests for CRS utility functions.
"""

import pytest
from app.utils.crs_utils import (
    get_utm_epsg,
    get_utm_crs_string,
    is_geographic_crs,
    crs_to_string,
    validate_crs,
)


class TestGetUtmEpsg:
    """Tests for UTM zone selection from lon/lat."""

    def test_new_delhi_utm_zone_43n(self):
        """New Delhi (77.2°E, 28.6°N) should be in UTM zone 43N (EPSG:32643)."""
        assert get_utm_epsg(77.2, 28.6) == 32643

    def test_london_utm_zone_30n(self):
        """London (-0.1°W, 51.5°N) should be in UTM zone 30N (EPSG:32630)."""
        # Longitude -0.1 → zone (180 - 0.1) / 6 + 1 = 30
        assert get_utm_epsg(-0.1, 51.5) == 32630

    def test_sydney_utm_zone_56s(self):
        """Sydney (151.2°E, -33.9°S) should be in UTM zone 56S (EPSG:32756)."""
        assert get_utm_epsg(151.2, -33.9) == 32756

    def test_equator_prime_meridian(self):
        """0°, 0° should be UTM zone 31N (EPSG:32631)."""
        assert get_utm_epsg(0.0, 0.0) == 32631

    def test_negative_180(self):
        """Dateline at -180° should give zone 1."""
        epsg = get_utm_epsg(-180.0, 45.0)
        assert epsg == 32601

    def test_returns_south_for_negative_lat(self):
        """Negative latitude should give 327xx codes."""
        epsg = get_utm_epsg(77.0, -10.0)
        assert epsg >= 32700


class TestGetUtmCrsString:
    def test_returns_epsg_string(self):
        result = get_utm_crs_string(77.2, 28.6)
        assert result == "EPSG:32643"


class TestIsGeographicCrs:
    def test_epsg_4326_is_geographic(self):
        assert is_geographic_crs("EPSG:4326") is True

    def test_utm_is_not_geographic(self):
        assert is_geographic_crs("EPSG:32643") is False

    def test_invalid_crs_returns_false(self):
        assert is_geographic_crs("NOT_A_CRS") is False


class TestCrsToString:
    def test_epsg_4326(self):
        result = crs_to_string("EPSG:4326")
        assert result == "EPSG:4326"

    def test_none_returns_none(self):
        assert crs_to_string(None) is None


class TestValidateCrs:
    def test_valid_epsg(self):
        assert validate_crs("EPSG:4326") is True

    def test_invalid_string(self):
        assert validate_crs("FAKE:9999") is False
