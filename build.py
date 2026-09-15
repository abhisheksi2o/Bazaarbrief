#!/usr/bin/env python3
"""Build the Bazaar Brief site: fetch news and quotes, run the editorial layer when
this is an edition, and write a static site into ./site for GitHub Pages.

Usage: python3 build.py --mode wire|edition|weekend [--site-url https://.../] [--out site]

  edition  the daily morning paper: stories, notes and recaps from editorial/,
           the site, and the four-page PDF
  wire     stories and quotes only (manual use)
  weekend  same as edition; kept for compatibility

The previous feed and the recap archive are fetched from the live site so that
notes and history survive between stateless CI runs.

Editorial content comes from one of two places:
  * ANTHROPIC_API_KEY set  -> editor.py calls the Claude API (pay-as-you-go)
  * otherwise              -> the editorial/ folder in this repo, which the
                              claude.ai Routines (covered by a Claude subscription)
                              push after each edition: editorial/feed.json,
                              editorial/dailies/<date>.json, editorial/weeklies/<week>.json
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


def load_repo_editorial():
    """Editorial documents pushed into the repo by the claude.ai Routines."""
    ed = os.path.join(HERE, "editorial")
    feed = None
    fp = os.path.join(ed, "feed.json")
    if os.path.exists(fp):
        try:
            feed = json.load(open(fp))
        except Exception as e:
            print("editorial/feed.json unreadable:", repr(e))
    docs = {"dailies": [], "weeklies": []}
    for kind in ("dailies", "weeklies"):
        d = os.path.join(ed, kind)
        if os.path.isdir(d):
            for name in sorted(os.listdir(d)):
                if name.endswith(".json"):
                    try:
                        docs[kind].append(json.load(open(os.path.join(d, name))))
                    except Exception as e:
                        print("skipping", name, repr(e))
    return feed, docs


def apply_repo_editorial(feed, ed_feed, now_utc):
    """Carry why/section/region from the Routine-edited feed and, if it is recent, its story order."""
    if not ed_feed or not ed_feed.get("articles"):
        return feed, False
    try:
        age_h = (now_utc - dt.datetime.fromisoformat(ed_feed["updatedAt"].replace("Z", "+00:00"))).total_seconds() / 3600
    except Exception:
        age_h = 999
    if age_h > 36:
        return feed, False
    ed = {a["id"]: a for a in ed_feed["articles"]}
    hits = 0
    for a in feed["articles"]:
        o = ed.get(a["id"])
        if o:
            hits += 1
            for k in ("why", "section", "region"):
                if o.get(k):
                    a[k] = o[k]
    if age_h <= 12:  # a fresh edition: keep the editor's order for the top of the page
        order = {a["id"]: i for i, a in enumerate(ed_feed["articles"][:40])}
        feed["articles"].sort(key=lambda a: (order.get(a["id"], 10 ** 6), -a.get("score", 0)))
        feed["sessionLabel"] = ed_feed.get("sessionLabel") or feed["sessionLabel"]
    print("repo editorial: notes carried for %d stories (edition %.1fh old)" % (hits, age_h))
    return feed, hits > 0


def merge_docs(existing, incoming, key):
    by = {d.get(key): d for d in existing if d.get(key)}
    for d in incoming:
        k = d.get(key)
        if not k:
            continue
        cur = by.get(k)
        if cur is None or (d.get("updatedAt", "") >= cur.get("updatedAt", "")):
            by[k] = d
    return sorted(by.values(), key=lambda d: d.get(key, ""), reverse=True)


def label_for(now_ist, mode):
    if mode == "weekend":
        return "Weekend edition"
    if mode == "wire":
        return "Wire update"
    return "Morning paper"


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

    # 3. Editorial layer: repo files pushed by the claude.ai Routines (always), then the API when a key exists
    edited = False
    ed_feed, ed_docs = load_repo_editorial()
    feed, from_repo = apply_repo_editorial(feed, ed_feed, now_utc)
    archive["dailies"] = merge_docs(archive["dailies"], ed_docs["dailies"], "date")[:14]
    archive["weeklies"] = merge_docs(archive["weeklies"], ed_docs["weeklies"], "week")[:8]
    if from_repo:
        status["editorial"] = "routines"
    if args.mode != "wire":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("ANTHROPIC_API_KEY not set: using the editorial/ folder only")
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

    # 5. The four-page paper (PDF + HTML). A paper failure must not take the site down.
    try:
        import paper
        idx = paper.build(feed, markets, archive, os.path.join(out, "paper"), site_url=args.site_url, now=now_utc)
        status["paper"] = idx.get("latest")
        with open(os.path.join(data, "status.json"), "w") as f:
            json.dump(status, f, ensure_ascii=False, separators=(",", ":"))
    except Exception as e:
        print("paper build failed:", repr(e))


if __name__ == "__main__":
    main()
