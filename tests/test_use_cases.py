import unittest
from unittest.mock import MagicMock
from domain.transaction import CanonicalTransaction
from application.use_cases.submit_manual_transaction import SubmitManualTransaction
from application.use_cases.get_manual_entry_context import GetManualEntryContext
from application.use_cases.calculate_analytics import CalculateAnalytics, AnalyticsResult
from application.use_cases.get_filtered_transactions import GetFilteredTransactions
from application.use_cases.import_statement import ImportStatement, ImportResult
from application.ports.transaction_repository import TransactionRepository
from application.ports.rules_config_reader import RulesConfigReader
from application.ports.statement_data_extractor import StatementDataExtractor, RawTransaction
from application.ports.import_repository import ImportRepository

class TestSubmitManualTransaction(unittest.TestCase):
    def setUp(self):
        self.repository = MagicMock(spec=TransactionRepository)
        self.use_case = SubmitManualTransaction(self.repository)

    def test_execute_success(self):
        # Arrange
        txn = CanonicalTransaction(
            date="2023-01-01",
            description="Test Transaction",
            amount=100.0,
            bank_id="test_bank",
            account_id="test_account",
            canonical_account_id="ca:test"
        )
        self.repository.exists.return_value = False
        self.repository.save.return_value = True

        # Act
        result = self.use_case.execute(txn)

        # Assert
        self.assertTrue(result)
        self.repository.exists.assert_called_once_with(txn.id)
        self.repository.save.assert_called_once_with(txn)

    def test_execute_duplicate(self):
        # Arrange
        txn = CanonicalTransaction(
            date="2023-01-01",
            description="Test Transaction",
            amount=100.0,
            bank_id="test_bank",
            account_id="test_account",
            canonical_account_id="ca:test"
        )
        self.repository.exists.return_value = True

        # Act
        result = self.use_case.execute(txn)

        # Assert
        self.assertFalse(result)
        self.repository.exists.assert_called_once_with(txn.id)
        self.repository.save.assert_not_called()


class TestGetManualEntryContext(unittest.TestCase):
    def setUp(self):
        self.config_reader = MagicMock(spec=RulesConfigReader)
        self.use_case = GetManualEntryContext(self.config_reader)

    def test_execute(self):
        # Arrange
        mock_categories = ["Food", "Transport"]
        mock_accounts = {"cc:visa": "Visa (Bank A)"}
        self.config_reader.get_categories.return_value = mock_categories
        self.config_reader.get_active_accounts.return_value = mock_accounts

        # Act
        result = self.use_case.execute()

        # Assert
        self.assertEqual(result["categories"], mock_categories)
        self.assertEqual(result["accounts"], mock_accounts)
        self.config_reader.get_categories.assert_called_once()
        self.config_reader.get_active_accounts.assert_called_once()


class TestCalculateAnalytics(unittest.TestCase):
    def setUp(self):
        self.repository = MagicMock(spec=TransactionRepository)
        self.use_case = CalculateAnalytics(self.repository)

    def test_execute_empty(self):
        self.repository.find_by_criteria.return_value = []
        result = self.use_case.execute()
        self.assertEqual(result.total, 0)
        self.assertEqual(result.total_spent, 0.0)

    def test_execute_with_data(self):
        # Arrange
        t1 = CanonicalTransaction(
            date="2024-01-01", description="Food", amount=50.0,
            bank_id="b1", account_id="a1", canonical_account_id="ca1",
            transaction_type="withdrawal",
            destination_name="Expenses:Food"
        )
        t2 = CanonicalTransaction(
            date="2024-01-02", description="Salary", amount=1000.0,
            bank_id="b1", account_id="a1", canonical_account_id="ca1",
            transaction_type="deposit",
            destination_name="Income:Salary"
        )
        self.repository.find_by_criteria.return_value = [t1, t2]

        # Act
        result = self.use_case.execute()

        # Assert
        self.assertEqual(result.total, 2)
        self.assertEqual(result.categorized, 2)
        self.assertEqual(result.total_spent, 50.0)
        self.assertEqual(result.categories["Food"], 1)
        self.assertIn("2024-01", result.monthly_spending_trends)
        self.assertEqual(result.monthly_spending_trends["2024-01"]["Food"], 50.0)

class TestImportStatement(unittest.TestCase):
    def setUp(self):
        self.config_reader = MagicMock(spec=RulesConfigReader)
        self.data_extractor = MagicMock(spec=StatementDataExtractor)
        self.transaction_repository = MagicMock(spec=TransactionRepository)
        self.import_repository = MagicMock(spec=ImportRepository)
        
        self.use_case = ImportStatement(
            self.config_reader,
            self.data_extractor,
            self.transaction_repository,
            self.import_repository
        )

    def test_execute_success(self):
        # Arrange
        bank_id = "test_bank"
        from domain.config_models import AppConfiguration, AppDefaults, BankConfig
        self.config_reader.get_app_config.return_value = AppConfiguration(
            defaults=AppDefaults(fallback_expense="Expenses:Unknown", currency="USD", accounts={}, payment_assets={}),
            banks={"test_bank": BankConfig("test_bank", "Test Bank", "Test Bank", "xlsx", "card", "test", "test", "test", "test")},
            rules=[],
            merchant_aliases=[],
            canonical_accounts={}
        )
        
        raw_txns = [
            RawTransaction(date="2024-01-01", description="Coffee", amount=-5.0, source="test.xml")
        ]
        self.data_extractor.extract.return_value = raw_txns
        self.import_repository.record_import.return_value = 123
        self.transaction_repository.save_all.return_value = {"inserted": 1, "skipped_duplicates": 0}

        # Act
        result = self.use_case.execute(bank_id, data_path=MagicMock())

        # Assert
        self.assertIsInstance(result, ImportResult)
        self.assertEqual(result.import_id, 123)
        self.assertEqual(result.inserted, 1)
        self.import_repository.record_import.assert_called_once()
        self.import_repository.update_status.assert_called_once_with(
            import_id=123, status="completed", row_count=1
        )
        self.transaction_repository.save_all.assert_called_once()

    def test_execute_failure(self):
        # Arrange
        self.config_reader.get_app_config.side_effect = Exception("Processing error")
        self.data_extractor.extract.return_value = []
        self.import_repository.record_import.return_value = 456

        # Act & Assert
        with self.assertRaises(Exception):
            self.use_case.execute("test_bank")
        
        self.import_repository.update_status.assert_called_once_with(
            import_id=456, status="failed", error="Processing error"
        )

if __name__ == '__main__':
    unittest.main()
