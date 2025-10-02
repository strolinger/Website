#!/usr/bin/env python3
# scripts/make_ticker_json.py
import json, os, sys, time
from datetime import datetime, timezone
import requests

SYMS = ["AAPL","AMD","AMZN","BA","BABA","COST","DIS","GOOGL","INTC",
        "IWM","META","MSFT","MU","NFLX","NVDA","TSLA","TXN","WDAY"]

URL = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=" + ",".join(SYMS)
HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_quotes():
    r = requests.get(URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    j = r.json()
    return j.get("quoteResponse", {}).get("result", [])

def to_json_rows(quotes):
    out = []
    for q in quotes:
        sym  = (q.get("symbol") or "").upper()
        px   = q.get("regularMarketPrice")
        chgP = q.get("regularMarketChangePercent")  # number
        # Format percent with sign and % (your UI likes +x.xx% / -x.xx%)
        pct_str = ""
        if chgP is not None:
            chgP = round(float(chgP), 2)
            pct_str = f"{'+' if chgP >= 0 else ''}{chgP:.2f}%"
        out.append({
            "symbol": sym,
            "price":  round(px, 2) if isinstance(px, (int, float)) else "",
            "changePct": pct_str
        })
    # stable order matching your UI carousel
    sym_index = {s:i for i,s in enumerate(SYMS)}
    out.sort(key=lambda r: sym_index.get(r["symbol"], 1e9))
    return out

def main():
    print("Fetching quotes…", file=sys.stderr)
    quotes = fetch_quotes()
    rows   = to_json_rows(quotes)

    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z"),
        "data": rows
    }

    # write to docs/
    os.makedirs("docs", exist_ok=True)
    out_path = os.path.join("docs", "ticker-prices.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload["data"], f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_path} with {len(rows)} rows.", file=sys.stderr)

if __name__ == "__main__":
    main()
