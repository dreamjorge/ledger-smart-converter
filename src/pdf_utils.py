# -*- coding: utf-8 -*-
"""PDF extraction utilities for bank statements.

This module provides utilities for extracting transaction data and metadata from
PDF bank statements using either text extraction or OCR fallback.
"""
import re
from datetime import datetime
import shutil
from pathlib import Path
from typing import Dict, Optional, Any, List

from logging_config import get_logger

logger = get_logger("pdf_utils")

try:
    import fitz  # PyMuPDF
    import cv2
    import numpy as np
    import pytesseract
    # Windows fallback for Tesseract
    if shutil.which("tesseract") is None:
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for p in common_paths:
            if Path(p).exists():
                pytesseract.pytesseract.tesseract_cmd = p
                logger.info(f"Tesseract found at: {p}")
                break
except ImportError as e:
    logger.warning(f"Optional PDF dependencies not available: {e}")
    fitz = None
    cv2 = None
    np = None
    pytesseract = None

# ----------------------------
# Text Extraction Regexes
# ----------------------------

# Common patterns for statements (HSBC, Santander, etc.)
PATTERNS = {
    "cutoff_date": [
        re.compile(r"(?:fecha|periodo)\s*de\s*corte[:\.\s]*(\d{1,2}\s*[/-]\s*[A-Za-z]{3}\s*[/-]\s*\d{2,4})", re.IGNORECASE),
        re.compile(r"corte[:\.\s]*(\d{1,2}\s*[/-]\s*\w{3}\s*[/-]\s*\d{2,4})", re.IGNORECASE),
    ],
    "due_date": [
        re.compile(r"(?:fecha|límite)\s*de\s*pago[:\.\s]*(\d{1,2}\s*[/-]\s*[A-Za-z]{3}\s*[/-]\s*\d{2,4})", re.IGNORECASE),
        re.compile(r"límite\s+de\s+pago[:\.\s]*(\d{1,2}\s*[/-]\s*\w{3}\s*[/-]\s*\d{2,4})", re.IGNORECASE),
    ],
    "period": [
        re.compile(r"periodo[:\.\s]*(\d{1,2}\s*\w{3}\s*\d{2,4}\s*-\s*\d{1,2}\s*\w{3}\s*\d{2,4})", re.IGNORECASE),
    ],
    # Money amounts
    "pago_minimo": [re.compile(r"pago\s*m[íi]nimo[:\.\s]*\$?\s*([\d,]+\.\d{2})", re.IGNORECASE)],
    "pago_no_intereses": [re.compile(r"pago\s*para\s*no\s*generar\s*intereses[:\.\s]*\$?\s*([\d,]+\.\d{2})", re.IGNORECASE)],
    "total_pagar": [re.compile(r"(?:total\s*a\s*pagar|saldo\s*total)[:\.\s]*\$?\s*([\d,]+\.\d{2})", re.IGNORECASE)],
}

def clean_date_str(s: str) -> str:
    """Clean whitespace from date string."""
    return re.sub(r"\s+", " ", s).strip()


def parse_amount_str(s: str) -> Optional[float]:
    """Parse amount string to float.

    Args:
        s: Amount string (e.g., "1,234.56" or "1.234,56")

    Returns:
        Parsed float value, or None if parsing fails
    """
    try:
        # Remove spaces and handle both comma/period separators
        cleaned = s.replace(" ", "").replace(",", "")
        return float(cleaned)
    except (ValueError, AttributeError) as e:
        logger.warning(f"Failed to parse amount '{s}': {e}")
        return None

# ----------------------------
# OCR Helpers
# ----------------------------

