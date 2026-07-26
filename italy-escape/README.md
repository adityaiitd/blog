# Our Italy Escape

A private, editable planning studio for a 14-hotel-night journey through Sardinia, Tuscany and the Amalfi Coast. Built with Next.js App Router, TypeScript, Tailwind CSS and React Leaflet.

## Run locally

Requirements: Node.js 22+ and npm.

```bash
npm install
npm run dev
```

Open `http://localhost:3000`. Quality checks:

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

No API keys or environment variables are required. OpenStreetMap/CARTO tiles require a network connection.

## Editing and persistence

Dates, destinations, marker coordinates, route legs, transport modes, hotels, rates, room levels, premiums, taxes, complimentary nights, activities, reservations, boats and cost categories are editable. Hotel-night changes add or remove schedule days and reflow all later dates. Undo/redo works from the header or `Cmd/Ctrl+Z`.

Edits are saved to `localStorage` as `italy-escape:draft:v1`. “Copy link” compresses the complete typed trip state into the `?t=` URL parameter; valid URL state takes precedence over the local draft. Invalid or outdated URL payloads show a warning and safely fall back.

“Save version” stores named snapshots locally and shows structural differences before restore. “Collaborate” adds a room ID and syncs peer-to-peer with Yjs/WebRTC. This needs no application backend, but discovery depends on public signaling availability. Set a comma-separated `NEXT_PUBLIC_SIGNALING_URLS` if you operate your own signaling service. The app falls back to solo editing if peers cannot connect.

## Print, PDF and presentation

- `/print` is an A4-friendly itinerary. Use the browser print dialog and choose **Save as PDF**.
- `/present` is a full-screen, editing-free spouse presentation. Use the arrow keys.

## Photography

The nine local WebP files in `public/images` are original generated travel placeholders, not scraped hotel photography: `costa-smeralda.webp`, `cala-di-volpe.webp`, `la-maddalena.webp`, `tuscany.webp`, `florence.webp`, `val-dorcia.webp`, `amalfi.webp`, `capri.webp`, and `positano.webp`.

To use personal photography, replace a file with your own image using the same filename. Use a landscape 16:9 image, at least 1600px wide, convert it to WebP, and preserve the filename so no code changes are needed. Only use images you own or are licensed to use.

## Screenshot workflow

With `npm run dev` running in one terminal, run:

```bash
npm run screenshots
```

This captures desktop journey, itinerary, hotels and budget views plus a mobile journey view into `screenshots/` (gitignored). On a fresh machine first run `npx playwright install chromium`.

## Deploy to Vercel

The repository contains this app in `italy-escape/`. In Vercel:

1. Import the repository.
2. Set **Root Directory** to `italy-escape`.
3. Leave Framework Preset as **Next.js**.
4. Deploy. No secrets are needed.

For a repository containing only this directory, `vercel` or `npx vercel` also works directly.

## Architecture

Seed content is in `src/data`. `TripProvider` and `tripReducer` hold canonical mutable state. Pure derivations in `src/lib/costCalculator.ts` and `src/lib/schedule.ts` feed every view, avoiding duplicated totals or stale dates. `src/lib/shareState.ts` validates shared data before hydration.
