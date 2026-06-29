"""Load OHLC data from CSV files (standard Yahoo Finance format).

Expected CSV columns: Date, Open, High, Low, Close, Volume
Handles NaN/empty values by skipping those rows.
"""

import csv
import math
import os
from decimal import Decimal, InvalidOperation
from typing import Any


def load_csv(filepath: str) -> list[dict[str, Any]]:
    """Load OHLC candles from a CSV file.

    Returns list of dicts with keys: date, open, high, low, close, volume.
    All prices are floats (converted from Decimal for compatibility with strategies).
    Rows with NaN or missing values are dropped.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    candles: list[dict[str, Any]] = []

    with open(filepath, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                open_val = float(row["Open"].strip())
                high_val = float(row["High"].strip())
                low_val = float(row["Low"].strip())
                close_val = float(row["Close"].strip())
                volume_val = int(float(row["Volume"].strip()))

                # Skip NaN values
                if any(math.isnan(v) for v in [open_val, high_val, low_val, close_val]):
                    continue

                candles.append({
                    "date": row["Date"].strip(),
                    "open": open_val,
                    "high": high_val,
                    "low": low_val,
                    "close": close_val,
                    "volume": volume_val,
                })
            except (ValueError, InvalidOperation, KeyError):
                # Skip malformed rows
                continue

    return candles
