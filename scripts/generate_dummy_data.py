#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate dummy transaction data for testing the analytics dashboard.

This script creates realistic transaction CSV files for both Santander and HSBC banks
with proper categorization, merchant tags, and period tags.
"""

import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple
import pandas as pd


# Merchant templates with categories
MERCHANTS = {
    "Groceries": [
        "OXXO", "7-ELEVEN", "WALMART", "SORIANA", "CHEDRAUI", "COMERCIAL MEXICANA",
        "LA COMER", "BODEGA AURRERA", "SUPERAMA", "COSTCO"
    ],
    "Restaurants": [
        "MCDONALDS", "STARBUCKS", "SUBWAY", "KFC", "BURGER KING", "DOMINOS PIZZA",
        "VIPS", "CHILIS", "ITALIANNIS", "TOKS", "SANBORNS", "EL PORTON"
    ],
    "Transport": [
        "UBER", "UBER EATS", "DIDI", "PEMEX", "BP GAS", "SHELL", "MOBIL",
        "ESTACIONAMIENTO", "METRO CDMX", "CABIFY"
    ],
    "Shopping": [
        "LIVERPOOL", "PALACIO DE HIERRO", "SEARS", "COPPEL", "ELEKTRA",
        "SUBURBIA", "ZARA", "H&M", "PULL&BEAR", "BERSHKA"
    ],
    "Entertainment": [
        "CINEPOLIS", "CINEMEX", "SPOTIFY", "NETFLIX", "HBO MAX", "DISNEY PLUS",
        "YOUTUBE PREMIUM", "AMAZON PRIME", "PLAYSTATION"
    ],
    "Subscriptions": [
        "NETFLIX", "SPOTIFY", "AMAZON PRIME", "HBO MAX", "DISNEY PLUS",
        "YOUTUBE PREMIUM", "APPLE MUSIC", "OFFICE 365", "DROPBOX"
    ],
    "Health": [
        "FARMACIA GUADALAJARA", "FARMACIA DEL AHORRO", "SIMILARES",
        "HOSPITAL ABC", "LABORATORIO CHOPO", "DENTALIA", "SALUD DIGNA"
    ],
    "Fees": [
        "COMISION ANUALIDAD", "COMISION CAJERO", "COMISION TRANSFERENCIA",
        "SEGURO TARJETA", "IVA COMISION", "INTERES MORATORIO"
    ],
    "Online": [
        "MERCADO LIBRE", "AMAZON MEXICO", "ALIEXPRESS", "SHEIN", "WISH",
        "EBAY", "LINIO", "COPPEL.COM", "LIVERPOOL.COM.MX"
    ],
}

# Expense account mappings
CATEGORY_ACCOUNTS = {
    "Groceries": "Expenses:Food:Groceries",
    "Restaurants": "Expenses:Food:Restaurants",
    "Transport": "Expenses:Transport:Transport",
    "Shopping": "Expenses:Shopping:Shopping",
    "Entertainment": "Expenses:Entertainment:Entertainment",
    "Subscriptions": "Expenses:Entertainment:Subscriptions",
    "Health": "Expenses:Health",
    "Fees": "Expenses:Fees:Fees",
    "Online": "Expenses:Shopping:Online",
}

# Amount ranges per category (min, max)
AMOUNT_RANGES = {
    "Groceries": (20.00, 500.00),
    "Restaurants": (50.00, 800.00),
    "Transport": (15.00, 300.00),
    "Shopping": (100.00, 2500.00),
    "Entertainment": (50.00, 400.00),
    "Subscriptions": (99.00, 299.00),
    "Health": (50.00, 1500.00),
    "Fees": (10.00, 150.00),
    "Online": (100.00, 3000.00),
}


def generate_transaction(
    date: datetime,
    category: str,
    merchant: str,
    bank_id: str,
    account_name: str,
    period: str,
) -> Dict:
    """Generate a single transaction entry."""
    # Generate amount
    min_amt, max_amt = AMOUNT_RANGES[category]
    amount = round(random.uniform(min_amt, max_amt), 2)

    # Build destination account
    destination_account = CATEGORY_ACCOUNTS[category]

    # Build tags
    merchant_tag = merchant.lower().replace(" ", "_").replace("&", "and")
    tags = f"merchant:{merchant_tag},period:{period}"

    return {
        "date": date.strftime("%Y-%m-%d"),
        "amount": amount,
        "description": merchant,
        "type": "withdrawal",
        "source_name": account_name,
        "source_id": f"{bank_id}_main",
        "destination_name": destination_account,
        "destination_id": "",
        "currency_code": "MXN",
        "foreign_currency_code": "",
        "foreign_amount": "",
        "internal_reference": "",
        "external_id": "",
        "notes": "",
        "category_name": category,
        "tags": tags,
    }


def generate_period_transactions(
    start_date: datetime,
    end_date: datetime,
    period: str,
    bank_id: str,
    account_name: str,
    num_transactions: int = 50,
) -> List[Dict]:
    """Generate transactions for a billing period."""
    transactions = []
    categories = list(MERCHANTS.keys())

    for _ in range(num_transactions):
        # Random date within period
        days_diff = (end_date - start_date).days
        random_days = random.randint(0, days_diff)
        txn_date = start_date + timedelta(days=random_days)

        # Random category and merchant
        category = random.choice(categories)
        merchant = random.choice(MERCHANTS[category])

        txn = generate_transaction(
            date=txn_date,
            category=category,
            merchant=merchant,
            bank_id=bank_id,
            account_name=account_name,
            period=period,
        )
        transactions.append(txn)

    return transactions


def generate_bank_data(
    bank_id: str,
    account_name: str,
    months_back: int = 6,
    txns_per_month: int = 50,
) -> pd.DataFrame:
    """Generate transaction data for a bank covering multiple months."""
    all_transactions = []

    # Generate data for the last N months
    current_date = datetime.now()

    for i in range(months_back):
        # Calculate period dates (assume closing day is 15th)
        if i == 0:
            # Current partial month
            end_date = current_date
            start_date = datetime(current_date.year, current_date.month, 15)
            if start_date > end_date:
                # If closing day hasn't arrived yet this month
                start_date = datetime(
                    current_date.year if current_date.month > 1 else current_date.year - 1,
                    current_date.month - 1 if current_date.month > 1 else 12,
                    15
                )
        else:
            # Previous months
            target_month = current_date.month - i
            target_year = current_date.year

            while target_month < 1:
                target_month += 12
                target_year -= 1

            end_date = datetime(target_year, target_month, 15)

            prev_month = target_month - 1
            prev_year = target_year
            if prev_month < 1:
                prev_month = 12
                prev_year -= 1

            start_date = datetime(prev_year, prev_month, 16)

        period = f"{end_date.year}-{end_date.month:02d}"

        # Generate transactions for this period
        period_txns = generate_period_transactions(
            start_date=start_date,
            end_date=end_date,
            period=period,
            bank_id=bank_id,
            account_name=account_name,
            num_transactions=txns_per_month,
        )

        all_transactions.extend(period_txns)

    # Create DataFrame
    df = pd.DataFrame(all_transactions)

    # Sort by date
    df = df.sort_values("date", ascending=True)

    return df


def main():
    """Generate dummy data for both banks."""
    print("Generating dummy transaction data for dashboard testing...")

    # Create data directories
    santander_dir = Path("data/santander")
    hsbc_dir = Path("data/hsbc")

    santander_dir.mkdir(parents=True, exist_ok=True)
    hsbc_dir.mkdir(parents=True, exist_ok=True)

    # Generate Santander data
    print("\n📊 Generating Santander LikeU data...")
    santander_df = generate_bank_data(
        bank_id="santander_likeu",
        account_name="Santander LikeU",
        months_back=6,
        txns_per_month=60,
    )

    santander_csv = santander_dir / "firefly_likeu.csv"
    santander_df.to_csv(santander_csv, index=False, encoding="utf-8")
    print(f"✅ Created {santander_csv}")
    print(f"   - {len(santander_df)} transactions")
    print(f"   - Date range: {santander_df['date'].min()} to {santander_df['date'].max()}")
    print(f"   - Total spent: ${santander_df['amount'].sum():,.2f}")

    # Generate HSBC data
    print("\n📊 Generating HSBC data...")
    hsbc_df = generate_bank_data(
        bank_id="hsbc",
        account_name="HSBC Credit",
        months_back=6,
        txns_per_month=55,
    )

    hsbc_csv = hsbc_dir / "firefly_hsbc.csv"
    hsbc_df.to_csv(hsbc_csv, index=False, encoding="utf-8")
    print(f"✅ Created {hsbc_csv}")
    print(f"   - {len(hsbc_df)} transactions")
    print(f"   - Date range: {hsbc_df['date'].min()} to {hsbc_df['date'].max()}")
    print(f"   - Total spent: ${hsbc_df['amount'].sum():,.2f}")

    # Summary
    print(f"\n✨ Successfully generated dummy data for dashboard testing!")
    print(f"   Total transactions: {len(santander_df) + len(hsbc_df)}")
    print(f"   Combined spending: ${(santander_df['amount'].sum() + hsbc_df['amount'].sum()):,.2f}")
    print(f"\n🚀 You can now test the analytics dashboard with realistic data.")


if __name__ == "__main__":
    main()
