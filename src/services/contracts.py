from typing import List, Literal, Optional, Tuple, TypedDict

ManualEntryResult = Tuple[bool, List[str]]
DedupDecision = Literal["skip", "overwrite", "keep_both"]


class TransactionInsertRow(TypedDict, total=False):
    source_hash: str
    date: str
    amount: float
    currency: str
    merchant: Optional[str]
    description: str
    raw_description: Optional[str]
    normalized_description: Optional[str]
    account_id: str
    canonical_account_id: str
    bank_id: str
    statement_period: Optional[str]
    category: Optional[str]
    tags: Optional[str]
    transaction_type: str
    source_name: Optional[str]
    destination_name: Optional[str]
    source_file: str
    user_id: Optional[str]
