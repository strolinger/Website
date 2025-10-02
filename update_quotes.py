#!/usr/bin/env python3
# Lightweight intraday quotes updater for ticker-prices.json
import json, time, os
from pathlib import Path
import yfinance as yf

WEBROOT = r"C:\Users\strol\OneDrive\Desktop\Trading - Desktop\00_Scripts\Website"
TICKERS = ["AAPL","AMD","AMZN","MSFT","META","BA","GOOGL","TSLA","COST","TXN",
           "WDAY","NFLX","NVDA","MU","INTC","DIS","BABA","IWM"]

def save_json(obj, path):
    Path(path).write_text(json.dumps(obj, indent=2), encoding="utf-8")

def main():
    out = []
    bundle = yf.Tickers(" ".join(TICKERS))
    for sym in TICKERS:
        try:
            t = bundle.tickers[sym]
            price = None
            try:
                price = float(getattr(t, "fast_info", {}).get("last_price"))
            except Exception:
                pass
            if price is None:
                price = float(t.info.get("regularMarketPrice"))
            pct = t.info.get("regularMarketChangePercent")
            if pct is None:
                prev = t.info.get("previousClose")
                pct = ((price - prev)/prev*100.0) if prev else 0.0
            out.append({"symbol": sym,
                        "price": f"{price:.2f}",
                        "changePct": f"{pct:+.2f}%"})
        except Exception as e:
            # keep going even if one fails
            print("quote fail", sym, e)
    if out:
        save_json(out, os.path.join(WEBROOT, "ticker-prices.json"))
        print("updated ticker-prices.json", time.strftime("%H:%M:%S"))

if __name__ == "__main__":
    main()
