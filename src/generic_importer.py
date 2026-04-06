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

from typing import Union
from pathlib import Path
from domain.config_models import AppConfiguration, BankConfig

class GenericImporter:
    def __init__(self, config_source: Union[AppConfiguration, Path, str], bank_id: str, ml_categorizer: Optional[Any] = None):
        if hasattr(config_source, "banks"):
            self.app_config = config_source
        else:
            from infrastructure.adapters.yaml_rules_repository import YamlRulesRepository
            repo = YamlRulesRepository(Path(config_source))
            self.app_config = repo.get_app_config()
            
        self.bank_id = bank_id
        
        self.bank_cfg = self.app_config.banks.get(bank_id)
        if not self.bank_cfg:
            from errors import ConfigError
            raise ConfigError(f"Bank ID '{bank_id}' not found in configuration")
            
        # Resolve credit account configuration
        acc_key = self.bank_cfg.account_key
        fallback_name = self.bank_cfg.fallback_name or "Unknown"
        
        if acc_key and acc_key in self.app_config.defaults.accounts:
            acc_def = self.app_config.defaults.accounts[acc_key]
            self.acc_name = acc_def.name
            self.closing_day = acc_def.closing_day
        else:
            self.acc_name = fallback_name
            self.closing_day = 1
            
        # Resolve payment asset configuration
        pay_key = self.bank_cfg.payment_asset_key
        fallback_asset = self.bank_cfg.fallback_asset or "Unknown"
        
        if pay_key and pay_key in self.app_config.defaults.payment_assets:
            self.pay_asset = self.app_config.defaults.payment_assets[pay_key]
        else:
            self.pay_asset = fallback_asset

        self.ml_categorizer = ml_categorizer

    def _build_pipeline_service(self) -> ImportPipelineService:
        return ImportPipelineService(
            app_config=self.app_config,
            bank_config=self.bank_cfg,
            account_name=self.acc_name,
            pay_asset=self.pay_asset,
            closing_day=self.closing_day,
            use_normalized_text=USE_NORMALIZED_TEXT,
            normalize_description_fn=normalize_description,
            clean_description_fn=cu.clean_description,
            classify_fn=cu.classify,
            validate_transaction_fn=validate_transaction,
            validate_tags_fn=validate_tags,
            resolve_canonical_account_id_fn=resolve_canonical_account_id,
            get_statement_period_fn=cu.get_statement_period,
            ml_categorizer=self.ml_categorizer,
        )

    def load_data(self, data_path: Optional[Path], pdf_path: Optional[Path], use_pdf_source: bool) -> List[TxnRaw]:
        # Always prioritize PDF source if requested
        if use_pdf_source and pdf_path:
            parser = ParserFactory.get_parser(self.bank_cfg.type, bank_id=self.bank_id, use_pdf_source=True)
            return parser.parse(pdf_path)

        if not data_path:
            return []

        parser = ParserFactory.get_parser(self.bank_cfg.type, bank_id=self.bank_id, use_pdf_source=False)
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

    from infrastructure.adapters.yaml_rules_repository import YamlRulesRepository
    rules_repo = YamlRulesRepository(Path(args.rules), Path("config/accounts.yml"))
    app_config = rules_repo.get_app_config()

    importer = GenericImporter(app_config, args.bank)
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
