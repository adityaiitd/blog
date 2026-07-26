# Current repository state

## Git

- **Repository root:** `/workspace`
- **Application root:** `/workspace/italy-escape`
- **Current branch:** `cursor/italy-escape-v2-bcfd`
- **Upstream:** `origin/cursor/italy-escape-v2-bcfd`
- **Implementation commit inspected:** `242d7f636afc808363d80ee1bfe810264eca0e7d` (`242d7f6`, `Label stays by rate and document new features`)
- **Ahead/behind at inspection:** `+0/-0`
- **Modified files before this handoff:** none
- **Staged files before this handoff:** none
- **Untracked files before this handoff:** none
- **Ignored local artifacts:** `italy-escape/.env.local`, `italy-escape/.next/`, `italy-escape/screenshots/`
- **Current work:** this handoff adds `docs/ai/*`; no product source was intentionally changed.

### Recent relevant commits

```text
242d7f6 Label stays by rate and document new features
e32bb90 Improve hotel lookup matching
d68f437 Add hotel lookup by name and reorderable trip legs
2109534 Attribute saves to the person making them
7ed62ed Make save and history available on every page
5ee7c73 Add value stays, saving with authors, explore guide and faster loads
6240d26 Fix crash from stale saved drafts
ab214d4 Use real hotel photos and private charter operators
39479aa Add budget chat coverage and documentation
a964418 Correct split stays with verified value hotels and budget target
a1e8fa7 Redesign itinerary and hotel planning experience
8e68711 Add value planning and trip assistant
93c7d92 Build interactive Italy escape planner
```

`master` remains the unrelated legacy repository baseline at `4ae3a0e`.

## Application inventory

- **Framework:** Next.js `16.2.12`, React `19.2.4`, TypeScript `5.9.3`, Tailwind CSS `4.3.3`.
- **Routes built:** 13 app routes: `/`, `/_not-found`, `/boats`, `/costs`, `/explore`, `/hotels`, `/itinerary`, `/map`, `/present`, `/print`, `/value`, `/api/chat`, `/api/place-lookup`.
- **Seed data:** 3 stays, 14 hotel nights, 16 itinerary days, 15 hotel options, 4 boat excursions, 26 destinations/waypoints, 9 cost categories.
- **No database/schema migrations:** there is no DB, ORM, migrations directory, or server-side trip store.

## Fully implemented features

### Planning and editing

- Canonical typed `TripState` and `TripAction` union: `italy-escape/src/lib/types.ts`.
- Reducer-backed updates and 50-level undo/redo: `tripReducer.ts`, `TripProvider.tsx`.
- Editable start date, trip title, travelers, stays/nights, night-by-night hotel assignment, hotel rates/room levels/taxes, activities, boat operator options, route details, cost categories, tax settings, and budget target.
- Leg reordering with date/day block reflow and rebuilt connections: `legOrder.ts`, `LegOrder.tsx`.
- Night changes insert/remove itinerary days and reflow offsets.

### Views

- `/`: overview, budget target, leg order, chapter summary, lazy route map, advanced route editor.
- `/itinerary`: simple/timeline/calendar modes, day-purpose/rationale, DnD, weather buffer, booking details.
- `/hotels`: per-night dropdowns, split recommendations, real remote hotel galleries, links, ratings, rates, add-by-name.
- `/boats`: private operator choices, durations, source links, inclusions/exclusions, live totals.
- `/explore`: 18 curated regional spots filtered by type and addable to itinerary.
- `/map`: Leaflet layers for hotels, boats, and transport with a side list.
- `/costs`: baseline/recommended/splurge totals, taxes, flights, target tracker, budget levers.
- `/value`: per-region luxury/value scenario page.
- `/print`: browser print/PDF layout.
- `/present`: keyboard-navigable spouse presentation.

### Persistence, sharing, collaboration

- Draft autosave: `localStorage` key `italy-escape:draft:v1`.
- History: `italy-escape:history:v2`, 5-day autosaves, maximum 200 entries, pinned saves retained.
- Legacy version migration: `italy-escape:versions:v1`.
- Author attribution: `italy-escape:author`.
- URL state: compressed `?t=` payload.
- P2P collaboration: `?room=`, Yjs/y-webrtc, whole-state and version-history sync, peer count.
- Named save/restore in the global header.
- Error recovery for stale/corrupt browser drafts: `src/app/error.tsx`, `src/lib/migrate.ts`.

### Integrations

- Nominatim hotel lookup (`GET /api/place-lookup`).
- CARTO/OpenStreetMap maps.
- Remote hotel imagery configured in `next.config.ts`.
- Deterministic local chat commands.
- Optional, currently unconnected OpenAI route (`POST /api/chat`).

## Partially implemented or behaviorally incomplete

