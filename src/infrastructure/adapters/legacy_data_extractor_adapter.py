from typing import List, Optional
from pathlib import Path
from application.ports.statement_data_extractor import StatementDataExtractor, RawTransaction
from generic_importer import GenericImporter

class LegacyDataExtractorAdapter(StatementDataExtractor):
    """
    Adapter that implements StatementDataExtractor by wrapping the legacy
    logic in GenericImporter.
    """
    def __init__(self, rules_path: Path):
        self.rules_path = rules_path

    def extract(
        self, 
        bank_id: str, 
        data_path: Optional[Path] = None, 
        pdf_path: Optional[Path] = None, 
        use_ocr: bool = False
    ) -> List[RawTransaction]:
        """
        Delegates extraction to GenericImporter and maps legacy TxnRaw to RawTransaction.
        """
        importer = GenericImporter(self.rules_path, bank_id)
        legacy_txns = importer.load_data(data_path, pdf_path, use_ocr)
        
        return [
            RawTransaction(
                date=t.date,
                description=t.description,
                amount=t.amount,
                rfc=t.rfc,
                account_hint=t.account_hint,
                source=t.source,
                page=t.page,
                source_line=t.source_line
            ) for t in legacy_txns
        ]
