# Bazaar Brief

A daily financial and economic newspaper for India and the world: one edition every morning at 06:00 IST, as a four-page PDF in a Mint-style broadsheet format, a website and a mobile app. Two deployments share one pipeline:

1. **Standalone site (GitHub Pages)** – https://abhisheksi2o.github.io/Bazaarbrief/ – built by GitHub Actions, no login needed, installable on a phone as a web app. This is the base for the Play Store / App Store build.
2. **Claude artifact** – https://claude.ai/code/artifact/b39ceaff-f50f-42a1-b31d-b4357b2f4808 – the original version, refreshed by claude.ai Routines.

## Files

- `pipeline.py` – fetches ~30 Indian and global feeds plus Yahoo Finance quotes, cleans, de-duplicates, classifies into 12 sections and 2 regions, ranks. `--merge` carries editorial notes over from the previous feed.
- `editor.py` – the editorial layer through the Claude API: section fixes, junk removal, story order, "why it matters" notes, recap of the day, recap of the week. Model defaults to `claude-opus-5`; set the `DESK_MODEL` repository variable to `claude-sonnet-5` for a cheaper desk.
- `build.py` – orchestrates a run (`--mode edition`) and writes the static site to `site/`, then calls `paper.py`.
- `paper.py` – the four-page paper: page 1 front page, page 2 Markets & Money, page 3 Economy & Policy, page 4 World & Corporate. Builds HTML (salmon paper, serif headlines, flowing columns) and prints it to PDF with headless Chromium. Output: `site/paper/latest.pdf`, `site/paper/bazaar-brief-YYYY-MM-DD.pdf`, `site/paper/index.json` (last 14 editions).
- `web/` – the standalone app: `index.html`, web manifest, service worker, icons. Reads `data/*.json` next to it.
- `.github/workflows/desk.yml` – builds on every push of `editorial/` (the desk's morning push) with a 06:45 IST fallback schedule.
- `editorial/` – edited feed and recaps pushed by the claude.ai Routines after every edition (covered by a Claude subscription, no API key needed). `build.py` uses these when `ANTHROPIC_API_KEY` is absent.
- `app.html`, `ROUTINE.md`, `ROUTINE-HOURLY.md`, `seed/` – the Claude-artifact deployment.

## Setting up the standalone site (one time)

1. Repository **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. Optional: **Settings → Secrets and variables → Actions → New repository secret** `ANTHROPIC_API_KEY` (pay-as-you-go, from https://console.anthropic.com). Not needed when the claude.ai Routines push `editorial/`; the site then gets recaps and why-notes from there.
3. Optional: **Variables → New repository variable** `DESK_MODEL` = `claude-sonnet-5` to cut editorial cost by about 60%.
4. **Actions → Bazaar Brief desk → Run workflow** (mode `edition`) for the first build, or wait for the next scheduled run.

Published data layout: `data/feed.json` (stories), `data/markets.json` (quotes), `data/archive.json` (last 14 daily recaps, last 8 weekly), `data/status.json` (last build).

## Local run

```
pip install anthropic
export ANTHROPIC_API_KEY=...          # optional
python3 build.py --mode edition --site-url https://abhisheksi2o.github.io/Bazaarbrief/ --out site
python3 -m http.server -d site 8000   # open http://localhost:8000
```

## Claude-artifact deployment: database layout

| Document | Content |
| --- | --- |
| `feed/latest` | ranked stories: id, title, summary, source, url, publishedAt, section, region, why |
| `markets/latest` | quotes with 1D / 5D / 1M moves and 12-session sparklines |
| `dailies/YYYY-MM-DD` | recap of the day (title, standfirst, scoreboard, grouped bullets, watch list) |
| `weeklies/YYYY-Www` | recap of the week |
| `pipeline/script` | the pipeline source |

## Schedule

- 06:00 IST daily: the desk Routine ("Bazaar Brief – morning paper") fetches the last 24 hours, edits, writes the recap (and the recap of the week on Saturdays), publishes to the artifact and pushes `editorial/` here.
- The push builds the site and the PDF within a few minutes; the paper is at https://abhisheksi2o.github.io/Bazaarbrief/paper/latest.pdf and listed on the site and in the app.
- No other refreshes run during the day.

The editorial Routines fire into one standing claude.ai session that has this repository checked out with push access ("Bazaar Brief desk (standing editorial session)"). Each edition writes to the artifact database and pushes `editorial/` here, which triggers the site build. Change or pause the Routines from the Routines list on claude.ai; if the standing session is ever archived, create a new session with this repo as its source and re-point the Routines at it.
