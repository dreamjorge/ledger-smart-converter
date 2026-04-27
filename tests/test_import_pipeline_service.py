import pytest
from unittest.mock import MagicMock
from services.import_pipeline_service import ImportPipelineService
from services.metrics_service import MetricsCollector, StageTiming
from infrastructure.parsers.models import TxnRaw
from domain.config_models import AppConfiguration, AppDefaults, BankConfig, RuleAction, CategorizationRule
from ml_categorizer import TransactionCategorizer


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

def test_ml_skipped_on_positive_amount(service, mock_ml):
    """ML MUST NOT run on deposits/payments (positive amount) — expense is ignored for transfers."""
    txn = TxnRaw(date="2026-01-10", description="Pago Tarjeta", amount=500.0)
    service.classify_fn = MagicMock(return_value=("Expenses:Other:Uncategorized", [], "pago"))
    mock_ml.predict.return_value = [("Expenses:Food:Groceries", 0.9)]

    processed, _, _ = service.process_transactions([txn])

    mock_ml.predict.assert_not_called()
    assert len(processed) == 1
    assert "ml:predicted" not in (processed[0].tags or "").split(",")


def test_metrics_collector_records_stage_timing(app_config, bank_config, mock_ml):
    """MetricsCollector should record normalize/validate/classify/build timing per transaction."""
    metrics = MetricsCollector(bank_id="test_bank", account_name="Test Account")
    service = ImportPipelineService(
        app_config=app_config,
        bank_config=bank_config,
        account_name="Test Account",
        pay_asset="Assets:Cash",
        closing_day=15,
        ml_categorizer=mock_ml,
        metrics_collector=metrics,
        normalize_description_fn=lambda *a, **k: "normalized",
        clean_description_fn=lambda *a, **k: "cleaned",
        validate_transaction_fn=lambda *a, **k: [],
        validate_tags_fn=lambda *a, **k: [],
        resolve_canonical_account_id_fn=lambda *a, **k: "acc",
        get_statement_period_fn=lambda *a, **k: "2026-01",
    )
    txns = [
        TxnRaw(date="2026-01-10", description="Test", amount=-50.0),
        TxnRaw(date="2026-01-11", description="Test2", amount=-25.0),
    ]
    service.classify_fn = MagicMock(return_value=("Expenses:Food", [], "test"))

    service.process_transactions(txns)

    assert metrics.processed == 2
    assert metrics.categorized == 2
    assert metrics.failed == 0
    assert metrics.stage_normalize.count == 2
    assert metrics.stage_validate.count == 2
    assert metrics.stage_classify.count == 2
    assert metrics.stage_build.count == 2


def test_metrics_collector_records_failed_transactions(app_config, bank_config, mock_ml):
    """Failed/filtered transactions should increment failed counter but not processed."""
    metrics = MetricsCollector(bank_id="test_bank", account_name="Test Account")
    service = ImportPipelineService(
        app_config=app_config,
        bank_config=bank_config,
        account_name="Test Account",
        pay_asset="Assets:Cash",
        closing_day=15,
        ml_categorizer=mock_ml,
        metrics_collector=metrics,
        normalize_description_fn=lambda *a, **k: "norm",
        clean_description_fn=lambda *a, **k: "clean",
        validate_transaction_fn=lambda *a, **k: ["error"],  # Always invalid
        validate_tags_fn=lambda *a, **k: [],
        resolve_canonical_account_id_fn=lambda *a, **k: "acc",
        get_statement_period_fn=lambda *a, **k: "2026-01",
    )
    txns = [
        TxnRaw(date="2026-01-10", description="Bad", amount=-50.0),
        TxnRaw(date="2026-01-11", description="Bad2", amount=-25.0),
    ]
    service.classify_fn = MagicMock(return_value=("Expenses:Food", [], "test"))

    service.process_transactions(txns)

    assert metrics.processed == 0
    assert metrics.failed == 2


def test_metrics_collector_records_ml_predictions(app_config, bank_config, mock_ml):
    """ML predictions should increment ml_predicted counter."""
    metrics = MetricsCollector(bank_id="test_bank", account_name="Test Account")
    service = ImportPipelineService(
        app_config=app_config,
        bank_config=bank_config,
        account_name="Test Account",
        pay_asset="Assets:Cash",
        closing_day=15,
        ml_categorizer=mock_ml,
        metrics_collector=metrics,
        normalize_description_fn=lambda *a, **k: "norm",
        clean_description_fn=lambda *a, **k: "clean",
        validate_transaction_fn=lambda *a, **k: [],
        validate_tags_fn=lambda *a, **k: [],
        resolve_canonical_account_id_fn=lambda *a, **k: "acc",
        get_statement_period_fn=lambda *a, **k: "2026-01",
    )
    txns = [
        TxnRaw(date="2026-01-10", description="Unknown", amount=-50.0),
    ]
    service.classify_fn = MagicMock(return_value=("Expenses:Other:Uncategorized", [], "unk"))
    mock_ml.predict.return_value = [("Expenses:Food:Groceries", 0.8)]

    service.process_transactions(txns)

    assert metrics.ml_predicted == 1


def test_metrics_collector_as_dict(app_config, bank_config, mock_ml):
    """MetricsCollector.as_dict() should return structured metrics."""
    metrics = MetricsCollector(bank_id="test_bank", account_name="Test Account")
    metrics.record_processed()
    metrics.record_processed()
    metrics.record_categorized()
    metrics.record_categorized()
    metrics.record_normalize(0.1)
    metrics.record_normalize(0.2)
    metrics.record_classify(0.05)

    result = metrics.as_dict()

    assert result["bank_id"] == "test_bank"
    assert result["account_name"] == "Test Account"
    assert result["processed"] == 2
    assert result["categorized"] == 2
    assert result["timing"]["normalize_s"] == pytest.approx(0.3)
    assert result["timing"]["normalize_avg_ms"] == pytest.approx(150.0)
    assert result["timing"]["normalize_count"] == 2


def test_stage_timing_avg_ms():
    """StageTiming.avg_ms() should compute milliseconds per call correctly."""
    st = StageTiming()
    st.add(0.1)
    st.add(0.2)
    assert st.avg_ms() == pytest.approx(150.0)
