# Decision ledger

This file is append-only. New decisions should be added at the end; do not rewrite old entries. Where decisions conflict, the most recent **accepted** decision is authoritative.

## D-001 — Build a client-first private trip planner

- **Status:** accepted
- **Decision:** Build a private, editable planning studio for a couple’s Italy trip, not a generic travel marketplace or enterprise SaaS.
- **Rationale:** The user needs to compare one complex shared trip and present it to a spouse.
- **Alternatives considered:** spreadsheet, static mockup, generic SaaS dashboard.
- **Consequences:** Seed content is trip-specific; no tenancy or monetization model.
- **Affected files:** `italy-escape/src/data/*`, all app routes.
- **Source:** conversation
- **Sequence:** initial request, July 2026

## D-002 — Use Next.js App Router, TypeScript, Tailwind, Leaflet/OSM, Vercel

- **Status:** accepted
- **Decision:** Use Next.js App Router with React 19, TypeScript, Tailwind CSS, React Leaflet, OpenStreetMap/CARTO, and deploy to Vercel.
- **Rationale:** Explicit technical requirement; keyless map and straightforward deployment.
- **Alternatives considered:** paid map providers, conventional SPA, server-rendered database app.
- **Consequences:** Leaflet must be client-only/dynamic; remote tiles require network.
- **Affected files:** `package.json`, `src/app/*`, `src/components/map/*`, `next.config.ts`.
- **Source:** conversation and repository
- **Sequence:** initial request

## D-003 — One canonical typed trip state

- **Status:** accepted
- **Decision:** All views derive from a single `TripState`; all user edits are `TripAction`s handled by `tripReducer`.
- **Rationale:** Avoid stale dates/totals and support undo, sharing, migration, collaboration, print, and presentation from one state.
- **Alternatives considered:** component-local state and duplicated calculations.
- **Consequences:** `TripState` is large; URL/history payloads now include substantial seed/media metadata.
- **Affected files:** `src/lib/types.ts`, `tripReducer.ts`, `TripProvider.tsx`, data files.
- **Source:** conversation and repository
- **Sequence:** v1 architecture

## D-004 — No required backend or paid API

- **Status:** accepted
- **Decision:** Normal operation uses browser persistence and keyless/free services; no DB or required API secret.
- **Rationale:** Explicit “no backend required/no paid API keys.”
- **Alternatives considered:** hosted shared trip DB, paid maps, booking APIs.
- **Consequences:** collaboration and saves are not durably server-hosted; shared links are bearer data.
- **Affected files:** `storage.ts`, `shareState.ts`, `collab.ts`, API routes.
- **Source:** conversation
- **Sequence:** initial request

## D-005 — URL + localStorage persistence

- **Status:** accepted
- **Decision:** `?t=` is compressed full state and overrides the local draft; draft/history/author use localStorage.
- **Rationale:** Share custom itineraries without accounts.
- **Alternatives considered:** server database, short-link service.
- **Consequences:** default payload is currently 32,005 characters; local quota and privacy risks exist.
- **Affected files:** `shareState.ts`, `storage.ts`, `TripProvider.tsx`.
- **Source:** conversation and repository
- **Sequence:** v1

## D-006 — P2P collaboration via Yjs/WebRTC

- **Status:** accepted, with known limitations
- **Decision:** `?room=` connects peers through `y-webrtc`; trip state and version arrays are synchronized.
- **Rationale:** Multiplayer without an application backend.
- **Alternatives considered:** Firebase/Supabase/server WebSockets; rejected by no-backend constraint.
- **Consequences:** no authentication; signaling dependency; whole-state last-write-wins can lose simultaneous edits.
- **Affected files:** `collab.ts`, `TripProvider.tsx`, `ShareBar.tsx`, `SaveBar.tsx`.
- **Source:** conversation and repository
- **Sequence:** v1/v2

## D-007 — Editorial luxury visual direction

