"""
Input validators for dates and location strings.
"""

import re
from datetime import date
from typing import Tuple, Optional


def is_gps_coordinates(input_str: str) -> Optional[Tuple[float, float]]:
    """
    Detect and parse GPS coordinate strings.
    Supports formats:
      - "48.8566, 2.3522"
      - "48.8566,2.3522"
      - "48.8566 2.3522"
      - "N48.8566 E2.3522"
    Returns (latitude, longitude) or None.
    """
    # Remove directional letters
    cleaned = input_str.strip().upper()
    cleaned = re.sub(r"[NSEW]", "", cleaned)
    # Try comma or space separated pair of floats
    pattern = r"^(-?\d{1,3}(?:\.\d+)?)\s*[,\s]\s*(-?\d{1,3}(?:\.\d+)?)$"
    m = re.match(pattern, cleaned.strip())
    if m:
        lat, lon = float(m.group(1)), float(m.group(2))
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
