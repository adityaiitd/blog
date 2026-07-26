# Our Italy Escape

A private, editable planning studio for a 14-hotel-night journey through Sardinia, Tuscany and the Amalfi Coast. Version 2 adds per-region value planning, a hotel-and-boat map, direct chat editing and five-day version history.

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

Every settled edit is also autosaved to a Google-Sheets-style timeline. Autosaves are retained for five days (up to 200 entries); named saves are pinned until removed from browser storage.

## New planning views

- `/map` overlays dated hotel stays, complete boat routes and all transport. Layers can be toggled independently and selected markers are editable.
- `/value` switches Sardinia, Tuscany or Amalfi independently between Luxury and a one-tier-below plan. Dates and core experiences stay fixed while hotel and boat choices move roughly 20–30% lower.
- `/itinerary` opens in a simple reading view that makes “at hotel,” “on the water,” “out exploring” and “in transit” explicit. Advanced editing remains available.
- `/costs` includes editable economy flight prices, Italian city tax, charter VAT and restaurant service.

The floating **Ask the trip** button understands commands such as “Make Amalfi cheaper,” “Set Tuscany to 5 nights,” “Move Capri boat to the weather day,” and “What is our total?” It works locally without a key. An optional `OPENAI_API_KEY` enables the server route for future free-form LLM integration; the deterministic assistant remains the default and no key is required.

The visual itinerary explains what each activity is for (eating, sightseeing, walking, relaxing, travel or boating), why it is included, and where the couple sleeps.

## Nights are priced individually

Hotels carry a role. Signature hotels hold the days the property itself is the point; boat bases under $400 a night cover days spent entirely at sea. The seeded plan therefore reads:

- Sardinia: three nights at Cala di Volpe, then two nights at Hotel La Vecchia Fonte in Palau (8.6/10 from ~1,149 reviews) beside the harbour both sails leave from.
- Tuscany: four nights at COMO Castello Del Nero, one base.
- Amalfi Coast: arrival plus both sailing nights at Palazzo Ferraioli in Atrani (4.3/5 from ~455 reviews, rooftop terrace, ten-minute walk to Amalfi), then two nights at Anantara for its cliffside infinity pool.

Every night is a dropdown, so any split can be changed. "Use recommended split" reapplies the pattern after edits.

## Honest pricing

Rates and charters are researched estimates, never live quotes. Each one shows a verification chip linking to the source it was priced from, and each hotel shows its rating, review count and review site. Boat budgets are anchored to Viator listings for these exact routes: La Maddalena private with skipper from about $880, Amalfi to Capri private from €1,090. Those headline prices cover 8–12 guests, so a party of two sits at the lower end. Non-included costs such as Capri docking fees and Blue Grotto tickets are listed on each card.

## Reordering the trip

The overview page lists the three legs in order. Moving one re-flows everything that depends on it: the dates, the day-by-day blocks (which travel with their region), the boat days, and the flights, trains and transfers between legs. Connections are derived from the order rather than stored, so a hop touching Sardinia flies while two mainland legs take the train, and the outbound and return flights always use airports.

## Adding your own hotel

Each leg has an "Add a hotel by name" control. Typing a name and pressing Look up queries OpenStreetMap (free, no API key) and returns matching properties with their real address, coordinates and website where tagged. Choosing one attaches those details; the new hotel then appears in that leg's night-by-night dropdown alongside the researched options, with booking and review links generated for it.

## Saving and version history

The header carries Save and History on every page. The first save asks who you are, and each entry records the name, timestamp and what changed. Saved versions are kept indefinitely; automatic snapshots are kept for five days. Anyone opening a "Share to edit together" link can edit and save too, and saves are merged across everyone in the room.

## Budget target

The trip carries an editable target, seeded at $35,000 all-in for two people, with a live tracker on the overview and budget pages. When the plan runs over, ranked levers show the savings each change produces and apply as a single undoable edit. The seeded plan lands near $34,900 including 7 percent contingency.

## Print, PDF and presentation

- `/print` is an A4-friendly itinerary. Use the browser print dialog and choose **Save as PDF**.
- `/present` is a full-screen, editing-free spouse presentation. Use the arrow keys.

## Photography

The nine local WebP files in `public/images` are original generated editorial destination images, not scraped hotel photography: `costa-smeralda.webp`, `cala-di-volpe.webp`, `la-maddalena.webp`, `tuscany.webp`, `florence.webp`, `val-dorcia.webp`, `amalfi.webp`, `capri.webp`, and `positano.webp`. Hotel cards clearly label this distinction and link to each property’s official room/gallery pages for current, accurate photography.

To use personal photography, replace a file with your own image using the same filename. Use a landscape 16:9 image, at least 1600px wide, convert it to WebP, and preserve the filename so no code changes are needed. Only use images you own or are licensed to use.

## Screenshot workflow

With `npm run dev` running in one terminal, run:

```bash
npm run screenshots
```

This captures desktop journey, map, value plan, itinerary, hotels and budget views plus a mobile journey view into `screenshots/` (gitignored). It fails if any page emits a browser console or runtime error. On a fresh machine first run `npx playwright install chromium`.

## Deploy to Vercel

The repository contains this app in `italy-escape/`. In Vercel:

1. Import the repository.
2. Set **Root Directory** to `italy-escape`.
3. Leave Framework Preset as **Next.js**.
4. Deploy. No secrets are needed.

For a repository containing only this directory, `vercel` or `npx vercel` also works directly.

The original edition remains at `italy-escape.vercel.app`. Version 2 is a separate Vercel project at `italy-escape1.vercel.app`; relink with `npx vercel link --project italy-escape1 --yes` before deploying v2.

## Architecture

Seed content is in `src/data`. `TripProvider` and `tripReducer` hold canonical mutable state. Pure derivations in `src/lib/costCalculator.ts` and `src/lib/schedule.ts` feed every view, avoiding duplicated totals or stale dates. `src/lib/shareState.ts` validates shared data before hydration.
