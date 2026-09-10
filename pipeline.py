#!/usr/bin/env python3
"""Bazaar Brief news pipeline.

Fetches Indian + global financial/economic news feeds and market quotes,
cleans, de-duplicates, classifies each story into a section and a region,
ranks, and writes:
  articles.json  - ranked, classified stories (for feed/latest)
  markets.json   - quotes with sparklines (for markets/latest)
Standard library only. Usage: python3 pipeline.py [outdir]
"""
import concurrent.futures as cf
import datetime as dt
import email.utils
import hashlib
import html
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
NOW = dt.datetime.now(dt.timezone.utc)
MAX_AGE_H = 36

# name, url, region hint, source weight, default section
FEEDS = [
    ("Economic Times", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "india", 1.0, "stocks"),
    ("Economic Times", "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms", "india", 0.9, "stocks"),
    ("Economic Times", "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms", "india", 1.1, "economy"),
    ("Economic Times", "https://economictimes.indiatimes.com/industry/banking/finance/rssfeeds/13358259.cms", "india", 0.9, "banking"),
    ("Economic Times", "https://economictimes.indiatimes.com/markets/commodities/rssfeeds/1808152121.cms", "india", 0.8, "fx-commodities"),
    ("Economic Times", "https://economictimes.indiatimes.com/markets/ipos/fpos/rssfeeds/14655708.cms", "india", 0.7, "stocks"),
    ("Mint", "https://www.livemint.com/rss/markets", "india", 1.0, "stocks"),
    ("Mint", "https://www.livemint.com/rss/economy", "india", 1.1, "economy"),
    ("Mint", "https://www.livemint.com/rss/companies", "india", 0.8, "corporate"),
    ("Business Standard", "https://www.business-standard.com/rss/markets-106.rss", "india", 1.0, "stocks"),
    ("Business Standard", "https://www.business-standard.com/rss/economy-102.rss", "india", 1.1, "economy"),
    ("Business Standard", "https://www.business-standard.com/rss/finance-103.rss", "india", 0.9, "banking"),
    ("Business Standard", "https://www.business-standard.com/rss/companies-101.rss", "india", 0.8, "corporate"),
    ("BusinessLine", "https://www.thehindubusinessline.com/markets/feeder/default.rss", "india", 0.9, "stocks"),
    ("BusinessLine", "https://www.thehindubusinessline.com/economy/feeder/default.rss", "india", 1.0, "economy"),
    ("BusinessLine", "https://www.thehindubusinessline.com/money-and-banking/feeder/default.rss", "india", 0.9, "banking"),
    ("CNBC-TV18", "https://www.cnbctv18.com/commonfeeds/v1/cne/rss/market.xml", "india", 0.8, "stocks"),
    ("Financial Express", "https://www.financialexpress.com/market/feed/", "india", 0.7, "stocks"),
    ("Financial Express", "https://www.financialexpress.com/economy/feed/", "india", 0.9, "economy"),
    ("RBI", "https://www.rbi.org.in/pressreleases_rss.xml", "india", 1.2, "central-banks"),
    ("Google News", "https://news.google.com/rss/search?q=%22RBI%22+OR+%22Reserve+Bank+of+India%22+OR+SEBI+OR+%22Finance+Ministry%22+OR+%22India+GDP%22+OR+%22India+inflation%22&hl=en-IN&gl=IN&ceid=IN:en", "india", 0.8, "economy"),
    ("BBC", "https://feeds.bbci.co.uk/news/business/rss.xml", "world", 1.0, "economy"),
    ("The Guardian", "https://www.theguardian.com/uk/business/rss", "world", 0.9, "economy"),
    ("WSJ", "https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "world", 1.1, "global-markets"),
    ("WSJ", "https://feeds.a.dj.com/rss/RSSWorldNews.xml", "world", 0.7, "geopolitics"),
    ("NYT", "https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml", "world", 1.1, "economy"),
    ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_topstories", "world", 1.0, "global-markets"),
    ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines", "world", 0.9, "global-markets"),
    ("FT", "https://www.ft.com/rss/home", "world", 1.1, "economy"),
    ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex", "world", 0.8, "global-markets"),
    ("Investing.com", "https://www.investing.com/rss/news.rss", "world", 0.7, "global-markets"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "world", 0.7, "geopolitics"),
    ("Google News", "https://news.google.com/rss/search?q=%22Federal+Reserve%22+OR+ECB+OR+%22Bank+of+Japan%22+OR+%22global+economy%22+OR+%22Wall+Street%22+OR+tariffs&hl=en-US&gl=US&ceid=US:en", "world", 0.8, "global-markets"),
]

SECTIONS = {
    "stocks":        ("Stocks", ["sensex", "nifty", "dalal street", "d-street", "bse", "nse", "stock market", "share market",
                      "shares", "stocks", "equities", "equity", "ipo", "fpo", "listing", "f&o", "futures", "options",
                      "fii", "dii", "midcap", "smallcap", "small-cap", "mid-cap", "largecap", "bank nifty", "market cap",
                      "rally", "selloff", "sell-off", "bull", "bear", "block deal", "qip", "buyback", "index", "vix",
                      "closing bell", "opening bell", "stock", "gainers", "losers", "brokerage", "target price", "demat"]),
    "global-markets": ("Global Markets", ["wall street", "s&p 500", "s&p500", "nasdaq", "dow jones", "dow ", "nikkei", "hang seng",
                      "kospi", "ftse", "dax", "stoxx", "shanghai composite", "us stocks", "us markets", "asian markets",
                      "european markets", "global markets", "world stocks", "futures", "treasury yields", "magnificent seven",
                      "nvidia", "tesla", "apple", "microsoft", "alphabet", "amazon", "meta ", "chip stocks", "ai stocks",
                      "us stock", "u.s. stock", "russell", "vix", "earnings season"]),
    "economy":       ("Economy & GDP", ["gdp", "growth", "economy", "economic", "recession", "slowdown", "fiscal", "deficit",
                      "trade deficit", "current account", "exports", "imports", "manufacturing", "pmi", "iip", "industrial output",
                      "industrial production", "jobs", "unemployment", "employment", "payrolls", "labour", "labor market",
                      "consumption", "demand", "investment", "capex", "infrastructure", "world bank", "imf", "oecd", "moody",
                      "s&p global", "fitch", "rating", "outlook", "gst collection", "tax collection", "revenue", "stimulus",
                      "productivity", "credit growth", "monsoon", "rural demand", "services sector", "core sector"]),
    "inflation":     ("Inflation & Prices", ["inflation", "cpi", "wpi", "consumer price", "wholesale price", "price index",
                      "prices rise", "price rise", "food prices", "vegetable prices", "cost of living", "pce", "ppi",
                      "producer price", "disinflation", "deflation", "stagflation", "price pressure", "core inflation",
                      "retail inflation", "fuel price", "petrol price", "diesel price", "lpg", "onion", "tomato"]),
    "central-banks": ("RBI & Central Banks", ["rbi", "reserve bank", "central bank", "monetary policy", "mpc", "repo rate",
                      "rate cut", "rate hike", "policy rate", "fed ", "federal reserve", "fomc", "powell", "ecb", "lagarde",
                      "bank of england", "boe", "bank of japan", "boj", "pboc", "people's bank", "liquidity", "crr", "slr",
                      "governor", "malhotra", "interest rate", "interest rates", "rate decision", "hawkish", "dovish",
                      "quantitative", "omo", "vrr", "vrrr", "swiss national bank", "rba", "rbnz", "bank of canada"]),
    "bonds":         ("Bonds & Rates", ["bond", "bonds", "yield", "yields", "g-sec", "gsec", "gilt", "treasury", "treasuries",
                      "10-year", "10 year", "debt market", "sovereign", "fixed income", "coupon", "auction", "borrowing",
                      "state development loan", "sdl", "bond index", "jpmorgan index", "credit spread", "junk bond",
                      "corporate bond", "ncd", "debenture", "term premium", "yield curve", "bund", "jgb"]),
    "fx-commodities": ("Currency & Commodities", ["rupee", "dollar", "usd", "inr", "forex", "currency", "yen", "euro", "yuan",
                      "pound", "sterling", "dxy", "crude", "oil", "brent", "wti", "opec", "gold", "silver", "copper", "metal",
                      "metals", "commodity", "commodities", "mcx", "natural gas", "lng", "coal", "steel", "aluminium",
                      "iron ore", "wheat", "rice", "sugar", "cotton", "palm oil", "bullion", "petrol", "diesel", "forex reserves",
                      "reserves"]),
    "corporate":     ("Corporate & Earnings", ["earnings", "q1", "q2", "q3", "q4", "quarterly", "results", "profit", "net profit",
                      "loss", "revenue", "guidance", "merger", "acquisition", "acquire", "acquires", "takeover", "stake",
                      "deal", "m&a", "ceo", "cfo", "chairman", "board", "dividend", "shareholders", "agm", "layoffs",
                      "expansion", "plant", "order win", "contract", "reliance", "tata", "adani", "infosys", "tcs", "wipro",
                      "hdfc", "icici", "sbi", "bajaj", "maruti", "mahindra", "airtel", "jio", "zomato", "swiggy", "paytm",
                      "ola", "vedanta", "jsw", "l&t", "larsen", "itc", "hul", "hindustan unilever", "nestle", "ongc", "ntpc",
                      "coal india", "oracle", "nvidia", "apple", "microsoft", "boeing", "startup", "unicorn", "funding round"]),
    "policy":        ("Policy & Government", ["budget", "sitharaman", "finance minister", "finance ministry", "government",
                      "govt", "cabinet", "parliament", "bill", "gst", "income tax", "tax", "sebi", "regulator", "regulation",
                      "regulatory", "pli", "scheme", "subsidy", "disinvestment", "privatisation", "privatization", "psu",
                      "policy", "modi", "niti aayog", "cag", "cbdt", "cbic", "irdai", "pfrda", "ministry", "capital gains",
                      "customs duty", "excise", "fdi", "fpi rules", "compliance", "ban", "crackdown", "antitrust", "cci",
                      "supreme court", "high court", "white house", "congress", "senate", "treasury secretary", "trump"]),
    "geopolitics":   ("Geopolitics & Trade", ["tariff", "tariffs", "trade war", "trade deal", "trade talks", "sanctions",
                      "war", "conflict", "ceasefire", "attack", "strike", "missile", "iran", "israel", "gaza", "ukraine",
                      "russia", "china", "beijing", "taiwan", "red sea", "hormuz", "west asia", "middle east", "geopolitical",
                      "nato", "g7", "g20", "brics", "wto", "export controls", "chip curbs", "supply chain", "diplomatic",
                      "election", "elections", "coup", "protests", "north korea", "houthi", "pakistan", "bangladesh"]),
    "banking":       ("Banking & Finance", ["bank", "banks", "banking", "nbfc", "lender", "lenders", "loan", "loans", "credit",
                      "deposit", "deposits", "npa", "bad loans", "provisions", "microfinance", "fintech", "upi", "payments",
                      "insurance", "insurer", "mutual fund", "amc", "sip", "asset management", "private equity", "pension",
                      "epfo", "nps", "housing finance", "home loan", "credit card", "digital lending", "co-operative bank",
                      "psu bank", "private bank", "wealth", "brokerage", "broker", "exchange", "clearing", "margin"]),
    "crypto":        ("Crypto", ["bitcoin", "btc", "ethereum", "ether", "crypto", "cryptocurrency", "stablecoin", "blockchain",
                      "coinbase", "binance", "solana", "xrp", "dogecoin", "token", "web3", "defi", "digital asset", "cbdc",
                      "digital rupee", "e-rupee"]),
}
SECTION_ORDER = list(SECTIONS.keys())

INDIA_TERMS = ["india", "indian", "sensex", "nifty", "rbi", "rupee", "sebi", "dalal", "mumbai", "delhi", "bengaluru",
    "crore", "lakh", "adani", "reliance", "tata", "infosys", "hdfc", "icici", "sbi", "modi", "sitharaman", "gst", "nse",
    "bse", "fii", "dii", "d-street", "bharat", "irdai", "niti", "gujarat", "maharashtra", "kolkata", "chennai", "hyderabad",
    "pib", "lok sabha", "rajya sabha", "bajaj", "mahindra", "airtel", "jio", "zomato", "paytm", "vedanta", "jsw", "l&t",
    "itc", "hul", "ongc", "ntpc", "coal india", "psu", "epfo", "upi", "mcx", "iip", "wpi", "malhotra", "bank nifty",
    "indian rupee", "new delhi", "pan card", "aadhaar"]
WORLD_TERMS = ["wall street", "s&p 500", "nasdaq", "dow jones", "fed ", "federal reserve", "fomc", "powell", "ecb", "eurozone",
    "bank of england", "bank of japan", "boj", "pboc", "china", "chinese", "japan", "europe", "european", "u.s.", "us ",
    "america", "american", "united states", "uk ", "britain", "british", "germany", "german", "france", "french", "trump",
    "white house", "congress", "senate", "iran", "israel", "russia", "ukraine", "taiwan", "korea", "nikkei", "hang seng",
    "opec", "imf", "world bank", "wto", "nvidia", "tesla", "apple", "microsoft", "alphabet", "amazon", "oracle", "boeing",
    "treasury", "treasuries", "dollar index", "bitcoin", "crypto", "brent", "wti", "gold price", "global", "world",
    "london", "new york", "tokyo", "beijing", "hong kong", "singapore", "canada", "australia", "brazil", "mexico",
    "middle east", "west asia", "gaza", "nato", "g7", "g20"]

IMPORTANT = {"rbi": 3, "reserve bank": 3, "federal reserve": 3, "fed ": 2, "fomc": 3, "gdp": 3, "inflation": 3, "cpi": 2,
    "rate cut": 3, "rate hike": 3, "repo rate": 3, "monetary policy": 3, "tariff": 2, "tariffs": 2, "sensex": 2, "nifty": 2,
    "rupee": 2, "crude": 1, "brent": 1, "bond": 1, "yield": 1, "yields": 1, "budget": 2, "sebi": 2, "record high": 2,
    "record low": 2, "all-time high": 2, "crash": 2, "plunge": 2, "surge": 1, "rally": 1, "sanctions": 2, "war": 1,
    "opec": 2, "jobs report": 2, "payrolls": 2, "recession": 2, "fitch": 1, "moody": 1, "s&p global": 1, "downgrade": 2,
    "upgrade": 1, "ipo": 1, "earnings": 1, "results": 1, "wpi": 2, "iip": 2, "pmi": 2, "fdi": 1, "fii": 1, "sitharaman": 2,
    "malhotra": 2, "powell": 2, "ecb": 2, "boj": 2, "trade deal": 3, "trade war": 3, "ceasefire": 2, "market wrap": 2,
    "closing bell": 2, "stock market today": 2, "market highlights": 2, "taking stock": 2, "ahead of market": 1}

JUNK = re.compile(r"(stocks?\s+to\s+(buy|watch|track)|buy\s+or\s+sell|top\s+(gainers|losers)|stock\s+radar|trade\s+setup|"
    r"technical\s+(view|pick|breakout)|target\s+price|multibagger|horoscope|stock\s+picks?|f&o\s+radar|"
    r"\btips?\b|how\s+to\s+invest|nfo\b|\bsip\b\s+calculator|tax\s+saving|should\s+you\s+(buy|invest|subscribe)|"
    r"penny\s+stock|stocks?\s+in\s+focus|hot\s+stocks|stock\s+of\s+the\s+day|brokerage\s+radar|"
    r"investment\s+ideas?|chart\s+check|options\s+strategy|weekly\s+options|expert\s+(view|picks)|"
    r"trading\s+guide|recommendations?\b|share\s+price\s+highlights|stock\s+price\s+history|price\s+history|"
    r"gmp\b|grey\s+market\s+premium|subscription\s+status|day\s+\d+\s+live|quiz|crossword|sudoku|"
    r"gift\s+nifty\s+signals|live\s+updates?\s*:|live\s+blog|share\s+price\s+live|share\s+price\s+today|"
    r"why\s+is\s+\S+\s+share\s+(price\s+)?(rising|falling)|opinion\s*\||mint\s+primer|explainer\s*:|"
    r"webinar|advertorial|sponsored|partner\s+content|best\s+credit\s+cards?|best\s+savings|best\s+fixed|"
    r"fd\s+rates|fixed\s+deposit\s+rates|senior\s+citizens?|pension\s+scheme|nps\s+account|"
    r"tds\b|itr\b|income\s+tax\s+return|form\s+16|pan\s+card|aadhaar|epf\s+(balance|withdrawal))", re.I)

PUBLISHER_ALIAS = {"livemint.com": "Mint", "livemint": "Mint", "the economic times": "Economic Times",
    "economictimes.indiatimes.com": "Economic Times", "bfsi.economictimes.indiatimes.com": "ET BFSI",
    "cnbc tv18": "CNBC-TV18", "cnbctv18": "CNBC-TV18", "moneycontrol.com": "Moneycontrol", "bloomberg.com": "Bloomberg",
    "businesstoday.in": "Business Today", "the new york times": "NYT", "the wall street journal": "WSJ",
    "financial times": "FT", "the hindu businessline": "BusinessLine", "business-standard.com": "Business Standard",
    "the financial express": "Financial Express", "financialexpress.com": "Financial Express", "reuters.com": "Reuters",
    "ndtvprofit.com": "NDTV Profit", "the times of india": "Times of India", "hindustan times": "Hindustan Times",
    "the indian express": "Indian Express", "theprint": "ThePrint", "ap news": "AP", "associated press": "AP",
    "the guardian": "The Guardian", "bbc": "BBC", "bbc news": "BBC", "cnbc": "CNBC", "marketwatch": "MarketWatch",
    "barron's": "Barron's", "nikkei asia": "Nikkei Asia", "south china morning post": "SCMP", "euronews.com": "Euronews",
    "dw": "DW", "the economist": "The Economist", "business insider": "Business Insider", "fortune": "Fortune",
    "zee business": "Zee Business", "et now": "ET Now", "news18": "News18", "deccan herald": "Deccan Herald",
    "the telegraph": "Telegraph", "outlook business": "Outlook Business", "the hindu": "The Hindu", "ptinews": "PTI",
    "the print": "ThePrint", "investing.com": "Investing.com", "yahoo finance": "Yahoo Finance", "forbes": "Forbes",
    "cnn": "CNN", "the washington post": "Washington Post", "politico": "Politico", "axios": "Axios",
    "france 24": "France 24", "al jazeera": "Al Jazeera", "ft.com": "FT", "wsj": "WSJ", "nyt": "NYT"}
GOOD_PUBLISHERS = {"Reuters", "Bloomberg", "Moneycontrol", "NDTV Profit", "Business Today", "Fortune India", "The Hindu",
    "Times of India", "Hindustan Times", "Indian Express", "ThePrint", "Financial Express", "CNBC", "CNBC-TV18", "Mint",
    "Economic Times", "ET BFSI", "Business Standard", "BusinessLine", "AP", "Al Jazeera", "The Guardian", "BBC", "NYT", "WSJ",
    "FT", "MarketWatch", "Barron's", "Forbes", "Nikkei Asia", "SCMP", "Euronews", "DW", "France 24", "Politico", "Axios",
    "Yahoo Finance", "Fortune", "Business Insider", "The Economist", "PTI", "Deccan Herald", "Telegraph", "News18",
    "Zee Business", "ET Now", "Outlook Business", "CNN", "Washington Post", "Investing.com", "Morningstar", "Investopedia"}

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
STOP = set("the a an of in on at to for and or as by with from is are was were be been its it this that these those "
           "after amid over up down into out about vs than more less new says said say will may can could would".split())


def fetch(url, timeout=25, retries=3):
    import time
    last = None
    ua = "Mozilla/5.0" if "finance.yahoo.com" in url else UA
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1) + (2.0 if "429" in repr(e) else 0))
    raise last


