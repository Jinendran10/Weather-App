"""
Input validators for dates and location strings.
"""

import re
from datetime import date
from typing import Tuple, Optional


# One coordinate: an optional hemisphere letter before or after a signed decimal number.
_COORDINATE = r"([NSEW])?\s*(-?\d{1,3}(?:\.\d+)?)\s*([NSEW])?"
_GPS_PATTERN = re.compile(rf"^{_COORDINATE}\s*[,\s]\s*{_COORDINATE}$")
_HEMISPHERE_SIGN = {"N": 1, "E": 1, "S": -1, "W": -1}


def _apply_hemisphere(prefix: Optional[str], number: str, suffix: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
    """Return the coordinate signed by its hemisphere letter (S and W are negative), and the letter."""
    if prefix and suffix:
        return None, None
    letter = prefix or suffix
    value = float(number)
    if letter:
        if value < 0:  # "S-33.8" contradicts itself
            return None, None
        value *= _HEMISPHERE_SIGN[letter]
    return value, letter


def is_gps_coordinates(input_str: str) -> Optional[Tuple[float, float]]:
    """
    Detect and parse GPS coordinate strings.
    Supports formats:
      - "48.8566, 2.3522"
      - "48.8566,2.3522"
      - "48.8566 2.3522"
      - "-33.8688, 151.2093"
      - "N48.8566 E2.3522" / "48.8566N 2.3522E" / "48.8566° N, 2.3522° E"
      - "S33.8688 W151.2093" (S and W become negative)
      - "E2.3522 N48.8566" (letters decide which value is the latitude)
    Returns (latitude, longitude) or None.
    """
    cleaned = input_str.strip().upper().replace("°", "")
    m = _GPS_PATTERN.match(cleaned)
    if not m:
        return None
    first, first_letter = _apply_hemisphere(*m.group(1, 2, 3))
    second, second_letter = _apply_hemisphere(*m.group(4, 5, 6))
    if first is None or second is None:
        return None

    lon_first = first_letter in ("E", "W") or second_letter in ("N", "S")
    lat_first = first_letter in ("N", "S") or second_letter in ("E", "W")
    if lon_first and lat_first:  # e.g. "N48 N2": both values claim the same axis
        return None
    lat, lon = (second, first) if lon_first else (first, second)

    if -90 <= lat <= 90 and -180 <= lon <= 180:
        return lat, lon
    return None


def is_zip_code(input_str: str) -> bool:
    """
    Detect common ZIP / postal code formats.
    US: 12345 or 12345-6789
    UK: EC1A 1BB
    Canada: A1A 1A1
    Generic numeric: up to 10 digits
    """
    patterns = [
        r"^\d{5}(-\d{4})?$",                # US ZIP
        r"^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$",  # UK Postcode
        r"^[A-Z]\d[A-Z]\s*\d[A-Z]\d$",     # Canadian Postal Code
        r"^\d{4,10}$",                       # Generic numeric
    ]
    stripped = input_str.strip().upper()
    return any(re.match(p, stripped) for p in patterns)


def validate_date_range(date_from: date, date_to: date) -> None:
    """
    Raises ValueError if the date range is invalid.
    """
    if date_from > date_to:
        raise ValueError("date_from must be on or before date_to.")

    delta = (date_to - date_from).days
    if delta > 365:
        raise ValueError("Date range cannot exceed 365 days.")


def sanitize_location_input(raw: str) -> str:
    """Strip dangerous characters while preserving legitimate location characters."""
    # Allow unicode letters, numbers, spaces, commas, dots, hyphens, apostrophes, parens
    sanitized = re.sub(r"[^\w\s,.\-'()°]+", " ", raw, flags=re.UNICODE)
    return " ".join(sanitized.split()).strip()
