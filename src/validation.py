import re
from typing import List

from domain.transaction import CanonicalTransaction


ISO_DATE_RX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TAG_RX = re.compile(r"^[a-zA-Z0-9:_\-\.\*]+$")


def validate_transaction(txn: CanonicalTransaction) -> List[str]:
    errors: List[str] = []
    if not ISO_DATE_RX.match(txn.date):
        errors.append("invalid_date")
    if not txn.description or not txn.description.strip():
        errors.append("missing_description")
    if txn.amount is None:
        errors.append("missing_amount")
    if not txn.bank_id:
        errors.append("missing_bank_id")
    if not txn.account_id:
        errors.append("missing_account_id")
    return errors


def validate_tags(tags: List[str]) -> List[str]:
    errors: List[str] = []
    for tag in tags:
        if not TAG_RX.match(tag):
            errors.append(f"invalid_tag:{tag}")
    return errors
