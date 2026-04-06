from dataclasses import dataclass
from hashlib import sha256
from typing import Optional


@dataclass(frozen=True)
class CanonicalTransaction:
    date: str
    description: str
    amount: Optional[float]
    bank_id: str
    account_id: str
    canonical_account_id: str
    transaction_type: str = "withdrawal"
    category: Optional[str] = None
    destination_name: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    raw_description: str = ""
    normalized_description: str = ""
    source: str = "data"
    rfc: str = ""
    is_synced: bool = False

    @property
    def id(self) -> str:
        from pathlib import Path
        source_name = Path(self.source).name if self.source else ""
        amount_str = f"{self.amount:.2f}" if self.amount is not None else ""
        description_key = (self.description or "").strip().lower()
        raw = (
            f"{self.bank_id}|{self.canonical_account_id or ''}|{source_name}|"
            f"{self.date}|{amount_str}|{description_key}"
        )
        return sha256(raw.encode("utf-8")).hexdigest()
