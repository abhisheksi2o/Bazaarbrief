#!/usr/bin/env python3
"""Bazaar Brief - the no-cost desk.

A rule-based editorial layer that runs entirely inside GitHub Actions: no Claude
API, no claude.ai Routine, no tokens. It does what the human/AI desk does, with
rules instead of judgement:

  edit_feed()    drop junk, tidy sections, put the stories in reading order
                 (market wrap, macro drivers, policy, corporate, global);
                 keeps every "why it matters" note it is given
  write_daily()  the recap of the day, built from the day's quotes and the
                 top stories in each group
  write_weekly() the recap of the week, from the 5-day moves and the week's
                 daily recaps

Every sentence is assembled from numbers in markets.json and headlines from
the fetched stories; nothing is invented.
"""
import datetime as dt
import re

SECTIONS = ["stocks", "global-markets", "economy", "inflation", "central-banks", "bonds", "fx-commodities",
            "corporate", "policy", "geopolitics", "banking", "crypto"]

# Reading order for the top of the paper. Lower number = earlier.
WRAP_RE = re.compile(r"^(sensex|nifty|stock market (today|highlights|live|prediction|outlook)|market (wrap|pulse|highlights|outlook)|"
                     r"ahead of market|taking stock|d-street|dalal street|closing bell|opening bell|gift nifty)", re.I)
MACRO_RE = re.compile(r"\b(rbi|reserve bank|repo rate|rate (hike|cut)|monetary policy|inflation|cpi|wpi|gdp|fed\b|federal reserve|"
                      r"fomc|ecb|bank of japan|boj|bank of england|rupee|brent|crude|oil price|bond yield|10-year|treasury|"
                      r"tariff|trade deal|trade war)\b", re.I)
POLICY_RE = re.compile(r"\b(sebi|government|ministry|cabinet|budget|gst|finance minister|sitharaman|parliament|policy|"
                       r"regulator|supreme court|customs|export|import)\b", re.I)
GROUP_RANK = {"wrap": 0, "macro": 1, "policy": 2, "corporate": 3, "global": 4, "other": 5}

EXTRA_JUNK = re.compile(r"(earnings call transcript|q[1-4] \d{4} earnings call|conference call transcript|"
                        r"share price target|stock split|bonus issue record date|dividend stocks?|"
                        r"how to (buy|sell|open|apply|check|save|get)|step[- ]by[- ]step|"
                        r"mutual fund(s)? to (buy|invest)|best (mutual|equity|debt) funds?|top funds|"
                        r"personal finance|money tips|loan emi|home loan rates?|credit score|"
                        r"sponsored|advertorial|promoted|partner content)", re.I)


def _group(a):
    t = a.get("title", "")
    if WRAP_RE.search(t.strip()):
        return "wrap"
    if a.get("section") in ("central-banks", "inflation", "bonds", "fx-commodities") or MACRO_RE.search(t):
        return "macro"
    if a.get("section") == "policy" or POLICY_RE.search(t):
        return "policy"
    if a.get("section") in ("corporate", "banking"):
        return "corporate"
    if a.get("region") == "world" or a.get("section") in ("global-markets", "geopolitics"):
        return "global"
    return "other"


def edit_feed(feed, markets, label, ist_now):
    """Return a new feed dict: junk dropped, top 30 in desk order, the rest in pipeline order."""
    arts = [a for a in feed["articles"] if not EXTRA_JUNK.search(a.get("title", "") + " " + (a.get("summary") or "")[:160])]
    top = arts[:45]
    rest = arts[45:]
    # India first inside each group, then the pipeline's score
    top.sort(key=lambda a: (GROUP_RANK[_group(a)], 0 if a.get("region") == "india" else 1, -a.get("score", 0)))
    # The lead must be the market wrap when there is one; keep at most two wraps at the top
    wraps = [a for a in top if _group(a) == "wrap"]
    if len(wraps) > 2:
        extra = wraps[2:]
        top = [a for a in top if a not in extra] + extra
    out = dict(feed)
    out["articles"] = top + rest
    out["count"] = len(out["articles"])
    out["sessionLabel"] = label
    out["sources"] = sorted({a["source"] for a in out["articles"]})
    out["editedAt"] = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    out["desk"] = "rules"
    return out


# ------------------------------------------------------------------ recaps

def _q(markets):
    return {x["symbol"]: x for x in markets.get("quotes", []) if not x.get("error") and x.get("price") is not None}


def _fmt(v):
    return ("{:,.2f}".format(v)) if abs(v) < 1000 else ("{:,.0f}".format(v))


def _dir(p, up="rose", down="fell", flat="was little changed"):
    if p is None:
        return flat
    if p > 0.05:
        return up
    if p < -0.05:
        return down
    return flat


