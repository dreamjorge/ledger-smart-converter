# -*- coding: utf-8 -*-
import re
from typing import Any, Dict, List, Tuple, Optional
from datetime import datetime, date, timedelta
from pathlib import Path

# ----------------------------
# Description Cleaning
# ----------------------------

# Words whose all-caps form loses Spanish accents — mapped to proper form.
# Also includes common bank abbreviations → full word.
_BANK_TERM_GLOSSARY = {
    # -ción endings (lose accent in all-caps)
    "COMISION": "Comisión",
    "ADMINISTRACION": "Administración",
    "CANCELACION": "Cancelación",
    "DEVOLUCION": "Devolución",
    "DISPOSICION": "Disposición",
    "RENOVACION": "Renovación",
    "OPERACION": "Operación",
    "TRANSACCION": "Transacción",
    "PROTECCION": "Protección",
    "REPOSICION": "Reposición",
    "FACTURACION": "Facturación",
    "COMUNICACION": "Comunicación",
    "NOTIFICACION": "Notificación",
    "PUBLICACION": "Publicación",
    # -ón endings
    "PENSION": "Pensión",
    # Proparoxytones (accent on 3rd-to-last syllable)
    "DEPOSITO": "Depósito",
    "CREDITO": "Crédito",
    "DEBITO": "Débito",
    "AUTOMATICO": "Automático",
    "ELECTRONICO": "Electrónico",
    "MEDICO": "Médico",
    "NUMERO": "Número",
    "MINIMO": "Mínimo",
    "MAXIMO": "Máximo",
    "UNICO": "Único",
    "PUBLICO": "Público",
    "NOMINA": "Nómina",
    # Agudas (accent on last syllable)
    "INTERES": "Interés",
    # Common bank abbreviations
    "TRANSF": "Transferencia",
    "SUPERCT": "Supercenter",
}

# Acronyms that must stay fully uppercase regardless of context.
_KEEP_UPPER = {
    "SPEI", "IVA", "RFC", "ATM", "PIN", "CVV", "CIE", "CLABE",
    "SAT", "CFE", "IMSS", "ISSSTE", "INFONAVIT",
}


def clean_description(desc: str) -> str:
    """Normalize a raw bank description for human readability.

    Applies three passes:
    1. Collapse whitespace.
    2. Restore Spanish accents / expand abbreviations via glossary.
    3. Title-case any remaining words (acronyms in _KEEP_UPPER stay uppercase).
    """
    desc = re.sub(r"\s+", " ", (desc or "").strip())
    words = desc.split(" ")
    result = []
    for word in words:
        upper = word.upper()
        if upper in _BANK_TERM_GLOSSARY:
            result.append(_BANK_TERM_GLOSSARY[upper])
        elif upper in _KEEP_UPPER:
            result.append(upper)
        else:
            result.append(word.title())
    return " ".join(result)


# ----------------------------
# Parsing Utilities
# ----------------------------

def strip_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def parse_money(x: Any) -> Optional[float]:
    """
    Parses a money string like '$1,234.56', '-123.45', or '1 234.56'.
    Returns float or None.
    """
    if x is None:
        return None
    s = str(x).strip()
    s = s.replace("$", "").replace(",", "").replace(" ", "")
    s = re.sub(r"[^\d\.\-+]", "", s)
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None

def get_statement_period(date_str: str, closing_day: int) -> str:
    """
    Determina el periodo del estado de cuenta (YYYY-MM).
    Si dia > closing_day, pertenece al mes siguiente.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return ""
    
    if dt.day > closing_day:
        # Mes siguiente
        year = dt.year
        month = dt.month + 1
        if month > 12:
            month = 1
            year += 1
        return f"{year}-{month:02d}"
    else:
        return f"{dt.year}-{dt.month:02d}"

def get_account_config(accounts: Dict[str, Any], key: str, default_name: str) -> Tuple[str, int]:
    """
    Obtiene (nombre_cuenta, closing_day) de la config.
    Soporta formato viejo (string) y nuevo (dict).
    """
    val = accounts.get(key)
    if not val:
        return default_name, 31 # Fallback closing day (end of month)
    
    if isinstance(val, str):
        return val, 31
    
    name = val.get("name", default_name)
    closing_day = val.get("closing_day", 31)
    return name, closing_day

# ----------------------------
# Rules & Classification
# ----------------------------

def compile_rules(rules_yml: Dict[str, Any]) -> List[Dict[str, Any]]:
    compiled = []
    for rule in rules_yml.get("rules", []):
        regexes = []
        for rx in rule.get("any_regex", []) or []:
            regexes.append(re.compile(rx, re.IGNORECASE))
        compiled.append({
            "name": rule.get("name", "unnamed"),
            "regexes": regexes,
            "set": rule.get("set", {}),
        })
    return compiled

def normalize_merchant(desc: str, merchant_aliases: List[Dict[str, Any]]) -> str:
    """
    Devuelve un merchant canónico para tags: merchant:<canon>.
    1) Si matchea alias -> canon
    2) fallback heurístico -> primeras 2 palabras sin números
    """
    d = (desc or "").lower()
    d = re.sub(r"\s+", " ", d).strip()

    for a in merchant_aliases:
        canon = (a.get("canon", "") or "").strip()
        for rx in a.get("any_regex", []) or []:
            if re.search(rx, d, re.IGNORECASE):
                return canon or "unknown"

    d2 = re.sub(r"\d+", "", d).strip()
    parts = [p for p in d2.split(" ") if p]
    return "_".join(parts[:2]) if parts else "unknown"

def classify(desc: str, compiled_rules: List[Dict[str, Any]], merchant_aliases: List[Dict[str, Any]], fallback_expense: str
             ) -> Tuple[str, List[str], str]:
    """
    Retorna:
      - expense_account (destination para cargos)
      - tags
      - merchant_canon
    """
    expense = None
    tags: List[str] = []

    for r in compiled_rules:
        if any(rx.search(desc or "") for rx in r["regexes"]):
            expense = r["set"].get("expense")
            tags.extend((r["set"].get("tags", []) or []))
            break

    if not expense:
        expense = fallback_expense

    merchant = normalize_merchant(desc, merchant_aliases)
    tags.append(f"merchant:{merchant}")

    # de-dup tags
    tags = sorted(set(t.strip() for t in tags if t and str(t).strip()))
    return expense, tags, merchant

def suggest_rule_from_merchant(merchant: str) -> Dict[str, Any]:
    """
    Sugiere una regla simple para el merchant.
    """
    safe = re.escape(merchant.replace("_", " "))
    rx = f"({safe})"
    return {
        "name": f"Auto:{merchant}",
        "any_regex": [rx],
        "set": {
            "expense": "Expenses:Other:Uncategorized",
            "tags": [f"bucket:{merchant}"]
        }
    }

def add_rule_to_yaml(rules_path: Path, merchant_name: str, regex_pattern: str, expense_account: str, bucket_tag: str):
    """
    Agrega una nueva regla al final de la lista de reglas en rules.yml.
    """
    import yaml
    with open(rules_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    if "rules" not in config:
        config["rules"] = []
    
    new_rule = {
        "name": f"UserCorrection:{merchant_name}",
        "any_regex": [regex_pattern],
        "set": {
            "expense": expense_account,
            "tags": [f"bucket:{bucket_tag}"]
        }
    }
    
    # Append to the beginning of the list to ensure it matches before general rules
    config["rules"].insert(0, new_rule)
    
    with open(rules_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, sort_keys=False, allow_unicode=True)