1. **Custom hotel map integration:** lookup returns `lat`/`lng`, but `AddHotel.tsx` does not create/update a `Destination`; custom hotels do not gain a map pin.
2. **Free-form LLM chat:** `/api/chat` exists, but `ChatPanel` never calls it.
3. **Collaboration semantics:** P2P transport works, but simultaneous edits replace the entire trip state; this is last-write-wins, not field-level merge.
4. **Value planning:** `/value` is built and included in screenshot QA but is absent from primary navigation.
5. **Review requirement enforcement:** the code contains hotels with `rating: 0`/unverified data. The “4.5+” preference is editorial, not enforced by schema or selector.
6. **Live data:** hotel/boat prices and ratings are static researched estimates, not live API results.

## Discussed but not implemented

- User accounts, authentication, authorization, server-side shared trip storage.
- Live hotel/boat inventory and booking transactions.
- Deposit/payment/cancellation deadline tracking.
- Currency conversion, calendar export, “today” travel mode.
- Weather API and connection-conflict alerts.
- Private WebRTC signaling infrastructure.
- CI/CD workflow and automated coverage gate.

## Confirmed working

- Production build and static generation.
- Unit tests for cost, reducer, history, migration, schedule, sharing, split stays, chat commands, and leg reorder.
- Screenshot/browser-console QA for overview, map, value, itinerary, hotels, boats, costs, and mobile overview.
- v2 and v1 production URLs respond.
- App operates without required API keys.

## Confirmed broken or incorrect

1. **Empty-destinations migration:** `normalizeTripState({...state, destinations: []})` returns zero destinations. Confirmed by direct probe; maps/routes lose place lookups.
2. **README drift:** README says Amalfi boat-base nights use Palazzo Ferraioli; seed data uses Hotel Onda Verde.
3. **Hotel lookup claim drift:** API returns coordinates, but coordinates are not persisted into trip destinations.
4. **Oversized sharing:** default `encodeTripState` output is `32,005` characters.

See `KNOWN_ISSUES.md` for full severity and reproduction details.

## Validation status

Validated from `/workspace/italy-escape` on `2026-07-26`:

| Command | Outcome |
|---|---|
| `npm run lint` | PASS |
| `npm run typecheck` | PASS |
| `npm test` | PASS — 9 files, 47 tests |
| `npm run build` | PASS — 15 generated route entries |
| `npm run screenshots` | PASS — desktop/mobile captures, no browser console/page errors |
| `npm audit --omit=dev` | FAIL — 3 high-severity advisories in Next’s bundled `postcss@8.4.31` and `sharp@0.34.5`; npm only proposes a breaking downgrade |
| Direct share/migration probe | `encodedLength=32005`, `emptyDestinationMigration=0` |

No destructive migrations or external write jobs were run for validation. No production deployment was performed during this handoff.

## Deployment status

- **CONFIRMED live:** `https://italy-escape1.vercel.app` responds with v2 content and `$32,651` seeded total.
- **CONFIRMED live:** `https://italy-escape.vercel.app` responds with the earlier v1 content.
- **Vercel project linking:** local `.vercel/` is ignored; README instructs `npx vercel link --project italy-escape1 --yes`.
- **No `vercel.json`:** deployment relies on Vercel’s Next.js defaults and Root Directory configuration.
- **PR:** existing draft PR is `https://github.com/adityaiitd/blog/pull/2`.

## Environment variables

Standard behavior requires none.

| Name | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | No | Enables dormant `/api/chat` route |
| `NEXT_PUBLIC_SIGNALING_URLS` | No | Comma-separated WebRTC signaling endpoints |
| `SCREENSHOT_BASE_URL` | No | Overrides screenshot script base URL |

`.env.local` exists locally and is ignored. Do not read or copy its value into documentation.

## Local startup

```bash
cd /workspace/italy-escape
npm install
npm run dev
# open http://localhost:3000
```

Quality gate:

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

Screenshot QA:

```bash
npx playwright install chromium  # first run only
npm run build
npm run start -- -p 3000
# in another shell:
npm run screenshots
```

## Generated/ignored artifacts

Do not manually edit:

- `italy-escape/.next/` — Next.js build output.
- `italy-escape/screenshots/` — generated by `scripts/screenshots.mjs`.
- `italy-escape/.env.local` — local Vercel/auth environment; secret values must not enter Git.
- `italy-escape/next-env.d.ts` — Next.js generated, ignored.
- `italy-escape/package-lock.json` — update only through npm/package changes, not manual edits.
- `/opt/cursor/artifacts/plans/*.plan.md` — historical plan artifacts outside the repository; not canonical and not modified by this handoff.

## Last verified

- **Timestamp:** `2026-07-26T22:14:34Z`
- **Branch:** `cursor/italy-escape-v2-bcfd`
- **Implementation commit inspected:** `242d7f636afc808363d80ee1bfe810264eca0e7d`
- **Working tree at inspection:** clean, tracking upstream at `+0/-0`
- **Note:** the final handoff documentation commit is newer than the inspected implementation commit and changes only `docs/ai/*`.
