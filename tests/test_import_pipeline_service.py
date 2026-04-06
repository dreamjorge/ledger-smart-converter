import pytest
from unittest.mock import MagicMock
from services.import_pipeline_service import ImportPipelineService
from infrastructure.parsers.models import TxnRaw
from domain.config_models import AppConfiguration, AppDefaults, BankConfig, RuleAction, CategorizationRule
from ml_categorizer import TransactionCategorizer

# These tests depend on ImportPipelineService.ml_categorizer introduced in
# feat/streamlit-global-controls-pr. Remove the skip markers after that branch merges to main.
pytestmark = pytest.mark.skip(reason="depends on feat/streamlit-global-controls-pr — remove after merge")

@pytest.fixture
def app_config():
    return AppConfiguration(
        banks={},
        defaults=AppDefaults(
            fallback_expense="Expenses:Other:Uncategorized",
            currency="MXN",
            accounts={},
            payment_assets={}
        ),
        rules=[],
        merchant_aliases=[],
        canonical_accounts={}
    )

@pytest.fixture
def bank_config():
    return BankConfig(
        bank_id="test_bank",
        name="Test Bank",
        display_name="Test Bank",
        type="xlsx",
        card_tag="test_card"
    )

@pytest.fixture
def mock_ml():
    mock = MagicMock(spec=TransactionCategorizer)
    mock.is_trained = True
    return mock

@pytest.fixture
def service(app_config, bank_config, mock_ml):
    return ImportPipelineService(
        app_config=app_config,
        bank_config=bank_config,
        account_name="Test Account",
        pay_asset="Assets:Cash",
        closing_day=15,
        ml_categorizer=mock_ml,
        ml_confidence_threshold=0.5,
        # Stub helpers to focus on classification
        normalize_description_fn=lambda *a, **k: a[0] if a else "",
        clean_description_fn=lambda *a, **k: a[0] if a else "",
        validate_transaction_fn=lambda *a, **k: [],
        validate_tags_fn=lambda *a, **k: [],
        resolve_canonical_account_id_fn=lambda *a, **k: "acc",
        get_statement_period_fn=lambda *a, **k: "2026-01"
    )

def test_ml_fallback_high_confidence(service, mock_ml):
    """If rules fail and ML has high confidence, use ML."""
    txn = TxnRaw(date="2026-01-10", description="Supermarket", amount=-100.0)
    
    # Mock rules to return fallback
    service.classify_fn = MagicMock(return_value=("Expenses:Other:Uncategorized", [], "supermarket"))
    
    # Mock ML to return high confidence
    mock_ml.predict.return_value = [("Expenses:Food:Groceries", 0.8)]
    
    processed, _, _ = service.process_transactions([txn])
    
    assert len(processed) == 1
    assert processed[0].destination_name == "Expenses:Food:Groceries"
    assert "ml:predicted" in processed[0].tags.split(",")
    mock_ml.predict.assert_called_once_with("Supermarket")

def test_ml_fallback_low_confidence(service, mock_ml):
    """If rules fail but ML has low confidence, stay uncategorized."""
    txn = TxnRaw(date="2026-01-10", description="Obscure Store", amount=-10.0)
    
    service.classify_fn = MagicMock(return_value=("Expenses:Other:Uncategorized", [], "obscure"))
    
    # Mock ML to return low confidence (below 0.5 threshold)
    mock_ml.predict.return_value = [("Expenses:Leisure", 0.3)]
    
    processed, _, _ = service.process_transactions([txn])
    
    assert len(processed) == 1
    assert processed[0].destination_name == "Expenses:Other:Uncategorized"
    assert "ml:predicted" not in processed[0].tags.split(",")

def test_ml_skipped_on_rule_match(service, mock_ml):
    """If rules match, ML should NOT be called."""
    txn = TxnRaw(date="2026-01-10", description="Known Rule", amount=-50.0)
    
    # Mock rules to return specific match
    service.classify_fn = MagicMock(return_value=("Expenses:Household", ["rule_tag"], "known"))
    
    processed, _, _ = service.process_transactions([txn])
    
    assert len(processed) == 1
    assert processed[0].destination_name == "Expenses:Household"
    assert "ml:predicted" not in processed[0].tags.split(",")
    mock_ml.predict.assert_not_called()

def test_no_ml_categorizer(service):
    """If no ML categorizer provided, legacy behavior applies."""
    service.ml_categorizer = None
    txn = TxnRaw(date="2026-01-10", description="Anything", amount=-10.0)
    service.classify_fn = MagicMock(return_value=("Expenses:Other:Uncategorized", [], "any"))
    
    processed, _, _ = service.process_transactions([txn])
    
    assert len(processed) == 1
    assert processed[0].destination_name == "Expenses:Other:Uncategorized"

def test_ml_not_trained(service, mock_ml):
    """If ML categorizer is provided but not trained, legacy behavior applies."""
    mock_ml.is_trained = False
    txn = TxnRaw(date="2026-01-10", description="Anything", amount=-10.0)
    service.classify_fn = MagicMock(return_value=("Expenses:Other:Uncategorized", [], "any"))
    
    processed, _, _ = service.process_transactions([txn])
    
    assert len(processed) == 1
    assert processed[0].destination_name == "Expenses:Other:Uncategorized"
    mock_ml.predict.assert_not_called()
