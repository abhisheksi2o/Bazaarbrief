# Bazaar Brief

A daily financial and economic newspaper for India and the world: one edition every morning at 06:00 IST, as a four-page PDF in a Mint-style broadsheet format, a website and a mobile app. It runs entirely on GitHub Actions and costs nothing: no Claude usage, no API key. Two deployments share one pipeline:

1. **Standalone site (GitHub Pages)** – https://abhisheksi2o.github.io/Bazaarbrief/ – built by GitHub Actions, no login needed, installable on a phone as a web app. This is the base for the Play Store / App Store build.
2. **Claude artifact** – https://claude.ai/code/artifact/b39ceaff-f50f-42a1-b31d-b4357b2f4808 – the original version, refreshed by claude.ai Routines.

## Files

- `pipeline.py` – fetches ~30 Indian and global feeds plus Yahoo Finance quotes, cleans, de-duplicates, classifies into 12 sections and 2 regions, ranks. `--merge` carries editorial notes over from the previous feed.
- `desk.py` – the free desk: rule-based junk removal, story order (market wrap, macro drivers, policy, corporate, global), the recap of the day from the day's quotes and top headlines, and the recap of the week on Saturdays. This is what runs by default.
- `editor.py` – optional: the same jobs done by Claude through the API ("why it matters" notes, written recaps). Only used when the `ANTHROPIC_API_KEY` secret is set (pay-as-you-go).
- `build.py` – orchestrates a run (`--mode edition`) and writes the static site to `site/`, then calls `paper.py`.
- `paper.py` – the four-page paper: page 1 front page, page 2 Markets & Money, page 3 Economy & Policy, page 4 World & Corporate. Builds HTML (salmon paper, serif headlines, flowing columns) and prints it to PDF with headless Chromium. Output: `site/paper/latest.pdf`, `site/paper/bazaar-brief-YYYY-MM-DD.pdf`, `site/paper/index.json` (last 14 editions).
- `web/` – the standalone app: `index.html`, web manifest, service worker, icons. Reads `data/*.json` next to it.
- `.github/workflows/desk.yml` – the 06:00 IST daily build, plus a build on every push to `main`.
- `editorial/` – optional: an edited feed and recaps pushed by a claude.ai Routine. When a file here is less than 12 hours old, `build.py` uses it instead of `desk.py`; otherwise it is ignored. The Routine is paused by default because it uses Claude subscription tokens.
- `app.html`, `ROUTINE.md`, `ROUTINE-HOURLY.md`, `seed/` – the Claude-artifact deployment.

## Setting up the standalone site (one time)

1. Repository **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. **Actions → Bazaar Brief desk → Run workflow** (mode `edition`) for the first build, or wait for the next 06:00 IST run.
3. Optional, only if you want Claude-written "why it matters" notes and recaps: either add the secret `ANTHROPIC_API_KEY` (pay-as-you-go) or re-enable the claude.ai Routine described in `ROUTINE.md` (uses subscription tokens).

Published data layout: `data/feed.json` (stories), `data/markets.json` (quotes), `data/archive.json` (last 14 daily recaps, last 8 weekly), `data/status.json` (last build).

## Local run

```
pip install playwright && python -m playwright install chromium
python3 build.py --mode edition --site-url https://abhisheksi2o.github.io/Bazaarbrief/ --out site
python3 -m http.server -d site 8000   # open http://localhost:8000
```
`--desk rules` forces the free desk even when `editorial/` is fresh.

## Claude-artifact deployment: database layout

| Document | Content |
| --- | --- |
| `feed/latest` | ranked stories: id, title, summary, source, url, publishedAt, section, region, why |
| `markets/latest` | quotes with 1D / 5D / 1M moves and 12-session sparklines |
| `dailies/YYYY-MM-DD` | recap of the day (title, standfirst, scoreboard, grouped bullets, watch list) |
| `weeklies/YYYY-Www` | recap of the week |
| `pipeline/script` | the pipeline source |

## Schedule

- 06:00 IST daily: GitHub Actions fetches the last 24 hours of news and quotes, runs `desk.py`, writes the site and the four-page PDF, and deploys. About 5 minutes, free, no Claude involved.
- The paper is at https://abhisheksi2o.github.io/Bazaarbrief/paper/latest.pdf and listed on the site and in the app. The last 14 editions are kept.
- No other refreshes run during the day. Every push to `main` also rebuilds the site.

Each run shows up under **Actions** and as one `github-pages` deployment; these are records of the same site being rebuilt, not copies of the project.

## Optional: the Claude desk

`ROUTINE.md` is the prompt for a claude.ai Routine that edits the paper with Claude (why-notes, written recaps) and pushes `editorial/`. It is paused because every run uses subscription tokens; re-enable it from the Routines list on claude.ai if you want it back. The build automatically prefers a fresh Routine edition over `desk.py`.
