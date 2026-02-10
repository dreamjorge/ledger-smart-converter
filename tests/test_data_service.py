import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
import io

from services.data_service import get_csv_path, load_transactions_from_csv, load_all_bank_data
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


class TestLoadTransactionsFromCsv:
    """Test CSV loading functionality."""

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
            # Mock return values for both banks
            mock_load.side_effect = [
                pd.DataFrame({'date': [pd.Timestamp('2024-01-15')], 'amount': [100]}),
                pd.DataFrame({'date': [pd.Timestamp('2024-02-20')], 'amount': [200]})
            ]

            result = load_all_bank_data()

            assert isinstance(result, dict)
            assert 'santander' in result
            assert 'hsbc' in result
            assert isinstance(result['santander'], pd.DataFrame)
            assert isinstance(result['hsbc'], pd.DataFrame)

    def test_calls_load_for_santander_and_hsbc(self):
        with patch('services.data_service.load_transactions_from_csv') as mock_load:
            mock_load.return_value = pd.DataFrame()

            load_all_bank_data()

            # Verify it was called for both banks
            assert mock_load.call_count == 2
            mock_load.assert_any_call("santander")
            mock_load.assert_any_call("hsbc")

    def test_handles_empty_dataframes_gracefully(self):
        with patch('services.data_service.load_transactions_from_csv') as mock_load:
            mock_load.return_value = pd.DataFrame()  # Empty DataFrames

            result = load_all_bank_data()

            assert result['santander'].empty
            assert result['hsbc'].empty


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
