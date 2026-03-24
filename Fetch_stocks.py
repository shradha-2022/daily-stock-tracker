import requests
import json
import csv
import os
from datetime import datetime, timedelta

# ✅ Indian Stocks - Yahoo Finance format
STOCKS = {
    "RELIANCE.NS": "Reliance Industries",
    "TCS.NS": "TCS",
    "INFY.NS": "Infosys",
    "WIPRO.NS": "Wipro",
    "HDFCBANK.NS": "HDFC Bank"
}

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

LOG_FILE = "data/stock_log.csv"
SUMMARY_FILE = "data/latest_summary.json"

# ─────────────────────────────────────────────
# 1. FETCH STOCK PRICE via Yahoo Finance
# ─────────────────────────────────────────────
def fetch_price(symbol, name):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        meta = data["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice", 0)
        prev_close = meta.get("previousClose", 0) or meta.get("chartPreviousClose", 0)
        change = round(price - prev_close, 2)
        change_pct = round((change / prev_close) * 100, 2) if prev_close else 0
        return {
            "symbol": symbol,
            "name": name,
            "price": round(price, 2),
            "prev_close": round(prev_close, 2),
            "change": change,
            "change_pct": change_pct,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S")
        }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return {
            "symbol": symbol, "name": name,
            "price": 0, "prev_close": 0,
            "change": 0, "change_pct": 0,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S")
        }

# ─────────────────────────────────────────────
# 2. BUY / SELL SIGNALS
# ─────────────────────────────────────────────
def get_signal(stock):
    pct = stock["change_pct"]
    if pct >= 2.0:
        return "🟢 STRONG BUY"
    elif pct >= 0.5:
        return "🟡 BUY"
    elif pct <= -2.0:
        return "🔴 STRONG SELL"
    elif pct <= -0.5:
        return "🟠 SELL"
    else:
        return "⚪ HOLD"

# ─────────────────────────────────────────────
# 3. SEND TELEGRAM MESSAGE
# ─────────────────────────────────────────────
def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }, timeout=10)
        if res.status_code == 200:
            print("✅ Telegram message sent!")
        else:
            print(f"Telegram error: {res.text}")
    except Exception as e:
        print(f"Telegram send failed: {e}")

# ─────────────────────────────────────────────
# 4. BUILD TELEGRAM MESSAGE
# ─────────────────────────────────────────────
def build_message(stocks):
    date_str = datetime.now().strftime("%d %b %Y %H:%M")
    msg = f"📈 *Daily Stock Update — {date_str} IST*\n\n"
    for s in stocks:
        signal = get_signal(s)
        emoji = "🔺" if s["change"] >= 0 else "🔻"
        msg += f"*{s['name']}* ({s['symbol']})\n"
        msg += f"  💰 ₹{s['price']} {emoji} {s['change_pct']:+.2f}%\n"
        msg += f"  📊 Signal: {signal}\n\n"
    msg += "_Powered by @DAY\\_STOCKBOT 🤖_"
    return msg

# ─────────────────────────────────────────────
# 5. MAIN
# ─────────────────────────────────────────────
def main():
    os.makedirs("data", exist_ok=True)

    print("Fetching stock prices from Yahoo Finance...")
    stocks = [fetch_price(sym, name) for sym, name in STOCKS.items()]

    # Save to CSV
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "time", "symbol", "name", "price", "prev_close", "change", "change_pct"])
        if not file_exists:
            writer.writeheader()
        writer.writerows(stocks)

    # Save summary JSON
    with open(SUMMARY_FILE, "w") as f:
        json.dump({
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stocks": stocks
        }, f, indent=2)

    # Update README
    with open("README.md", "w") as f:
        f.write(f"# 📈 Daily Stock Price Tracker\n\n")
        f.write(f"Auto-updated every weekday via GitHub Actions.\n\n")
        f.write(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST\n\n")
        f.write(f"## Today's Prices & Signals\n\n")
        f.write(f"| Stock | Price | Change % | Signal |\n")
        f.write(f"|-------|-------|----------|--------|\n")
        for s in stocks:
            f.write(f"| {s['name']} | ₹{s['price']} | {s['change_pct']:+.2f}% | {get_signal(s)} |\n")

    # Send Telegram
    message = build_message(stocks)
    send_telegram(message)

    print("✅ Done!")
    for s in stocks:
        print(f"  {s['name']}: ₹{s['price']} ({s['change_pct']:+.2f}%) → {get_signal(s)}")

if __name__ == "__main__":
    main()
