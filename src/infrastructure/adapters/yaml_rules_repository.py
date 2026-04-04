import yaml # type: ignore
from typing import Dict, Any, List, Optional
from pathlib import Path
from application.ports.rules_config_reader import RulesConfigReader
from domain.config_models import AppConfiguration

class YamlRulesRepository(RulesConfigReader):
    def __init__(self, rules_path: Path, accounts_path: Optional[Path] = None):
        self.rules_path = rules_path
        self.accounts_path = accounts_path or Path("config/accounts.yml")

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def get_app_config(self) -> AppConfiguration:
        from domain.config_models import (
            AppConfiguration, BankConfig, AppDefaults, AccountDefault,
            CategorizationRule, RuleAction, MerchantAlias, CanonicalAccount
        )
        
        rules_cfg = self._load_yaml(self.rules_path)
        acc_cfg = self._load_yaml(self.accounts_path)
        
        # 1. Parse Banks
        banks = {}
        for bid, b_data in rules_cfg.get("banks", {}).items():
            banks[bid] = BankConfig(
                bank_id=bid,
                name=b_data.get("name", bid),
                display_name=b_data.get("display_name", bid),
                type=b_data.get("type", "generic"),
                card_tag=b_data.get("card_tag", ""),
                account_key=b_data.get("account_key"),
                payment_asset_key=b_data.get("payment_asset_key"),
                fallback_name=b_data.get("fallback_name"),
                fallback_asset=b_data.get("fallback_asset")
            )
            
        # 2. Parse Defaults
        raw_defs = rules_cfg.get("defaults", {})
        accounts_defs = {}
        for acc_k, acc_v in raw_defs.get("accounts", {}).items():
            if isinstance(acc_v, dict):
                accounts_defs[acc_k] = AccountDefault(
                    name=acc_v.get("name", acc_k),
                    closing_day=int(acc_v.get("closing_day", 1))
                )
        
        defaults = AppDefaults(
            currency=raw_defs.get("currency", "MXN"),
            fallback_expense=raw_defs.get("fallback_expense", "Expenses:Other:Uncategorized"),
            accounts=accounts_defs,
            payment_assets={k: v for k, v in raw_defs.get("accounts", {}).items() if not isinstance(v, dict)}
        )
        
        # 3. Parse Merchant Aliases
        merchant_aliases = [
            MerchantAlias(canon=ma.get("canon", ""), any_regex=ma.get("any_regex", []))
            for ma in rules_cfg.get("merchant_aliases", [])
        ]
        
        # 4. Parse Rules
        rules = [
            CategorizationRule(
                name=r.get("name", ""),
                any_regex=r.get("any_regex", []),
                set=RuleAction(
                    expense=r.get("set", {}).get("expense", defaults.fallback_expense),
                    tags=r.get("set", {}).get("tags", [])
                )
            )
            for r in rules_cfg.get("rules", [])
        ]
        
        # 5. Parse Canonical Accounts
        canonical_accounts = {}
        for cid, c_data in acc_cfg.get("canonical_accounts", {}).items():
            canonical_accounts[cid] = CanonicalAccount(
                canonical_id=cid,
                display_name=c_data.get("display_name", cid),
                bank_ids=c_data.get("bank_ids", []),
                account_ids=c_data.get("account_ids", [])
            )
            
        return AppConfiguration(
            banks=banks,
            defaults=defaults,
            merchant_aliases=merchant_aliases,
            rules=rules,
            canonical_accounts=canonical_accounts
        )

    def get_categories(self) -> List[str]:
        """Extracts sorted categories from rules.yml, including fallback."""
        config = self._load_yaml(self.rules_path)
        expenses = set()
        
        fallback = config.get("defaults", {}).get("fallback_expense")
        if fallback:
            expenses.add(fallback)

        for rule in config.get("rules", []):
            expense = (rule.get("set") or {}).get("expense")
            if expense:
                expenses.add(expense)

        return sorted(expenses)

    def get_active_accounts(self) -> Dict[str, str]:
        """
        Returns mapping of canonical IDs to formatted display names.
        Logic consolidated from load_accounts_from_config.
        """
        acc_cfg = self._load_yaml(self.accounts_path)
        rules_cfg = self._load_yaml(self.rules_path)
        
        canonical_accounts = acc_cfg.get("canonical_accounts", {})
        bank_names = {
            bid: bcfg.get("display_name", bid) 
            for bid, bcfg in rules_cfg.get("banks", {}).items()
        }
        
        result = {}
        for cid, entry in canonical_accounts.items():
            account_ids = entry.get("account_ids", [])
            bank_ids = entry.get("bank_ids", [])
            
            display_name = account_ids[0] if account_ids else cid
            
            if bank_ids:
                bank_id = bank_ids[0]
                bank_display = bank_names.get(bank_id, bank_id)
                display_name = f"{display_name} ({bank_display})"
            
            result[cid] = display_name
            
        return result

    def get_account_details(self, canonical_id: str) -> Dict[str, Any]:
        """Resolves bank_id and account_id from accounts.yml."""
        acc_cfg = self._load_yaml(self.accounts_path)
        canonical_accounts = acc_cfg.get("canonical_accounts", {})
        
        entry = canonical_accounts.get(canonical_id, {})
        bank_ids = entry.get("bank_ids", [])
        account_ids = entry.get("account_ids", [])
        
        return {
            "bank_id": bank_ids[0] if bank_ids else canonical_id,
            "account_id": account_ids[0] if account_ids else canonical_id,
            "display_name": entry.get("account_ids", [canonical_id])[0]
        }
