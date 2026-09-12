"""Editorial layer for Bazaar Brief, written by Claude through the Anthropic API.

Three jobs, each one Messages API call with a JSON-schema output format:
  edit_feed()    - fix sections/regions, drop junk, order the top stories, write "why it matters"
  write_daily()  - the recap of the day
  write_weekly() - the recap of the week

Set ANTHROPIC_API_KEY in the environment. DESK_MODEL overrides the model
(default claude-opus-5; claude-sonnet-5 is about 40% of the cost).
"""
import datetime as dt
import json
import os

import anthropic

MODEL = os.environ.get("DESK_MODEL", "claude-opus-5")
SECTIONS = ["stocks", "global-markets", "economy", "inflation", "central-banks", "bonds", "fx-commodities",
            "corporate", "policy", "geopolitics", "banking", "crypto"]

SYSTEM = (
    "You are the desk editor of Bazaar Brief, a financial and economic news app for a busy Indian reader who "
    "has little time. Facts come only from the material you are given; never invent numbers or events. "
    "India first, but always with global context. Plain English, specific, no hype, no emoji, no markdown "
    "symbols inside text fields. Section ids: " + ", ".join(SECTIONS) + ". Regions: india, world."
)


def _client():
    return anthropic.Anthropic()


def _ask(prompt, schema, max_tokens=16000, effort="medium"):
    """One structured call. Streams so long outputs never hit HTTP timeouts."""
    with _client().messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        system=SYSTEM,
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        raise RuntimeError("model declined the request: %s" % (msg.stop_details and msg.stop_details.explanation))
    if msg.stop_reason == "max_tokens":
        raise RuntimeError("output cut off at max_tokens")
    text = next(b.text for b in msg.content if b.type == "text")
    return json.loads(text), msg.usage


def _market_line(markets):
    parts = []
    for q in markets.get("quotes", []):
        if q.get("error"):
            continue
        if q.get("kind") == "yield":
            parts.append("%s %.3f%% (%+.0f bp, 5D %+.1f%%)" % (q["label"], q["price"], q["change"] * 100, q["weekPct"]))
        else:
            parts.append("%s %s (%+.2f%%, 5D %+.2f%%)" % (q["label"], _fmt(q["price"]), q["changePct"], q["weekPct"]))
    return "; ".join(parts)


def _fmt(v):
    return ("%.2f" % v) if abs(v) < 1000 else ("{:,.0f}".format(v))


def _story_lines(articles, n=90, with_why=True):
    lines = []
    for a in articles[:n]:
        line = "- id=%s | %s | %s | %s | %s | %s" % (a["id"], a["section"], a["region"], a["source"],
                                                    a["publishedAt"][:16].replace("T", " ") + "Z", a["title"])
        if a.get("summary"):
            line += "\n    " + a["summary"][:220]
        if with_why and a.get("why"):
            line += "\n    why(existing): " + a["why"]
        lines.append(line)
    return "\n".join(lines)


EDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "drop": {"type": "array", "items": {"type": "string"}},
        "fixes": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string"}, "section": {"type": "string"}, "region": {"type": "string"}},
            "required": ["id", "section", "region"], "additionalProperties": False}},
        "order": {"type": "array", "items": {"type": "string"}},
        "why": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string"}, "text": {"type": "string"}},
            "required": ["id", "text"], "additionalProperties": False}},
    },
    "required": ["drop", "fixes", "order", "why"],
    "additionalProperties": False,
}


def edit_feed(feed, markets, label, ist_now):
    """Return a new feed dict with editorial fixes applied, plus usage."""
    articles = feed["articles"]
    prompt = (
        "It is %s IST. Edition: %s. Markets now: %s\n\n"
        "Here are the top stories from the wire, ranked by the pipeline (id | section | region | source | published | title):\n%s\n\n"
        "Do four things and reply as JSON.\n"
        "1. drop: ids of junk to remove (stock tips, buy/sell calls, share-price live pages, earnings-call transcripts of "
        "obscure foreign firms, personal-finance how-tos, sponsored posts, duplicates of a story already listed higher).\n"
        "2. fixes: stories whose section or region is wrong; give the corrected section AND region for each (repeat the "
        "correct value if only one changes). Only list stories that need a change.\n"
        "3. order: the ids of the top 30 stories in reading order. First the market wrap for the current session (the "
        "Sensex/Nifty close, or the morning setup and overnight Wall Street if before the open), then the biggest macro drivers "
        "(oil, rupee, RBI, inflation, Fed/ECB, bonds), then policy and SEBI, corporate, then global. Prefer the freshest and "
        "best-sourced version of each story.\n"
        "4. why: for every story in your top 35 that has no existing why line, or whose existing line is now out of date, "
        "write one to two sentences (max 45 words) telling a reader with no time why it matters for the Indian economy or "
        "their investments. Keep existing lines that are still right by not listing them."
    ) % (ist_now.strftime("%a %d %b %Y, %H:%M"), label, _market_line(markets), _story_lines(articles))
    data, usage = _ask(prompt, EDIT_SCHEMA, effort="medium")
    byid = {a["id"]: a for a in articles}
    drop = set(i for i in data["drop"] if i in byid)
    for f in data["fixes"]:
        a = byid.get(f["id"])
        if not a:
            continue
        if f.get("section") in SECTIONS:
            a["section"] = f["section"]
        if f.get("region") in ("india", "world"):
            a["region"] = f["region"]
    for w in data["why"]:
        a = byid.get(w["id"])
        if a and w.get("text"):
            a["why"] = w["text"].strip()
    order = {i: n for n, i in enumerate([i for i in data["order"] if i in byid and i not in drop])}
    kept = [a for a in articles if a["id"] not in drop]
    kept.sort(key=lambda a: (order.get(a["id"], 10 ** 6), -a.get("score", 0)))
    out = dict(feed)
    out["articles"] = kept
    out["count"] = len(kept)
    out["sessionLabel"] = label
    out["sources"] = sorted({a["source"] for a in kept})
    out["editedAt"] = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    return out, usage


