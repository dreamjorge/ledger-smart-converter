import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from re import Pattern

@dataclass(frozen=True)
class RuleAction:
    expense: str
    tags: List[str] = field(default_factory=list)

@dataclass(frozen=True)
class CategorizationRule:
    name: str
    any_regex: List[str]
    set: RuleAction
    compiled_regexes: List[Pattern] = field(init=False, default_factory=list)
    
    def __post_init__(self):
        object.__setattr__(self, 'compiled_regexes', [re.compile(rx, re.IGNORECASE) for rx in self.any_regex])

@dataclass(frozen=True)
class MerchantAlias:
    canon: str
    any_regex: List[str]
    compiled_regexes: List[Pattern] = field(init=False, default_factory=list)
    
    def __post_init__(self):
        object.__setattr__(self, 'compiled_regexes', [re.compile(rx, re.IGNORECASE) for rx in self.any_regex])

@dataclass(frozen=True)
class BankConfig:
    bank_id: str
    name: str
    display_name: str
    type: str # 'xlsx', 'xml', etc.
    card_tag: str
    account_key: Optional[str] = None
    payment_asset_key: Optional[str] = None
    fallback_name: Optional[str] = None
    fallback_asset: Optional[str] = None
    
    def __post_init__(self):
        if not self.type:
            raise ValueError(f"BankConfig {self.bank_id} missing type")

@dataclass(frozen=True)
class AccountDefault:
    name: str
    closing_day: int
    
    def __post_init__(self):
        if not 1 <= self.closing_day <= 31:
            raise ValueError(f"closing_day must be between 1 and 31. Got {self.closing_day} for {self.name}")

@dataclass(frozen=True)
class AppDefaults:
    currency: str
    fallback_expense: str
    accounts: Dict[str, AccountDefault]
    payment_assets: Dict[str, str]

@dataclass(frozen=True)
class CanonicalAccount:
    canonical_id: str
    display_name: str
    bank_ids: List[str]
    account_ids: List[str]

@dataclass(frozen=True)
class AppConfiguration:
    banks: Dict[str, BankConfig]
    defaults: AppDefaults
    merchant_aliases: List[MerchantAlias]
    rules: List[CategorizationRule]
    canonical_accounts: Dict[str, CanonicalAccount]
