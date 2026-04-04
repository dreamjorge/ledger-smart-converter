import yaml # type: ignore
from typing import Dict, Any, List, Optional
from pathlib import Path
from application.ports.rules_config_reader import RulesConfigReader

class YamlRulesRepository(RulesConfigReader):
    def __init__(self, rules_path: Path, accounts_path: Path):
        self.rules_path = rules_path
        self.accounts_path = accounts_path

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def get_accounts(self) -> List[Dict[str, Any]]:
        """Extracts the raw list of configured accounts from rules.yml."""
        config = self._load_yaml(self.rules_path)
        return config.get('accounts', [])

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

    def get_rules(self) -> List[Dict[str, Any]]:
        """Extracts categorization rules from rules.yml."""
        config = self._load_yaml(self.rules_path)
        return config.get('rules', [])

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

    def get_rules_context(self) -> Dict[str, Any]:
        """
        Returns compiled rules and aliases for transaction categorization.
        """
        from common_utils import compile_rules
        config = self._load_yaml(self.rules_path)
        
        return {
            "compiled_rules": compile_rules(config),
            "merchant_aliases": config.get("merchant_aliases", []),
            "fallback_expense": config.get("defaults", {}).get("fallback_expense", "Expenses:Other:Uncategorized")
        }
