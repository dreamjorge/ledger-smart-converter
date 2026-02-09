#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HSBC CFDI 4.0 (XML) -> Firefly III CSV (STANDARD, igual que Santander)
- Extrae movimientos desde cfdi:Addenda:
    - MovimientosDelCliente
    - MovimientoDelClienteFiscal (incluye RFCenajenante)
- Categorización por rules.yml (YAML)
- Aprendizaje asistido:
    - unknown_merchants.csv (agregado)
    - rules_suggestions.yml (para copiar/pegar)
- Salida CSV con columnas estándar:
    type,date,amount,currency_code,description,source_name,destination_name,category_name,tags
"""

import argparse
import csv
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# Local modules
import common_utils as cu
import pdf_utils as pu
from logging_config import get_logger

logger = get_logger(__name__)

CFDI_NS = {"cfdi": "http://www.sat.gob.mx/cfd/4"}


def parse_iso_date(s: str) -> str:
    """
    '2025-12-20T12:00:00' -> '2025-12-20'
    """
    s = (s or "").strip()
    if not s:
        return ""
    try:
        dt = datetime.fromisoformat(s)
        return dt.date().isoformat()
    except ValueError:
        return s[:10]


# ----------------------------
# Modelo
# ----------------------------

@dataclass(frozen=True)
class TxnRaw:
    date: str
    description: str
    amount: float
    rfc: str
    account_hint: str  # numerodecuenta si viene
    source: str = "xml"
    page: int = 0
    source_line: str = ""


def txn_match_key(txn: TxnRaw) -> Tuple[str, float]:
    """Claves simples para emparejar transacciones entre PDF y XML."""
    return txn.date, round(abs(txn.amount), 2)


def apply_xml_reference_to_pdf(pdf_txns: List[TxnRaw], xml_txns: List[TxnRaw]) -> Tuple[List[TxnRaw], Dict[str, Any]]:
    """
    Fusiona los datos del PDF con los metadatos del XML cuando existe coincidencia.
    Retorna la lista final de TxnRaw y un resumen de la validación.
    """
    xml_index = defaultdict(list)
    for idx, txn in enumerate(xml_txns):
        xml_index[txn_match_key(txn)].append((idx, txn))

    merged: List[TxnRaw] = []
    pdf_only: List[TxnRaw] = []
    diffs: List[Dict[str, Any]] = []
    used_xml = set()

    for pdf in pdf_txns:
        key = txn_match_key(pdf)
        candidate = None
        for idx, xml_txn in xml_index.get(key, []):
            if idx not in used_xml:
                candidate = (idx, xml_txn)
                break

        if candidate:
            idx, xml_txn = candidate
            used_xml.add(idx)
            merged.append(TxnRaw(
                date=pdf.date,
                description=pdf.description or xml_txn.description,
                amount=pdf.amount,
                rfc=xml_txn.rfc or pdf.rfc,
                account_hint=xml_txn.account_hint or pdf.account_hint,
                source=pdf.source,
            ))

            desc_pdf = cu.strip_ws(pdf.description)
            desc_xml = cu.strip_ws(xml_txn.description)
            if (desc_pdf.lower() != desc_xml.lower()) or abs(pdf.amount - xml_txn.amount) > 0.01:
                diffs.append({
                    "date": pdf.date,
                    "pdf_amount": pdf.amount,
                    "xml_amount": xml_txn.amount,
                    "pdf_desc": desc_pdf,
                    "xml_desc": desc_xml,
                })
        else:
            merged.append(pdf)
            pdf_only.append(pdf)

    xml_only = [txn for idx, txn in enumerate(xml_txns) if idx not in used_xml]

    summary = {
        "matched": len(pdf_txns) - len(pdf_only),
        "total_pdf": len(pdf_txns),
        "total_xml": len(xml_txns),
        "pdf_only": pdf_only,
        "xml_only": xml_only,
        "differences": diffs,
    }
    return merged, summary


def print_pdf_xml_validation_summary(summary: Optional[Dict[str, Any]]) -> None:
    """Log PDF vs XML validation summary."""
    if not summary:
        return

    logger.info("PDF vs XML Validation")
    logger.info(f"Matches: {summary['matched']} / {summary['total_pdf']} (PDF) vs {summary['total_xml']} (XML)")

    if summary["differences"]:
        logger.warning(f"Detected {len(summary['differences'])} differences (description or amount)")
        for diff in summary["differences"][:3]:
            logger.debug(f"  {diff['date']}: PDF ${diff['pdf_amount']:.2f} [{diff['pdf_desc']}] vs XML [{diff['xml_desc']}] (${diff['xml_amount']:.2f})")
        if len(summary["differences"]) > 3:
            extras = len(summary["differences"]) - 3
            logger.debug(f"  ... and {extras} more differences")

    if summary["pdf_only"]:
        count = len(summary["pdf_only"])
        logger.info(f"PDF-only entries: {count}")
        for txn in summary["pdf_only"][:3]:
            logger.debug(f"  {txn.date} - ${txn.amount:.2f} - {txn.description}")
        if count > 3:
            logger.debug(f"  ... {count - 3} more")

    if summary["xml_only"]:
        count = len(summary["xml_only"])
        logger.info(f"XML-only entries: {count}")
        for txn in summary["xml_only"][:3]:
            logger.debug(f"  {txn.date} - ${txn.amount:.2f} - {txn.description}")
        if count > 3:
            logger.debug(f"  ... {count - 3} more")


# ----------------------------
# Parse XML HSBC (Addenda)
# ----------------------------

def get_addenda(root: ET.Element) -> Optional[ET.Element]:
    return root.find("cfdi:Addenda", CFDI_NS)


def get_datos_generales(addenda: ET.Element) -> Dict[str, str]:
    # HSBC suele traer DatosGenerales en Addenda
    for child in list(addenda):
        tag = child.tag.split("}")[-1]
        if tag == "DatosGenerales":
            return {k: (v or "") for k, v in child.attrib.items()}
    return {}


def extract_movimientos(addenda: ET.Element) -> List[TxnRaw]:
    datos = get_datos_generales(addenda)
    account_hint = (datos.get("numerodecuenta", "") or "").strip()

    out: List[TxnRaw] = []

    def iter_all(e: ET.Element):
        yield e
        for c in list(e):
            yield from iter_all(c)

    for e in iter_all(addenda):
        tag = e.tag.split("}")[-1]

        if tag == "MovimientosDelCliente":
            date = parse_iso_date(e.attrib.get("fecha", ""))
            desc = cu.strip_ws(e.attrib.get("descripcion", ""))
            amt = cu.parse_money(e.attrib.get("importe", ""))
            if date and desc and amt is not None:
                out.append(TxnRaw(date=date, description=desc, amount=amt, rfc="", account_hint=account_hint))

        elif tag == "MovimientoDelClienteFiscal":
            date = parse_iso_date(e.attrib.get("fecha", ""))
            desc = cu.strip_ws(e.attrib.get("descripcion", ""))
            rfc = (e.attrib.get("RFCenajenante", "") or "").strip()
            amt = cu.parse_money(e.attrib.get("importe", ""))
            if date and desc and amt is not None:
                out.append(TxnRaw(date=date, description=desc, amount=amt, rfc=rfc, account_hint=account_hint))

    out.sort(key=lambda t: (t.date, t.description, t.amount, t.rfc))
    return out


# ----------------------------
# Inferencia: cargo vs pago (CLAVE para HSBC)
# ----------------------------

PAYMENT_HINT = re.compile(r"\b(pago|abono|payment|pymt|pagos?)\b", re.IGNORECASE)
PAYMENT_PROCESSOR_HINT = re.compile(r"\b(mercadopago|merpago|paypal|alipay|clip\s+mx|conekta)\b", re.IGNORECASE)
CHARGE_SERVICE_HINT = re.compile(r"(netflix|spotify|nintendo|hbo|disney|openai|chatgpt|duolingo|google|youtube)", re.IGNORECASE)
REFUND_HINT = re.compile(r"\b(reembolso|devoluci[oó]n|refund)\b", re.IGNORECASE)
CASHBACK_HINT = re.compile(r"\b(cashback|bonificaci[oó]n)\b", re.IGNORECASE)

def infer_kind(description: str, amount: float, rfc: str) -> str:
    """
    Retorna: 'charge' | 'payment' | 'refund' | 'cashback'
    
    Priority:
    1. If it's a known service (Netflix, Nintendo, etc.) -> charge
    2. If it's from a payment processor (MercadoPago, PayPal) -> check context
    3. If it mentions PAGO but is clearly a charge -> charge
    4. Traditional payment keywords -> payment
    """
    d = description or ""
    
    # Known subscription/service charges should always be charges
    if CHARGE_SERVICE_HINT.search(d):
        return "charge"
    
    # Cashback and refunds
    if CASHBACK_HINT.search(d):
        return "cashback"
    if REFUND_HINT.search(d):
        return "refund"
    
    # If it's through a payment processor, treat as charge unless it's clearly a payment
    if PAYMENT_PROCESSOR_HINT.search(d):
        # "SU PAGO GRACIAS" is a clear payment
        if "SU PAGO GRACIAS" in d.upper() or "GRACIAS SPEI" in d.upper():
            return "payment"
        # Otherwise it's a charge processed through the platform
        return "charge"
    
    # Clear payment keywords
    if PAYMENT_HINT.search(d):
        return "payment"
    
    # Have RFC? Likely a charge
    if (rfc or "").strip():
        return "charge"
    
    # Default based on amount sign
    return "charge" if amount < 0 else "payment"


# ----------------------------
# MAIN
# ----------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="HSBC CFDI(XML) -> Firefly CSV (standard) + rules + assisted learning"
    )
    ap.add_argument("--xml", help="Ruta al CFDI XML (HSBC).")
    ap.add_argument("--csv", help="Ruta a un CSV (HSBC) opcional.")
    ap.add_argument("--rules", required=True, help="Ruta a rules.yml (mismo estándar que Santander).")
    ap.add_argument("--pdf", default="", help="(Opcional) PDF para extracción de fechas y montos.")
    ap.add_argument("--pdf-source", action="store_true", help="Usar el PDF como fuente primaria de transacciones (OCR).")
    ap.add_argument("--out", default="firefly_hsbc.csv", help="CSV salida para Firefly.")
    ap.add_argument("--unknown-out", default="unknown_merchants.csv", help="CSV de desconocidos (asistido).")
    ap.add_argument("--suggestions-out", default="rules_suggestions.yml", help="YAML con sugerencias.")
    args = ap.parse_args()

    xml_path = Path(args.xml) if args.xml else None
    csv_path = Path(args.csv) if args.csv else None
    pdf_path = Path(args.pdf) if args.pdf else None
    pdf_source_mode = bool(args.pdf_source and pdf_path and pdf_path.exists())
    rules_path = Path(args.rules)

    if not xml_path and not csv_path and not pdf_source_mode:
        logger.error(" Debe proporcionar --xml, --csv o --pdf (con --pdf-source)")
        return 2

    if not rules_path.exists():
        logger.error(f" No existe rules.yml: {rules_path}")
        return 2

    # Metadata extraction (Always try PDF for metadata if available)
    pdf_meta = {}
    if pdf_path and pdf_path.exists():
        logger.info(f" Analizando PDF: {pdf_path.name} ---")
        pdf_meta = pu.extract_pdf_metadata(pdf_path)
        for k, v in pdf_meta.items():
            logger.info(f"{k}: {v}")

    xml_reference_txns: List[TxnRaw] = []
    xml_reference_datos: Dict[str, str] = {}
    xml_reference_loaded = False
    if xml_path and xml_path.exists() and xml_path.suffix.lower() == ".xml":
        try:
            root = ET.fromstring(xml_path.read_text(encoding="utf-8", errors="strict"))
        except UnicodeDecodeError:
            root = ET.fromstring(xml_path.read_text(encoding="utf-8", errors="ignore"))

        addenda = get_addenda(root)
        if addenda is None:
            msg = "ERROR: No encontré cfdi:Addenda en el XML. Este script espera movimientos dentro de la Addenda."
            if pdf_source_mode:
                logger.warning(f" {msg} - el PDF sigue siendo la fuente principal.")
            else:
                logger.error(msg)
                return 3
        else:
            xml_reference_datos = get_datos_generales(addenda)
            xml_reference_txns = extract_movimientos(addenda)
            xml_reference_loaded = True
    elif xml_path and not xml_path.exists():
        logger.error(f" No existe XML: {xml_path}")
        return 2

    pdf_xml_summary: Optional[Dict[str, Any]] = None

    # Parse Transactions
    raw_txns = []
    datos = {}
    
    if pdf_source_mode:
        logger.info(f" Usando PDF (OCR) como fuente de transacciones ---")
        pdf_txns = pu.extract_transactions_from_pdf(pdf_path, use_ocr=True)
        year = datetime.now().year
        if "cutoff_date" in pdf_meta:
            m = re.search(r"(\d{4})", pdf_meta["cutoff_date"])
            if m: year = int(m.group(1))
            
        for pt in pdf_txns:
            iso_date = pu.parse_mx_date(pt["raw_date"], year=year)
            if not iso_date:
                logger.debug(f" Skipping row - Invalid OCR Date: {pt['raw_date']}")
                continue
            raw_txns.append(TxnRaw(
                date=iso_date,
                description=pt["description"],
                amount=pt["amount"],
                rfc="",
                account_hint="",
                source="pdf",
                page=pt.get("page", 0),
                source_line=pt.get("line", "")
            ))

        datos = xml_reference_datos.copy() if xml_reference_datos else {}
        datos.setdefault("nombredelCliente", "PDF Extract")
        datos.setdefault("periodo", pdf_meta.get("cutoff_date", xml_reference_datos.get("periodo", "Unknown")))
        if xml_reference_txns:
            raw_txns, pdf_xml_summary = apply_xml_reference_to_pdf(raw_txns, xml_reference_txns)
        elif not raw_txns:
            logger.warning(" No se extrajeron movimientos del PDF.")

        if not datos:
            datos = {"nombredelCliente": "PDF Extract", "periodo": pdf_meta.get("cutoff_date", "Unknown")}
    elif (csv_path and csv_path.exists()) or (xml_path and xml_path.suffix.lower() in [".csv", ".xlsx", ".xls"]):
        # Handle cases where user might have passed CSV/XLSX to --xml or used --csv
        source = csv_path or xml_path
        logger.info(f" Leyendo Archivo (HSBC): {source.name} ---")
        import pandas as pd
        
        if source.suffix.lower() in [".xlsx", ".xls"]:
            df = pd.read_excel(source)
        else:
            df = pd.read_csv(source)
            
        df.columns = [c.strip().lower() for c in df.columns]
        
        # Map columns
        col_map = {}
        for c in df.columns:
            if any(k in c for k in ["fecha", "date"]): col_map["date"] = c
            if any(k in c for k in ["desc", "concepto", "movement", "descripcion"]): col_map["desc"] = c
            if "cargo" in c: col_map["charges"] = c
            if "abono" in c: col_map["payments"] = c
            if "importe" in c: col_map["amount"] = c

        if "date" not in col_map or "desc" not in col_map:
            logger.error(f" No pude identificar columnas básicas en el archivo. Columnas: {list(df.columns)}")
            return 3
            
        for _, row in df.iterrows():
            d_val = row[col_map["date"]]
            if pd.isna(d_val): continue
            
            iso_date = None
            if isinstance(d_val, datetime):
                iso_date = d_val.date().isoformat()
            else:
                d_str = str(d_val).strip()
                # Try some common date formats
                for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%m/%d/%Y", "%d-%m-%Y"]:
                    try:
                        iso_date = datetime.strptime(d_str, fmt).date().isoformat()
                        break
                    except ValueError: continue
                
                if not iso_date:
                    iso_date = pu.parse_mx_date(d_str)
            
            if not iso_date: continue
            
            desc = str(row[col_map["desc"]])
            
            # Amount logic
            amt = None
            if "amount" in col_map:
                amt = cu.parse_money(row[col_map["amount"]])
            elif "charges" in col_map and "payments" in col_map:
                c = cu.parse_money(row[col_map["charges"]]) or 0.0
                p = cu.parse_money(row[col_map["payments"]]) or 0.0
                amt = p - c 
            
            if amt is not None and amt != 0:
                raw_txns.append(TxnRaw(date=iso_date, description=desc, amount=amt, rfc="", account_hint=""))
        
        datos = {"nombredelCliente": "File Extract", "periodo": "See transactions"}
    else:
        if not xml_reference_loaded:
            logger.error(" El XML proporcionado no contiene movimientos válidos.")
            return 3
        datos = xml_reference_datos
        raw_txns = xml_reference_txns

    rules_yml = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    defaults = rules_yml.get("defaults", {}) or {}
    accounts = defaults.get("accounts", {}) or {}
    fallback_expense = defaults.get("fallback_expense", "Expenses:Other:Uncategorized")
    currency = defaults.get("currency", "MXN")

    # Igual que Santander:
    # Prefer HSBC-specific keys from rules.yml, fallback to built-in defaults
    # We avoid using the generic 'credit_card' key as it usually points to Santander
    cc_name, closing_day = cu.get_account_config(accounts, "hsbc_credit_card", "Liabilities:CC:HSBC")
    payment_asset, _ = cu.get_account_config(accounts, "hsbc_payment_asset", "Assets:HSBC Débito")

    merchant_aliases = rules_yml.get("merchant_aliases", []) or []
    compiled = cu.compile_rules(rules_yml)

    # Salida estándar + asistido
    out_rows: List[Dict[str, str]] = []
    unknown_agg = defaultdict(lambda: {"count": 0, "total": 0.0, "examples": set()})

    sum_charges = 0.0
    sum_payments = 0.0

    for t in raw_txns:
        expense, tags, merchant = cu.classify(t.description, compiled, merchant_aliases, fallback_expense)

        # Tags estándar
        tags = list(tags)
        period = cu.get_statement_period(t.date, closing_day)
        tags.append("card:hsbc")
        if period:
            tags.append(f"period:{period}")
        if t.rfc:
            tags.append(f"rfc:{t.rfc}")

        kind = infer_kind(t.description, t.amount, t.rfc)
        amt_abs = abs(t.amount)

        # Derive category
        category = ""
        if expense and ":" in expense:
            parts = expense.split(":")
            if len(parts) > 1:
                category = parts[1]

        if kind == "charge":
            sum_charges += amt_abs
            out_rows.append({
                "type": "withdrawal",
                "date": t.date,
                "amount": f"{amt_abs:.2f}",
                "currency_code": currency,
                "description": t.description,
                "source_name": cc_name,
                "destination_name": expense,
                "category_name": category,
                "tags": ",".join(sorted(set(tags))),
            })

            if expense == fallback_expense:
                ua = unknown_agg[merchant]
                ua["count"] += 1
                ua["total"] += amt_abs
                if len(ua["examples"]) < 5:
                    ua["examples"].add(t.description)

        elif kind == "payment":
            sum_payments += amt_abs
            out_rows.append({
                "type": "transfer",
                "date": t.date,
                "amount": f"{amt_abs:.2f}",
                "currency_code": currency,
                "description": t.description,
                "source_name": payment_asset,
                "destination_name": cc_name,
                "category_name": "",
                "tags": f"pago,credit-card,card:hsbc,period:{period}" if period else "pago,credit-card,card:hsbc",
            })

        elif kind in ("refund", "cashback"):
            # Estándar recomendado: que reduzca saldo de tarjeta (abono a CC)
            # -> transfer desde Income hacia la tarjeta
            income_src = "Income:Cashback" if kind == "cashback" else "Income:Other"
            out_rows.append({
                "type": "transfer",
                "date": t.date,
                "amount": f"{amt_abs:.2f}",
                "currency_code": currency,
                "description": t.description,
                "source_name": income_src,
                "destination_name": cc_name,
                "category_name": "",
                "tags": f"{kind},card:hsbc,period:{period}" if period else f"{kind},card:hsbc",
            })

    # CSV Firefly (ESTÁNDAR, igual que Santander)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "type", "date", "amount", "currency_code",
        "description", "source_name", "destination_name",
        "category_name", "tags"
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    # Unknown merchants agregado (asistido)
    unknown_path = Path(args.unknown_out)
    unknown_path.parent.mkdir(parents=True, exist_ok=True)
    with unknown_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["merchant", "count", "total", "examples"])
        w.writeheader()
        for merchant, data in sorted(unknown_agg.items(), key=lambda kv: (-kv[1]["total"], kv[0])):
            w.writerow({
                "merchant": merchant,
                "count": data["count"],
                "total": f"{data['total']:.2f}",
                "examples": " | ".join(sorted(data["examples"])),
            })

    # Suggestions YAML
    suggestions = {
        "version": 1,
        "suggested_rules": [cu.suggest_rule_from_merchant(m) for m in sorted(unknown_agg.keys())]
    }
    sugg_path = Path(args.suggestions_out)
    sugg_path.parent.mkdir(parents=True, exist_ok=True)
    sugg_path.write_text(yaml.safe_dump(suggestions, sort_keys=False, allow_unicode=True), encoding="utf-8")

    # Resumen
    cliente = datos.get("nombredelCliente", "")
    periodo = datos.get("periodo", "")
    cuenta_xml = datos.get("numerodecuenta", "")

    # Validación PDF
    pdf_path = Path(args.pdf)
    if args.pdf and pdf_path.exists():
        logger.info(f"\n--- Analizando PDF: {pdf_path.name} ---")
        meta = pu.extract_pdf_metadata(pdf_path)
        for k, v in meta.items():
            logger.info(f"{k}: {v}")

    logger.info("\n--- Resultados ---")
    logger.info(f"Cliente: {cliente}")
    logger.info(f"Periodo: {periodo}")
    logger.info(f"Cuenta (XML): {cuenta_xml}")
    logger.info(f"CSV Firefly: {out_path.resolve()}")
    logger.info(f"Movimientos exportados: {len(out_rows)}")
    logger.info(f"Suma cargos: {sum_charges:.2f}")
    logger.info(f"Suma pagos: {sum_payments:.2f}")

    if pdf_xml_summary:
        print_pdf_xml_validation_summary(pdf_xml_summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