def _move(x, week=False):
    """'rose 0.8% to 24,120' or 'fell 12 bp to 4.96%'."""
    if x.get("kind") == "yield":
        bp = (x.get("weekPct") or 0) if week else (x.get("change") or 0) * 100
        if week:
            return "%s %.1f%% over the week to %.2f%%" % (_dir(bp), abs(bp), x["price"])
        return "%s %.0f bp to %.2f%%" % (_dir(bp), abs(bp), x["price"])
    p = x.get("weekPct") if week else x.get("changePct")
    if p is None:
        return "was at %s" % _fmt(x["price"])
    return "%s %.2f%% to %s" % (_dir(p), abs(p), _fmt(x["price"]))


def scoreboard(markets, week=False):
    q = _q(markets)
    out = []
    for sym, label in (("^NSEI", "Nifty 50"), ("^BSESN", "Sensex"), ("INR=X", "USD/INR"), ("BZ=F", "Brent $"), ("GC=F", "Gold $")):
        x = q.get(sym)
        if x:
            val = "{:,.2f}".format(x["price"]) if sym != "GC=F" else "{:,.0f}".format(x["price"])
            if sym in ("BZ=F", "GC=F"):
                val = "$" + val
            out.append({"label": label, "value": val, "changePct": round((x.get("weekPct") if week else x.get("changePct")) or 0, 2)})
    if week:
        x = q.get("^GSPC")
        if x:
            out.append({"label": "S&P 500", "value": "{:,.2f}".format(x["price"]), "changePct": round(x.get("weekPct") or 0, 2)})
    else:
        x = q.get("^TNX")
        if x:
            out.append({"label": "US 10Y", "value": "%.2f%%" % x["price"], "change": "%+.0f bp" % ((x.get("change") or 0) * 100),
                        "changePct": None})
    return out


def _headline(a, n=150):
    t = re.sub(r"\s+", " ", a.get("title", "")).strip().rstrip(".")
    t = re.sub(r"\s*[|:]\s*(live updates?|highlights?)\s*.*$", "", t, flags=re.I)
    if len(t) > n:
        t = t[:n].rsplit(" ", 1)[0] + "…"
    return t


def _item(a):
    return {"text": "%s (%s)." % (_headline(a), a.get("source", "")), "ids": [a["id"]]}


def _pick(arts, pred, n, used):
    out = []
    for a in arts:
        if a["id"] in used:
            continue
        if pred(a):
            out.append(a)
            used.add(a["id"])
            if len(out) >= n:
                break
    return out


def _market_sentences(markets, week=False):
    q = _q(markets)
    s = []
    n, b = q.get("^NSEI"), q.get("^BSESN")
    if n and b:
        s.append("The Nifty 50 %s and the Sensex %s%s." % (_move(n, week), _move(b, week), " over the week" if week else ""))
    elif n:
        s.append("The Nifty 50 %s." % _move(n, week))
    parts = []
    r = q.get("INR=X")
    if r:
        parts.append("the rupee %s per dollar" % _move(r, week).replace("rose", "weakened").replace("fell", "strengthened"))
    o = q.get("BZ=F")
    if o:
        parts.append("Brent crude %s a barrel" % _move(o, week).replace(" to ", " to $"))
    g = q.get("GC=F")
    if g:
        parts.append("gold %s an ounce" % _move(g, week).replace(" to ", " to $"))
    if parts:
        line = ", ".join(parts[:-1]) + (" and " if len(parts) > 1 else "") + parts[-1]
        s.append(line[0].upper() + line[1:] + ".")
    y = q.get("^TNX")
    sp = q.get("^GSPC")
    if y or sp:
        w = []
        if sp:
            w.append("the S&P 500 %s" % _move(sp, week))
        if y:
            w.append("the US 10-year yield %s" % _move(y, week))
        s.append(("On Wall Street " + " and ".join(w) + ".").replace("On Wall Street the", "On Wall Street, the"))
    return s


def _title(markets, arts, week=False):
    q = _q(markets)
    n = q.get("^NSEI")
    lead = next((a for a in arts if _group(a) != "wrap"), arts[0] if arts else None)
    if n and n.get("weekPct" if week else "changePct") is not None:
        p = n["weekPct"] if week else n["changePct"]
        verb = "gains" if p > 0.05 else "falls" if p < -0.05 else "holds"
        head = "Nifty %s %.1f%% %s %s" % (verb, abs(p), "over the week" if week else "at", "" if week else _fmt(n["price"]))
        head = head.replace("holds  at", "holds at").strip()
        if lead:
            return "%s. %s" % (head, _headline(lead, 90))
        return head
    return _headline(lead, 120) if lead else "The day in brief"


