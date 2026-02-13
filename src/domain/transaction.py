from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class CanonicalTransaction:
    date: str
    description: str
    amount: float
    bank_id: str
    account_id: str
    canonical_account_id: str
    raw_description: str = ""
    normalized_description: str = ""
    source: str = "data"
    rfc: str = ""

    @property
    def id(self) -> str:
        text_for_id = (self.normalized_description or self.description or "").strip().lower()
        raw = (
            f"{self.bank_id}|{self.account_id}|{self.canonical_account_id}|"
            f"{self.date}|{self.amount:.2f}|{text_for_id}|{self.rfc.strip().lower()}"
        )
        return sha256(raw.encode("utf-8")).hexdigest()
