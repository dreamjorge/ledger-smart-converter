from abc import ABC, abstractmethod
from typing import Dict, Any, List

class RulesConfigReader(ABC):
    @abstractmethod
    def get_accounts(self) -> List[Dict[str, Any]]:
        """Retrieves the raw list of configured accounts."""
        pass

    @abstractmethod
    def get_categories(self) -> List[str]:
        """Retrieves the list of available categories from rules."""
        pass

    @abstractmethod
    def get_rules(self) -> List[Dict[str, Any]]:
        """Retrieves the set of categorization rules."""
        pass

    @abstractmethod
    def get_account_details(self, canonical_id: str) -> Dict[str, Any]:
        """
        Resolves bank_id and account_id from a canonical account ID.
        
        Args:
            canonical_id: The unique canonical identifier for the account.
            
        Returns:
            Dict with 'bank_id' and 'account_id'.
        """
        pass

    @abstractmethod
    def get_active_accounts(self) -> Dict[str, str]:
        """
        Returns a mapping of canonical IDs to display names.
        
        Returns:
            Dict where key is canonical_id and value is display_name (formatted).
        """
        pass

    @abstractmethod
    def get_rules_context(self) -> Dict[str, Any]:
        """
        Returns a dictionary containing the compiled categorization rules,
        merchant aliases, and fallback expense configuration.
        """
        pass