RECAP_ITEM = {"type": "object", "properties": {
    "text": {"type": "string"}, "ids": {"type": "array", "items": {"type": "string"}}},
    "required": ["text", "ids"], "additionalProperties": False}
RECAP_GROUP = {"type": "object", "properties": {
    "label": {"type": "string"}, "items": {"type": "array", "items": RECAP_ITEM}},
    "required": ["label", "items"], "additionalProperties": False}
DAILY_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "standfirst": {"type": "string"},
        "groups": {"type": "array", "items": RECAP_GROUP},
        "watch": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "standfirst", "groups", "watch"],
    "additionalProperties": False,
}


def _scoreboard(markets, week=False):
    q = {x["symbol"]: x for x in markets.get("quotes", []) if not x.get("error")}
    out = []
    for sym, label in (("^NSEI", "Nifty 50"), ("^BSESN", "Sensex"), ("INR=X", "USD/INR"), ("BZ=F", "Brent $"), ("GC=F", "Gold $")):
        x = q.get(sym)
        if x:
            out.append({"label": label, "value": "{:,.2f}".format(x["price"]),
                        "changePct": round(x["weekPct"] if week else x["changePct"], 2)})
    if week:
        x = q.get("^GSPC")
        if x:
            out.append({"label": "S&P 500", "value": "{:,.2f}".format(x["price"]), "changePct": round(x["weekPct"], 2)})
    else:
        x = q.get("^TNX")
        if x:
            out.append({"label": "US 10Y", "value": "%.2f%%" % x["price"], "change": "%+.0f bp" % (x["change"] * 100),
                        "changePct": None})
    return out


def write_daily(feed, markets, label, ist_now):
    scope = {"Morning brief": "the previous evening and overnight session, setting up today's trade",
             "Closing wrap": "today's Indian session and the day so far",
             "Late edition": "the whole day including the US and European sessions",
             "Weekend edition": "the last 24 hours and the state of play going into the weekend"}.get(label, "the day")
    prompt = (
        "It is %s IST. Write the %s, the recap of the day covering %s. Markets now: %s\n\n"
        "Stories (id | section | region | source | published | title, with summary and desk note):\n%s\n\n"
        "Reply as JSON with: title (one specific headline, max 20 words, with the key number if there is one); "
        "standfirst (2-3 sentences for India and the world); groups: exactly three groups labelled 'Markets', "
        "'RBI, SEBI and policy' and 'World', each with 3-5 items, every item one or two clear sentences with numbers and "
        "the ids of the stories it draws on; watch: 3-4 short lines on what to watch next (data releases, central bank "
        "meetings, price levels). Three minutes of reading in total."
    ) % (ist_now.strftime("%a %d %b %Y, %H:%M"), label, scope, _market_line(markets), _story_lines(feed["articles"], 60))
    data, usage = _ask(prompt, DAILY_SCHEMA, effort="medium")
    doc = {
        "date": ist_now.strftime("%Y-%m-%d"), "dateLabel": ist_now.strftime("%a %-d %b"), "sessionLabel": label,
        "readMinutes": 3, "updatedAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": data["title"], "standfirst": data["standfirst"], "scoreboard": _scoreboard(markets),
        "groups": data["groups"], "watch": data["watch"],
    }
    return doc, usage


def write_weekly(feed, markets, dailies, ist_now):
    monday = ist_now.date() - dt.timedelta(days=ist_now.weekday())
    if ist_now.weekday() >= 5:  # weekend: the week that just ended
        pass
    friday = monday + dt.timedelta(days=4)
    iso = ist_now.isocalendar()
    recaps = "\n\n".join("%s (%s): %s\n%s" % (d.get("dateLabel"), d.get("sessionLabel"), d.get("title"),
                                            " ".join(i["text"] for g in d.get("groups", []) for i in g["items"]))
                         for d in dailies if monday.isoformat() <= d.get("date", "") <= friday.isoformat())
    prompt = (
        "It is %s IST. Write the recap of the week %d to %d %s. Weekly market moves (5D): %s\n\n"
        "Daily recaps from this week:\n%s\n\nCurrent stories for extra detail:\n%s\n\n"
        "Reply as JSON with: title (one headline for the week, max 22 words); standfirst (3 sentences); groups: exactly two "
        "groups labelled 'India' and 'World', each with 5 items, one or two sentences each with numbers and story ids where "
        "available (ids may be empty for items drawn only from the daily recaps); watch: 3-4 lines for the week ahead. "
        "Four minutes of reading."
    ) % (ist_now.strftime("%a %d %b %Y, %H:%M"), monday.day, friday.day, friday.strftime("%b %Y"), _market_line(markets),
         recaps or "(none available)", _story_lines(feed["articles"], 40, with_why=False))
    data, usage = _ask(prompt, DAILY_SCHEMA, effort="medium")
    doc = {
        "week": "%d-W%02d" % (iso[0], iso[1]), "rangeLabel": "%d-%d %s" % (monday.day, friday.day, friday.strftime("%b")),
        "readMinutes": 4, "updatedAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": data["title"], "standfirst": data["standfirst"], "scoreboard": _scoreboard(markets, week=True),
        "groups": data["groups"], "watch": data["watch"],
    }
    return doc, usage