- **Status:** accepted
- **Decision:** Warm editorial presentation, high-end travel typography, large imagery, minimal gradients/cards, responsive light/dark themes.
- **Rationale:** User wants Four Seasons/Belmond-appropriate presentation rather than SaaS chrome.
- **Alternatives considered:** dashboard-style UI.
- **Consequences:** custom CSS tokens and photography-heavy hotel/hero views.
- **Affected files:** `globals.css`, `layout.tsx`, page/components.
- **Source:** conversation
- **Sequence:** initial request

## D-008 — Progressive disclosure and visible rationale

- **Status:** accepted
- **Decision:** Default itinerary is a visual/simple mode; advanced controls are expandable. Each activity/property explains purpose and why it is included.
- **Rationale:** User repeatedly reported dense screens as confusing.
- **Alternatives considered:** always-visible editable grids.
- **Consequences:** dual simple/advanced UI and additional `purpose`/`rationale` fields.
- **Affected files:** `ItineraryPlanner.tsx`, `types.ts`, `itinerary.ts`.
- **Source:** conversation and external UX research
- **Sequence:** v2 redesign

## D-009 — Split hotels night-by-night around boat days

- **Status:** accepted
- **Decision:** Use signature resorts on land/resort days and lower-cost boat bases on days spent at sea.
- **Rationale:** Avoid paying thousands for resort facilities not used.
- **Alternatives considered:** one hotel per region; full-value-tier replacement.
- **Consequences:** `Stay.nightHotelIds[]`, `splitStay.ts`, more complex cost and map behavior.
- **Affected files:** `hotels.ts`, `splitStay.ts`, `costCalculator.ts`, hotel/itinerary views.
- **Source:** conversation
- **Sequence:** under-$35k redesign

## D-010 — `$35,000` target for two

- **Status:** accepted
- **Decision:** Seed `budgetTarget=35000`; show live target status and reversible savings levers.
- **Rationale:** Explicit user target.
- **Alternatives considered:** informational range only.
- **Consequences:** `fitToTarget` ranks split/boat/dining changes; current live seed reports `$32,651`.
- **Affected files:** `data/index.ts`, `costCalculator.ts`, `BudgetTarget.tsx`.
- **Source:** conversation and repository
- **Sequence:** under-$35k redesign

## D-011 — Private boats only; half-day is valid

- **Status:** accepted; supersedes earlier shared/value boat variants
- **Decision:** All offered charters are private. Do not propose shared tours. Use half-day private boats when sufficient for two people.
- **Rationale:** Latest explicit user instruction.
- **Alternatives considered:** shared small-group cruises; rejected.
- **Consequences:** `BoatOption` list uses private operators/durations; selected option drives all totals.
- **Affected files:** `boatTrips.ts`, `BoatPlanner.tsx`, `costCalculator.ts`.
- **Source:** conversation
- **Sequence:** late v2

## D-012 — Real property photos and external source links

- **Status:** accepted; supersedes initial no-hotlink/local-placeholder requirement
- **Decision:** Show real hotel/pool/room photos from property/Booking.com CDNs, with official, room, booking, and review links.
- **Rationale:** Latest explicit user requirement after rejecting generated imagery.
- **Alternatives considered:** generated/local placeholders; explicitly rejected for hotel cards.
- **Consequences:** external CDN dependencies and copyright/availability concerns; nine generated local destination images remain for non-property editorial use.
- **Affected files:** `hotels.ts`, `HotelStoryPlanner.tsx`, `next.config.ts`, `public/images/*`.
- **Source:** conversation and repository
- **Sequence:** late v2

## D-013 — Recommendation rating floor

- **Status:** accepted as product intent; not fully enforced in code
- **Decision:** Actively suggested hotels and private operators should have 4.5+ Tripadvisor ratings and strong review evidence.
- **Rationale:** Explicit user requirement.
- **Alternatives considered:** aggregate ratings from other platforms and unreviewed operator pages.
- **Consequences:** Onda Verde replaced lower-rated Palazzo Ferraioli in seed; many catalog entries still have `rating: 0`, so enforcement remains a task.
- **Affected files:** `hotels.ts`, `boatTrips.ts`, verification UI.
- **Source:** conversation; repository only partially enforces
- **Sequence:** late v2

