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


from domain.config_models import AppConfiguration, BankConfig

@dataclass
class ImportPipelineService:
    """Enrich raw importer rows into canonical Firefly-ready records."""

    app_config: AppConfiguration
    bank_config: BankConfig
    account_name: str
    pay_asset: str
    closing_day: int
    
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
    ) -> Tuple[List[CanonicalTransaction], List[Dict[str, Any]], int]:
        out_txns = []
        unknown_agg = defaultdict(lambda: {"count": 0, "total": 0.0, "examples": set()})
        warning_count = 0

        for txn in txns:
            raw_desc = (txn.description or "").strip()
            normalized_desc = self.normalize_description_fn(raw_desc, bank_id=self.bank_config.bank_id)
            legacy_desc = self.clean_description_fn(raw_desc)
            text_for_matching = normalized_desc if (self.use_normalized_text and normalized_desc) else legacy_desc
            
            # Initial canonical object with core fields
            canonical = CanonicalTransaction(
                date=txn.date,
                description=legacy_desc,
                amount=float(txn.amount),
                bank_id=self.bank_config.bank_id,
                account_id=self.account_name,
                canonical_account_id=self.resolve_canonical_account_id_fn(self.bank_config.bank_id, self.account_name),
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
                self.app_config.rules,
                self.app_config.merchant_aliases,
                self.app_config.defaults.fallback_expense,
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
            tag_str = ",".join(sorted(tags))

            if self.bank_config.bank_id == "hsbc":
                from import_hsbc_cfdi_firefly import infer_kind
                kind = infer_kind(text_for_matching, txn.amount, txn.rfc)
                
                if kind == "charge":
                    final_txn = self._make_withdrawal(canonical, expense, category, tag_str)
                elif kind == "payment":
                    final_txn = self._make_transfer(canonical, self.pay_asset, self.account_name, tag_str, "pago")
                else:
                    source_name = "Income:Cashback" if kind == "cashback" else "Income:Other"
                    final_txn = self._make_transfer(canonical, source_name, self.account_name, tag_str, kind)
            else:
                if txn.amount < 0:
                    final_txn = self._make_withdrawal(canonical, expense, category, tag_str)
                else:
                    final_txn = self._make_transfer(canonical, self.pay_asset, self.account_name, tag_str, "pago")

            if final_txn:
                out_txns.append(final_txn)
                if final_txn.transaction_type == "withdrawal" and expense == self.app_config.defaults.fallback_expense:
                    bucket = unknown_agg[merchant]
                    bucket["count"] += 1
                    bucket["total"] += abs(txn.amount)
                    if len(bucket["examples"]) < 5:
                        bucket["examples"].add(normalized_desc or legacy_desc)

        return out_txns, self._format_unknown(unknown_agg), warning_count

    def _card_tag(self) -> str:
        return self.bank_config.card_tag

    def _make_withdrawal(
        self,
        base: CanonicalTransaction,
        destination: str,
        category: str,
        tags: str,
    ) -> CanonicalTransaction:
        from dataclasses import replace
        return replace(
            base,
            transaction_type="withdrawal",
            amount=abs(base.amount),
            destination_name=destination,
            category=category,
            tags=tags
        )

    def _make_transfer(
        self,
        base: CanonicalTransaction,
        source: str,
        dest: str,
        tags: str,
        extra_tag: str,
    ) -> CanonicalTransaction:
        from dataclasses import replace
        transfer_tags = sorted(list(set(tags.split(",") + [extra_tag])))
        return replace(
            base,
            transaction_type="transfer",
            amount=abs(base.amount),
            account_id=source, # Source for transfers
            destination_name=dest,
            category="",
            tags=",".join(transfer_tags)
        )

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
