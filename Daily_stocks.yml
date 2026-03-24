name: 📈 Daily Stock Price Logger

on:
  schedule:
    - cron: '30 4 * * 1-5'  # Runs Mon-Fri at 10:00 AM IST (4:30 UTC)
  workflow_dispatch:          # Allows manual trigger from GitHub UI

jobs:
  fetch-and-commit:
    runs-on: ubuntu-latest

    steps:
      - name: ⬇️ Checkout repository
        uses: actions/checkout@v3

      - name: 🐍 Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: 📦 Install dependencies
        run: pip install requests

      - name: 📊 Fetch stock prices
        env:
          ALPHA_VANTAGE_KEY: ${{ secrets.ALPHA_VANTAGE_KEY }}
        run: python fetch_stocks.py

      - name: ✅ Commit and push changes
        run: |
          git config --global user.name "stock-bot"
          git config --global user.email "stock-bot@github.com"
          git add .
          git diff --staged --quiet || git commit -m "📈 Stock update: $(date +'%Y-%m-%d')"
          git push