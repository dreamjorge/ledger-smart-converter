"""
Parser for Banamex JOY credit card PDF statements.

Statement structure (text-selectable PDF):
- Page 1: Metadata (period, cutoff date, card number)
- Page 2+: "DESGLOSE DE MOVIMIENTOS" with transaction table
- Last pages: Disputes, notes, CFDI → skipped

Transaction table format:
    Fecha de la   Fecha      Descripción del movimiento        Monto
    operación     de cargo
    21-feb-2026   24-feb-2026  PAYPAL *ORDENARISB2 ...        + $300.00
    23-feb-2026   23-feb-2026  PAGO INTERBANCARIO             - $576.84

Notes:
- Multiple card sections (titular / digital) are merged
- Descriptions can span multiple lines (e.g. PAGO INTERBANCARIO)
- Monto: "+ $NNN.NN" = cargo (positive), "- $NNN.NN" = abono (negative)
- Date format: dd-mmm-yyyy (Spanish month abbreviations)
"""

import re
from pathlib import Path
from typing import List, Optional

from infrastructure.parsers.base_parser import StatementParser
from infrastructure.parsers.models import TxnRaw

_MONTH_MAP = {
    "ene": "01",
    "feb": "02",
    "mar": "03",
    "abr": "04",
    "may": "05",
    "jun": "06",
    "jul": "07",
    "ago": "08",
    "sep": "09",
    "oct": "10",
    "nov": "11",
    "dic": "12",
}

# Matches: "21-feb-2026" or "21-feb-26"
_DATE_RE = re.compile(
    r"(\d{1,2})-(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)-(\d{2,4})",
    re.IGNORECASE,
)

# Matches: "+ $1,234.56" or "- $576.84"
_AMOUNT_RE = re.compile(r"([+\-])\s*\$\s*([\d,]+\.?\d*)")

# Lines that signal we've left the transaction section
_STOP_PATTERNS = (
    "CARGOS NO RECONOCIDOS",
    "NOTAS ACLARATORIAS",
    "GLOSARIO DE",
    "ESTE DOCUMENTO ES UNA REPRESENTACIÓN",
    "ATENCIÓN DE QUEJAS",
)

# Lines to skip inside the transaction section
_SKIP_PATTERNS = (
    "DESGLOSE DE MOVIMIENTOS",
    "CARGOS, ABONOS Y COMPRAS REGULARES",
    "Tarjeta titular",
    "Tarjeta digital",
    "Fecha de la",
    "operación",
    "de cargo",
    "Descripción del movimiento",
    "Monto",
    "Total cargos",
    "Total abonos",
    "Notas:",
    "Número de tarjeta:",
    "Ver notas en la sección",
    "Página ",
)


def _parse_date(raw: str) -> Optional[str]:
    m = _DATE_RE.search(raw)
    if not m:
        return None
    day, month_str, year = m.group(1), m.group(2).lower(), m.group(3)
    month = _MONTH_MAP.get(month_str)
    if not month:
        return None
    if len(year) == 2:
        year = "20" + year
    return f"{year}-{month}-{day.zfill(2)}"


def _parse_amount(raw: str) -> Optional[float]:
    m = _AMOUNT_RE.search(raw)
    if not m:
        return None
    sign = -1.0 if m.group(1) == "+" else 1.0
    value = float(m.group(2).replace(",", ""))
    return sign * value


def _should_skip(line: str) -> bool:
    stripped = line.strip()
    return any(stripped.startswith(p) for p in _SKIP_PATTERNS) or not stripped


def _is_stop(line: str) -> bool:
    stripped = line.strip().upper()
    return any(p.upper() in stripped for p in _STOP_PATTERNS)


def _extract_text_lines(pdf_path: Path) -> List[str]:
    try:
        import pdfplumber
    except ImportError as e:
        raise ImportError(
            "pdfplumber is required for Banamex PDF parsing. "
            "Run: pip install pdfplumber"
        ) from e
    lines = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
            lines.extend(text.splitlines())
    return lines


class BanamexPdfParser(StatementParser):
    """Parser for Banamex JOY credit card PDF statements."""

    def parse(self, file_path: Path) -> List[TxnRaw]:
        lines = _extract_text_lines(file_path)
        return _parse_transactions(lines)


def _parse_transactions(lines: List[str]) -> List[TxnRaw]:
    """
    State machine over the raw text lines.

    States:
      SEARCHING  → looking for "DESGLOSE DE MOVIMIENTOS"
      IN_SECTION → inside the transaction block, accumulating rows
    """
    in_section = False
    txns: List[TxnRaw] = []

    # Each pending row: we accumulate lines until we see the next date row
    pending_date: Optional[str] = None
    pending_desc_parts: List[str] = []
    pending_amount: Optional[float] = None

    def flush():
        nonlocal pending_date, pending_desc_parts, pending_amount
        if pending_date and pending_amount is not None and pending_desc_parts:
            desc = " ".join(pending_desc_parts).strip()
            txns.append(
                TxnRaw(
                    date=pending_date,
                    description=desc,
                    amount=pending_amount,
                    source="pdf",
                )
            )
        pending_date = None
        pending_desc_parts = []
        pending_amount = None

    for line in lines:
        stripped = line.strip()

        if not in_section:
            if "DESGLOSE DE MOVIMIENTOS" in stripped.upper():
                in_section = True
            continue

        if _is_stop(stripped):
            flush()
            break

        if _should_skip(stripped):
            continue

        # Check if this line starts with two dates (new transaction row)
        # Pattern: "dd-mmm-yyyy  dd-mmm-yyyy  description... [amount]"
        dates_found = _DATE_RE.findall(stripped)
        amount_found = _parse_amount(stripped)

        if len(dates_found) >= 1:
            # New transaction row — flush previous
            flush()

            # Extract the operation date (first date)
            first_match = _DATE_RE.search(stripped)
            if first_match is None:
                continue
            pending_date = _parse_date(first_match.group(0))

            # Remove both dates from the line to get the description fragment
            desc_fragment = _DATE_RE.sub("", stripped).strip()

            # Amount may be on this same line
            if amount_found is not None:
                pending_amount = amount_found
                desc_fragment = _AMOUNT_RE.sub("", desc_fragment).strip()

            if desc_fragment:
                pending_desc_parts.append(desc_fragment)

        elif pending_date is not None:
            # Continuation line for current transaction
            if amount_found is not None and pending_amount is None:
                pending_amount = amount_found
                remainder = _AMOUNT_RE.sub("", stripped).strip()
                if remainder:
                    pending_desc_parts.append(remainder)
            else:
                # Pure description continuation — but skip reference/metadata lines
                # from multi-line payments like PAGO INTERBANCARIO
                if (
                    stripped
                    and not stripped.startswith("CLAVE DE RASTREO")
                    and not stripped.startswith("CUENTA ORDENANTE")
                    and not stripped.startswith("POR ORDEN DE")
                    and not stripped.startswith("FECHA Y HORA DE LIQUIDACIÓN")
                    and not stripped.startswith("REFERENCIA")
                    and not stripped.startswith("CONCEPTO")
                ):
                    pending_desc_parts.append(stripped)

    flush()
    return txns