def _watch(arts, ist_now, week=False):
    """What to watch: stories that talk about something upcoming, then the standing calendar."""
    ahead = re.compile(r"\b(ahead of|next week|this week|on (monday|tuesday|wednesday|thursday|friday)|due (on|this|next)|"
                       r"to (announce|decide|meet|release|report)|meeting|decision|expected to|set to|will)\b", re.I)
    out, seen = [], set()
    for a in arts[:60]:
        t = a.get("title", "")
        if ahead.search(t) and a["id"] not in seen:
            seen.add(a["id"])
            out.append(_headline(a, 120) + ".")
        if len(out) >= 3:
            break
    d = ist_now.date()
    cal = []
    if week:
        cal.append("Next week's data and results calendar; the RBI's next policy meeting and the Fed's schedule.")
    if d.day < 12:
        cal.append("India CPI inflation and IIP for the previous month, due around the 12th.")
    elif d.day < 14:
        cal.append("India WPI inflation for the previous month, due around the 14th.")
    if d.day >= 25 or d.day <= 3:
        cal.append("Monthly auto sales, GST collections and the manufacturing PMI at the turn of the month.")
    cal.append("The Nifty 50 against its recent range, the rupee and Brent crude at the open.")
    for c in cal:
        if len(out) >= 4:
            break
        out.append(c)
    return out[:4]


def write_daily(feed, markets, label, ist_now):
    arts = feed["articles"]
    used = set()
    mkt = _pick(arts, lambda a: a.get("section") in ("stocks", "bonds", "fx-commodities", "crypto") or _group(a) == "wrap", 3, used)
    pol = _pick(arts, lambda a: a.get("section") in ("central-banks", "policy", "inflation", "economy", "banking") and a.get("region") == "india", 4, used)
    wld = _pick(arts, lambda a: a.get("region") == "world" or a.get("section") in ("global-markets", "geopolitics"), 4, used)
    if len(pol) < 3:
        pol += _pick(arts, lambda a: a.get("region") == "india", 3 - len(pol), used)
    if len(wld) < 3:
        wld += _pick(arts, lambda a: True, 3 - len(wld), used)
    ms = _market_sentences(markets)
    market_items = [{"text": s, "ids": []} for s in ms] + [_item(a) for a in mkt]
    groups = [{"label": "Markets", "items": market_items[:5]},
              {"label": "RBI, SEBI and policy", "items": [_item(a) for a in pol][:5]},
              {"label": "World", "items": [_item(a) for a in wld][:5]}]
    stand = " ".join(ms[:2])
    lead = arts[0] if arts else None
    if lead:
        stand += " Top of the paper: %s (%s)." % (_headline(lead, 140), lead.get("source", ""))
    return {
        "date": ist_now.strftime("%Y-%m-%d"), "dateLabel": ist_now.strftime("%a %-d %b"), "sessionLabel": label,
        "readMinutes": 3, "updatedAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": _title(markets, arts), "standfirst": stand.strip(), "scoreboard": scoreboard(markets),
        "groups": groups, "watch": _watch(arts, ist_now), "desk": "rules",
    }


def write_weekly(feed, markets, dailies, ist_now):
    monday = ist_now.date() - dt.timedelta(days=ist_now.weekday())
    if ist_now.weekday() >= 5:
        pass
    friday = monday + dt.timedelta(days=4)
    iso = ist_now.isocalendar()
    week_docs = [d for d in dailies if monday.isoformat() <= d.get("date", "") <= friday.isoformat()]
    week_docs.sort(key=lambda d: d.get("date", ""))
    india, world = [], []
    for d in week_docs:
        lab = d.get("dateLabel") or d.get("date")
        for g in d.get("groups", []):
            items = g.get("items", [])
            if not items:
                continue
            first = items[0]
            entry = {"text": "%s: %s" % (lab, first["text"]), "ids": first.get("ids", [])}
            if g.get("label") == "World":
                world.append(entry)
            elif g.get("label") == "Markets":
                india.append(entry)
    arts = feed["articles"]
    used = set()
    for a in _pick(arts, lambda a: a.get("region") == "india", 5 - len(india) if len(india) < 5 else 0, used):
        india.append(_item(a))
    for a in _pick(arts, lambda a: a.get("region") == "world", 5 - len(world) if len(world) < 5 else 0, used):
        world.append(_item(a))
    ms = _market_sentences(markets, week=True)
    return {
        "week": "%d-W%02d" % (iso[0], iso[1]), "rangeLabel": "%d-%d %s" % (monday.day, friday.day, friday.strftime("%b")),
        "readMinutes": 4, "updatedAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": _title(markets, arts, week=True), "standfirst": " ".join(ms), "scoreboard": scoreboard(markets, week=True),
        "groups": [{"label": "India", "items": india[:5]}, {"label": "World", "items": world[:5]}],
        "watch": _watch(arts, ist_now, week=True), "desk": "rules",
    }
