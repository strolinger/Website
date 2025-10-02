#!/usr/bin/env python3
"""
update_dashboard.py — generates dashboard data & snapshots
(Updated: writes calendar-today.json with Time/Release/Period/Actual/Forecast(Median)/Previous)

Usage:
  python update_dashboard.py "C:\\Users\\strol\\OneDrive\\Desktop\\Trading - Desktop\\00_Scripts\\Website"
"""

import os, sys, json, time, math, re, datetime
from pathlib import Path

import requests
import feedparser
from bs4 import BeautifulSoup
import yfinance as yf
from playwright.sync_api import sync_playwright

# ---------------- CONFIG ----------------
DEFAULT_WEBROOT = os.getcwd()
TICKERS = [
    "AAPL","AMD","AMZN","MSFT","META","BA","GOOGL","TSLA",
    "COST","TXN","WDAY","NFLX","NVDA","MU","INTC","DIS","BABA","IWM"
]
YAHOO_RSS_TEMPLATE = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
MARKETWATCH_CAL_URL = "https://www.marketwatch.com/economy-politics/calendar"
FEAR_GREED_URL = "https://money.cnn.com/data/fear-and-greed/"
HEATMAP_URL    = "https://finviz.com/map.ashx"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
# ---------------------------------------

def ensure_dir(p): Path(p).mkdir(parents=True, exist_ok=True)
def save_json(obj, path): Path(path).write_text(json.dumps(obj, indent=2), encoding="utf-8")

# ---------- NEWS ----------
def fetch_rss_top3(session, ticker):
    url = YAHOO_RSS_TEMPLATE.format(ticker=ticker)
    r = session.get(url, timeout=20, headers={"User-Agent":"market-dashboard/1.0"})
    r.raise_for_status()
    parsed = feedparser.parse(r.content)
    items = []
    for e in parsed.get("entries", [])[:3]:
        items.append({
            "title": (e.get("title") or "").strip(),
            "link": e.get("link") or e.get("id") or "",
            "published": e.get("published","") or e.get("updated","")
        })
    return items

def write_all_news(webroot, tickers):
    s = requests.Session()
    for t in tickers:
        try:
            items = fetch_rss_top3(s, t)
            save_json(items, Path(webroot)/f"news-{t.lower()}.json")
            time.sleep(0.2)
        except Exception as e:
            print("NEWS fail", t, e)

# ---------- QUOTES ----------
def write_quotes_and_movers(webroot, tickers):
    data = []
    bundle = yf.Tickers(" ".join(tickers))
    for sym in tickers:
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
            name = t.info.get("shortName") or t.info.get("longName") or sym
            data.append({"symbol":sym,"name":name,"price":f"{price:.2f}","changePct":f"{pct:+.2f}%"})
        except Exception as e:
            print("Quote fail", sym, e)
    if data:
        save_json(data, Path(webroot)/"ticker-prices.json")
        data2 = sorted(data, key=lambda x: float(str(x["changePct"]).replace("%","")), reverse=True)
        save_json(data2[:10], Path(webroot)/"winners.json")
        save_json(list(reversed(data2))[:10], Path(webroot)/"losers.json")
        print("Wrote prices + winners/losers")

# ---------- MARKETWATCH (weekly + today structured) ----------
def fetch_marketwatch_html_requests():
    import requests
    s = requests.Session()
    r = s.get(MARKETWATCH_CAL_URL, timeout=30, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache", "Pragma": "no-cache",
        "Referer": "https://www.marketwatch.com/",
    })
    r.raise_for_status()
    return r.text

def fetch_marketwatch_html_playwright():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width":1400,"height":1000}, user_agent=UA)
        page = ctx.new_page()
        page.goto(MARKETWATCH_CAL_URL, wait_until="domcontentloaded", timeout=60000)
        for sel in ["button:has-text('Accept')","button:has-text('I Accept')",
                    "text=/^Agree$/i","text=/Accept All/i","[aria-label*='accept']"]:
            try:
                if page.locator(sel).count(): page.locator(sel).first.click(timeout=1500); break
            except: pass
        try: page.wait_for_selector("table", timeout=15000)
        except: pass
        page.wait_for_timeout(1200)
        html = page.content()
        ctx.close(); browser.close()
        return html

def fetch_marketwatch_html():
    try:
        return fetch_marketwatch_html_requests()
    except Exception as e:
        print("MarketWatch requests() failed — falling back to Playwright:", e)
        return fetch_marketwatch_html_playwright()