def clean_text(s):
    if not s:
        return ""
    s = html.unescape(s)
    s = TAG_RE.sub(" ", s)
    s = html.unescape(s)
    s = s.replace("#39;", "'").replace("&nbsp;", " ")
    return WS_RE.sub(" ", s).strip()


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        d = email.utils.parsedate_to_datetime(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d.astimezone(dt.timezone.utc)
    except Exception:
        pass
    try:
        d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d.astimezone(dt.timezone.utc)
    except Exception:
        return None


def local(tag):
    return tag.split("}")[-1] if "}" in tag else tag


def parse_feed(xml_bytes):
    """Yield dicts with title, link, summary, date, publisher (optional)."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        txt = xml_bytes.decode("utf-8", "ignore")
        txt = re.sub(r"[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD]", "", txt)
        txt = re.sub(r"&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", txt)
        txt = re.sub(r"<\?xml[^>]*\?>", "", txt, count=1).lstrip()
        root = ET.fromstring(txt)
    items = []
    for el in root.iter():
        if local(el.tag) in ("item", "entry"):
            items.append(el)
    for it in items:
        d = {"title": "", "link": "", "summary": "", "date": None, "publisher": None}
        for ch in it:
            t = local(ch.tag)
            txt = (ch.text or "").strip()
            if t == "title":
                d["title"] = clean_text(txt)
            elif t == "link":
                href = ch.get("href")
                if href and (not txt) and ch.get("rel") in (None, "alternate"):
                    d["link"] = href.strip()
                elif txt:
                    d["link"] = txt
            elif t in ("description", "summary", "content", "encoded") and not d["summary"]:
                d["summary"] = clean_text(txt)
            elif t in ("pubDate", "published", "updated", "date") and not d["date"]:
                d["date"] = parse_date(txt)
            elif t == "source" and txt:
                d["publisher"] = clean_text(txt)
        if d["title"] and d["link"]:
            yield d


def norm_words(title):
    w = re.findall(r"[a-z0-9&$%]+", title.lower())
    return [x for x in w if x not in STOP and len(x) > 1]


MOVE_RE = re.compile(r"\b(shares?|stock)\b.*\b(rally|rallies|jump|jumps|surge|surges|fall|falls|drop|drops|slump|slumps|plunge|plunges|soar|soars|gain|gains|rise|rises|tank|tanks|crash|crashes|hit|hits|slip|slips|climb|climbs|dip|dips|up|down)\b|share price", re.I)
GLOBAL_RE = re.compile(r"^(global market|us stocks?|wall street|asian (markets|shares|stocks)|european (shares|stocks|markets)|dow jones|s&p 500|nasdaq|nikkei|hang seng)", re.I)
INDIA_MKT_RE = re.compile(r"^(sensex|nifty|stock market (today|highlights|live)|market (wrap|pulse|highlights)|ahead of market|taking stock|d-street|dalal street|closing bell|opening bell|market outlook)", re.I)


def classify(text, default, title=""):
    t = " " + text.lower() + " "
    tt = " " + title.lower() + " "
    if title and GLOBAL_RE.search(title.strip()):
        return "global-markets", {}
    if title and INDIA_MKT_RE.search(title.strip()):
        return "stocks", {}
    scores = {}
    for key, (label, kws) in SECTIONS.items():
        s = 0.0
        for kw in kws:
            k = kw.strip()
            pat = r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])"
            n = len(re.findall(pat, t))
            if n:
                s += 1.0 + 0.5 * min(n - 1, 2)
                if re.search(pat, tt):
                    s += 1.0
        scores[key] = s
    if title and MOVE_RE.search(title):
        scores["stocks"] = scores.get("stocks", 0) + 3.0
    # title-weighted tie-breaks: prefer more specific sections
    specificity = {"crypto": 1.6, "inflation": 1.5, "central-banks": 1.45, "bonds": 1.4, "fx-commodities": 1.2,
                   "geopolitics": 1.15, "policy": 1.0, "economy": 1.0, "banking": 1.0, "corporate": 0.9,
                   "global-markets": 1.0, "stocks": 0.85}
    best, bestv = default, 0.0
    for k, v in scores.items():
        v2 = v * specificity[k]
        if v2 > bestv:
            best, bestv = k, v2
    if bestv < 1.0:
        return default, scores
    return best, scores


def region_of(text, hint):
    t = " " + text.lower() + " "
    ind = sum(1 for k in INDIA_TERMS if re.search(r"(?<![a-z0-9])" + re.escape(k.strip()) + r"(?![a-z0-9])", t))
    wld = sum(1 for k in WORLD_TERMS if re.search(r"(?<![a-z0-9])" + re.escape(k.strip()) + r"(?![a-z0-9])", t))
    if ind > wld:
        return "india"
    if wld > ind:
        return "world"
    return hint


def importance(text):
    t = " " + text.lower() + " "
    return sum(v for k, v in IMPORTANT.items() if k in t)


def run_feeds():
    results = []
    def job(feed):
        name, url, hint, weight, default = feed
        try:
            raw = fetch(url)
            items = list(parse_feed(raw))
            return (feed, items, None)
        except Exception as e:
            return (feed, [], repr(e))
    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        for feed, items, err in ex.map(job, FEEDS):
            results.append((feed, items, err))
    return results


def build_articles():
    fetched = run_feeds()
    raw = []
    stats = {}
    for (name, url, hint, weight, default), items, err in fetched:
        stats[url] = {"source": name, "count": len(items), "error": err}
        for it in items:
            d = it["date"]
            if d is None:
                continue
            age_h = (NOW - d).total_seconds() / 3600
            if age_h > MAX_AGE_H or age_h < -2:
                continue
            title = it["title"]
            publisher = name
            if name == "Google News":
                # "Headline - Publisher"
                if it["publisher"]:
                    publisher = it["publisher"]
                    if title.endswith(" - " + publisher):
                        title = title[: -len(" - " + publisher)].strip()
                elif " - " in title:
                    title, publisher = title.rsplit(" - ", 1)
                publisher = PUBLISHER_ALIAS.get(publisher.lower(), publisher)
                if publisher not in GOOD_PUBLISHERS:
                    continue
            summary = it["summary"]
            if summary.lower().startswith(title.lower()[:40]):
                summary = ""
            if name == "Google News":
                summary = ""
            if len(summary) > 320:
                summary = summary[:317].rsplit(" ", 1)[0] + "…"
            if JUNK.search(title):
                continue
            text = title + " " + summary
            section, _ = classify(text, default, title)
            region = region_of(text, hint)
            # Al Jazeera / WSJ world: only keep economy-related
            if name in ("Al Jazeera",) and section in ("geopolitics",) and importance(text) < 2:
                continue
            aid = hashlib.sha1(it["link"].encode()).hexdigest()[:12]
            raw.append({
                "id": aid, "title": title, "summary": summary, "source": publisher, "url": it["link"],
                "publishedAt": d.isoformat().replace("+00:00", "Z"), "section": section, "region": region,
                "_age": age_h, "_weight": weight, "_imp": importance(text), "_words": set(norm_words(title)),
            })
    # de-duplicate by url and by title similarity
    seen_url = set()
    uniq = []
    for a in sorted(raw, key=lambda x: x["_age"]):
        key = re.sub(r"[?#].*$", "", a["url"]).rstrip("/")
        if key in seen_url:
            continue
        seen_url.add(key)
        uniq.append(a)
    clusters = []  # each: dict with rep article and members
    for a in uniq:
        placed = False
        for c in clusters:
            r = c["rep"]
            w1, w2 = a["_words"], r["_words"]
            if not w1 or not w2:
                continue
            j = len(w1 & w2) / len(w1 | w2)
            if j >= 0.5 or (len(w1 & w2) >= 5 and j >= 0.35):
                c["members"].append(a)
                # prefer higher-weight source as representative
                if a["_weight"] * (1 + a["_imp"] * 0.05) > r["_weight"] * (1 + r["_imp"] * 0.05):
                    c["rep"] = a
                placed = True
                break
        if not placed:
            clusters.append({"rep": a, "members": [a]})
    out = []
    for c in clusters:
        a = c["rep"]
        n = len(c["members"])
        recency = max(0.0, 1.0 - a["_age"] / MAX_AGE_H)
        score = (a["_weight"] * 2.0) + (a["_imp"] * 0.6) + (recency * 3.0) + (min(n - 1, 4) * 1.2)
        if a["region"] == "india":
            score += 0.6
        a["score"] = round(score, 2)
        a["sources"] = sorted({m["source"] for m in c["members"]})
        out.append(a)
    out.sort(key=lambda x: -x["score"])
    # caps: per section and per source, overall
    per_sec, per_src, final = {}, {}, []
    for a in out:
        if per_sec.get(a["section"], 0) >= 28 or per_src.get(a["source"], 0) >= 32:
            continue
        per_sec[a["section"]] = per_sec.get(a["section"], 0) + 1
        per_src[a["source"]] = per_src.get(a["source"], 0) + 1
        final.append(a)
        if len(final) >= 170:
            break
    for a in final:
        for k in ("_age", "_weight", "_imp", "_words"):
            a.pop(k, None)
    return final, stats


SYMBOLS = [
    ("^NSEI", "Nifty 50", "India", "index"), ("^BSESN", "Sensex", "India", "index"),
    ("^NSEBANK", "Bank Nifty", "India", "index"), ("^INDIAVIX", "India VIX", "India", "vol"),
    ("INR=X", "USD/INR", "FX", "fx"), ("DX-Y.NYB", "Dollar Index", "FX", "fx"),
    ("^TNX", "US 10Y Yield", "Rates", "yield"),
    ("BZ=F", "Brent Crude", "Commodities", "usd"), ("GC=F", "Gold", "Commodities", "usd"), ("SI=F", "Silver", "Commodities", "usd"),
    ("^GSPC", "S&P 500", "World", "index"), ("^IXIC", "Nasdaq", "World", "index"), ("^DJI", "Dow Jones", "World", "index"),
    ("^N225", "Nikkei 225", "World", "index"), ("^HSI", "Hang Seng", "World", "index"), ("^STOXX50E", "Euro Stoxx 50", "World", "index"),
    ("000001.SS", "Shanghai", "World", "index"), ("BTC-USD", "Bitcoin", "Crypto", "usd"),
]


def build_markets():
    quotes = []
    def job(sym):
        s, label, group, kind = sym
        try:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.request.quote(s, safe="") + "?range=1mo&interval=1d"
            j = json.loads(fetch(url))
            res = j["chart"]["result"][0]
            meta = res["meta"]
            closes = res["indicators"]["quote"][0].get("close") or []
            ts = res.get("timestamp") or []
            pts = [(t, c) for t, c in zip(ts, closes) if c is not None]
            if not pts:
                return None
            price = meta.get("regularMarketPrice") or pts[-1][1]
            # If the last bar is today's live session, previous close is the bar before it.
            last_t = pts[-1][0]
            mkt_t = meta.get("regularMarketTime") or last_t
            same_day = abs(mkt_t - last_t) < 20 * 3600
            prev = pts[-2][1] if (same_day and len(pts) >= 2) else pts[-1][1]
            if same_day and abs(pts[-1][1] - price) > 1e-9:
                pts[-1] = (pts[-1][0], price)
            elif not same_day:
                pts.append((mkt_t, price))
            week_ref = pts[-6][1] if len(pts) >= 6 else pts[0][1]
            month_ref = pts[0][1]
            return {
                "symbol": s, "label": label, "group": group, "kind": kind,
                "price": round(price, 4), "prevClose": round(prev, 4),
                "change": round(price - prev, 4), "changePct": round((price / prev - 1) * 100, 3) if prev else 0,
                "weekPct": round((price / week_ref - 1) * 100, 3) if week_ref else 0,
                "monthPct": round((price / month_ref - 1) * 100, 3) if month_ref else 0,
                "high52": meta.get("fiftyTwoWeekHigh"), "low52": meta.get("fiftyTwoWeekLow"),
                "currency": meta.get("currency"), "asOf": dt.datetime.fromtimestamp(mkt_t, dt.timezone.utc).isoformat().replace("+00:00", "Z"),
                "spark": [round(c, 4) for _, c in pts[-12:]],
                "sparkDates": [dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d") for t, _ in pts[-12:]],
            }
        except Exception as e:
            return {"symbol": s, "label": label, "group": group, "kind": kind, "error": repr(e)}
    import time
    for sym in SYMBOLS:
        q = job(sym)
        if q:
            quotes.append(q)
        time.sleep(0.4)
    return quotes


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    articles, stats = build_articles()
    markets = build_markets()
    with open(os.path.join(OUT, "articles.json"), "w") as f:
        json.dump({"generatedAt": NOW.isoformat().replace("+00:00", "Z"), "articles": articles, "feedStats": stats}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "markets.json"), "w") as f:
        json.dump({"updatedAt": NOW.isoformat().replace("+00:00", "Z"), "quotes": markets}, f, ensure_ascii=False, indent=1)
    secs = {}
    for a in articles:
        secs[a["section"]] = secs.get(a["section"], 0) + 1
    print("articles:", len(articles), "sections:", json.dumps(secs))
    print("regions:", {r: sum(1 for a in articles if a["region"] == r) for r in ("india", "world")})
    for url, s in stats.items():
        if s["error"] or s["count"] == 0:
            print("FEED ISSUE:", s["source"], url, s["error"])
    print("quotes:", len(markets), "errors:", [q["symbol"] for q in markets if q.get("error")])
