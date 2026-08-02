# Bookmark Briefs

Turn your last ~100 X.com bookmarks into plain-English digests so you can understand each post in about two minutes.

## What you get

For every saved post:

- **Company / topic** — what it’s about
- **Plain-English summary** — the point, simply
- **Why you might care** — quick context
- **Quick facts** — author, date, links
- **Links followed** — page title + description when available

Browse them in `public/index.html`.

## Get your bookmarks into the app

### Option A — Agent browser (preferred)

1. Open the agent’s browser and log into X.
2. Tell the agent you’re logged in.
3. The agent scrapes `/i/bookmarks`, enriches links, and fills `data/bookmarks.json`.

### Option B — Your own browser (works if you’re already logged in)

1. Go to [https://x.com/i/bookmarks](https://x.com/i/bookmarks).
2. Open DevTools → Console.
3. Paste everything in `scripts/export-bookmarks.js` and press Enter.
4. Save the downloaded `raw-bookmarks.json` into `bookmarks-digest/data/raw-bookmarks.json`.
5. Run:

```bash
python3 bookmarks-digest/scripts/enrich_and_summarize.py
```

6. Open the viewer:

```bash
cd bookmarks-digest/public && python3 -m http.server 8765
```

Then visit `http://localhost:8765` (it loads `../data/bookmarks.json`).

## Files

| Path | Purpose |
|------|---------|
| `data/raw-bookmarks.json` | Raw scrape / export |
| `data/bookmarks.json` | Enriched digests for the UI |
| `data/schema.json` | Shape of the digest database |
| `scripts/export-bookmarks.js` | Browser console exporter |
| `scripts/enrich_and_summarize.py` | Link fetch + simple summaries |
| `public/index.html` | Simple reader UI |
