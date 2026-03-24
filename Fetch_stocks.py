import requests
import json
import csv
import os
from datetime import datetime

# ✅ Add your favorite stocks here
STOCKS = ["RELIANCE.BSE", "TCS.BSE", "INFY.BSE", "WIPRO.BSE", "HDFCBANK.BSE"]

# Using Alpha Vantage free API (get your free key at https://www.alphavantage.co/support/#api-key)
API_KEY = os.environ.get("ALPHA_VANTAGE_KEY", "demo")

LOG_FILE = "data/stock_log.csv"
SUMMARY_FILE = "data/latest_summary.json"

def fetch_price(symbol):
    """Fetch latest stock price from Alpha Vantage"""
    # Strip exchange suffix for API call
    ticker = symbol.split(".")[0]
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={API_KEY}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        quote = data.get("Global Quote", {})
        return {
            "symbol": symbol,
            "price": quote.get("05. price", "N/A"),
            "change": quote.get("09. change", "N/A"),
            "change_pct": quote.get("10. change percent", "N/A"),
            "volume": quote.get("06. volume", "N/A"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S")
        }
    except Exception as e:
        return {
            "symbol": symbol,
            "price": "ERROR",
            "change": "N/A",
            "change_pct": "N/A",
            "volume": "N/A",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S")
        }

def main():
    os.makedirs("data", exist_ok=True)

    results = [fetch_price(stock) for stock in STOCKS]

    # Append to CSV log
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "time", "symbol", "price", "change", "change_pct", "volume"])
        if not file_exists:
            writer.writeheader()
        writer.writerows(results)

    # Save latest summary as JSON
    with open(SUMMARY_FILE, "w") as f:
        json.dump({
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stocks": results
        }, f, indent=2)

    # Update README with latest prices
    with open("README.md", "w") as f:
        f.write(f"# 📈 Daily Stock Price Tracker\n\n")
        f.write(f"Auto-updated every day via GitHub Actions.\n\n")
        f.write(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST\n\n")
        f.write(f"## Today's Prices\n\n")
        f.write(f"| Symbol | Price | Change | Change % | Volume |\n")
        f.write(f"|--------|-------|--------|----------|--------|\n")
        for r in results:
            f.write(f"| {r['symbol']} | {r['price']} | {r['change']} | {r['change_pct']} | {r['volume']} |\n")
        f.write(f"\n## 📊 Historical data is stored in `data/stock_log.csv`\n")

    print("✅ Stock prices fetched and logged successfully!")
    for r in results:
        print(f"  {r['symbol']}: ₹{r['price']} ({r['change_pct']})")

if __name__ == "__main__":
    main()