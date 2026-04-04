from typing import Dict, List, Any
from application.ports.rules_config_reader import RulesConfigReader

class GetManualEntryContext:
    """
    Use case to retrieve the initial context required for manual transaction entry.
    This includes available categories and active account mappings.
    """
    def __init__(self, config_reader: RulesConfigReader):
        self.config_reader = config_reader

    def execute(self) -> Dict[str, Any]:
        """
        Executes the use case to aggregate configuration data.
        
        Returns:
            Dict containing:
                - 'categories': List[str]
                - 'accounts': Dict[str, str] (canonical_id -> display_name)
        """
        return {
            "categories": self.config_reader.get_categories(),
            "accounts": self.config_reader.get_active_accounts()
        }