## D-014 — Leg order is editable and connections are derived

- **Status:** accepted
- **Decision:** Moving a regional stay moves its entire day block and rebuilds flights/trains/cars from stay hub metadata.
- **Rationale:** User wants to choose starting leg and have all pages follow.
- **Alternatives considered:** manually editing each route/day after reorder.
- **Consequences:** stored seed route legs can diverge from rebuilt route legs until a reorder occurs.
- **Affected files:** `legOrder.ts`, `LegOrder.tsx`, `types.ts`, `tripReducer.ts`.
- **Source:** conversation and repository
- **Sequence:** latest implementation milestone

## D-015 — Hotel lookup uses Nominatim without a key

- **Status:** accepted, incomplete
- **Decision:** Search a hotel name through a server-side Nominatim proxy and add it as a leg option.
- **Rationale:** No paid Places API; user wants arbitrary hotel entry.
- **Alternatives considered:** Google Places/paid API; plain text-only hotel.
- **Consequences:** address/site data is used, but coordinates are currently discarded; endpoint needs rate limiting.
- **Affected files:** `/api/place-lookup`, `AddHotel.tsx`, `tripReducer.ts`.
- **Source:** conversation and repository
- **Sequence:** latest implementation milestone

## D-016 — Named saves and five-day history with authors

- **Status:** accepted
- **Decision:** Global Save/History on every page; named versions are pinned, autosaves retained five days, author stored locally and synced via collaboration.
- **Rationale:** Couple needs Google-Sheets-like revertability and attribution.
- **Alternatives considered:** manual-only snapshots; server revision DB.
- **Consequences:** full state clones consume localStorage; cross-device persistence only while peers synchronize.
- **Affected files:** `SaveBar.tsx`, `TripProvider.tsx`, `storage.ts`, `collab.ts`.
- **Source:** conversation and repository
- **Sequence:** late v2

## D-017 — Chat remains deterministic by default

- **Status:** accepted for shipped behavior; optional LLM route is tentative
- **Decision:** `ChatPanel` translates supported phrases locally to typed actions. The OpenAI route is not called.
- **Rationale:** Works without keys, remains deterministic, avoids sending trip data externally.
- **Alternatives considered:** mandatory OpenAI assistant.
- **Consequences:** free-form requests outside parser intents are unsupported; dormant route is technical/security debt.
- **Affected files:** `ChatPanel.tsx`, `chatCommands.ts`, `/api/chat`.
- **Source:** repository and conversation
- **Sequence:** v2

## D-018 — Two separate production versions

- **Status:** accepted
- **Decision:** Preserve v1 at `italy-escape.vercel.app`; update v2 at `italy-escape1.vercel.app`.
- **Rationale:** User explicitly asked to keep the first version.
- **Alternatives considered:** overwrite one Vercel project.
- **Consequences:** deployment/release work must target the correct linked Vercel project.
- **Affected files:** README/deployment process; Vercel configuration outside Git.
- **Source:** conversation and live verification
- **Sequence:** v2 kickoff

## D-019 — Tests before release

- **Status:** accepted
- **Decision:** Lint, typecheck, Vitest, production build, and screenshot/browser-console QA are release gates.
- **Rationale:** Explicit quality requirement and prior production crash.
- **Alternatives considered:** build-only validation.
- **Consequences:** 47 pure-library tests exist; component/API/E2E coverage remains incomplete.
- **Affected files:** `package.json`, `vitest.config.ts`, `scripts/screenshots.mjs`, `src/lib/__tests__/*`.
- **Source:** conversation and repository
- **Sequence:** initial request onward

## D-020 — Context files are canonical memory

- **Status:** accepted
- **Decision:** `docs/ai/*` is the durable context source for future sessions.
- **Rationale:** Conversation is approaching context limit.
- **Alternatives considered:** continue relying on transcript and `/opt` plan artifacts.
- **Consequences:** Future material changes must update these files.
- **Affected files:** `docs/ai/*`.
- **Source:** latest user instruction
- **Date:** 2026-07-26