def parse_weekly_table(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    events = []
    table = soup.find("table")
    if not table: return events
    for tr in table.find_all("tr"):
        cols = [td.get_text(strip=True) for td in tr.find_all(["td","th"])]
        if cols: events.append(cols)
    return events

def extract_today_rows(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    import re, datetime
    now = datetime.datetime.now()
    dow = now.strftime("%A").upper()
    mon = now.strftime("%b").upper().rstrip('.')
    day = str(int(now.strftime("%d")))
    header_re = re.compile(rf"{dow}.*{mon}.*{day}\b")

    header = None
    for t in soup.find_all(string=header_re):
        header = t.parent; break

    def is_day_header(el):
        txt = el.get_text(" ", strip=True).upper()
        return bool(re.search(r"(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)", txt))

    rows = []
    if header:
        ptr = header
        while ptr:
            ptr = ptr.find_next(["tr","h2","h3","div"])
            if not ptr: break
            if is_day_header(ptr) and ptr is not header: break
            if ptr.name == "tr":
                tds = [td.get_text(" ", strip=True) for td in ptr.find_all("td")]
                if len(tds) >= 2: rows.append(tds)

    if not rows:  # fallback: scan first table, keep time-looking rows
        for cols in parse_weekly_table(html):
            if cols and re.search(r"\b(am|pm)\b", cols[0], re.I):
                rows.append(cols)

    out = []
    for cols in rows:
        c = cols + [""] * (6 - len(cols))
        rec = {"time":c[0], "release":c[1], "period":c[2], "actual":c[3], "median":c[4], "previous":c[5]}
        if len(cols)==4 and rec["actual"] and not rec["median"] and not rec["previous"]:
            rec["previous"]=c[3]; rec["actual"]=c[2]; rec["period"]=""; rec["median"]=""
        out.append(rec)
    return out

def write_calendar_files(webroot):
    html = fetch_marketwatch_html()   # <-- this exact function name
    weekly_rows = parse_weekly_table(html)
    if weekly_rows:
        save_json([{"row": r} for r in weekly_rows[:400]], Path(webroot)/"calendar-week.json")
        print("Saved calendar-week.json (raw rows)")
    today_rows = extract_today_rows(html)
    save_json(today_rows, Path(webroot)/"calendar-today.json")
    print(f"Saved calendar-today.json ({len(today_rows)} rows)")


# ---------- SCREENSHOTS ----------
def capture_screenshots(webroot, headless=True):
    fg_path = Path(webroot) / "fear-greed-snapshot.png"
    hm_path = Path(webroot) / "heatmap-snapshot.png"

    def click_if_exists(page, locator, timeout=3000):
        try:
            el = page.locator(locator)
            if el.count() and el.first.is_visible():
                el.first.click(timeout=timeout)
                return True
        except Exception:
            pass
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": 1400, "height": 900}, user_agent=UA)
        page = context.new_page()

        # Heatmap
        try:
            page.goto(HEATMAP_URL, wait_until="domcontentloaded", timeout=45000)
            click_if_exists(page, "text=I agree")
            click_if_exists(page, "button:has-text('Accept')")
            page.wait_for_timeout(800)
            if page.locator("#map").count():
                page.locator("#map").screenshot(path=str(hm_path))
            else:
                page.screenshot(path=str(hm_path), full_page=False)
            print("Saved", hm_path)
        except Exception as e:
            print("Heatmap snapshot fail:", e)

        # Fear & Greed (we only link to it now, but keep snapshot for flexibility)
        try:
            page.goto(FEAR_GREED_URL, wait_until="domcontentloaded", timeout=45000)
            page.evaluate("document.body.style.zoom='1.5'")
            click_if_exists(page, "button:has-text('Agree')")
            page.wait_for_timeout(600)
            page.screenshot(path=str(fg_path), full_page=False)
            print("Saved", fg_path)
        except Exception as e:
            print("Fear&Greed snapshot fail:", e)

        context.close(); browser.close()

# ---------- MAIN ----------
def main():
    webroot = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_WEBROOT)
    ensure_dir(webroot)
    print("Writing to webroot:", webroot)

    write_quotes_and_movers(webroot, TICKERS)
    write_calendar_files(webroot)          # <-- writes calendar-today.json
    capture_screenshots(webroot, headless=True)
    write_all_news(webroot, TICKERS)

    print("update_dashboard.py finished.")

if __name__ == "__main__":
    main()
