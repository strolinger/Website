#!/usr/bin/env python3
# scripts/make_ticker_json.py
import json, time
from datetime import datetime, timezone
import yfinance as yf

# Big caps you want on the ticker:
SYMBOLS = [
    "AAPL","AMD","AMZN","MSFT","META","BA","GOOGL","TSLA","COST","TXN","WDAY",
    "NFLX","NVDA","MU","INTC","DIS","BABA","IWM","SPY","QQQ"
]

def to_float(x, default=None):
    try:
        return float(x)
    except Exception:
        return default

def main(out_path):
    # yfinance lets us fetch many symbols in one call
    tickers = yf.Tickers(" ".join(SYMBOLS))
    out = []
    for sym in SYMBOLS:
        t = tickers.tickers[sym]
        # fast_info is quick & avoids huge payloads
        fi = getattr(t, "fast_info", {}) or {}
        price = to_float(fi.get("last_price"))
        prev  = to_float(fi.get("previous_close"))
        vol   = to_float(fi.get("last_volume"), 0)

        # Fallback if fast_info is missing something
        if price is None or prev is None:
            try:
                hist = t.history(period="2d", interval="1d")
                if not hist.empty:
                    price = to_float(hist["Close"].iloc[-1])
                    prev  = to_float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
            except Exception:
                pass

        if price is None or prev is None:
            # still nothing—skip this symbol gracefully
            continue

        chg_pct = (price - prev) / prev * 100 if prev else 0.0

        out.append({
            "symbol": sym,
            "price": round(price, 2),
            "changePct": round(chg_pct, 2),
            "volume": int(vol) if vol is not None else None,
        })

    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "data": out
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    # default output for GitHub Pages built from /docs:
    main("docs/ticker-prices.json")
