from abc import ABC, abstractmethod
from typing import List
from pathlib import Path

# Assuming TxnRaw will continue to live in generic_importer or domain later, 
# for now we import it from generic_importer.
from infrastructure.parsers.models import TxnRaw

class StatementParser(ABC):
    """Interface for parsing bank statements into raw transactions."""
    
    @abstractmethod
    def parse(self, file_path: Path) -> List[TxnRaw]:
        """Parse a statement file and return a list of raw transactions."""
        pass
