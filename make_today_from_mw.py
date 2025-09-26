#!/usr/bin/env python3
"""
make_today_from_mw.py  -> creates today.json from calendar-week.json

- Looks in the same folder for calendar-week.json
- Picks items matching today's weekday or date
- Heuristically classifies Fed speakers vs economic reports
Usage:
  python make_today_from_mw.py "C:\\path\\to\\Website"
"""
import sys, os, json, re, datetime
from pathlib import Path

WEBROOT = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
src = Path(WEBROOT) / "calendar-week.json"
dst = Path(WEBROOT) / "today.json"

def is_today(date_str):
    """
    Matches common MW formats like 'Mon', 'Tue', or 'Wed, Sep 25', or 'Sep 25, 2025'.
    Falls back to partial match.
    """
    if not date_str:
        return False
    today = datetime.datetime.now()
    wd = today.strftime("%a")       # Mon
    m_d = today.strftime("%b %-d") if os.name != "nt" else today.strftime("%b %#d")  # Sep 5  (Windows needs %#d)
    m_d_y = today.strftime("%b %d, %Y")
    # tolerant checks:
    date_str_n = date_str.strip()
    return (
        wd.lower() in date_str_n.lower() or
        m_d.lower() in date_str_n.lower() or
        m_d_y.lower() in date_str_n.lower()
    )

SPEAKER_RE = re.compile(r"(fed|federal|fomc|chair|governor|president|speaks|remarks|fireside|panel)", re.I)

def classify(item):
    text = " ".join([item.get("event",""), item.get("notes","") or ""])
    if SPEAKER_RE.search(text):
        # try to extract a name before 'speaks/remarks'
        name = re.split(r"\b(speaks|remarks|fireside|panel)\b", text, flags=re.I)[0].strip(" ,–-")
        if not name or len(name) > 120:
            name = "Fed speaker"
        return "speaker", {
            "time": item.get("time",""),
            "name": name,
            "topic": item.get("event","")
        }
    else:
        return "report", {
            "time": item.get("time",""),
            "event": item.get("event","")
        }

def main():
    if not src.exists():
        print("calendar-week.json not found:", src)
        return
    week = json.loads(src.read_text(encoding="utf-8"))
    reports, speakers = [], []
    for it in week:
        if is_today(it.get("date","")):
            kind, payload = classify(it)
            if kind == "speaker":
                speakers.append(payload)
            else:
                reports.append(payload)
    # sort by time if available (keeps blanks last)
    def key_time(x): return (x.get("time") is None, x.get("time",""))
    reports.sort(key=key_time)
    speakers.sort(key=key_time)

    out = {"reports": reports, "speakers": speakers}
    dst.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("Wrote", dst, f"(reports={len(reports)}, speakers={len(speakers)})")

if __name__ == "__main__":
    main()
