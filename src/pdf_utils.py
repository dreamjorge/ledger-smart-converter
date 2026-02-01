# -*- coding: utf-8 -*-
import re
import shutil
from pathlib import Path
from typing import Dict, Optional, Any, List

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
                break
except ImportError:
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
    return re.sub(r"\s+", " ", s).strip()

def parse_amount_str(s: str) -> float:
    return float(s.replace(",", "").replace(" ", ""))

# ----------------------------
# OCR Helpers
# ----------------------------

def preprocess_for_ocr(bgr):
    if cv2 is None: return bgr
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    thr = cv2.resize(thr, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    return thr

def ocr_image(img) -> str:
    if pytesseract is None: return ""
    try:
        cfg = "--psm 6"
        txt = pytesseract.image_to_string(img, lang="eng", config=cfg)
        txt = re.sub(r"[ \t]+", " ", txt)
        return txt
    except Exception:
        # Tesseract binary likely not found or not in PATH
        return ""

def render_page(doc, page_index: int, zoom: float = 2.0):
    if fitz is None: return None
    page = doc.load_page(page_index)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    return img

# ----------------------------
# Main Extraction Logic
# ----------------------------

def parse_mx_date(date_str: str, year: Optional[int] = None) -> str:
    """
    Converts "12 ENE" or "12/01/24" or "12-01-2024" to "2024-01-12".
    """
    s = date_str.upper().strip()
    if not year:
        year = datetime.now().year
    
    # Months mapping
    months = {
        "ENE": "01", "FEB": "02", "MAR": "03", "ABR": "04", "MAY": "05", "JUN": "06",
        "JUL": "07", "AGO": "08", "SEP": "09", "OCT": "10", "NOV": "11", "DIC": "12"
    }
    
    # Case: "12 ENE"
    m = re.match(r"(\d{1,2})\s+([A-Z]{3})", s)
    if m:
        day = int(m.group(1))
        month_str = m.group(2)
        month = months.get(month_str, "01")
        return f"{year}-{month}-{day:02d}"
    
    # Case: "12/01/24" or "12-01-2024"
    m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", s)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        yr = int(m.group(3))
        if yr < 100: yr += 2000
        return f"{yr}-{month:02d}-{day:02d}"
    
    return date_str

def extract_transactions_from_pdf(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Experimental: Extracts transaction rows from PDF using OCR.
    Useful when XML/XLSX is missing or for verification.
    """
    if not pdf_path.exists() or fitz is None or pytesseract is None:
        return []

    doc = fitz.open(str(pdf_path))
    txns = []
    
    # Regex for typical transaction rows:
    # 1. Date (DD MMM or DD/MM/YY)
    # 2. Description (Text)
    # 3. Amount (Number with commas/dots at the end)
    # Example: "12 ENE AMAZON MEXICO 1,234.56"
    row_rx = re.compile(r"^(\d{1,2}(?:\s+[A-Za-z]{3}|[/-]\d{1,2}[/-]\d{2,4}))\s+(.*?)\s+([\d,]+\.\d{2})$", re.MULTILINE)

    for page_idx in range(doc.page_count):
        # We process the whole page as one image
        img = render_page(doc, page_idx, zoom=2.0)
        if img is None: continue
        
        # Preprocess and OCR
        gray = preprocess_for_ocr(img)
        txt = pytesseract.image_to_string(gray, lang="spa+eng", config="--psm 6")
        
        # Clean text and find matches
        for line in txt.splitlines():
            line = line.strip()
            # Basic cleanup for amount signs in OCR
            line = line.replace(" - ", "-").replace(" $ ", "$")
            
            m = row_rx.search(line)
            if m:
                txns.append({
                    "raw_date": m.group(1),
                    "description": m.group(2),
                    "amount": parse_amount_str(m.group(3)),
                    "page": page_idx + 1
                })
    
    doc.close()
    return txns

def extract_pdf_metadata(pdf_path: Path) -> Dict[str, Any]:
    """
    Extracts dates and amounts from PDF.
    Tries Text extraction first.
    Falls back to OCR for specific regions if needed (though text usually works for headers).
    """
    if not pdf_path.exists():
        return {}
    
    if fitz is None:
        print("WARNING: PyMuPDF (fitz) not installed. PDF extraction skipped.")
        return {}

    doc = fitz.open(str(pdf_path))
    metadata = {}
    
    # 1. Text Extraction (Page 1 is covering 99% of summary info)
    page1_text = ""
    if doc.page_count > 0:
        # Simple text is usually enough
        page1_text = doc[0].get_text()

    # Search regexes in text
    for key, regexes in PATTERNS.items():
        for rx in regexes:
            m = rx.search(page1_text)
            if m:
                val = m.group(1)
                if key in ["pago_minimo", "pago_no_intereses", "total_pagar"]:
                    metadata[key] = parse_amount_str(val)
                else:
                    metadata[key] = clean_date_str(val)
                break # found match for this key

    # 2. OCR Fallback (Only if we missed keys and have dependencies)
    # This is expensive, so only do it if we are missing critical data AND have the libs
    missing_critical = not ("cutoff_date" in metadata and "total_pagar" in metadata)
    
    if missing_critical and cv2 is not None and pytesseract is not None:
        # Try OCR on crop of page 1
        img = render_page(doc, 0, zoom=2.0)
        if img is not None:
            h, w = img.shape[:2]
            # Top half crop
            crop = img[int(h * 0.05):int(h * 0.50), int(w * 0.05):int(w * 0.95)]
            txt_ocr = ocr_image(preprocess_for_ocr(crop)).lower()
            
            # Re-run regexes on OCR text
            for key, regexes in PATTERNS.items():
                if key in metadata: continue # already found
                for rx in regexes:
                    m = rx.search(txt_ocr)
                    if m:
                        val = m.group(1)
                        if key in ["pago_minimo", "pago_no_intereses", "total_pagar"]:
                            metadata[key] = parse_amount_str(val)
                        else:
                            metadata[key] = clean_date_str(val)
                        break

    doc.close()
    return metadata
