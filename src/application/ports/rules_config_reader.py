from abc import ABC, abstractmethod
from typing import Dict, Any, List
from domain.config_models import AppConfiguration, CanonicalAccount, CategorizationRule

class RulesConfigReader(ABC):
    @abstractmethod
    def get_app_config(self) -> AppConfiguration:
        """Retrieves strongly typed global application configuration."""
        pass

    @abstractmethod
    def get_categories(self) -> List[str]:
        """Retrieves the list of available categories from rules."""
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
    def get_account_details(self, canonical_id: str) -> Dict[str, Any]:
        """
        Resolves bank_id and account_id from a canonical account ID.
        """
        pass
