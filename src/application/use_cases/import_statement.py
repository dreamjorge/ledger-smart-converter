from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from application.ports.rules_config_reader import RulesConfigReader
from application.ports.statement_data_extractor import StatementDataExtractor
from application.ports.transaction_repository import TransactionRepository
from application.ports.import_repository import ImportRepository
from services.import_pipeline_service import ImportPipelineService
from domain.transaction import CanonicalTransaction
from logging_config import get_logger

LOGGER = get_logger("import_statement_use_case")

@dataclass
class ImportResult:
    import_id: int
    bank_id: str
    status: str
    total_processed: int
    inserted: int
    skipped_duplicates: int
    errors: int
    unknown_merchants: List[Dict[str, Any]]
    processed_transactions: List[Dict[str, Any]]

class ImportStatement:
    """
    Use Case for orchestrating the extraction, categorization, 
    and persistence of bank statements.
    """
    def __init__(
        self,
        config_reader: RulesConfigReader,
        data_extractor: StatementDataExtractor,
        transaction_repository: TransactionRepository,
        import_repository: ImportRepository
    ):
        self.config_reader = config_reader
        self.data_extractor = data_extractor
        self.transaction_repository = transaction_repository
        self.import_repository = import_repository

    def execute(
        self,
        bank_id: str,
        data_path: Optional[Path] = None,
        pdf_path: Optional[Path] = None,
        use_ocr: bool = False,
        strict: bool = False
    ) -> ImportResult:
        """
        Runs the import process for a given bank and statement files.
        """
        # 2. Extract raw transactions (before record_import to know the count)
        try:
            raw_txns = self.data_extractor.extract(bank_id, data_path, pdf_path, use_ocr)
        except Exception as e:
            LOGGER.error(f"Extraction failed for {bank_id}: {str(e)}")
            raise e

        # 3. Record the start of the import
        source_file = (data_path or pdf_path).name if (data_path or pdf_path) else "unknown"
        import_id = self.import_repository.record_import(
            bank_id=bank_id,
            source_file=source_file,
            status="processing",
            row_count=len(raw_txns)
        )

        try:
            # 4. Resolve configuration for the bank (INSIDE try block for status reporting)
            app_config = self.config_reader.get_app_config()
            bank_config_obj = app_config.banks.get(bank_id)
            if not bank_config_obj:
                raise ValueError(f"No configuration found for bank_id: {bank_id}")

            # 5. Initialize Pipeline Service with resolved rules
            acc_key = bank_config_obj.account_key
            fallback_name = bank_config_obj.fallback_name or bank_id
            if acc_key and acc_key in app_config.defaults.accounts:
                acc_def = app_config.defaults.accounts[acc_key]
                acc_name = acc_def.name
                closing_day = acc_def.closing_day
            else:
                acc_name = fallback_name
                closing_day = 1
                
            pay_key = bank_config_obj.payment_asset_key
            fallback_asset = bank_config_obj.fallback_asset or "Assets:Cash"
            if pay_key and pay_key in app_config.defaults.payment_assets:
                pay_asset = app_config.defaults.payment_assets[pay_key]
            else:
                pay_asset = fallback_asset

            pipeline = ImportPipelineService(
                app_config=app_config,
                bank_config=bank_config_obj,
                account_name=acc_name,
                pay_asset=pay_asset,
                closing_day=closing_day
            )

            # 5. Process transactions through categorization pipeline
            processed_txns, unknowns, warnings = pipeline.process_transactions(raw_txns, strict=strict)
            
            # 6. Save all to repository
            persist_results = self.transaction_repository.save_all(processed_txns)
            
            # 7. Map processed transactions to Dicts for UI/CSV (Firefly format)
            ui_txns = [self._map_to_firefly_dict(t) for t in processed_txns]

            # 8. Update import status
            self.import_repository.update_status(
                import_id=import_id,
                status="completed",
                row_count=persist_results.get("inserted", 0)
            )

            return ImportResult(
                import_id=import_id,
                bank_id=bank_id,
                status="completed",
                total_processed=len(raw_txns),
                inserted=persist_results.get("inserted", 0),
                skipped_duplicates=persist_results.get("skipped_duplicates", 0),
                errors=warnings,
                unknown_merchants=unknowns,
                processed_transactions=ui_txns
            )

        except Exception as e:
            LOGGER.error(f"Import processing failed for {bank_id}: {str(e)}", exc_info=True)
            self.import_repository.update_status(
                import_id=import_id,
                status="failed",
                error=str(e)
            )
            raise e

    def _map_to_firefly_dict(self, t: CanonicalTransaction) -> Dict[str, Any]:
        """Maps a CanonicalTransaction to the legacy Firefly CSV format."""
        return {
            "type": t.transaction_type,
            "date": t.date,
            "amount": f"{abs(t.amount):.2f}",
            "description": t.description,
            "source_name": t.account_id if t.transaction_type == "withdrawal" else t.account_id, # Simplified
            "destination_name": t.destination_name,
            "category_name": t.category,
            "tags": t.tags,
        }
