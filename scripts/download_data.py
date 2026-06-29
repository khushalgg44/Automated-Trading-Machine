"""Download real historical OHLC data from Yahoo Finance for NSE stocks.

Downloads 6 months of daily data for RELIANCE, TCS, INFY.
Saves in the format expected by data_loader.py: Date,Open,High,Low,Close,Volume
"""

import os
import sys

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed. Run: pip install yfinance")
    sys.exit(1)


# NSE stock tickers on Yahoo Finance
STOCKS = {
    "RELIANCE.NS": "reliance_6m.csv",
    "TCS.NS": "tcs_6m.csv",
    "INFY.NS": "infy_6m.csv",
}

# Output directory
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def download_stock(ticker: str, filename: str) -> bool:
    """Download 6 months of daily OHLC data for a stock."""
    print(f"  Downloading {ticker}...", end=" ")

    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="6mo", interval="1d")

        if df.empty:
            print("FAILED — no data returned")
            return False

        # Drop NaN rows
        df = df.dropna(subset=["Open", "High", "Low", "Close", "Volume"])

        # Reset index to get Date as a column
        df = df.reset_index()

        # Format for our CSV: Date,Open,High,Low,Close,Volume
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
        df["Open"] = df["Open"].round(2)
        df["High"] = df["High"].round(2)
        df["Low"] = df["Low"].round(2)
        df["Close"] = df["Close"].round(2)
        df["Volume"] = df["Volume"].astype(int)

        output_path = os.path.join(DATA_DIR, filename)
        df[["Date", "Open", "High", "Low", "Close", "Volume"]].to_csv(
            output_path, index=False
        )

        print(f"OK — {len(df)} candles → {filename}")
        return True

    except Exception as e:
        print(f"FAILED — {e}")
        return False


def main():
    print(f"Downloading NSE stock data to: {DATA_DIR}")
    os.makedirs(DATA_DIR, exist_ok=True)

    success_count = 0
    for ticker, filename in STOCKS.items():
        if download_stock(ticker, filename):
            success_count += 1

    print(f"\nDone: {success_count}/{len(STOCKS)} stocks downloaded successfully.")

    if success_count == 0:
        print("WARNING: No data downloaded. Check your network connection.")
        sys.exit(1)


if __name__ == "__main__":
    main()
