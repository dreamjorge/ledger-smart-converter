from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import common_utils as cu

from account_mapping import resolve_canonical_account_id
from description_normalizer import normalize_description
from domain.transaction import CanonicalTransaction
from errors import ValidationError
from logging_config import get_logger
from validation import validate_tags, validate_transaction

LOGGER = get_logger("import_pipeline_service")

NormalizeDescriptionFn = Callable[[str, str], str]
CleanDescriptionFn = Callable[[str], str]
ClassifyFn = Callable[[str, Any, Any, str], Tuple[str, List[str], str]]
ValidateTransactionFn = Callable[[CanonicalTransaction], List[str]]
ValidateTagsFn = Callable[[List[str]], List[str]]
ResolveCanonicalAccountIdFn = Callable[[str, str], str]
GetStatementPeriodFn = Callable[[str, int], Optional[str]]


@dataclass
class ImportPipelineService:
    """Enrich raw importer rows into canonical Firefly-ready records."""

    bank_id: str
    account_name: str
    card_tag: str
    pay_asset: str
    closing_day: int
    currency: str
    fallback_expense: str
    compiled_rules: List[Dict[str, Any]]
    merchant_aliases: List[Any]
    use_normalized_text: bool = True
    normalize_description_fn: NormalizeDescriptionFn = normalize_description
    clean_description_fn: CleanDescriptionFn = cu.clean_description
    classify_fn: ClassifyFn = cu.classify
    validate_transaction_fn: ValidateTransactionFn = validate_transaction
    validate_tags_fn: ValidateTagsFn = validate_tags
    resolve_canonical_account_id_fn: ResolveCanonicalAccountIdFn = resolve_canonical_account_id
    get_statement_period_fn: GetStatementPeriodFn = cu.get_statement_period

    def process_transactions(
        self,
        txns: List[Any],
        strict: bool = False,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
        out_rows = []
        unknown_agg = defaultdict(lambda: {"count": 0, "total": 0.0, "examples": set()})
        warning_count = 0

        for txn in txns:
            raw_desc = (txn.description or "").strip()
            normalized_desc = self.normalize_description_fn(raw_desc, bank_id=self.bank_id)
            legacy_desc = self.clean_description_fn(raw_desc)
            text_for_matching = normalized_desc if (self.use_normalized_text and normalized_desc) else legacy_desc
            canonical = CanonicalTransaction(
                date=txn.date,
                description=legacy_desc,
                amount=float(txn.amount),
                bank_id=self.bank_id,
                account_id=self.account_name,
                canonical_account_id=self.resolve_canonical_account_id_fn(self.bank_id, self.account_name),
                raw_description=raw_desc,
                normalized_description=normalized_desc,
                source=txn.source,
                rfc=txn.rfc,
            )

            record_errors = self.validate_transaction_fn(canonical)
            if record_errors:
                warning_count += 1
                LOGGER.warning("skipping invalid transaction: %s", {"errors": record_errors, "txn": canonical.id})
                if strict:
                    raise ValidationError(f"Invalid transaction {canonical.id}: {record_errors}")
                continue

            expense, tags, merchant = self.classify_fn(
                text_for_matching,
                self.compiled_rules,
                self.merchant_aliases,
                self.fallback_expense,
            )
            tags = set(tags)
            tags.add(self._card_tag())
            period = self.get_statement_period_fn(txn.date, self.closing_day)
            if period:
                tags.add(f"period:{period}")
            if txn.rfc:
                tags.add(f"rfc:{txn.rfc}")
            tags.add(f"txn:{canonical.id[:10]}")

            tag_errors = self.validate_tags_fn(list(tags))
            if tag_errors:
                warning_count += 1
                LOGGER.warning("tag validation warning: %s", {"errors": tag_errors, "txn": canonical.id})
                if strict:
                    raise ValidationError(f"Invalid tags {canonical.id}: {tag_errors}")

            category = expense.split(":")[1] if ":" in expense else ""

            if self.bank_id == "hsbc":
                from import_hsbc_cfdi_firefly import infer_kind

                kind = infer_kind(text_for_matching, txn.amount, txn.rfc)
                if kind == "charge":
                    row = self._make_withdrawal(txn, legacy_desc, expense, category, tags)
                elif kind == "payment":
                    row = self._make_transfer(txn, legacy_desc, self.pay_asset, self.account_name, tags, "pago")
                else:
                    source = "Income:Cashback" if kind == "cashback" else "Income:Other"
                    row = self._make_transfer(txn, legacy_desc, source, self.account_name, tags, kind)
            else:
                if txn.amount < 0:
                    row = self._make_withdrawal(txn, legacy_desc, expense, category, tags)
                else:
                    row = self._make_transfer(txn, legacy_desc, self.pay_asset, self.account_name, tags, "pago")

            if row:
                out_rows.append(row)
                if row["type"] == "withdrawal" and expense == self.fallback_expense:
                    bucket = unknown_agg[merchant]
                    bucket["count"] += 1
                    bucket["total"] += abs(txn.amount)
                    if len(bucket["examples"]) < 5:
                        bucket["examples"].add(normalized_desc or legacy_desc)

        return out_rows, self._format_unknown(unknown_agg), warning_count

    def _card_tag(self) -> str:
        return self.card_tag

    def _make_withdrawal(
        self,
        txn: Any,
        desc: str,
        expense: str,
        category: str,
        tags,
    ) -> Dict[str, Any]:
        return {
            "type": "withdrawal",
            "date": txn.date,
            "amount": f"{abs(txn.amount):.2f}",
            "currency_code": self.currency,
            "description": desc,
            "source_name": self.account_name,
            "destination_name": expense,
            "category_name": category,
            "tags": ",".join(sorted(tags)),
        }

    def _make_transfer(
        self,
        txn: Any,
        desc: str,
        source: str,
        dest: str,
        tags,
        extra_tag: str,
    ) -> Dict[str, Any]:
        transfer_tags = set(tags)
        transfer_tags.add(extra_tag)
        return {
            "type": "transfer",
            "date": txn.date,
            "amount": f"{abs(txn.amount):.2f}",
            "currency_code": self.currency,
            "description": desc,
            "source_name": source,
            "destination_name": dest,
            "category_name": "",
            "tags": ",".join(sorted(transfer_tags)),
        }

    def _format_unknown(self, agg: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for merchant, data in agg.items():
            out.append(
                {
                    "merchant": merchant,
                    "count": data["count"],
                    "total": f"{data['total']:.2f}",
                    "examples": " | ".join(sorted(data["examples"])),
                }
            )
        return sorted(out, key=lambda item: -float(item["total"]))
