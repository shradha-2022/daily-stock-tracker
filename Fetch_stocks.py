import requests
import json
import csv
import os
from datetime import datetime, timedelta

# ✅ Stocks to track
STOCKS = ["RELIANCE.BSE", "TCS.BSE", "INFY.BSE", "WIPRO.BSE", "HDFCBANK.BSE"]

# API Keys from GitHub Secrets
ALPHA_VANTAGE_KEY = os.environ.get("ALPHA_VANTAGE_KEY", "demo")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

LOG_FILE = "data/stock_log.csv"
SUMMARY_FILE = "data/latest_summary.json"
WEEKLY_FILE = "data/weekly_report.json"

# ─────────────────────────────────────────────
# 1. FETCH STOCK PRICE
# ─────────────────────────────────────────────
def fetch_price(symbol):
    ticker = symbol.split(".")[0]
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHA_VANTAGE_KEY}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        quote = data.get("Global Quote", {})
        price = float(quote.get("05. price", 0))
        prev_close = float(quote.get("08. previous close", 0))
        change = float(quote.get("09. change", 0))
        change_pct = quote.get("10. change percent", "0%").replace("%", "")
        return {
            "symbol": symbol,
            "price": price,
            "prev_close": prev_close,
            "change": change,
            "change_pct": float(change_pct),
            "volume": quote.get("06. volume", "N/A"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S")
        }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return {
            "symbol": symbol, "price": 0, "prev_close": 0,
            "change": 0, "change_pct": 0, "volume": "N/A",
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
# 3. AI PRICE SUMMARY (OpenAI)
# ─────────────────────────────────────────────
def get_ai_summary(stocks):
    if not OPENAI_API_KEY:
        return "AI summary unavailable (no API key)."
    
    stock_info = "\n".join([
        f"{s['symbol']}: ₹{s['price']} ({s['change_pct']:+.2f}%)"
        for s in stocks
    ])
    
    prompt = f"""You are a stock market analyst. Here are today's Indian stock prices:

{stock_info}

Give a brief 3-4 line daily summary analyzing overall market sentiment, 
highlight the best and worst performer, and give a simple outlook. 
Keep it simple and friendly for a retail investor."""

    try:
        res = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200
            },
            timeout=15
        )
        return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"AI summary error: {e}"

# ─────────────────────────────────────────────
# 4. WEEKLY REPORT
# ─────────────────────────────────────────────
def generate_weekly_report(stocks):
    today = datetime.now()
    is_friday = today.weekday() == 4  # 0=Mon, 4=Fri

    if not is_friday:
        return None

    # Load historical data
    if not os.path.exists(LOG_FILE):
        return None

    weekly_data = {}
    with open(LOG_FILE, "r") as f:
        reader = csv.DictReader(f)
        week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        for row in reader:
            if row["date"] >= week_ago:
                sym = row["symbol"]
                if sym not in weekly_data:
                    weekly_data[sym] = []
                weekly_data[sym].append(float(row["price"]) if row["price"] else 0)

    report = {}
    for sym, prices in weekly_data.items():
        if len(prices) >= 2:
            weekly_change = ((prices[-1] - prices[0]) / prices[0]) * 100
            report[sym] = {
                "start_price": prices[0],
                "end_price": prices[-1],
                "weekly_change_pct": round(weekly_change, 2),
                "high": max(prices),
                "low": min(prices)
            }

    with open(WEEKLY_FILE, "w") as f:
        json.dump({"week_ending": today.strftime("%Y-%m-%d"), "report": report}, f, indent=2)

    return report

# ─────────────────────────────────────────────
# 5. SEND TELEGRAM MESSAGE
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
# 6. BUILD TELEGRAM MESSAGE
# ─────────────────────────────────────────────
def build_daily_message(stocks, ai_summary, weekly_report=None):
    date_str = datetime.now().strftime("%d %b %Y")
    msg = f"📈 *Daily Stock Update — {date_str}*\n\n"

    for s in stocks:
        signal = get_signal(s)
        emoji = "🔺" if s["change"] >= 0 else "🔻"
        msg += f"*{s['symbol']}*\n"
        msg += f"  Price: ₹{s['price']:.2f} {emoji} {s['change_pct']:+.2f}%\n"
        msg += f"  Signal: {signal}\n\n"

    msg += f"🤖 *AI Summary:*\n{ai_summary}\n"

    if weekly_report:
        msg += "\n📊 *Weekly Report (Friday Summary):*\n"
        for sym, data in weekly_report.items():
            emoji = "🟢" if data["weekly_change_pct"] >= 0 else "🔴"
            msg += f"{emoji} {sym}: {data['weekly_change_pct']:+.2f}% this week\n"

    return msg

# ─────────────────────────────────────────────
# 7. MAIN
# ─────────────────────────────────────────────
def main():
    os.makedirs("data", exist_ok=True)

    print("Fetching stock prices...")
    stocks = [fetch_price(s) for s in STOCKS]

    # Save to CSV
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "time", "symbol", "price", "prev_close", "change", "change_pct", "volume"])
        if not file_exists:
            writer.writeheader()
        writer.writerows(stocks)

    # AI Summary
    print("Getting AI summary...")
    ai_summary = get_ai_summary(stocks)

    # Weekly Report (Fridays only)
    weekly_report = generate_weekly_report(stocks)

    # Save summary JSON
    with open(SUMMARY_FILE, "w") as f:
        json.dump({
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stocks": stocks,
            "ai_summary": ai_summary
        }, f, indent=2, default=str)

    # Update README
    with open("README.md", "w") as f:
        f.write(f"# 📈 Daily Stock Price Tracker\n\n")
        f.write(f"Auto-updated every weekday via GitHub Actions + AI Analysis.\n\n")
        f.write(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST\n\n")
        f.write(f"## Today's Prices & Signals\n\n")
        f.write(f"| Symbol | Price | Change % | Signal |\n")
        f.write(f"|--------|-------|----------|--------|\n")
        for s in stocks:
            f.write(f"| {s['symbol']} | ₹{s['price']} | {s['change_pct']:+.2f}% | {get_signal(s)} |\n")
        f.write(f"\n## 🤖 AI Summary\n\n{ai_summary}\n")
        f.write(f"\n## 📊 Historical data → `data/stock_log.csv`\n")

    # Send Telegram
    print("Sending Telegram notification...")
    message = build_daily_message(stocks, ai_summary, weekly_report)
    send_telegram(message)

    print("✅ All done!")
    for s in stocks:
        print(f"  {s['symbol']}: ₹{s['price']} ({s['change_pct']:+.2f}%) → {get_signal(s)}")

if __name__ == "__main__":
    main()
