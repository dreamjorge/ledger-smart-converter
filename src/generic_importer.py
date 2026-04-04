#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generic Importer for Firefly III
- Reads bank configuration from rules.yml
- Supports multiple formats (XLSX, XML, CSV via PDF/OCR)
- Centralizes classification and output logic
"""

import argparse
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import yaml

# Local modules
import common_utils as cu
from description_normalizer import normalize_description
from account_mapping import resolve_canonical_account_id
from errors import ConfigError
from logging_config import build_run_log, get_logger, write_json_atomic
import pdf_utils as pu
from date_utils import parse_spanish_date as parse_es_date
from validation import validate_tags, validate_transaction
from services.import_pipeline_service import ImportPipelineService
from infrastructure.parsers.parser_factory import ParserFactory

LOGGER = get_logger("generic_importer")
USE_NORMALIZED_TEXT = os.getenv("LSC_USE_NORMALIZED_TEXT", "true").strip().lower() not in {"0", "false", "no"}

from infrastructure.parsers.models import TxnRaw

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

    def _build_pipeline_service(self) -> ImportPipelineService:
        return ImportPipelineService(
            bank_id=self.bank_id,
            account_name=self.acc_name,
            card_tag=self.bank_cfg["card_tag"],
            pay_asset=self.pay_asset,
            closing_day=self.closing_day,
            currency=self.currency,
            fallback_expense=self.fallback_expense,
            compiled_rules=self.compiled_rules,
            merchant_aliases=self.merchant_aliases,
            use_normalized_text=USE_NORMALIZED_TEXT,
            normalize_description_fn=normalize_description,
            clean_description_fn=cu.clean_description,
            classify_fn=cu.classify,
            validate_transaction_fn=validate_transaction,
            validate_tags_fn=validate_tags,
            resolve_canonical_account_id_fn=resolve_canonical_account_id,
            get_statement_period_fn=cu.get_statement_period,
        )

    def load_data(self, data_path: Optional[Path], pdf_path: Optional[Path], use_pdf_source: bool) -> List[TxnRaw]:
        # Always prioritize PDF source if requested
        if use_pdf_source and pdf_path:
            parser = ParserFactory.get_parser(self.bank_cfg["type"], use_pdf_source=True)
            return parser.parse(pdf_path)

        if not data_path: 
            return []
            
        parser = ParserFactory.get_parser(self.bank_cfg["type"], use_pdf_source=False)
        txns = parser.parse(data_path)
            
        return sorted(txns, key=lambda t: (t.date, t.description.lower(), round(float(t.amount), 2), t.rfc))


    def process(self, txns: List[TxnRaw], strict: bool = False) -> Tuple[List[Dict], List[Dict], int]:
        pipeline = self._build_pipeline_service()
        return pipeline.process_transactions(txns, strict=strict)

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
