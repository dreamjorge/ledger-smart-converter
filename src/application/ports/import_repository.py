from abc import ABC, abstractmethod
from typing import Optional

class ImportRepository(ABC):
    """Port for tracking and recording statement import events."""
    
    @abstractmethod
    def record_import(
        self,
        bank_id: str,
        source_file: str,
        status: str,
        row_count: int = 0,
        error: Optional[str] = None,
    ) -> int:
        """Records the start of an import process and returns its ID."""
        pass

    @abstractmethod
    def update_status(
        self,
        import_id: int,
        status: str,
        row_count: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """Updates the status and results of an existing import record."""
        pass
