"""Generate synthetic sample OHLC data for backtesting."""

import csv
import random
from datetime import date, timedelta

random.seed(42)


def generate_ohlc(
    filename: str,
    start_price: float = 2500.0,
    days: int = 180,
    start_date: date = date(2025, 7, 1),
) -> None:
    """Generate a CSV with synthetic daily OHLC candles.

    Random walk with slight upward drift, realistic daily ranges.
    """
    rows = []
    price = start_price
    current_date = start_date

    for _ in range(days):
        # Skip weekends
        while current_date.weekday() >= 5:
            current_date += timedelta(days=1)

        # Daily return: slight drift + noise
        daily_return = random.gauss(0.0003, 0.015)  # ~0.03% drift, 1.5% volatility
        close = price * (1 + daily_return)

        # Intraday range
        intraday_vol = abs(random.gauss(0, 0.008))
        high = max(price, close) * (1 + intraday_vol)
        low = min(price, close) * (1 - intraday_vol)
        open_price = price + random.gauss(0, price * 0.003)

        # Clamp open within high/low
        open_price = max(low, min(high, open_price))

        volume = random.randint(500000, 5000000)

        rows.append({
            "Date": current_date.strftime("%Y-%m-%d"),
            "Open": f"{open_price:.2f}",
            "High": f"{high:.2f}",
            "Low": f"{low:.2f}",
            "Close": f"{close:.2f}",
            "Volume": str(volume),
        })

        price = close
        current_date += timedelta(days=1)

    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Date", "Open", "High", "Low", "Close", "Volume"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} candles → {filename}")


if __name__ == "__main__":
    generate_ohlc("sample_data.csv")
