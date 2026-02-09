#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Santander LikeU (u otro banco similar):
- Fuente principal: XLSX (movimientos)
- Salida: CSV para Firefly (credit card / liability)
- Categorización: rules.yml (YAML)
- Aprendizaje asistido:
    - unknown_merchants.csv (agregado)
    - rules_suggestions.yml (para copiar/pegar)
- Validación opcional con PDF: OCR/Texto de resumen
"""

import argparse
import csv
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml

# Local modules
import common_utils as cu
import pdf_utils as pu
from logging_config import get_logger

logger = get_logger(__name__)

MONTHS = {
    "ene": "01", "feb": "02", "mar": "03", "abr": "04", "may": "05", "jun": "06",
    "jul": "07", "ago": "08", "sep": "09", "oct": "10", "nov": "11", "dic": "12",
}

DATE_ES_RE = re.compile(r"^\s*(\d{1,2})/([A-Za-z]{3})/(\d{2,4})\s*$")


# Import consolidated date parsing function
from date_utils import parse_spanish_date as parse_es_date


def find_header_row(df: pd.DataFrame) -> int:
    """Encuentra la fila donde la primera columna es FECHA."""
    for i in range(len(df)):
        v = str(df.iloc[i, 0]).strip().upper()
        if v == "FECHA":
            return i
    raise ValueError("No encontré encabezado (FECHA/CONCEPTO/IMPORTE).")


# ----------------------------
# MAIN
# ----------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="XLSX -> Firefly (credit card) + rules + assisted learning + optional PDF validation")
    ap.add_argument("--xlsx", help="Ruta al XLSX del banco (movimientos).")
    ap.add_argument("--rules", required=True, help="Ruta a rules.yml")
    ap.add_argument("--pdf", default="", help="(Opcional) PDF para validación OCR (resumen).")
    ap.add_argument("--pdf-source", action="store_true", help="Usar el PDF como fuente primaria de transacciones (OCR).")
    ap.add_argument("--out", default="firefly_likeu.csv", help="CSV salida para importar en Firefly.")
    ap.add_argument("--unknown-out", default="unknown_merchants.csv", help="CSV de desconocidos (aprendizaje asistido).")
    ap.add_argument("--suggestions-out", default="rules_suggestions.yml", help="YAML con sugerencias de reglas.")
    args = ap.parse_args()

    xlsx_path = Path(args.xlsx) if args.xlsx else None
    pdf_path = Path(args.pdf) if args.pdf else None
    rules_path = Path(args.rules)

    if not xlsx_path and not (args.pdf_source and pdf_path):
        logger.error(" Debe proporcionar --xlsx o --pdf (con --pdf-source)")
        return 2
    if not rules_path.exists():
        logger.error(f" No existe rules.yml: {rules_path}")
        return 2

    rules_yml = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    defaults = rules_yml.get("defaults", {}) or {}
    accounts = defaults.get("accounts", {}) or {}
    fallback_expense = defaults.get("fallback_expense", "Expenses:Other:Uncategorized")
    currency = defaults.get("currency", "MXN")

    cc_name, closing_day = cu.get_account_config(accounts, "credit_card", "Liabilities:CC:Santander LikeU")
    payment_asset, _ = cu.get_account_config(accounts, "payment_asset", "Assets:Santander Débito")

    merchant_aliases = rules_yml.get("merchant_aliases", []) or []
    compiled = cu.compile_rules(rules_yml)

    # Metadata extraction
    pdf_meta = {}
    if pdf_path and pdf_path.exists():
        logger.info(f"\n--- Analizando PDF: {pdf_path.name} ---")
        pdf_meta = pu.extract_pdf_metadata(pdf_path)
        for k, v in pdf_meta.items():
            logger.info(f"  {k}: {v}")

    # Lee datos
    df = pd.DataFrame()
    
    if args.pdf_source and pdf_path:
        logger.info(f"--- Usando PDF (OCR) como fuente de transacciones ---")
        pdf_txns = pu.extract_transactions_from_pdf(pdf_path, use_ocr=True)
        year = datetime.now().year
        if "cutoff_date" in pdf_meta:
            m = re.search(r"(\d{4})", pdf_meta["cutoff_date"])
            if m: year = int(m.group(1))
            
        rows = []
        for pt in pdf_txns:
            # Convert OCR date to XLSX-like format for parse_es_date to handle
            iso_date = pu.parse_mx_date(pt["raw_date"], year=year)
            # We bypass parse_es_date later by putting ISO directly if we want,
            # but let's just make a dataframe that matches the XLSX structure.
            rows.append({
                "fecha": iso_date,
                "concepto": pt["description"],
                "importe": pt["amount"]
            })
        df = pd.DataFrame(rows)
    else:
        # Lee XLSX
        if not xlsx_path or not xlsx_path.exists():
            logger.error(f" No existe XLSX: {xlsx_path}")
            return 2
            
        raw = pd.read_excel(xlsx_path, sheet_name=0, header=None)
        hdr = find_header_row(raw)
        cols = [str(x).strip().lower() for x in raw.iloc[hdr].tolist()]
        df = raw.iloc[hdr + 1:].copy()
        df.columns = cols

        for col in ["fecha", "concepto", "importe"]:
            if col not in df.columns:
                logger.error(f" No encontré columna '{col}'. Columnas: {list(df.columns)}")
                return 3

        df = df.dropna(subset=["fecha", "concepto", "importe"], how="any")

    # Salida Firefly y agregación para asistido
    out_rows: List[Dict[str, str]] = []
    unknown_agg = defaultdict(lambda: {"count": 0, "total": 0.0, "examples": set()})

    sum_cargos = 0.0
    sum_abonos = 0.0

    for _, r in df.iterrows():
        date = parse_es_date(r["fecha"])
        if not date:
            # Only print if we are in PDF OCR mode, to avoid clutter in standard Excel mode
            if args.pdf_source:
                logger.debug(f" Skipped row - Invalid Date: {r['fecha']}")
            continue

        desc = str(r["concepto"]).strip()
        amt = cu.parse_money(r["importe"])
        if amt is None or amt == 0:
            if args.pdf_source:
                logger.debug(f" Skipped row - Invalid Amount: {r['importe']} ({desc})")
            continue

        expense, tags, merchant = cu.classify(desc, compiled, merchant_aliases, fallback_expense)
        period = cu.get_statement_period(date, closing_day)
        tags.append("card:likeu")
        if period:
            tags.append(f"period:{period}")
        
        # Derive category from expense (e.g., "Expenses:Food:Restaurants" -> "Food")
        category = ""
        if expense and ":" in expense:
            parts = expense.split(":")
            if len(parts) > 1:
                category = parts[1]

        if amt < 0:
            # Compra / cargo: withdrawal desde CC hacia Expenses:<...>
            sum_cargos += abs(amt)
            out_rows.append({
                "type": "withdrawal",
                "date": date,
                "amount": f"{abs(amt):.2f}",
                "currency_code": currency,
                "description": desc,
                "source_name": cc_name,
                "destination_name": expense,
                "category_name": category,
                "tags": ",".join(tags),
            })

            if expense == fallback_expense:
                ua = unknown_agg[merchant]
                ua["count"] += 1
                ua["total"] += abs(amt)
                if len(ua["examples"]) < 5:
                    ua["examples"].add(desc)

        else:
            # Abono / pago: transfer desde asset hacia CC
            sum_abonos += abs(amt)
            out_rows.append({
                "type": "transfer",
                "date": date,
                "amount": f"{abs(amt):.2f}",
                "currency_code": currency,
                "description": desc,
                "source_name": payment_asset,
                "destination_name": cc_name,
                "category_name": "",
                "tags": f"pago,credit-card,card:likeu,period:{period}" if period else "pago,credit-card,card:likeu",
            })

    # Escribe CSV Firefly
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["type", "date", "amount", "currency_code", "description", "source_name", "destination_name", "category_name", "tags"]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    # Escribe unknown_merchants.csv (agregado)
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

    # Escribe rules_suggestions.yml
    suggestions = {
        "version": 1,
        "suggested_rules": [cu.suggest_rule_from_merchant(m) for m in sorted(unknown_agg.keys())]
    }
    sugg_path = Path(args.suggestions_out)
    sugg_path.parent.mkdir(parents=True, exist_ok=True)
    sugg_path.write_text(yaml.safe_dump(suggestions, sort_keys=False, allow_unicode=True), encoding="utf-8")

    # Validación PDF
    pdf_path = Path(args.pdf)
    if args.pdf and pdf_path.exists():
        logger.info(f"\n--- Analizando PDF: {pdf_path.name} ---")
        meta = pu.extract_pdf_metadata(pdf_path)
        for k, v in meta.items():
            logger.info(f"  {k}: {v}")
        
        # Comparaciones útiles
        if "total_pagar" in meta:
            diff_net = abs(meta["total_pagar"] - (sum_cargos - sum_abonos)) # aprox
            logger.info(f"  (Ref) Total Pagar PDF: {meta['total_pagar']:.2f}")

    logger.info("\n--- Resultados ---")
    logger.info(f"CSV Firefly: {out_path.resolve()}")
    logger.info(f"Movimientos exportados: {len(out_rows)}")
    logger.info(f"Suma cargos: {sum_cargos:.2f}")
    logger.info(f"Suma abonos: {sum_abonos:.2f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