def preprocess_for_ocr(bgr):
    """Preprocess image for better OCR results.

    Applies grayscale conversion, Otsu thresholding, and upscaling.

    Args:
        bgr: BGR image array

    Returns:
        Preprocessed image ready for OCR
    """
    if cv2 is None:
        logger.warning("OpenCV not available, skipping preprocessing")
        return bgr

    try:
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        thr = cv2.resize(thr, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        return thr
    except Exception as e:
        logger.error(f"Image preprocessing failed: {e}")
        return bgr


def ocr_image(img, lang: str = "eng") -> str:
    """Extract text from image using Tesseract OCR.

    Args:
        img: Image array
        lang: Tesseract language(s), e.g., "eng", "spa", "spa+eng"

    Returns:
        Extracted text, or empty string if OCR fails
    """
    if pytesseract is None:
        logger.warning("Tesseract not available for OCR")
        return ""

    try:
        cfg = "--psm 6"  # Assume uniform text block
        txt = pytesseract.image_to_string(img, lang=lang, config=cfg)
        txt = re.sub(r"[ \t]+", " ", txt)
        logger.debug(f"OCR extracted {len(txt)} characters")
        return txt
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return ""


def render_page(doc, page_index: int, zoom: float = 2.0):
    """Render PDF page to image array.

    Args:
        doc: PyMuPDF document object
        page_index: Zero-based page index
        zoom: Zoom factor (higher = better quality, slower)

    Returns:
        RGB image array, or None if rendering fails
    """
    if fitz is None:
        logger.warning("PyMuPDF not available, cannot render page")
        return None

    try:
        page = doc.load_page(page_index)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        return img
    except Exception as e:
        logger.error(f"Failed to render page {page_index}: {e}")
        return None

# ----------------------------
# Main Extraction Logic
# ----------------------------

def parse_mx_date(date_str: str, year: Optional[int] = None) -> Optional[str]:
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
        >>> parse_mx_date("12 ENE", 2024)
        '2024-01-12'
        >>> parse_mx_date("12/01/24")
        '2024-01-12'
        >>> parse_mx_date("31/12/2023")
        '2023-12-31'
    """
    if not date_str or not isinstance(date_str, str):
        logger.debug(f"Invalid date_str: {date_str!r}")
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
            logger.debug(f"Invalid day in date: {day}")
            return None
        month = months.get(month_str)
        if not month:
            logger.debug(f"Unknown month abbreviation: {month_str}")
            return None
        return f"{year}-{month}-{day:02d}"

    # Try: "12/01/24" or "12-01-2024" (DD/MM/YY or DD/MM/YYYY)
    m = re.match(r"(\d{1,2})\s*[/-]\s*(\d{1,2})\s*[/-]\s*(\d{2,4})", s)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        yr = int(m.group(3))
        if not (1 <= day <= 31):
            logger.debug(f"Invalid day: {day}")
            return None
        if not (1 <= month <= 12):
            logger.debug(f"Invalid month: {month}")
            return None
        if yr < 100:
            # Assume 2000s for two-digit years
            yr += 2000
        return f"{yr}-{month:02d}-{day:02d}"

    logger.debug(f"Could not parse date: {date_str!r}")
    return None

def extract_transactions_from_pdf(pdf_path: Path, use_ocr: bool = False) -> List[Dict[str, Any]]:
    """Extract transaction rows from PDF using text extraction or OCR.

    This function attempts text extraction first for speed, then falls back to OCR
    if no transactions are found (unless OCR is explicitly forced).

    Args:
        pdf_path: Path to PDF file
        use_ocr: If True, force OCR instead of text extraction

    Returns:
        List of transaction dictionaries with keys:
        - raw_date: Original date string from PDF
        - description: Transaction description
        - amount: Amount as float (or None if parsing failed)
        - page: Page number (1-indexed)
        - line: Original line text

    Examples:
        >>> txns = extract_transactions_from_pdf(Path("statement.pdf"))
        >>> print(txns[0])
        {'raw_date': '12 ENE', 'description': 'OXXO', 'amount': 45.50, ...}
    """
    if not pdf_path.exists():
        logger.error(f"PDF file not found: {pdf_path}")
        return []

    if fitz is None:
        logger.error("PyMuPDF not available. Cannot extract from PDF.")
        return []

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        logger.error(f"Failed to open PDF {pdf_path}: {e}")
        return []

    txns = []

    # Regex for typical transaction rows:
    # 1. Date (DD MMM or DD/MM/YY)
    # 2. Description (non-greedy match until amount)
    # 3. Amount (digits with optional thousands separator and mandatory decimal)
    row_rx = re.compile(
        r"(\d{1,2}(?:\s*[A-Z]{3}|[/-]\s*\d{1,2}\s*[/-]\s*\d{2,4}))\s+(.*?)\s+([-+]?[\d,\.\s]+[,\.]\d{2})",
        re.IGNORECASE
    )

    for page_idx in range(doc.page_count):
        txt = ""
        used_method = ""

        # 1. Try Text Extraction first (unless OCR is forced)
        if not use_ocr:
            try:
                page = doc[page_idx]
                txt = page.get_text()
                if len(txt.strip()) > 50:
                    used_method = "Text Layer"
            except Exception as e:
                logger.warning(f"Text extraction failed on page {page_idx + 1}: {e}")

        # 2. Parse text for transaction rows
        sub_txns = []
        if txt:
            for line in txt.splitlines():
                m = row_rx.search(line)
                if m and parse_mx_date(m.group(1)):
                    amount = parse_amount_str(m.group(3).replace(",", "."))
                    if amount is not None:
                        sub_txns.append({
                            "raw_date": m.group(1),
                            "description": m.group(2).strip(),
                            "amount": amount,
                            "page": page_idx + 1,
                            "line": line.strip()
                        })

        # 3. Fallback to OCR if no transactions found
        if not sub_txns and pytesseract:
            logger.debug(f"No transactions found via text extraction on page {page_idx + 1}, trying OCR")
            img = render_page(doc, page_idx, zoom=3.0)
            if img is not None:
                gray = preprocess_for_ocr(img)
                txt = ocr_image(gray, lang="spa+eng")
                used_method = "OCR (fallback)" if not use_ocr else "OCR (forced)"

                for line in txt.splitlines():
                    # Clean OCR artifacts
                    line = line.replace(" - ", "-").replace(" $ ", "$").replace("$", "")
                    m = row_rx.search(line)
                    if m and parse_mx_date(m.group(1)):
                        amount = parse_amount_str(m.group(3).replace(",", "."))
                        if amount is not None:
                            sub_txns.append({
                                "raw_date": m.group(1),
                                "description": m.group(2).strip(),
                                "amount": amount,
                                "page": page_idx + 1,
                                "line": line.strip()
                            })

        logger.info(f"Page {page_idx + 1}: Used {used_method}. Found {len(sub_txns)} transactions.")

        # Debug first page if no results
        if page_idx == 0 and not sub_txns and txt:
            logger.debug(f"Page 1 text sample (first 200 chars):\n{txt[:200]}")

        txns.extend(sub_txns)

    doc.close()
    logger.info(f"Extracted {len(txns)} total transactions from {pdf_path.name}")
    return txns


def collect_pdf_lines(pdf_path: Path, use_ocr: bool = False) -> List[Dict[str, Any]]:
    """
    Returns every text line from the PDF pages, including OCR fallback lines.
    """
    if not pdf_path.exists() or fitz is None:
        return []

    doc = fitz.open(str(pdf_path))
    lines: List[Dict[str, Any]] = []

    for page_idx in range(doc.page_count):
        page = doc.load_page(page_idx)
        text = page.get_text()
        method = "text"
        if not text.strip() and use_ocr and pytesseract:
            img = render_page(doc, page_idx, zoom=3.0)
            if img is not None:
                gray = preprocess_for_ocr(img)
                text = pytesseract.image_to_string(gray, lang="spa+eng", config="--psm 6")
                method = "ocr"

        for raw_line in text.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue
            lines.append({
                "page": page_idx + 1,
                "method": method,
                "text": stripped
            })

    doc.close()
    return lines

def extract_pdf_metadata(pdf_path: Path, patterns: Optional[Dict[str, List[re.Pattern]]] = None) -> Dict[str, Any]:
    """Extract metadata (dates, amounts) from PDF statement.

    Tries text extraction first for speed. Falls back to OCR on page 1 header
    if critical metadata is missing.

    Args:
        pdf_path: Path to PDF file
        patterns: Custom regex patterns dict, or None to use defaults

    Returns:
        Dictionary with extracted metadata fields:
        - cutoff_date: Statement cutoff date string
        - due_date: Payment due date string
        - period: Statement period string
        - pago_minimo: Minimum payment amount (float)
        - pago_no_intereses: No-interest payment amount (float)
        - total_pagar: Total amount due (float)

    Examples:
        >>> meta = extract_pdf_metadata(Path("statement.pdf"))
        >>> print(meta.get("cutoff_date"))
        '15 ENE 2024'
        >>> print(meta.get("total_pagar"))
        1234.56
    """
    if not pdf_path.exists():
        logger.error(f"PDF file not found: {pdf_path}")
        return {}

    if fitz is None:
        logger.error("PyMuPDF not available. Cannot extract metadata.")
        return {}

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        logger.error(f"Failed to open PDF {pdf_path}: {e}")
        return {}

    metadata = {}

    # Use provided patterns or default
    active_patterns = patterns if patterns is not None else PATTERNS

    # 1. Text Extraction (Page 1 typically contains all summary info)
    page1_text = ""
    if doc.page_count > 0:
        try:
            page1_text = doc[0].get_text()
            logger.debug(f"Extracted {len(page1_text)} characters from page 1")
        except Exception as e:
            logger.warning(f"Failed to extract text from page 1: {e}")

    # Search patterns in extracted text
    for key, regexes in active_patterns.items():
        for rx in regexes:
            m = rx.search(page1_text)
            if m:
                val = m.group(1)
                if key in ["pago_minimo", "pago_no_intereses", "total_pagar"]:
                    parsed_amount = parse_amount_str(val)
                    if parsed_amount is not None:
                        metadata[key] = parsed_amount
                else:
                    metadata[key] = clean_date_str(val)
                logger.debug(f"Found {key}: {val}")
                break  # Found match for this key

    # 2. OCR Fallback (only if missing critical data)
    missing_critical = not ("cutoff_date" in metadata and "total_pagar" in metadata)

    if missing_critical and cv2 is not None and pytesseract is not None:
        logger.info("Missing critical metadata, attempting OCR on page 1 header")
        img = render_page(doc, 0, zoom=2.0)
        if img is not None:
            h, w = img.shape[:2]
            # Crop top portion (header area where metadata usually is)
            crop = img[int(h * 0.05):int(h * 0.50), int(w * 0.05):int(w * 0.95)]
            preprocessed = preprocess_for_ocr(crop)
            txt_ocr = ocr_image(preprocessed, lang="spa+eng").lower()

            # Re-run patterns on OCR text
            for key, regexes in active_patterns.items():
                if key in metadata:
                    continue  # Already found via text extraction
                for rx in regexes:
                    m = rx.search(txt_ocr)
                    if m:
                        val = m.group(1)
                        if key in ["pago_minimo", "pago_no_intereses", "total_pagar"]:
                            parsed_amount = parse_amount_str(val)
                            if parsed_amount is not None:
                                metadata[key] = parsed_amount
                        else:
                            metadata[key] = clean_date_str(val)
                        logger.debug(f"Found {key} via OCR: {val}")
                        break

    doc.close()
    logger.info(f"Extracted {len(metadata)} metadata fields from {pdf_path.name}")
    return metadata
