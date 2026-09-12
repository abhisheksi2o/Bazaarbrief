# Bazaar Brief

A daily financial and economic news desk for India and the world, published as a Claude artifact.

- App: https://claude.ai/code/artifact/b39ceaff-f50f-42a1-b31d-b4357b2f4808
- `app.html` – the page (single file, no build step). Reads live data from the artifact database and never hardcodes news.
- `pipeline.py` – fetches ~30 Indian and global feeds plus Yahoo Finance quotes, cleans, de-duplicates, classifies into 12 sections and 2 regions, ranks. A copy is stored in the database at `pipeline/script` so scheduled runs can fetch it.
- `ROUTINE.md` – the prompt for the editorial Routines; `ROUTINE-HOURLY.md` – the prompt for the hourly wire refresh.
- `seed/` – the first edition's documents and the enrichment script used to write them.

## Database layout

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
