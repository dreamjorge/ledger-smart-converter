from typing import Optional
from application.ports.import_repository import ImportRepository
from services.db_service import DatabaseService

class SqliteImportRepository(ImportRepository):
    """
    Adapter that implements ImportRepository using SQLite through DatabaseService.
    """
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service

    def record_import(
        self,
        bank_id: str,
        source_file: str,
        status: str,
        row_count: int = 0,
        error: Optional[str] = None,
    ) -> int:
        return self.db_service.record_import(
            bank_id=bank_id,
            source_file=source_file,
            status=status,
            row_count=row_count,
            error=error
        )

    def update_status(
        self,
        import_id: int,
        status: str,
        row_count: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        self.db_service.update_import_status(
            import_id=import_id,
            status=status,
            row_count=row_count,
            error=error
        )
