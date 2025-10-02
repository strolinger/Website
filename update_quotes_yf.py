#!/usr/bin/env python3
"""
update_quotes_yf.py
Creates:
  - ticker-prices.json  (for your scrolling ticker)
  - winners.json        (top + movers by %)
  - losers.json         (top - movers by %)
Usage:
  python update_quotes_yf.py "C:\\Users\\strol\\OneDrive\\Desktop\\Trading - Desktop\\00_Scripts\\Website"
"""
import sys, os, json, math
from pathlib import Path
import yfinance as yf

WEBROOT = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
BIG_CAPS = [
    "AAPL","AMD","AMZN","MSFT","META","BA","GOOGL","TSLA",
    "COST","TXN","WDAY","NFLX","NVDA","MU","INTC","DIS","BABA","IWM"
]

def save_json(obj, path):
    Path(path).write_text(json.dumps(obj, indent=2), encoding="utf-8")

def main():
    # Batch download live quote fields
    tickers = yf.Tickers(" ".join(BIG_CAPS))  # space-separated list
    data = []
    for sym in BIG_CAPS:
        info = tickers.tickers[sym].fast_info  # quick fields
        try:
            price = float(info.last_price)
            # change% from regular-session fields when available
            pct = tickers.tickers[sym].info.get("regularMarketChangePercent", None)
            if pct is None:
                # fallback: compute from previousClose
                prev = tickers.tickers[sym].info.get("previousClose", None)
                pct = ((price - prev) / prev * 100.0) if prev else 0.0
            name = tickers.tickers[sym].info.get("shortName") or tickers.tickers[sym].info.get("longName") or sym
            data.append({
                "symbol": sym,
                "name": name,
                "price": f"{price:.2f}",
                "changePct": f"{pct:+.2f}%"
            })
        except Exception:
            # skip any symbol that fails
            continue

    if not data:
        print("No quotes returned"); return

    # ticker-prices.json (kept in your preferred order)
    save_json(data, os.path.join(WEBROOT, "ticker-prices.json"))
    print("Wrote ticker-prices.json")

    # winners/losers by % change
    def pct_num(s):
        try: return float(str(s).replace("%",""))
        except: return float("nan")
    ranked = [d for d in data if not math.isnan(pct_num(d["changePct"]))]
    ranked.sort(key=lambda x: pct_num(x["changePct"]), reverse=True)

    winners = ranked[:10]
    losers  = list(reversed(ranked))[:10]
    save_json(winners, os.path.join(WEBROOT, "winners.json"))
    save_json(losers,  os.path.join(WEBROOT, "losers.json"))
    print("Wrote winners.json and losers.json")

if __name__ == "__main__":
    main()
