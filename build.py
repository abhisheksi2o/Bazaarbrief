#!/usr/bin/env python3
"""Build the Bazaar Brief site: fetch news and quotes, run the editorial layer when
this is an edition, and write a static site into ./site for GitHub Pages.

Usage: python3 build.py --mode wire|edition|weekend [--site-url https://.../] [--out site]

  wire     hourly: refresh stories and quotes, keep existing editorial notes
  edition  weekday editorial edition: edit the feed, write the recap of the day
           (and the recap of the week on Friday evening)
  weekend  weekend edition: edit, recap of the day, recap of the week

The previous feed and the recap archive are fetched from the live site so that
notes and history survive between stateless CI runs. Without ANTHROPIC_API_KEY
the editorial steps are skipped and the run behaves like a wire refresh.
"""
import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "bazaar-brief-build", "Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print("fetch skipped:", url, repr(e))
        return None


def label_for(now_ist, mode):
    if mode == "weekend":
        return "Weekend edition"
    if mode == "wire":
        return "Hourly update"
    h = now_ist.hour + now_ist.minute / 60
    return "Morning brief" if h < 11 else ("Closing wrap" if h < 17 else "Late edition")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="wire", choices=["wire", "edition", "weekend"])
    ap.add_argument("--site-url", default=os.environ.get("SITE_URL", ""))
    ap.add_argument("--out", default="site")
    args = ap.parse_args()

    now_utc = dt.datetime.now(dt.timezone.utc)
    now_ist = now_utc.astimezone(IST)
    out = os.path.abspath(args.out)
    work = os.path.join(HERE, "out")
    prev = os.path.join(HERE, "prev")
    os.makedirs(work, exist_ok=True)
    os.makedirs(prev, exist_ok=True)

    # 1. Previous state from the live site (feed for editorial carry-over, archive for history)
    base = args.site_url.rstrip("/") + "/" if args.site_url else ""
    prev_feed = fetch_json(base + "data/feed.json?b=%d" % int(now_utc.timestamp())) if base else None
    archive = (fetch_json(base + "data/archive.json?b=%d" % int(now_utc.timestamp())) if base else None) or {"dailies": [], "weeklies": []}
    merge_arg = []
    if prev_feed:
        with open(os.path.join(prev, "feed.json"), "w") as f:
            json.dump(prev_feed, f)
        merge_arg = ["--merge", os.path.join(prev, "feed.json")]

    # 2. Wire: stories and quotes
    subprocess.run([sys.executable, os.path.join(HERE, "pipeline.py"), work] + merge_arg, check=True)
    feed = json.load(open(os.path.join(work, "feed.json"))) if merge_arg else None
    if feed is None:
        arts = json.load(open(os.path.join(work, "articles.json")))
        feed = {"updatedAt": arts["generatedAt"], "articles": arts["articles"], "count": len(arts["articles"]),
                "sessionLabel": "Hourly update", "sources": sorted({a["source"] for a in arts["articles"]})}
    markets = json.load(open(os.path.join(work, "markets.json")))
    quotes_ok = sum(1 for q in markets["quotes"] if not q.get("error"))
    if quotes_ok < 8 and prev_feed:
        print("quotes look broken (%d ok); keeping previous markets" % quotes_ok)
        markets = fetch_json(base + "data/markets.json") or markets

    label = label_for(now_ist, args.mode)
    feed["sessionLabel"] = label
    status = {"mode": args.mode, "builtAt": now_utc.isoformat().replace("+00:00", "Z"), "label": label,
              "stories": len(feed["articles"]), "edited": False, "usage": {}}

    # 3. Editorial layer
    edited = False
    if args.mode != "wire":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("ANTHROPIC_API_KEY not set: skipping the editorial layer")
        else:
            import editor
            try:
                feed, u1 = editor.edit_feed(feed, markets, label, now_ist)
                daily, u2 = editor.write_daily(feed, markets, label, now_ist)
                archive["dailies"] = [d for d in archive["dailies"] if d.get("date") != daily["date"]]
                archive["dailies"].insert(0, daily)
                archive["dailies"].sort(key=lambda d: d.get("date", ""), reverse=True)
                archive["dailies"] = archive["dailies"][:14]
                usage = {"edit": u1.output_tokens, "daily": u2.output_tokens,
                         "input": u1.input_tokens + u2.input_tokens}
                want_weekly = args.mode == "weekend" or (now_ist.weekday() == 4 and now_ist.hour >= 15)
                if want_weekly:
                    weekly, u3 = editor.write_weekly(feed, markets, archive["dailies"], now_ist)
                    archive["weeklies"] = [w for w in archive["weeklies"] if w.get("week") != weekly["week"]]
                    archive["weeklies"].insert(0, weekly)
                    archive["weeklies"].sort(key=lambda w: w.get("week", ""), reverse=True)
                    archive["weeklies"] = archive["weeklies"][:8]
                    usage["weekly"] = u3.output_tokens
                    usage["input"] += u3.input_tokens
                status["usage"] = usage
                edited = True
            except Exception as e:  # never lose the wire refresh because the editor failed
                print("editorial layer failed:", repr(e))
                status["editorError"] = repr(e)
    status["edited"] = edited
    archive["updatedAt"] = now_utc.isoformat().replace("+00:00", "Z")

    # 4. Write the site
    if os.path.isdir(out):
        shutil.rmtree(out)
    shutil.copytree(os.path.join(HERE, "web"), out)
    data = os.path.join(out, "data")
    os.makedirs(data, exist_ok=True)
    for name, doc in (("feed.json", feed), ("markets.json", markets), ("archive.json", archive), ("status.json", status)):
        with open(os.path.join(data, name), "w") as f:
            json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    print("site written to", out, "|", label, "|", len(feed["articles"]), "stories | edited:", edited,
          "| dailies:", len(archive["dailies"]), "| weeklies:", len(archive["weeklies"]))


if __name__ == "__main__":
    main()
