import re
import unicodedata
from typing import Dict, List, Optional


_ABBREVIATIONS: Dict[str, str] = {
    "TRANSF": "Transferencia",
    "TRANSFER": "Transferencia",
    "DEBITO": "Débito",
    "CREDITO": "Crédito",
    "COMISION": "Comisión",
    "MERPAGO": "MercadoPago",
    "MERCADOPAGO": "MercadoPago",
    "MERCADO": "Mercado",
    "PAGO": "Pago",
}

_ACCENT_RESTORATION: Dict[str, str] = {
    "DEBITO": "Débito",
    "CREDITO": "Crédito",
    "COMISION": "Comisión",
    "INTERES": "Interés",
    "NOMINA": "Nómina",
}

_ACRONYMS = {"SPEI", "RFC", "IVA", "ATM", "PIN", "CVV", "SAT", "CFE"}
_NOISE_RX = re.compile(r"^[\d\-_/]+$")


def _collapse_ws(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _normalize_unicode(value: str) -> str:
    return unicodedata.normalize("NFKC", value)


def normalize_tokens(tokens: List[str], bank_id: Optional[str] = None) -> List[str]:
    del bank_id  # extension hook for future bank-specific rules
    if not tokens:
        return []

    cleaned: List[str] = []
    for tok in tokens:
        raw = tok.strip()
        if not raw:
            continue
        if _NOISE_RX.match(raw):
            continue
        if len(raw) >= 12 and raw.isdigit():
            continue
        upper = raw.upper()
        if upper in _ABBREVIATIONS:
            cleaned.append(_ABBREVIATIONS[upper])
            continue
        if upper in _ACCENT_RESTORATION:
            cleaned.append(_ACCENT_RESTORATION[upper])
            continue
        if upper in _ACRONYMS:
            cleaned.append(upper)
            continue
        cleaned.append(raw.title())

    # Canonicalize MercadoPago multi-token form.
    out: List[str] = []
    i = 0
    while i < len(cleaned):
        cur = cleaned[i]
        nxt = cleaned[i + 1] if i + 1 < len(cleaned) else None
        if cur.lower() == "mercado" and nxt and nxt.lower() == "pago":
            out.append("MercadoPago")
            i += 2
            continue
        out.append(cur)
        i += 1

    # Remove trailing numeric reference tokens if they leaked through.
    while out and (_NOISE_RX.match(out[-1]) or out[-1].isdigit()):
        out.pop()
    return out


def normalize_description(raw: str, bank_id: Optional[str] = None) -> str:
    text = _collapse_ws(_normalize_unicode(raw or ""))
    if not text:
        return ""
    upper_tokens = re.split(r"[ \t]+", text.upper())
    normalized_tokens = normalize_tokens(upper_tokens, bank_id=bank_id)
    return " ".join(normalized_tokens)
