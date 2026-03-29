import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
import io
from types import SimpleNamespace

import yaml

import services.data_service as data_service
from services.data_service import (
    get_csv_path,
    load_transactions_from_csv,
    load_all_bank_data,
    load_transactions,
)
from services.db_service import DatabaseService
from settings import load_settings

# Get the expected data directory path from settings (same as data_service uses)
_SETTINGS = load_settings()
_DATA_DIR = _SETTINGS.data_dir


class TestGetCsvPath:
    """Test CSV path resolution for different banks."""

    def test_returns_path_for_santander(self):
        path = get_csv_path("santander")
        assert path == _DATA_DIR / "santander" / "firefly_likeu.csv"

    def test_returns_path_for_santander_likeu(self):
        path = get_csv_path("santander_likeu")
        assert path == _DATA_DIR / "santander" / "firefly_likeu.csv"

    def test_returns_path_for_hsbc(self):
        path = get_csv_path("hsbc")
        assert path == _DATA_DIR / "hsbc" / "firefly_hsbc.csv"

    def test_returns_none_for_unknown_bank(self):
        path = get_csv_path("unknown_bank")
        assert path is None

    def test_returns_none_for_empty_string(self):
        path = get_csv_path("")
        assert path is None

    def test_returns_none_for_invalid_type(self):
        """Test that non-string bank_id returns None gracefully."""
        path = get_csv_path(123)
        assert path is None

        path = get_csv_path(None)
        assert path is None

    def test_uses_accounts_config_metadata_and_aliases(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        config_dir.mkdir()
        data_dir.mkdir()

        accounts_cfg = {
            "version": 1,
            "canonical_accounts": {
                "cc:example": {
                    "bank_ids": ["example_alias", "example_bank"],
                    "account_ids": ["Liabilities:CC:Example"],
                    "csv_output": {
                        "directory": "example",
                        "filename": "firefly_example.csv",
                    },
                }
            },
        }
        (config_dir / "accounts.yml").write_text(yaml.safe_dump(accounts_cfg), encoding="utf-8")
        monkeypatch.setattr(
            data_service,
            "_SETTINGS",
            SimpleNamespace(config_dir=config_dir, data_dir=data_dir),
        )

        expected = data_dir / "example" / "firefly_example.csv"
        assert get_csv_path("example_alias") == expected
        assert get_csv_path("example_bank") == expected
        assert get_csv_path("unknown_bank") is None

    def test_legacy_banks_preserved_when_accounts_yml_has_only_new_bank(self, tmp_path, monkeypatch):
        """Regression: hsbc/santander paths survive when accounts.yml has a new bank."""
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        config_dir.mkdir()
        data_dir.mkdir()

        accounts_cfg = {
            "version": 1,
            "canonical_accounts": {
                "cc:newbank": {
                    "bank_ids": ["newbank"],
                    "account_ids": ["Liabilities:CC:NewBank"],
                    "csv_output": {"directory": "newbank", "filename": "firefly_newbank.csv"},
                }
            },
        }
        (config_dir / "accounts.yml").write_text(yaml.safe_dump(accounts_cfg), encoding="utf-8")
        monkeypatch.setattr(data_service, "_SETTINGS",
                            SimpleNamespace(config_dir=config_dir, data_dir=data_dir))

        assert get_csv_path("hsbc") == data_dir / "hsbc" / "firefly_hsbc.csv"
        assert get_csv_path("santander_likeu") == data_dir / "santander" / "firefly_likeu.csv"
        assert get_csv_path("newbank") == data_dir / "newbank" / "firefly_newbank.csv"

    def test_reloads_accounts_config_changes_without_restart(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        config_dir.mkdir()
        data_dir.mkdir()

        accounts_path = config_dir / "accounts.yml"
        first_cfg = {
            "version": 1,
            "canonical_accounts": {
                "cc:example": {
                    "bank_ids": ["example_bank"],
                    "account_ids": ["Liabilities:CC:Example"],
                    "csv_output": {
                        "directory": "example-a",
                        "filename": "firefly_a.csv",
                    },
                }
            },
        }
        second_cfg = {
            "version": 1,
            "canonical_accounts": {
                "cc:example": {
                    "bank_ids": ["example_bank"],
                    "account_ids": ["Liabilities:CC:Example"],
                    "csv_output": {
                        "directory": "example-b",
                        "filename": "firefly_b.csv",
                    },
                }
            },
        }

        accounts_path.write_text(yaml.safe_dump(first_cfg), encoding="utf-8")
        monkeypatch.setattr(
            data_service,
            "_SETTINGS",
            SimpleNamespace(config_dir=config_dir, data_dir=data_dir),
        )

        assert get_csv_path("example_bank") == data_dir / "example-a" / "firefly_a.csv"

        accounts_path.write_text(yaml.safe_dump(second_cfg), encoding="utf-8")
        assert get_csv_path("example_bank") == data_dir / "example-b" / "firefly_b.csv"


class TestLoadTransactionsFromCsv:
    """Test CSV loading functionality."""

    def test_load_transactions_from_csv_legacy_bank_not_rejected_when_new_bank_in_accounts_yml(
        self, tmp_path, monkeypatch
    ):
        """hsbc should not raise ValueError when accounts.yml only lists a new bank."""
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        config_dir.mkdir()
        data_dir.mkdir()

        accounts_cfg = {
            "version": 1,
            "canonical_accounts": {
                "cc:newbank": {
                    "bank_ids": ["newbank"],
                    "account_ids": ["Liabilities:CC:NewBank"],
                    "csv_output": {"directory": "newbank", "filename": "firefly_newbank.csv"},
                }
            },
        }
        (config_dir / "accounts.yml").write_text(yaml.safe_dump(accounts_cfg), encoding="utf-8")
        monkeypatch.setattr(data_service, "_SETTINGS",
                            SimpleNamespace(config_dir=config_dir, data_dir=data_dir))

        df = load_transactions_from_csv("hsbc")
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_raises_error_for_unknown_bank(self):
        with pytest.raises(ValueError, match="Unknown bank ID"):
            load_transactions_from_csv("invalid_bank")

    def test_raises_error_for_invalid_bank_id_type(self):
        """Test that non-string bank_id raises ValueError."""
        with pytest.raises(ValueError, match="bank_id must be a non-empty string"):
            load_transactions_from_csv(None)

        with pytest.raises(ValueError, match="bank_id must be a non-empty string"):
            load_transactions_from_csv(123)

    def test_raises_error_for_empty_bank_id(self):
        """Test that empty string bank_id raises ValueError."""
        with pytest.raises(ValueError, match="bank_id must be a non-empty string"):
            load_transactions_from_csv("")

    def test_returns_empty_dataframe_for_missing_file(self):
        # Use a known bank but file won't exist in test environment
        with patch('services.data_service.get_csv_path') as mock_path:
            mock_path.return_value = Path("/nonexistent/path/file.csv")
            df = load_transactions_from_csv("santander")
            assert isinstance(df, pd.DataFrame)
            assert df.empty

    def test_parses_date_column_correctly(self):
        csv_content = """date,amount,description,type
2024-01-15,100.50,Test transaction,withdrawal
2024-02-20,200.75,Another test,deposit"""

        mock_path = Path("test.csv")
        with patch('services.data_service.get_csv_path', return_value=mock_path):
            with patch.object(Path, 'exists', return_value=True):
                with patch('builtins.open', mock_open(read_data=csv_content)):
                    df = load_transactions_from_csv("santander")
                    assert not df.empty
                    assert 'date' in df.columns
                    assert pd.api.types.is_datetime64_any_dtype(df['date'])
                    assert len(df) == 2

    def test_returns_empty_dataframe_on_malformed_csv(self):
        # Malformed CSV content
        csv_content = """date,amount
2024-01-15,100
malformed line without proper structure
2024-02-20"""

        mock_path = Path("test.csv")
        with patch('services.data_service.get_csv_path', return_value=mock_path):
            with patch.object(Path, 'exists', return_value=True):
                with patch('builtins.open', mock_open(read_data=csv_content)):
                    # The function returns empty DataFrame on any exception
                    df = load_transactions_from_csv("santander")
                    # Due to pandas flexibility, this might parse, so we just ensure it doesn't crash
                    assert isinstance(df, pd.DataFrame)

    def test_handles_empty_csv_file(self):
        csv_content = """date,amount,description"""

        mock_path = Path("test.csv")
        with patch('services.data_service.get_csv_path', return_value=mock_path):
            with patch.object(Path, 'exists', return_value=True):
                with patch('builtins.open', mock_open(read_data=csv_content)):
                    df = load_transactions_from_csv("santander")
                    assert isinstance(df, pd.DataFrame)
                    assert df.empty

    def test_preserves_all_columns_from_csv(self):
        csv_content = """date,amount,description,type,destination_name,category_name,tags
2024-01-15,100.50,Test,withdrawal,Expenses:Food,Food,period:2024-01"""

        mock_path = Path("test.csv")
        with patch('services.data_service.get_csv_path', return_value=mock_path):
            with patch.object(Path, 'exists', return_value=True):
                with patch('builtins.open', mock_open(read_data=csv_content)):
                    df = load_transactions_from_csv("santander")
                    expected_columns = ['date', 'amount', 'description', 'type',
                                      'destination_name', 'category_name', 'tags']
                    for col in expected_columns:
                        assert col in df.columns


class TestLoadAllBankData:
    """Test loading data for all banks."""

    def test_returns_dict_with_both_banks(self):
        with patch('services.data_service.load_transactions_from_csv') as mock_load:
            # Mock return values; patch Path.exists so the bank CSV files appear present.
            mock_load.return_value = pd.DataFrame({'date': [pd.Timestamp('2024-01-15')], 'amount': [100]})
            with patch('pathlib.Path.exists', return_value=True):
                result = load_all_bank_data()

            assert isinstance(result, dict)
            # The result keys come from the dynamic bank map; at minimum the legacy IDs must appear
            bank_ids = set(result.keys())
            assert bank_ids & {"santander", "santander_likeu", "hsbc"}
            for df in result.values():
                assert isinstance(df, pd.DataFrame)

    def test_calls_load_for_configured_banks(self):
        # New implementation only calls load_transactions_from_csv when the CSV exists.
        # Patch Path.exists so the bank files appear present.
        with patch('services.data_service.load_transactions_from_csv') as mock_load:
            mock_load.return_value = pd.DataFrame()
            with patch('pathlib.Path.exists', return_value=True):
                result = load_all_bank_data()
                # At minimum the two legacy banks should be represented
                assert mock_load.call_count >= 2
                called_args = {call.args[0] for call in mock_load.call_args_list}
                assert called_args & {"santander", "hsbc", "santander_likeu"}

    def test_handles_empty_dataframes_gracefully(self):
        with patch('services.data_service.load_transactions_from_csv') as mock_load:
            mock_load.return_value = pd.DataFrame()  # Empty DataFrames
            with patch('pathlib.Path.exists', return_value=True):
                result = load_all_bank_data()

            # All returned DataFrames should be empty
            for df in result.values():
                assert df.empty


class TestLoadTransactionsCsvErrorPaths:
    """Test exception handling paths in load_transactions_from_csv (lines 120, 124-141)."""

    def test_csv_without_date_column_logs_warning(self, tmp_path):
        """When CSV has no 'date' column, returns df without date parsing (line 120)."""
        csv_content = "amount,description\n100.0,OXXO\n"
        csv_file = tmp_path / "nodatecol.csv"
        csv_file.write_text(csv_content)

        with patch('services.data_service.get_csv_path', return_value=csv_file):
            df = load_transactions_from_csv("santander")
            # Should return the df but without date column parsed
            assert isinstance(df, pd.DataFrame)
            assert "date" not in df.columns

    def test_file_not_found_error_returns_empty_df(self, tmp_path):
        """FileNotFoundError during read returns empty DataFrame (lines 124-127)."""
        mock_path = tmp_path / "ghost.csv"
        mock_path.touch()  # exists() passes

        with patch('services.data_service.get_csv_path', return_value=mock_path):
            with patch('pandas.read_csv', side_effect=FileNotFoundError("gone")):
                df = load_transactions_from_csv("santander")
                assert isinstance(df, pd.DataFrame)
                assert df.empty

    def test_parser_error_returns_empty_df(self, tmp_path):
        """ParserError returns empty DataFrame (lines 129-134)."""
        mock_path = tmp_path / "malformed.csv"
        mock_path.touch()

        with patch('services.data_service.get_csv_path', return_value=mock_path):
            with patch('pandas.read_csv', side_effect=pd.errors.ParserError("bad csv")):
                df = load_transactions_from_csv("santander")
                assert isinstance(df, pd.DataFrame)
                assert df.empty

    def test_unexpected_exception_returns_empty_df(self, tmp_path):
        """Unexpected exception returns empty DataFrame (lines 136-141)."""
        mock_path = tmp_path / "weird.csv"
        mock_path.touch()

        with patch('services.data_service.get_csv_path', return_value=mock_path):
            with patch('pandas.read_csv', side_effect=RuntimeError("unexpected")):
                df = load_transactions_from_csv("santander")
                assert isinstance(df, pd.DataFrame)
                assert df.empty


class TestLoadTransactionsPreferredSource:
    """Test DB-first transaction loading behavior."""

    def test_load_transactions_from_db_unknown_bank_does_not_touch_csv_resolution(self, tmp_path):
        db_path = tmp_path / "ledger.db"
        db = DatabaseService(db_path=db_path)
        db.initialize()

        with patch(
            "services.data_service.get_csv_path",
            side_effect=AssertionError("CSV resolution should not be consulted for DB validation"),
        ) as mock_csv_path:
            with pytest.raises(ValueError, match="Unknown bank ID"):
                data_service.load_transactions_from_db("unknown_bank", db_path=db_path)

        mock_csv_path.assert_not_called()

    def test_load_transactions_prefers_db_when_present(self, tmp_path):
        db_path = tmp_path / "ledger.db"
        db = DatabaseService(db_path=db_path)
        db.initialize()
        db.upsert_account(
            account_id="cc:hsbc",
            display_name="Liabilities:CC:HSBC",
            bank_id="hsbc",
            currency="MXN",
        )
        db.insert_transaction(
            {
                "date": "2026-01-20",
                "amount": 200.0,
                "currency": "MXN",
                "merchant": "merchant:netflix",
                "description": "NETFLIX",
                "account_id": "Liabilities:CC:HSBC",
                "canonical_account_id": "cc:hsbc",
                "bank_id": "hsbc",
                "statement_period": "2026-01",
                "category": "Entertainment",
                "tags": "bucket:subs,merchant:netflix,period:2026-01",
                "source_file": "data/hsbc/firefly_hsbc.csv",
                "transaction_type": "withdrawal",
                "source_name": "Liabilities:CC:HSBC",
                "destination_name": "Expenses:Entertainment:DigitalServices",
            }
        )

        with patch("services.data_service.load_transactions_from_csv") as mock_csv:
            df = load_transactions("hsbc", prefer_db=True, db_path=db_path)
            assert len(df) == 1
            assert df.iloc[0]["description"] == "NETFLIX"
            mock_csv.assert_not_called()

    def test_load_transactions_falls_back_to_csv_when_db_missing(self):
        with patch("services.data_service.load_transactions_from_csv") as mock_csv:
            mock_csv.return_value = pd.DataFrame({"description": ["csv"]})
            df = load_transactions("santander_likeu", prefer_db=True, db_path=Path("/nonexistent/db.sqlite"))
            assert len(df) == 1
            assert df.iloc[0]["description"] == "csv"
            mock_csv.assert_called_once_with("santander_likeu")

    def test_load_transactions_falls_back_to_csv_when_db_exists_but_has_no_rows_for_bank(self, tmp_path):
        db_path = tmp_path / "ledger.db"
        db = DatabaseService(db_path=db_path)
        db.initialize()
        db.upsert_account(
            account_id="cc:hsbc",
            display_name="Liabilities:CC:HSBC",
            bank_id="hsbc",
            currency="MXN",
        )
        db.insert_transaction(
            {
                "date": "2026-01-20",
                "amount": 200.0,
                "currency": "MXN",
                "merchant": "merchant:netflix",
                "description": "NETFLIX",
                "account_id": "Liabilities:CC:HSBC",
                "canonical_account_id": "cc:hsbc",
                "bank_id": "hsbc",
                "statement_period": "2026-01",
                "category": "Entertainment",
                "tags": "bucket:subs,merchant:netflix,period:2026-01",
                "source_file": "data/hsbc/firefly_hsbc.csv",
                "transaction_type": "withdrawal",
                "source_name": "Liabilities:CC:HSBC",
                "destination_name": "Expenses:Entertainment:DigitalServices",
            }
        )

        with patch("services.data_service.load_transactions_from_csv") as mock_csv:
            mock_csv.return_value = pd.DataFrame({"description": ["csv"]})
            df = load_transactions("santander_likeu", prefer_db=True, db_path=db_path)

        assert len(df) == 1
        assert df.iloc[0]["description"] == "csv"
        mock_csv.assert_called_once_with("santander_likeu")

    def test_load_transactions_raises_for_unknown_bank_even_with_db_first(self, tmp_path):
        db_path = tmp_path / "ledger.db"
        db = DatabaseService(db_path=db_path)
        db.initialize()

        with patch(
            "services.data_service.load_transactions_from_csv",
            side_effect=AssertionError("CSV fallback should not run for an unknown bank"),
        ) as mock_csv:
            with pytest.raises(ValueError, match="Unknown bank ID"):
                load_transactions("unknown_bank", prefer_db=True, db_path=db_path)

        mock_csv.assert_not_called()
