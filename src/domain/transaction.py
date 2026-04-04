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
        text_for_id = (self.normalized_description or self.description or "").strip().lower()
        amount_str = f"{self.amount:.2f}" if self.amount is not None else ""
        raw = (
            f"{self.bank_id}|{self.account_id}|{self.canonical_account_id}|"
            f"{self.date}|{amount_str}|{text_for_id}|{self.rfc.strip().lower()}"
        )
        return sha256(raw.encode("utf-8")).hexdigest()
