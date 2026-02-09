#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generic Importer for Firefly III
- Reads bank configuration from rules.yml
- Supports multiple formats (XLSX, XML, CSV via PDF/OCR)
- Centralizes classification and output logic
"""

import argparse
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import yaml

# Local modules
import common_utils as cu
from domain.transaction import CanonicalTransaction
from errors import ConfigError, ValidationError
from logging_config import build_run_log, get_logger, write_json_atomic
import pdf_utils as pu
from validation import validate_tags, validate_transaction

LOGGER = get_logger("generic_importer")

@dataclass(frozen=True)
class TxnRaw:
    date: str
    description: str
    amount: float
    rfc: str = ""
    account_hint: str = ""
    source: str = "data"
    page: int = 0
    source_line: str = ""

def parse_iso_date(s: str) -> str:
    s = (s or "").strip()
    if not s: return ""
    try:
        dt = datetime.fromisoformat(s)
        return dt.date().isoformat()
    except ValueError:
        return s[:10]

# Import consolidated date parsing functions
from date_utils import parse_spanish_date as parse_es_date

class GenericImporter:
    def __init__(self, rules_path: Path, bank_id: str):
        self.rules_path = rules_path
        self.bank_id = bank_id
        self.config = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        self.bank_cfg = self.config.get("banks", {}).get(bank_id)
        if not self.bank_cfg:
            raise ConfigError(f"Bank ID '{bank_id}' not found in rules.yml")
            
        self.defaults = self.config.get("defaults", {})
        self.accounts = self.defaults.get("accounts", {})
        self.fallback_expense = self.defaults.get("fallback_expense", "Expenses:Other:Uncategorized")
        self.currency = self.defaults.get("currency", "MXN")
        
        acc_key = self.bank_cfg.get("account_key")
        pay_key = self.bank_cfg.get("payment_asset_key")
        
        self.acc_name, self.closing_day = cu.get_account_config(self.accounts, acc_key, self.bank_cfg.get("fallback_name"))
        self.pay_asset, _ = cu.get_account_config(self.accounts, pay_key, self.bank_cfg.get("fallback_asset"))
        
        self.compiled_rules = cu.compile_rules(self.config)
        self.merchant_aliases = self.config.get("merchant_aliases", [])

    def load_data(self, data_path: Optional[Path], pdf_path: Optional[Path], use_pdf_source: bool) -> List[TxnRaw]:
        txns = []
        
        if use_pdf_source and pdf_path:
            raw_pdf = pu.extract_transactions_from_pdf(pdf_path, use_ocr=True)
            year = datetime.now().year
            # Prefer year from filename or metadata if possible
            for pt in raw_pdf:
                iso_date = pu.parse_mx_date(pt["raw_date"], year=year)
                if iso_date:
                    txns.append(TxnRaw(date=iso_date, description=pt["description"], amount=pt["amount"], source="pdf"))
            return txns

        if not data_path: return []
        
        ext = data_path.suffix.lower()
        if ext == ".xml" and self.bank_cfg["type"] == "xml":
            txns = self._load_xml(data_path)
        elif ext in [".xlsx", ".xls"] and self.bank_cfg["type"] == "xlsx":
            txns = self._load_xlsx(data_path)
        else:
            # Fallback to generic CSV/Excel if type mismatch but file exists
            txns = self._load_generic(data_path)
            
        return sorted(txns, key=lambda t: (t.date, t.description.lower(), round(float(t.amount), 2), t.rfc))

    def _load_xml(self, path: Path) -> List[TxnRaw]:
        # Special case for HSBC-like XML
        root = ET.fromstring(path.read_text(encoding="utf-8", errors="ignore"))
        addenda = root.find(".//{*}Addenda")
        if addenda is None: return []
        
        out = []
        for e in addenda.iter():
            tag = e.tag.split("}")[-1]
            if tag in ["MovimientosDelCliente", "MovimientoDelClienteFiscal"]:
                date = parse_iso_date(e.attrib.get("fecha"))
                desc = cu.strip_ws(e.attrib.get("descripcion"))
                amt = cu.parse_money(e.attrib.get("importe"))
                rfc = e.attrib.get("RFCenajenante", "")
                if date and desc and amt is not None:
                    out.append(TxnRaw(date=date, description=desc, amount=amt, rfc=rfc))
        return out

    def _load_xlsx(self, path: Path) -> List[TxnRaw]:
        df = pd.read_excel(path, header=None)
        # Find header row (generic: look for "FECHA")
        header_idx = 0
        for i in range(min(20, len(df))):
            if any("FECHA" in str(v).upper() for v in df.iloc[i]):
                header_idx = i
                break
        
        df.columns = [str(c).strip().lower() for c in df.iloc[header_idx]]
        df = df.iloc[header_idx+1:].dropna(subset=["fecha", "concepto", "importe"], how="any")
        
        out = []
        for _, r in df.iterrows():
            date = parse_es_date(str(r["fecha"]))
            amt = cu.parse_money(r["importe"])
            if date and amt is not None:
                out.append(TxnRaw(
                    date=date, 
                    description=str(r["concepto"]).strip(), 
                    amount=amt
                ))
        return out

    def _load_generic(self, path: Path) -> List[TxnRaw]:
        df = pd.read_excel(path) if path.suffix.lower() in [".xlsx", ".xls"] else pd.read_csv(path)
        df.columns = [c.strip().lower() for c in df.columns]
        
        # Heuristic mapping
        col_map = {}
        for c in df.columns:
            if any(k in c for k in ["fecha", "date"]): col_map["date"] = c
            if any(k in c for k in ["desc", "concepto", "descripcion"]): col_map["desc"] = c
            if any(k in c for k in ["importe", "amount", "monto"]): col_map["amt"] = c
            
        if "date" not in col_map or "desc" not in col_map: return []
        
        out = []
        for _, r in df.iterrows():
            date = parse_iso_date(str(r[col_map["date"]])) or parse_es_date(str(r[col_map["date"]]))
            amt = cu.parse_money(r[col_map["amt"]]) if "amt" in col_map else 0.0
            if date and amt is not None:
                out.append(TxnRaw(date=date, description=str(r[col_map["desc"]]), amount=amt))
        return out

    def process(self, txns: List[TxnRaw], strict: bool = False) -> Tuple[List[Dict], List[Dict], int]:
        out_rows = []
        unknown_agg = defaultdict(lambda: {"count": 0, "total": 0.0, "examples": set()})
        warning_count = 0
        
        for t in txns:
            clean_desc = cu.clean_description(t.description)
            canonical = CanonicalTransaction(
                date=t.date,
                description=clean_desc,
                amount=float(t.amount),
                bank_id=self.bank_id,
                account_id=self.acc_name,
                source=t.source,
                rfc=t.rfc,
            )
            record_errors = validate_transaction(canonical)
            if record_errors:
                warning_count += 1
                LOGGER.warning("skipping invalid transaction: %s", {"errors": record_errors, "txn": canonical.id})
                if strict:
                    raise ValidationError(f"Invalid transaction {canonical.id}: {record_errors}")
                continue

            expense, tags, merchant = cu.classify(clean_desc, self.compiled_rules, self.merchant_aliases, self.fallback_expense)
            tags = set(tags)
            tags.add(self.bank_cfg["card_tag"])
            period = cu.get_statement_period(t.date, self.closing_day)
            if period: tags.add(f"period:{period}")
            if t.rfc: tags.add(f"rfc:{t.rfc}")
            tags.add(f"txn:{canonical.id[:10]}")
            tag_errors = validate_tags(list(tags))
            if tag_errors:
                warning_count += 1
                LOGGER.warning("tag validation warning: %s", {"errors": tag_errors, "txn": canonical.id})
                if strict:
                    raise ValidationError(f"Invalid tags {canonical.id}: {tag_errors}")
            
            # Category from expense
            category = expense.split(":")[1] if ":" in expense else ""
            
            # HSBC special inference if it's HSBC
            if self.bank_id == "hsbc":
                from import_hsbc_cfdi_firefly import infer_kind
                kind = infer_kind(clean_desc, t.amount, t.rfc)
                if kind == "charge":
                    row = self._make_withdrawal(t, clean_desc, expense, category, tags)
                elif kind == "payment":
                    row = self._make_transfer(t, clean_desc, self.pay_asset, self.acc_name, tags, "pago")
                else: # refund/cashback
                    src = "Income:Cashback" if kind == "cashback" else "Income:Other"
                    row = self._make_transfer(t, clean_desc, src, self.acc_name, tags, kind)
            else:
                # Standard Logic
                if t.amount < 0: # Charge
                    row = self._make_withdrawal(t, clean_desc, expense, category, tags)
                else: # Payment
                    row = self._make_transfer(t, clean_desc, self.pay_asset, self.acc_name, tags, "pago")

            if row:
                out_rows.append(row)
                if row["type"] == "withdrawal" and expense == self.fallback_expense:
                    ua = unknown_agg[merchant]
                    ua["count"] += 1
                    ua["total"] += abs(t.amount)
                    if len(ua["examples"]) < 5: ua["examples"].add(clean_desc)
                    
        return out_rows, self._format_unknown(unknown_agg), warning_count

    def _make_withdrawal(self, t, desc, expense, category, tags):
        return {
            "type": "withdrawal", "date": t.date, "amount": f"{abs(t.amount):.2f}",
            "currency_code": self.currency, "description": desc,
            "source_name": self.acc_name, "destination_name": expense,
            "category_name": category, "tags": ",".join(sorted(tags))
        }

    def _make_transfer(self, t, desc, source, dest, tags, extra_tag):
        t2 = set(tags)
        t2.add(extra_tag)
        return {
            "type": "transfer", "date": t.date, "amount": f"{abs(t.amount):.2f}",
            "currency_code": self.currency, "description": desc,
            "source_name": source, "destination_name": dest,
            "category_name": "", "tags": ",".join(sorted(t2))
        }

    def _format_unknown(self, agg):
        out = []
        for m, d in agg.items():
            out.append({"merchant": m, "count": d["count"], "total": f"{d['total']:.2f}", "examples": " | ".join(sorted(d["examples"]))})
        return sorted(out, key=lambda x: -float(x["total"]))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", required=True, help="Bank ID from rules.yml")
    ap.add_argument("--data", help="Input file (XML/XLSX/CSV)")
    ap.add_argument("--pdf", help="Optional PDF for OCR/Metadata")
    ap.add_argument("--pdf-source", action="store_true", help="Use PDF as main source")
    ap.add_argument("--rules", default="config/rules.yml")
    ap.add_argument("--out", required=True)
    ap.add_argument("--unknown-out", default="unknown_merchants.csv")
    ap.add_argument("--strict", action="store_true", help="Fail if validation issues are detected")
    ap.add_argument("--dry-run", action="store_true", help="Parse and validate, but do not write output files")
    ap.add_argument("--log-json", help="Write execution manifest JSON")
    args = ap.parse_args()

    importer = GenericImporter(Path(args.rules), args.bank)
    txns = importer.load_data(Path(args.data) if args.data else None, Path(args.pdf) if args.pdf else None, args.pdf_source)
    
    # Optional PDF Metadata validation
    if args.pdf:
         meta = pu.extract_pdf_metadata(Path(args.pdf))
         LOGGER.info("pdf metadata: %s", meta)

    rows, unknown, warning_count = importer.process(txns, strict=args.strict)
    
    # Save results
    if not args.dry_run:
        write_csv_atomic(pd.DataFrame(rows), Path(args.out))
        write_csv_atomic(pd.DataFrame(unknown), Path(args.unknown_out))
    
    manifest = build_run_log(
        bank_id=args.bank,
        input_count=len(txns),
        output_count=len(rows),
        warning_count=warning_count,
        metadata={"dry_run": args.dry_run, "strict": args.strict},
    )
    if args.log_json:
        write_json_atomic(Path(args.log_json), manifest)

    LOGGER.info("processed %s transactions (input=%s warnings=%s)", len(rows), len(txns), warning_count)
    if args.dry_run:
        LOGGER.info("dry-run enabled, no CSV files were written")
    else:
        LOGGER.info("saved outputs to %s and %s", args.out, args.unknown_out)

def write_csv_atomic(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)

if __name__ == "__main__":
    main()
