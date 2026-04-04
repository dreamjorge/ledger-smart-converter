from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

@dataclass(frozen=True)
class RawTransaction:
    """Represents a raw transaction extracted from a bank statement BEFORE categorization."""
    date: str
    description: str
    amount: float
    rfc: str = ""
    account_hint: str = ""
    source: str = "data"
    page: int = 0
    source_line: str = ""

class StatementDataExtractor(ABC):
    """Port for extracting raw transactional data from various statement formats."""
    
    @abstractmethod
    def extract(
        self, 
        bank_id: str, 
        data_path: Optional[Path] = None, 
        pdf_path: Optional[Path] = None, 
        use_ocr: bool = False
    ) -> List[RawTransaction]:
        """
        Parses a file and returns a list of RawTransaction objects.
        
        Args:
            bank_id: Identified for the bank (e.g., 'hsbc', 'santander_likeu').
            data_path: Path to the main data file (XML, XLSX, CSV).
            pdf_path: Optional path to a PDF for OCR/Extraction.
            use_ocr: Whether to force OCR for PDF extraction.
        """
        pass
