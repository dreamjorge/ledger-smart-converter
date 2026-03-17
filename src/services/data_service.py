"""Data service for loading and managing bank transaction CSV files.

This service provides centralized access to bank transaction data stored in CSV files.
It handles file path resolution, CSV loading, date parsing, and error handling.
"""

import pandas as pd
from typing import Dict, Optional
from pathlib import Path

from logging_config import get_logger
from errors import ConfigError, ParseError
from settings import load_settings
from services.db_service import DatabaseService

logger = get_logger("data_service")

# Load settings to get proper data directory path
_SETTINGS = load_settings()
_DATA_DIR = _SETTINGS.data_dir

BANK_FILE_MAP = {
    "santander": _DATA_DIR / "santander" / "firefly_likeu.csv",
    "santander_likeu": _DATA_DIR / "santander" / "firefly_likeu.csv",
    "hsbc": _DATA_DIR / "hsbc" / "firefly_hsbc.csv",
}


def get_csv_path(bank_id: str) -> Optional[Path]:
    """Get the CSV file path for a given bank ID.

    Args:
        bank_id: Bank identifier (e.g., 'santander', 'hsbc')

    Returns:
        Path object pointing to the bank's CSV file, or None if bank_id is unknown.

    Example:
        >>> path = get_csv_path("santander")
        >>> print(path)
        data/santander/firefly_likeu.csv
    """
    if not isinstance(bank_id, str):
        logger.warning(f"Invalid bank_id type: {type(bank_id)}. Expected str.")
        return None

    if not bank_id:
        logger.warning("Empty bank_id provided to get_csv_path")
        return None

    return BANK_FILE_MAP.get(bank_id)


def load_transactions_from_csv(bank_id: str) -> pd.DataFrame:
    """Load transaction data for a given bank from its CSV file.

    This function handles:
    - Bank ID validation
    - File existence checking
    - CSV parsing with error handling
    - Date column parsing to datetime format
    - Graceful degradation (returns empty DataFrame on errors)

    Args:
        bank_id: Bank identifier (e.g., 'santander', 'hsbc')

    Returns:
        DataFrame containing transaction data with parsed date column.
        Returns empty DataFrame if:
        - Bank ID is unknown
        - File does not exist
        - CSV is malformed or cannot be parsed
        - Date column cannot be parsed

    Raises:
        ValueError: If bank_id is unknown (not in BANK_FILE_MAP)

    Example:
        >>> df = load_transactions_from_csv("santander")
        >>> print(df.columns)
        Index(['date', 'amount', 'description', 'type', ...])
    """
    if not isinstance(bank_id, str) or not bank_id:
        logger.error(f"Invalid bank_id: {bank_id!r}")
        raise ValueError(f"bank_id must be a non-empty string, got: {bank_id!r}")

    file_path = get_csv_path(bank_id)
    if not file_path:
        logger.error(f"Unknown bank ID: {bank_id}")
        raise ValueError(f"Unknown bank ID: {bank_id}")

    # Check file existence before attempting to read
    if not file_path.exists():
        logger.warning(
            f"CSV file not found for bank '{bank_id}' at path: {file_path}. "
            "Returning empty DataFrame."
        )
        return pd.DataFrame()

    try:
        logger.info(f"Loading transactions for bank '{bank_id}' from {file_path}")
        df = pd.read_csv(file_path)

        if df.empty:
            logger.info(f"CSV file for bank '{bank_id}' is empty")
            return df

        # Ensure 'date' column exists and is datetime
        if 'date' in df.columns:
            try:
                df['date'] = pd.to_datetime(df['date'])
                logger.debug(f"Successfully parsed {len(df)} transactions for '{bank_id}'")
            except Exception as date_err:
                logger.error(
                    f"Failed to parse date column for bank '{bank_id}': {date_err}. "
                    "Returning empty DataFrame."
                )
                # Return empty DataFrame for graceful degradation
                return pd.DataFrame()
        else:
            logger.warning(f"CSV for bank '{bank_id}' missing 'date' column")

        return df

    except FileNotFoundError:
        # This shouldn't happen due to exists() check, but handle it anyway
        logger.warning(f"File not found during read for bank '{bank_id}': {file_path}")
        return pd.DataFrame()

    except pd.errors.ParserError as parse_err:
        logger.error(
            f"CSV parsing error for bank '{bank_id}' at {file_path}: {parse_err}. "
            "File may be malformed. Returning empty DataFrame."
        )
        return pd.DataFrame()

    except Exception as e:
        logger.error(
            f"Unexpected error loading data for bank '{bank_id}' from {file_path}: {e}",
            exc_info=True
        )
        return pd.DataFrame()


def load_transactions_from_db(bank_id: str, db_path: Optional[Path] = None) -> pd.DataFrame:
    """Load transaction data for a given bank from SQLite."""
    if not isinstance(bank_id, str) or not bank_id:
        logger.error(f"Invalid bank_id: {bank_id!r}")
        raise ValueError(f"bank_id must be a non-empty string, got: {bank_id!r}")

    settings = load_settings()
    effective_db = Path(db_path) if db_path else (settings.data_dir / "ledger.db")
    if not effective_db.exists():
        logger.info(f"SQLite DB not found at {effective_db}; returning empty DataFrame")
        return pd.DataFrame()

    try:
        db = DatabaseService(db_path=effective_db)
        rows = db.fetch_all(
            """
            SELECT
                date,
                amount,
                description,
                COALESCE(transaction_type, 'withdrawal') AS type,
                destination_name,
                category AS category_name,
                tags
            FROM transactions
            WHERE bank_id = ?
            ORDER BY date
            """,
            (bank_id,),
        )
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df
    except Exception as exc:
        logger.error(f"Failed loading DB transactions for '{bank_id}': {exc}", exc_info=True)
        return pd.DataFrame()


def load_transactions(bank_id: str, prefer_db: bool = True, db_path: Optional[Path] = None) -> pd.DataFrame:
    """Load transactions from preferred source (DB first, CSV fallback)."""
    if prefer_db:
        df_db = load_transactions_from_db(bank_id, db_path=db_path)
        if not df_db.empty:
            return df_db
    return load_transactions_from_csv(bank_id)


def load_all_bank_data() -> Dict[str, pd.DataFrame]:
    """Load transaction data for all supported banks.

    This is a convenience function that loads data for all banks defined
    in BANK_FILE_MAP. It handles errors gracefully - if one bank fails to load,
    others will still be loaded.

    Returns:
        Dictionary mapping bank IDs to their transaction DataFrames.
        Keys: 'santander', 'hsbc'
        Values: DataFrames (may be empty if loading failed)

    Example:
        >>> all_data = load_all_bank_data()
        >>> santander_df = all_data['santander']
        >>> hsbc_df = all_data['hsbc']
    """
    logger.info("Loading transaction data for all banks")
    all_data = {}

    # Load each bank independently - failures are isolated
    all_data["santander"] = load_transactions_from_csv("santander")
    all_data["hsbc"] = load_transactions_from_csv("hsbc")

    total_transactions = sum(len(df) for df in all_data.values())
    logger.info(
        f"Loaded {total_transactions} total transactions across {len(all_data)} banks"
    )

    return all_data
