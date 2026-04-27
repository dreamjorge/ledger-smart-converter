from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from logging_config import get_logger

logger = get_logger("metrics_service")


@dataclass
class StageTiming:
    total_seconds: float = 0.0
    count: int = 0

    def add(self, seconds: float) -> None:
        self.total_seconds += seconds
        self.count += 1

    def avg_ms(self) -> float:
        return (self.total_seconds / self.count * 1000) if self.count > 0 else 0.0


@dataclass
class MetricsCollector:
    """Collects structured timing and count metrics from the import pipeline."""

    stage_normalize: StageTiming = field(default_factory=StageTiming)
    stage_validate: StageTiming = field(default_factory=StageTiming)
    stage_classify: StageTiming = field(default_factory=StageTiming)
    stage_build: StageTiming = field(default_factory=StageTiming)

    processed: int = 0
    failed: int = 0
    categorized: int = 0
    ml_predicted: int = 0

    bank_id: str = ""
    account_name: str = ""

    def record_normalize(self, seconds: float) -> None:
        self.stage_normalize.add(seconds)

    def record_validate(self, seconds: float) -> None:
        self.stage_validate.add(seconds)

    def record_classify(self, seconds: float) -> None:
        self.stage_classify.add(seconds)

    def record_build(self, seconds: float) -> None:
        self.stage_build.add(seconds)

    def record_processed(self) -> None:
        self.processed += 1

    def record_failed(self) -> None:
        self.failed += 1

    def record_categorized(self) -> None:
        self.categorized += 1

    def record_ml_predicted(self) -> None:
        self.ml_predicted += 1

    def as_dict(self) -> Dict[str, Any]:
        total_time = (
            self.stage_normalize.total_seconds
            + self.stage_validate.total_seconds
            + self.stage_classify.total_seconds
            + self.stage_build.total_seconds
        )
        return {
            "bank_id": self.bank_id,
            "account_name": self.account_name,
            "processed": self.processed,
            "failed": self.failed,
            "categorized": self.categorized,
            "ml_predicted": self.ml_predicted,
            "timing": {
                "normalize_s": round(self.stage_normalize.total_seconds, 4),
                "normalize_avg_ms": round(self.stage_normalize.avg_ms(), 2),
                "normalize_count": self.stage_normalize.count,
                "validate_s": round(self.stage_validate.total_seconds, 4),
                "validate_avg_ms": round(self.stage_validate.avg_ms(), 2),
                "validate_count": self.stage_validate.count,
                "classify_s": round(self.stage_classify.total_seconds, 4),
                "classify_avg_ms": round(self.stage_classify.avg_ms(), 2),
                "classify_count": self.stage_classify.count,
                "build_s": round(self.stage_build.total_seconds, 4),
                "build_avg_ms": round(self.stage_build.avg_ms(), 2),
                "build_count": self.stage_build.count,
                "total_s": round(total_time, 4),
            },
        }

    def write_to_db(self, db_service) -> None:
        metrics = self.as_dict()
        recorded_at = datetime.now(timezone.utc).isoformat()

        db_service.execute(
            """
            INSERT INTO import_metrics
                (bank_id, account_name, processed, failed, categorized,
                 ml_predicted, normalize_s, normalize_avg_ms, normalize_count,
                 validate_s, validate_avg_ms, validate_count,
                 classify_s, classify_avg_ms, classify_count,
                 build_s, build_avg_ms, build_count, total_s, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metrics["bank_id"],
                metrics["account_name"],
                metrics["processed"],
                metrics["failed"],
                metrics["categorized"],
                metrics["ml_predicted"],
                metrics["timing"]["normalize_s"],
                metrics["timing"]["normalize_avg_ms"],
                metrics["timing"]["normalize_count"],
                metrics["timing"]["validate_s"],
                metrics["timing"]["validate_avg_ms"],
                metrics["timing"]["validate_count"],
                metrics["timing"]["classify_s"],
                metrics["timing"]["classify_avg_ms"],
                metrics["timing"]["classify_count"],
                metrics["timing"]["build_s"],
                metrics["timing"]["build_avg_ms"],
                metrics["timing"]["build_count"],
                metrics["timing"]["total_s"],
                recorded_at,
            ),
        )
        logger.debug("wrote import_metrics for %s/%s", self.bank_id, self.account_name)


def ensure_import_metrics_table(db_service) -> None:
    try:
        db_service.execute(
            """
            CREATE TABLE IF NOT EXISTS import_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_id TEXT NOT NULL,
                account_name TEXT NOT NULL,
                processed INTEGER NOT NULL,
                failed INTEGER NOT NULL,
                categorized INTEGER NOT NULL,
                ml_predicted INTEGER NOT NULL,
                normalize_s REAL NOT NULL,
                normalize_avg_ms REAL NOT NULL,
                normalize_count INTEGER NOT NULL,
                validate_s REAL NOT NULL,
                validate_avg_ms REAL NOT NULL,
                validate_count INTEGER NOT NULL,
                classify_s REAL NOT NULL,
                classify_avg_ms REAL NOT NULL,
                classify_count INTEGER NOT NULL,
                build_s REAL NOT NULL,
                build_avg_ms REAL NOT NULL,
                build_count INTEGER NOT NULL,
                total_s REAL NOT NULL,
                recorded_at TEXT NOT NULL
            )
            """
        )
    except Exception:
        logger.warning("could not ensure import_metrics table exists")
