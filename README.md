# Bazaar Brief

A daily financial and economic news desk for India and the world. Two deployments share one pipeline:

1. **Standalone site (GitHub Pages)** – https://abhisheksi2o.github.io/Bazaarbrief/ – built by GitHub Actions, no login needed, installable on a phone as a web app. This is the base for the Play Store / App Store build.
2. **Claude artifact** – https://claude.ai/code/artifact/b39ceaff-f50f-42a1-b31d-b4357b2f4808 – the original version, refreshed by claude.ai Routines.

## Files

- `pipeline.py` – fetches ~30 Indian and global feeds plus Yahoo Finance quotes, cleans, de-duplicates, classifies into 12 sections and 2 regions, ranks. `--merge` carries editorial notes over from the previous feed.
- `editor.py` – the editorial layer through the Claude API: section fixes, junk removal, story order, "why it matters" notes, recap of the day, recap of the week. Model defaults to `claude-opus-5`; set the `DESK_MODEL` repository variable to `claude-sonnet-5` for a cheaper desk.
- `build.py` – orchestrates a run (`--mode wire|edition|weekend`) and writes the static site to `site/`.
- `web/` – the standalone app: `index.html`, web manifest, service worker, icons. Reads `data/*.json` next to it.
- `.github/workflows/desk.yml` – the schedule: hourly wire refresh, weekday editions at 07:00 / 16:30 / 22:00 IST, weekend edition at 09:00 IST.
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

## Schedule (Routines)

- Every hour: wire refresh. Runs `pipeline.py --merge` against the current feed so new stories arrive hourly while editorial notes on existing stories are kept.
- Weekdays at 07:00, 16:30 and 22:00 IST: morning brief, closing wrap, late edition (editorial pass, why-it-matters notes, recap of the day).
- Saturday and Sunday at 09:00 IST: weekend edition plus recap of the week.

Change or pause them from the Routines list on claude.ai.
