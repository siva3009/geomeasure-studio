"""
CRS utility functions.
Handles UTM zone selection from geometry centroids and CRS validation.
"""

import pyproj
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def get_utm_epsg(lon: float, lat: float) -> int:
    """
    Determine the appropriate UTM EPSG code from a longitude/latitude point.

    UTM zones are 6° wide, numbered 1-60 from 180°W.
    North hemisphere uses EPSG:326xx, south uses EPSG:327xx.

    Args:
        lon: Longitude in degrees (-180 to 180).
        lat: Latitude in degrees (-90 to 90).

    Returns:
        EPSG code for the appropriate UTM zone.
    """
    # Clamp longitude to valid range
    lon = max(-180.0, min(180.0, lon))
    lat = max(-90.0, min(90.0, lat))

    zone_number = int((lon + 180) / 6) + 1
    # Clamp zone number to valid range (1-60)
    zone_number = max(1, min(60, zone_number))

    if lat >= 0:
        return 32600 + zone_number  # North hemisphere
    else:
        return 32700 + zone_number  # South hemisphere


def get_utm_crs_string(lon: float, lat: float) -> str:
    """
    Return the UTM CRS as an 'EPSG:XXXXX' string.

    Args:
        lon: Longitude in degrees.
        lat: Latitude in degrees.

    Returns:
        CRS string like 'EPSG:32643'.
    """
    return f"EPSG:{get_utm_epsg(lon, lat)}"


def is_geographic_crs(crs) -> bool:
    """
    Check if a CRS is geographic (lon/lat in degrees).

    Args:
        crs: A pyproj-compatible CRS object or string.

    Returns:
        True if the CRS is geographic, False if projected or unknown.
    """
    try:
        proj_crs = pyproj.CRS(crs)
        return proj_crs.is_geographic
    except Exception:
        return False


def crs_to_string(crs) -> Optional[str]:
    """
    Convert a CRS object to a human-readable string (preferably EPSG code).

    Args:
        crs: A pyproj-compatible CRS object.

    Returns:
        String representation like 'EPSG:4326', or the WKT if no EPSG.
    """
    if crs is None:
        return None
    try:
        proj_crs = pyproj.CRS(crs)
        epsg = proj_crs.to_epsg()
        if epsg:
            return f"EPSG:{epsg}"
        return proj_crs.to_wkt()
    except Exception:
        return str(crs)


def validate_crs(crs_string: str) -> bool:
    """
    Check if a CRS string is valid and recognized by pyproj.

    Args:
        crs_string: CRS identifier string.

    Returns:
        True if valid.
    """
    try:
        pyproj.CRS(crs_string)
        return True
    except Exception:
        return False
