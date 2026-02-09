# -*- coding: utf-8 -*-
"""Unified date parsing utilities for bank statement importers.

This module consolidates all date parsing logic from various importers to provide
a single source of truth for date format handling.
"""
import re
from datetime import datetime
from typing import Optional


# Spanish month abbreviations mapping
MONTHS_ES = {
    "ene": "01", "enero": "01",
    "feb": "02", "febrero": "02",
    "mar": "03", "marzo": "03",
    "abr": "04", "abril": "04",
    "may": "05", "mayo": "05",
    "jun": "06", "junio": "06",
    "jul": "07", "julio": "07",
    "ago": "08", "agosto": "08",
    "sep": "09", "septiembre": "09",
    "oct": "10", "octubre": "10",
    "nov": "11", "noviembre": "11",
    "dic": "12", "diciembre": "12",
}

# Compiled regex patterns for performance
DATE_ES_RE = re.compile(r"^\s*(\d{1,2})/([A-Za-z]{3,10})/(\d{2,4})\s*$")
DATE_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_spanish_date(date_str: str) -> Optional[str]:
    """Parse Spanish date format to ISO format (YYYY-MM-DD).

    Supports formats:
    - "DD/MMM/YY" (e.g., "30/ene/26" -> "2026-01-30")
    - "DD/MMM/YYYY" (e.g., "15/ene/2024" -> "2024-01-15")
    - "YYYY-MM-DD" (already ISO format, passed through)

    Args:
        date_str: Date string in Spanish format

    Returns:
        ISO format date string (YYYY-MM-DD), or None if parsing fails

    Examples:
        >>> parse_spanish_date("30/ene/26")
        '2026-01-30'
        >>> parse_spanish_date("15/enero/2024")
        '2024-01-15'
        >>> parse_spanish_date("2024-01-15")
        '2024-01-15'
    """
    if date_str is None:
        return None

    s = str(date_str).strip()

    # If already ISO format (YYYY-MM-DD), return as-is
    if DATE_ISO_RE.match(s):
        return s

    # Try Spanish date format (DD/MMM/YY or DD/MMM/YYYY)
    m = DATE_ES_RE.match(s)
    if not m:
        return None

    day = m.group(1).zfill(2)
    month_str = m.group(2).lower()
    year = m.group(3)

    # Look up month number
    month = MONTHS_ES.get(month_str)
    if not month:
        return None

    # Convert 2-digit year to 4-digit (assume 2000s)
    if len(year) == 2:
        year = f"20{year}"

    return f"{year}-{month}-{day}"


def parse_mexican_date(date_str: str, year: Optional[int] = None) -> Optional[str]:
    """Parse Mexican date formats to ISO format (YYYY-MM-DD).

    Supports multiple formats:
    - "12 ENE" or "12ENE" (requires year parameter)
    - "12/01/24" or "12-01-24" (DD/MM/YY)
    - "12/01/2024" or "12-01-2024" (DD/MM/YYYY)
    - "2024-01-12" (already ISO format)

    Args:
        date_str: Date string to parse
        year: Year to use for formats without year (defaults to current year)

    Returns:
        ISO format date string (YYYY-MM-DD), or None if parsing fails

    Examples:
        >>> parse_mexican_date("12 ENE", 2024)
        '2024-01-12'
        >>> parse_mexican_date("12/01/24")
        '2024-01-12'
        >>> parse_mexican_date("31/12/2023")
        '2023-12-31'
    """
    if not date_str or not isinstance(date_str, str):
        return None

    s = date_str.upper().strip()
    if not year:
        year = datetime.now().year

    # Months mapping (Standard Spanish abbreviations and common OCR variations)
    months = {
        "ENE": "01", "ENERO": "01",
        "FEB": "02", "FEBRERO": "02",
        "MAR": "03", "MARZO": "03",
        "ABR": "04", "ABRIL": "04",
        "MAY": "05", "MAYO": "05",
        "JUN": "06", "JUNIO": "06",
        "JUL": "07", "JULIO": "07",
        "AGO": "08", "AGOSTO": "08",
        "SEP": "09", "SET": "09", "SEPTIEMBRE": "09",
        "OCT": "10", "OCTUBRE": "10",
        "NOV": "11", "NOVIEMBRE": "11",
        "DIC": "12", "DICIEMBRE": "12",
    }

    # Try: Already ISO format "2024-01-12"
    m = re.match(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", s)
    if m:
        yr, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= day <= 31 and 1 <= month <= 12:
            return f"{yr}-{month:02d}-{day:02d}"

    # Try: "12 ENE" or "12ENE"
    m = re.match(r"(\d{1,2})\s*([A-Z]{3,10})", s)
    if m:
        day = int(m.group(1))
        month_str = m.group(2)
        if not (1 <= day <= 31):
            return None
        month = months.get(month_str)
        if not month:
            return None
        return f"{year}-{month}-{day:02d}"

    # Try: "12/01/24" or "12-01-2024" (DD/MM/YY or DD/MM/YYYY)
    m = re.match(r"(\d{1,2})\s*[/-]\s*(\d{1,2})\s*[/-]\s*(\d{2,4})", s)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        yr = int(m.group(3))
        if not (1 <= day <= 31):
            return None
        if not (1 <= month <= 12):
            return None
        if yr < 100:
            # Assume 2000s for two-digit years
            yr += 2000
        return f"{yr}-{month:02d}-{day:02d}"

    return None


def parse_iso_date(date_str: str) -> Optional[str]:
    """Parse ISO 8601 date format (YYYY-MM-DD).

    Validates that the date string is already in ISO format.

    Args:
        date_str: Date string to parse

    Returns:
        ISO format date string (YYYY-MM-DD), or None if invalid

    Examples:
        >>> parse_iso_date("2024-01-15")
        '2024-01-15'
        >>> parse_iso_date("invalid")
        None
    """
    if not date_str or not isinstance(date_str, str):
        return None

    s = date_str.strip()

    # Validate ISO format
    if not DATE_ISO_RE.match(s):
        return None

    # Try to parse to validate it's a real date
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        return None
