#!/usr/bin/env python3
"""Bazaar Brief - the four-page daily paper.

Builds a Mint-style broadsheet (salmon paper, serif headlines, multi-column)
from the day's edited feed, recap and market data, then prints it to PDF with
headless Chromium.

  python3 paper.py --feed data/feed.json --markets data/markets.json \
                   --archive data/archive.json --out site/paper

Writes <out>/bazaar-brief-YYYY-MM-DD.pdf, <out>/latest.pdf, <out>/latest.html
and <out>/index.json (the list of editions kept on the site).

Pages: 1 Front page  2 Markets & Money  3 Economy & Policy  4 World & Corporate
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import urllib.request

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
KEEP_EDITIONS = 14

SECTION_LABEL = {
    "stocks": "Stocks", "global-markets": "Global markets", "economy": "Economy", "inflation": "Inflation",
    "central-banks": "RBI & central banks", "bonds": "Bonds", "fx-commodities": "Currency & commodities",
    "corporate": "Corporate", "policy": "Policy", "geopolitics": "Geopolitics & trade", "banking": "Banking",
    "crypto": "Crypto",
}
PAGE2 = ["stocks", "bonds", "fx-commodities", "banking", "crypto"]
PAGE3 = ["economy", "inflation", "central-banks", "policy"]
PAGE4 = ["global-markets", "geopolitics", "corporate"]


def esc(s):
    return html.escape(str(s or ""), quote=True)


def clip(s, n):
    s = re.sub(r"\s+", " ", (s or "")).strip()
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "…"


def ordinal_day(d):
    n = d.day
    suf = "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def fmt_num(v):
    if v is None:
        return "–"
    return f"{v:,.2f}" if abs(v) < 1000 else f"{v:,.0f}"


def pct(v):
    if v is None:
        return "–"
    return f"{v:+.2f}%"


def move_class(v):
    if v is None:
        return "flat"
    return "up" if v > 0.0001 else "down" if v < -0.0001 else "flat"


# ---------------------------------------------------------------- content

def story_html(a, kind="std"):
    """kind: lead | second | std | brief"""
    head_len = {"lead": 110, "second": 90, "std": 80, "brief": 70}[kind]
    sum_len = {"lead": 650, "second": 420, "std": 330, "brief": 170}[kind]
    why_len = {"lead": 260, "second": 200, "std": 170, "brief": 0}[kind]
    kicker = SECTION_LABEL.get(a.get("section"), a.get("section", ""))
    region = "India" if a.get("region") == "india" else "World"
    why = a.get("why") if why_len else ""
    parts = [f'<article class="story {kind}">',
             f'<div class="kicker"><span class="sec">{esc(kicker)}</span><span class="reg">{esc(region)}</span></div>',
             f'<h2>{esc(clip(a.get("title"), head_len))}</h2>']
    if a.get("summary"):
        parts.append(f'<p class="body">{esc(clip(a["summary"], sum_len))}</p>')
    if why:
        parts.append(f'<p class="why"><b>Why it matters</b> {esc(clip(why, why_len))}</p>')
    parts.append(f'<div class="byline">{esc(a.get("source", ""))}</div>')
    parts.append("</article>")
    return "".join(parts)


def pick(articles, sections, used, n):
    out = []
    for a in articles:
        if a["id"] in used:
            continue
        if a.get("section") in sections:
            out.append(a)
            used.add(a["id"])
            if len(out) >= n:
                break
    return out


def fill_from_any(articles, used, n):
    out = []
    for a in articles:
        if a["id"] in used:
            continue
        out.append(a)
        used.add(a["id"])
        if len(out) >= n:
            break
    return out


def section_page(title, blurb, stories, page_no, date_line, box_html="", box_title="", box_wide=False):
    """Section page: a lead band (lead story + two stories, or lead + a box), then flowing 4-column copy."""
    lead = stories[0] if stories else None
    rest = stories[1:]
    band = [f'<div class="band-lead">{story_html(lead, "second") if lead else ""}</div>']
    flow_start = 0
    if box_html and box_wide:
        band.append(f'<div class="band-box wide"><div class="boxhead">{esc(box_title)}</div>{box_html}</div>')
    elif box_html:
        band.append(f'<div class="band-a">{story_html(rest[0], "std") if rest else ""}</div>')
        band.append(f'<div class="band-box"><div class="boxhead">{esc(box_title)}</div>{box_html}</div>')
        flow_start = 1
    else:
        for a in rest[:2]:
            band.append(f'<div class="band-a">{story_html(a, "std")}</div>')
        flow_start = 2
    flow = []
    for i, a in enumerate(rest[flow_start:]):
        flow.append(story_html(a, "std" if i < 10 else "brief"))
    cls = "band wide" if (box_html and box_wide) else "band"
    return f'''<section class="page">
  <header class="pagehead"><span class="ptitle">{esc(title)}</span><span class="pblurb">{esc(blurb)}</span><span class="pdate">{esc(date_line)}</span></header>
  <div class="{cls}">{"".join(band)}</div>
  <div class="flow">{"".join(flow)}</div>
  <footer class="pagefoot"><span>Bazaar Brief</span><span>Page {page_no}</span></footer>
</section>'''


def market_table_html(markets, groups=("India", "FX", "Rates", "Commodities", "World", "Crypto")):
    q = [x for x in markets.get("quotes", []) if not x.get("error")]
    rows = []
    for g in groups:
        rs = [x for x in q if x.get("group") == g]
        if not rs:
            continue
        rows.append(f'<tr class="grp"><td colspan="4">{esc({"FX": "Currencies"}.get(g, g))}</td></tr>')
        for x in rs:
            isy = x.get("kind") == "yield"
            last = f'{x["price"]:.3f}%' if isy else fmt_num(x["price"])
            chg = f'{x["change"] * 100:+.0f} bp' if isy else pct(x.get("changePct"))
            rows.append(f'<tr><td>{esc(x["label"])}</td><td class="num">{last}</td>'
                        f'<td class="num {move_class(x.get("change"))}">{chg}</td><td class="num">{pct(x.get("weekPct"))}</td></tr>')
    return f'<table class="mkt"><thead><tr><th>Instrument</th><th class="num">Last</th><th class="num">1D</th><th class="num">5D</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'


def market_strip_html(markets):
    order = ["^NSEI", "^BSESN", "^NSEBANK", "INR=X", "^TNX", "BZ=F", "GC=F", "^GSPC", "^IXIC", "BTC-USD"]
    q = {x["symbol"]: x for x in markets.get("quotes", []) if not x.get("error")}
    items = []
    for s in order:
        x = q.get(s)
        if not x:
            continue
        isy = x.get("kind") == "yield"
        val = f'{x["price"]:.2f}%' if isy else fmt_num(x["price"])
        chg = f'{x["change"] * 100:+.0f} bp' if isy else pct(x.get("changePct"))
        items.append(f'<div class="tick"><span class="l">{esc(x["label"])}</span><span class="v">{val}</span><span class="c {move_class(x.get("change"))}">{chg}</span></div>')
    return f'<div class="strip">{"".join(items)}</div>'


def recap_html(daily, limit_per_group=5):
    if not daily:
        return ""
    out = []
    for g in daily.get("groups", []):
        out.append(f'<h4>{esc(g["label"])}</h4><ul>')
        for it in g["items"][:limit_per_group]:
            out.append(f'<li>{esc(clip(it["text"], 260))}</li>')
        out.append("</ul>")
    return "".join(out)


def watch_html(daily):
    if not daily or not daily.get("watch"):
        return ""
    return "<ul class='watch'>" + "".join(f"<li>{esc(clip(w, 160))}</li>" for w in daily["watch"][:4]) + "</ul>"


def build_html(feed, markets, archive, paper_date, edition_no):
    articles = [a for a in feed.get("articles", []) if a.get("title")]
    daily = None
    for d in archive.get("dailies", []):
        if d.get("date") == paper_date.strftime("%Y-%m-%d"):
            daily = d
            break
    if daily is None and archive.get("dailies"):
        daily = archive["dailies"][0]
    weekly = (archive.get("weeklies") or [None])[0]

    used = set()
    # Front page: lead, second lead, three briefs. Prefer stories with why-notes (the editor's picks).
    front_pool = [a for a in articles if a.get("why")] or articles
    front = fill_from_any(front_pool, used, 8)
    p2 = pick(articles, PAGE2, used, 26)
    p3 = pick(articles, PAGE3, used, 26)
    p4 = pick(articles, PAGE4, used, 24)
    for lst, n in ((p2, 18), (p3, 18), (p4, 18)):
        if len(lst) < n:
            lst.extend(fill_from_any(articles, used, n - len(lst)))

    date_line = f'{paper_date.strftime("%A")}, {ordinal_day(paper_date)} {paper_date.strftime("%B %Y")}'
    inside = [("2", "Markets & Money", p2[0]["title"] if p2 else ""), ("3", "Economy & Policy", p3[0]["title"] if p3 else ""),
              ("4", "World & Corporate", p4[0]["title"] if p4 else "")]
    inside_html = "".join(f'<div class="inside-item"><span class="pg">{n}</span><span><b>{esc(t)}</b><br>{esc(clip(h, 70))}</span></div>' for n, t, h in inside)
    numbers = ""
    if daily and daily.get("scoreboard"):
        numbers = "".join(
            f'<div class="num-tile"><span class="l">{esc(e["label"])}</span><span class="v">{esc(e["value"])}</span>'
            f'<span class="c {move_class(e.get("changePct") if e.get("changePct") is not None else (1 if str(e.get("change", "")).startswith("+") else -1))}">'
            f'{pct(e["changePct"]) if e.get("changePct") is not None else esc(e.get("change", ""))}</span></div>'
            for e in daily["scoreboard"][:6])

    front_lead = story_html(front[0], "lead") if front else ""
    front_lead += "".join(story_html(a, "std") for a in front[5:8])
    front_second = story_html(front[1], "second") if len(front) > 1 else ""
    front_briefs = "".join(story_html(a, "std") for a in front[2:5])
    standfirst = esc(clip(daily.get("standfirst", ""), 420)) if daily else ""
    recap_title = esc(clip(daily.get("title", ""), 120)) if daily else ""

    page1 = f'''<section class="page front">
  <header class="masthead">
    <div class="mast-top"><span>{esc(date_line)}</span><span>Edition {edition_no} · Mumbai · Free</span></div>
    <h1>Bazaar Brief</h1>
    <div class="mast-sub">Markets · Economy · Policy · World &nbsp;|&nbsp; The day's finance and economics, edited for readers with no time</div>
  </header>
  {market_strip_html(markets)}
  <div class="front-grid">
    <div class="col lead-col">{front_lead}</div>
    <div class="col second-col">{front_second}<div class="briefs">{front_briefs}</div></div>
    <div class="col side-col">
      <div class="box"><div class="boxhead">The day in brief</div><p class="standfirst"><b>{recap_title}</b> {standfirst}</p></div>
      <div class="box"><div class="boxhead">The day in numbers</div><div class="numbers">{numbers}</div></div>
      <div class="box"><div class="boxhead">Inside</div>{inside_html}</div>
    </div>
  </div>
  <footer class="pagefoot"><span>Sources: {esc(", ".join((feed.get("sources") or [])[:12]))}. Summaries and notes are AI-assisted; not investment advice.</span><span>Page 1</span></footer>
</section>'''

    page2 = section_page("Markets & Money", "Stocks, bonds, the rupee, commodities and banks", p2, 2, date_line,
                         market_table_html(markets), "Markets at close")
    page3 = section_page("Economy & Policy", "Growth, prices, the RBI and the government", p3, 3, date_line)
    p4_extra = f'<h4 class="rt">{recap_title}</h4><div class="recap-cols">{recap_html(daily, 4)}</div>'
    watch = watch_html(daily)
    if watch:
        p4_extra += f'<div class="boxhead small">What to watch</div>{watch}'
    if weekly:
        p4_extra += f'<div class="boxhead small">The week, {esc(weekly.get("rangeLabel", ""))}</div><p class="weekly">{esc(clip(weekly.get("title", ""), 140))}</p>'
    page4 = section_page("World & Corporate", "Wall Street, geopolitics, trade and company news", p4, 4, date_line, p4_extra, "Recap of the day", box_wide=True)

    css = CSS
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Bazaar Brief, {esc(date_line)}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600;6..72,700&family=Instrument+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{css}</style></head><body>{page1}{page2}{page3}{page4}</body></html>'''


CSS = """
@page { size: 297mm 420mm; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #E9E4DE; }
body { font-family: "Newsreader", Georgia, "Times New Roman", serif; color: #1B1B1B; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.page { width: 297mm; height: 420mm; padding: 11mm 12mm 9mm; background: #F6DBCF; overflow: hidden; position: relative; page-break-after: always; break-after: page; margin: 0 auto; }
.page:last-child { page-break-after: auto; break-after: auto; }
@media screen { .page { margin: 10mm auto; box-shadow: 0 6px 30px rgba(0,0,0,.25); } }
h1, h2, h3, h4 { margin: 0; font-weight: 600; }

/* masthead */
.masthead { border-bottom: 2.2pt solid #1B1B1B; padding-bottom: 2mm; margin-bottom: 3mm; }
.mast-top { display: flex; justify-content: space-between; font-family: "Instrument Sans", Arial, sans-serif; font-size: 8.5pt; letter-spacing: .06em; text-transform: uppercase; border-bottom: .5pt solid #1B1B1B; padding-bottom: 1.2mm; }
.masthead h1 { font-family: "Instrument Sans", Arial, sans-serif; font-weight: 700; font-size: 58pt; letter-spacing: -.035em; line-height: 1; margin: 2mm 0 1mm; }
.mast-sub { font-family: "Instrument Sans", Arial, sans-serif; font-size: 9pt; letter-spacing: .02em; color: #333; }

/* ticker strip */
.strip { display: flex; gap: 0; border-top: .5pt solid #1B1B1B; border-bottom: .5pt solid #1B1B1B; margin-bottom: 4mm; }
.tick { flex: 1; padding: 1.4mm 2mm; border-right: .4pt solid #7a6a63; display: flex; flex-direction: column; }
.tick:last-child { border-right: 0; }
.tick .l { font-family: "Instrument Sans", Arial, sans-serif; font-size: 7pt; letter-spacing: .05em; text-transform: uppercase; color: #444; }
.tick .v { font-family: "IBM Plex Mono", monospace; font-size: 11pt; font-weight: 500; }
.tick .c { font-family: "IBM Plex Mono", monospace; font-size: 8pt; }
.up { color: #0B6B45; } .down { color: #B3261E; } .flat { color: #555; }

/* front page grid */
.front-grid { display: grid; grid-template-columns: 2.1fr 1.5fr 1fr; gap: 0 5mm; height: 314mm; }
.lead-col .story.std h2 { font-size: 15pt; }
.col { min-width: 0; overflow: hidden; }
.second-col, .side-col { border-left: .4pt solid #7a6a63; padding-left: 5mm; }
.story { padding-bottom: 3mm; margin-bottom: 3mm; border-bottom: .4pt solid #9a8a83; overflow: hidden; }
.story:last-child { border-bottom: 0; }
.kicker { font-family: "Instrument Sans", Arial, sans-serif; font-size: 7.5pt; letter-spacing: .08em; text-transform: uppercase; color: #8A2F1F; display: flex; justify-content: space-between; margin-bottom: 1mm; }
.kicker .reg { color: #666; }
.story h2 { font-size: 14pt; line-height: 1.15; letter-spacing: -.01em; margin-bottom: 1.6mm; }
.story.lead h2 { font-size: 34pt; line-height: 1.02; letter-spacing: -.02em; margin-bottom: 3mm; font-weight: 700; }
.story.second h2 { font-size: 20pt; line-height: 1.08; }
.story.brief h2 { font-size: 11.5pt; }
.body { font-size: 10pt; line-height: 1.38; margin: 0 0 1.5mm; text-align: justify; hyphens: auto; }
.story.lead .body { font-size: 11.5pt; line-height: 1.42; column-count: 2; column-gap: 5mm; column-rule: .4pt solid #9a8a83; }
.story.lead .body::first-letter { font-size: 3.1em; float: left; line-height: .85; padding: .05em .08em 0 0; font-weight: 600; }
.story.brief .body { font-size: 9.2pt; }
.why { font-family: "Instrument Sans", Arial, sans-serif; font-size: 8.8pt; line-height: 1.35; margin: 0 0 1.2mm; padding-left: 2.2mm; border-left: 1.6pt solid #8A2F1F; color: #2a2a2a; }
.why b { color: #8A2F1F; text-transform: uppercase; font-size: 7.2pt; letter-spacing: .08em; margin-right: 1mm; }
.byline { font-family: "Instrument Sans", Arial, sans-serif; font-size: 7.5pt; color: #666; letter-spacing: .03em; }
.briefs { margin-top: 2mm; border-top: 1.6pt solid #1B1B1B; padding-top: 2mm; }

/* boxes */
.box { border-top: 1.6pt solid #1B1B1B; padding-top: 1.6mm; margin-bottom: 4mm; overflow: hidden; }
.boxhead { font-family: "Instrument Sans", Arial, sans-serif; font-size: 8pt; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; margin-bottom: 1.6mm; }
.boxhead.small { margin-top: 2.5mm; border-top: .4pt solid #9a8a83; padding-top: 1.5mm; }
.standfirst { font-size: 10.2pt; line-height: 1.4; margin: 0; }
.numbers { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5mm; }
.num-tile { background: rgba(255,255,255,.35); padding: 1.6mm 2mm; display: flex; flex-direction: column; }
.num-tile .l { font-family: "Instrument Sans", Arial, sans-serif; font-size: 7pt; text-transform: uppercase; letter-spacing: .05em; color: #444; }
.num-tile .v { font-family: "IBM Plex Mono", monospace; font-size: 11pt; font-weight: 500; }
.num-tile .c { font-family: "IBM Plex Mono", monospace; font-size: 8pt; }
.inside-item { display: flex; gap: 2mm; font-size: 9pt; line-height: 1.3; margin-bottom: 1.6mm; }
.inside-item .pg { font-family: "Instrument Sans", Arial, sans-serif; font-weight: 700; font-size: 14pt; line-height: 1; color: #8A2F1F; min-width: 6mm; }
.inside-item b { font-family: "Instrument Sans", Arial, sans-serif; font-size: 8pt; text-transform: uppercase; letter-spacing: .06em; }

/* section pages */
.pagehead { display: flex; align-items: baseline; gap: 4mm; border-bottom: 2.2pt solid #1B1B1B; padding-bottom: 1.5mm; margin-bottom: 3.5mm; }
.ptitle { font-family: "Instrument Sans", Arial, sans-serif; font-weight: 700; font-size: 22pt; letter-spacing: -.02em; }
.pblurb { font-size: 10.5pt; font-style: italic; color: #333; flex: 1; }
.pdate { font-family: "Instrument Sans", Arial, sans-serif; font-size: 8pt; text-transform: uppercase; letter-spacing: .06em; }
.band { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 0 5mm; height: 112mm; overflow: hidden; border-bottom: 1.6pt solid #1B1B1B; margin-bottom: 3.5mm; }
.band.wide { grid-template-columns: 1.15fr 1fr; }
.band > div { min-width: 0; overflow: hidden; border-right: .4pt solid #9a8a83; padding-right: 5mm; }
.band > div:last-child { border-right: 0; padding-right: 0; }
.band .story { border-bottom: 0; }
.band-lead .story.second h2 { font-size: 25pt; line-height: 1.06; }
.band-lead .body { column-count: 2; column-gap: 5mm; column-rule: .4pt solid #9a8a83; font-size: 10.5pt; }
.band-box { border-top: 1.6pt solid #1B1B1B; padding-top: 1.6mm; }
.band-box.wide .recap-cols { column-count: 2; column-gap: 5mm; column-rule: .4pt solid #9a8a83; }
.flow { column-count: 4; column-gap: 5mm; column-rule: .4pt solid #9a8a83; column-fill: auto; height: 252mm; overflow: hidden; }
.flow .story { break-inside: avoid; -webkit-column-break-inside: avoid; padding-bottom: 2.4mm; margin-bottom: 2.4mm; border-bottom: .4pt solid #9a8a83; }
.mkt { width: 100%; border-collapse: collapse; font-family: "IBM Plex Mono", monospace; font-size: 7.3pt; }
.mkt th { font-family: "Instrument Sans", Arial, sans-serif; font-size: 7pt; text-transform: uppercase; letter-spacing: .05em; text-align: left; border-bottom: .6pt solid #1B1B1B; padding: .6mm 0; }
.mkt td { padding: .4mm 0; border-bottom: .3pt solid #c9b7ad; }
.mkt .num, .mkt th.num { text-align: right; }
.mkt tr.grp td { font-family: "Instrument Sans", Arial, sans-serif; font-size: 6.8pt; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; padding-top: 1.2mm; border-bottom: .5pt solid #1B1B1B; }
.band-box h4 { font-family: "Instrument Sans", Arial, sans-serif; font-size: 7.5pt; text-transform: uppercase; letter-spacing: .1em; color: #8A2F1F; margin: 1.6mm 0 .8mm; }
.band-box h4.rt { font-family: "Newsreader", serif; font-size: 12.5pt; text-transform: none; letter-spacing: -.01em; color: #1B1B1B; line-height: 1.15; margin: 0 0 1.5mm; }
.band-box ul { margin: 0 0 1mm; padding-left: 3.5mm; font-size: 8.8pt; line-height: 1.32; }
.band-box li { margin-bottom: .9mm; }
.weekly { font-size: 9.5pt; font-style: italic; margin: 0; line-height: 1.3; }

.pagefoot { position: absolute; left: 12mm; right: 12mm; bottom: 5mm; display: flex; justify-content: space-between; gap: 6mm; font-family: "Instrument Sans", Arial, sans-serif; font-size: 7pt; color: #555; border-top: .4pt solid #7a6a63; padding-top: 1.2mm; }
"""


# ---------------------------------------------------------------- render

def render_pdf(html_path, pdf_path):
    from playwright.sync_api import sync_playwright
    exe = os.environ.get("PW_CHROMIUM_PATH")
    with sync_playwright() as p:
        kw = {"executable_path": exe} if exe else {}
        browser = p.chromium.launch(**kw)
        page = browser.new_page()
        page.goto("file://" + os.path.abspath(html_path), wait_until="networkidle")
        page.wait_for_timeout(500)
        page.pdf(path=pdf_path, width="297mm", height="420mm", print_background=True, prefer_css_page_size=True,
                 margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        browser.close()


def fetch_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "bazaar-brief-paper", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def build(feed, markets, archive, out_dir, site_url="", now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    paper_date = now.astimezone(IST).date()
    os.makedirs(out_dir, exist_ok=True)

    # Existing editions from the live site (the build is stateless)
    index = {"editions": []}
    if site_url:
        try:
            index = json.loads(fetch_bytes(site_url.rstrip("/") + "/paper/index.json?b=%d" % int(now.timestamp())).decode("utf-8"))
        except Exception as e:
            print("paper index not fetched:", repr(e))
    editions = [e for e in index.get("editions", []) if e.get("date") != paper_date.isoformat()]
    editions.sort(key=lambda e: e.get("date", ""), reverse=True)
    editions = editions[:KEEP_EDITIONS - 1]
    for e in editions:
        name = e.get("file")
        if not name or not site_url:
            continue
        try:
            with open(os.path.join(out_dir, name), "wb") as f:
                f.write(fetch_bytes(site_url.rstrip("/") + "/paper/" + name))
        except Exception as ex:
            print("could not keep edition", name, repr(ex))
            e["missing"] = True
    editions = [e for e in editions if not e.get("missing")]

    edition_no = (editions[0].get("number", len(editions)) + 1) if editions else 1
    html_doc = build_html(feed, markets, archive, paper_date, edition_no)
    fname = f"bazaar-brief-{paper_date.isoformat()}.pdf"
    html_path = os.path.join(out_dir, "latest.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    pdf_path = os.path.join(out_dir, fname)
    render_pdf(html_path, pdf_path)
    shutil.copyfile(pdf_path, os.path.join(out_dir, "latest.pdf"))

    daily = next((d for d in archive.get("dailies", []) if d.get("date") == paper_date.isoformat()), None) or (archive.get("dailies") or [{}])[0]
    entry = {"date": paper_date.isoformat(), "file": fname, "number": edition_no, "pages": 4,
             "title": (daily or {}).get("title", ""), "bytes": os.path.getsize(pdf_path),
             "builtAt": now.isoformat().replace("+00:00", "Z")}
    index = {"latest": entry, "editions": [entry] + editions, "updatedAt": entry["builtAt"]}
    with open(os.path.join(out_dir, "index.json"), "w") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print("paper:", fname, entry["bytes"], "bytes; editions kept:", len(index["editions"]))
    return index


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed", required=True)
    ap.add_argument("--markets", required=True)
    ap.add_argument("--archive", required=True)
    ap.add_argument("--out", default="site/paper")
    ap.add_argument("--site-url", default=os.environ.get("SITE_URL", ""))
    a = ap.parse_args()
    build(json.load(open(a.feed)), json.load(open(a.markets)), json.load(open(a.archive)), a.out, a.site_url)
