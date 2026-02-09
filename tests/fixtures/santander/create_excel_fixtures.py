#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script to create Excel test fixtures for Santander importer tests."""

import pandas as pd
from pathlib import Path

fixtures_dir = Path(__file__).parent

# Valid statement with proper header
valid_data = [
    ["", "", "", ""],  # Empty rows
    ["Banco Santander", "", "", ""],
    ["Estado de Cuenta LikeU", "", "", ""],
    ["FECHA", "CONCEPTO", "IMPORTE", "SALDO"],  # Header row at index 3
    ["15/ene/24", "OXXO REFORMA", "-45.50", "1000.00"],
    ["16/ene/24", "WALMART INSURGENTES", "-234.00", "766.00"],
    ["17/ene/24", "AMAZON MEXICO", "-567.89", "198.11"],
    ["18/ene/24", "PAGO TARJETA GRACIAS", "1500.00", "1698.11"],
    ["19/ene/24", "NETFLIX SUBSCRIPTION", "-159.00", "1539.11"],
]

df_valid = pd.DataFrame(valid_data)
df_valid.to_excel(fixtures_dir / "valid_statement.xlsx", index=False, header=False)

# Malformed Excel - missing FECHA column
malformed_data = [
    ["", "", "", ""],
    ["DESCRIPTION", "AMOUNT", "BALANCE", ""],  # Wrong header
    ["OXXO", "-45.50", "1000.00", ""],
]

df_malformed = pd.DataFrame(malformed_data)
df_malformed.to_excel(fixtures_dir / "malformed_statement.xlsx", index=False, header=False)

# Missing columns - has FECHA but missing other required columns
missing_cols_data = [
    ["", "", ""],
    ["FECHA", "CONCEPTO", ""],  # Missing IMPORTE
    ["15/ene/24", "OXXO", ""],
]

df_missing = pd.DataFrame(missing_cols_data)
df_missing.to_excel(fixtures_dir / "missing_columns.xlsx", index=False, header=False)

# Header at different position
header_offset_data = [
    ["", "", "", ""],
    ["", "", "", ""],
    ["", "", "", ""],
    ["", "", "", ""],
    ["", "", "", ""],
    ["FECHA", "CONCEPTO", "IMPORTE", "SALDO"],  # Header at index 5
    ["15/ene/24", "OXXO", "-45.50", "1000.00"],
]

df_offset = pd.DataFrame(header_offset_data)
df_offset.to_excel(fixtures_dir / "header_offset.xlsx", index=False, header=False)

# Empty DataFrame
df_empty = pd.DataFrame([["", ""]])
df_empty.to_excel(fixtures_dir / "empty_statement.xlsx", index=False, header=False)

print("Excel fixtures created successfully!")
print(f"Location: {fixtures_dir}")
