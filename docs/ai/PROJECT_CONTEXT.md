# Project context

## Canonical scope

- **CONFIRMED:** The Git repository root is `/workspace`. The application is the `italy-escape/` subdirectory; the repository also contains unrelated legacy blog/data folders.
- **CONFIRMED:** The product is **Our Italy Escape — Sardinia, Tuscany and Amalfi**, a private, editable planner for a married couple's 14-hotel-night Italy trip.
- **CONFIRMED:** The seeded trip starts `2026-08-30`, has 2 travelers, 5 nights in Sardinia, 4 in Tuscany, 5 on the Amalfi Coast, and a `$35,000` target.
- **CONFIRMED:** Production v2 is `https://italy-escape1.vercel.app`. The earlier immutable v1 is `https://italy-escape.vercel.app`.

## User and central problem

- **CONFIRMED:** Primary users are the user and his wife. Anyone with a collaboration link may also edit and save.
- **CONFIRMED:** The central problem is comparing a complex luxury itinerary—dates, region order, hotel splits, boats, transfers, activities, and cost—without requiring the couple to reconcile disconnected spreadsheets, maps, booking pages, and messages.
- **CONFIRMED:** The planner must explain *why* each activity or property is included, not merely list it.
- **INFERRED:** This is a personal planning product rather than a revenue-generating SaaS. No monetization, organizational tenancy, or public marketplace requirements have been stated.

## Intended experience

- **CONFIRMED:** Editorial luxury-travel aesthetic: warm neutral palette, excellent serif/sans typography, large photography, minimal gradients/cards, responsive iPhone/tablet/desktop layouts, light/dark modes, and performance appropriate for a high-end travel client.
- **CONFIRMED:** Progressive disclosure is preferred: summary first, editing/details on demand.
- **CONFIRMED:** Edits should be structured controls and dropdowns where possible; downstream dates, routes, maps, hotel totals, boat totals, taxes, scenarios, per-night and per-person costs must recalculate.
- **CONFIRMED:** One canonical state must drive all pages so changing leg order, dates, nights, hotel assignments, or boat operators cascades across the itinerary, map, budget, print, and presentation views.
- **CONFIRMED:** Real-world choices need visible rationale, source/review links, and honest “estimate versus confirmed” framing.

## Product objectives

1. **CONFIRMED:** Make the trip understandable at a glance: location, day purpose, where the couple sleeps, and whether time is for eating, sightseeing, walking, relaxing, transit, or sailing.
2. **CONFIRMED:** Support collaborative experimentation without losing prior versions.
3. **CONFIRMED:** Keep the seeded trip under `$35,000` for two while preserving selected luxury “signature stay” days.
4. **CONFIRMED:** Avoid paying signature-hotel rates on days spent primarily on boats; support night-by-night split stays.
5. **CONFIRMED:** Offer private boats only. Options should be appropriately sized for two people and may be half-day rather than always full-day.
6. **CONFIRMED:** Hotel and boat recommendations must have real operator/property links and review evidence. The latest explicit preference is a Tripadvisor rating floor of 4.5 for anything actively recommended.

## Terminology

- **Leg / stay:** One regional chapter (`Stay`) with region, nights, hotel assignments, and arrival/departure hubs.
- **Signature stay:** A hotel whose resort, pool, view, spa, or beach is part of the day’s value proposition.
- **Boat-day base:** A lower-cost hotel near the departure point, used when most of the day is spent at sea.
- **Value stay:** A lower-cost alternative, generally under `$500/night` where requested.
- **Night assignment:** `Stay.nightHotelIds[]`; the hotel can differ per night.
- **Day block:** The itinerary days belonging to a stay. Leg reorder moves the entire block.
- **Boat option:** A private operator/duration/price choice inside a `BoatExcursion`.
- **Weather buffer:** An open itinerary day that can receive a weather-dependent boat activity.
- **Baseline total:** Current categories plus the configured contingency.
- **Budget lever:** A reversible set of `TripAction`s suggested by `fitToTarget`.
- **Pinned version:** A named save retained indefinitely in local browser history.
- **Autosave:** An unnamed state snapshot retained for five days.

## Non-negotiable requirements

### Product

- **CONFIRMED:** Next.js App Router, TypeScript, Tailwind CSS, React Leaflet, OpenStreetMap/CARTO, Vercel.
- **CONFIRMED:** No paid API key is required for normal operation.
- **CONFIRMED:** No application database or conventional backend is required.
- **CONFIRMED:** State persists in URL query parameters and `localStorage`.
- **CONFIRMED:** Shared editing uses a link; save/history records author, timestamp, and summary.
- **CONFIRMED:** Dates, locations, hotels, room/rate inputs, routes, costs, activities, boats, and leg order are editable.
- **CONFIRMED:** Print/PDF-friendly and spouse presentation modes must remain.
- **CONFIRMED:** Keyboard navigation, reduced motion, invalid-state recovery, loading/empty states, no TypeScript/console errors, and easy mobile use are expected.

### Content and sourcing

- **CONFIRMED, authoritative latest instruction:** Hotel cards should show real property/room/pool photographs and working property/booking/review links.
- **SUPERSEDED:** The original brief prohibited scraping/hotlinking copyrighted hotel images and asked for local placeholders. Later explicit user instructions required real property photos. Current code uses remote images from hotel/Booking.com CDNs plus nine local generated destination images.
- **CONFIRMED:** Rates are estimates, not live quotes; the UI must not imply otherwise.
- **CONFIRMED:** Boat choices are private only. Shared boat tours are rejected.
- **CONFIRMED:** User-added hotels should be discoverable by name and saveable to any regional leg.

## User preferences captured during the conversation

- Highly visual, breathtaking, intuitive navigation; low cognitive load.
- Strong dislike of dense always-visible forms.
- Wants concise reasons for each choice and visible trade-offs.
- Wants pools, rooftops, views, room guidance, booking links, review links, and real prices.
- Wants luxury and under-`$500` options mixed in each leg’s dropdown.
- Wants boats at Sardinia’s tail and Amalfi’s beginning so expensive resort time is used on land.
- Wants private half-day boats when full-day is unnecessary.
- Wants leg order editable from the overview with all pages reflowing.
- Wants chat edits, named saves, five-day history, author attribution, and link-based collaboration.
- Wants restaurants, tourist sights, calm spots, swimming, and slow-travel suggestions per base.
- Wants the production app fast and verified end-to-end before handoff.

## Explicit exclusions and deferred work

- **ACCEPTED exclusion:** No accounts, passwords, role-based access control, server-side tenancy, or application database.
- **ACCEPTED exclusion:** No live booking transaction or payment processing.
- **ACCEPTED exclusion:** No paid maps or booking API.
- **CONFIRMED deferred:** Free-form LLM chat is not connected to the UI. `/api/chat` exists as an optional OpenAI route, but `ChatPanel` uses a deterministic local parser.
- **CONFIRMED deferred from earlier planning:** deposit/payment schedules, cancellation-deadline tracking, USD/EUR toggle, `.ics` export, a dedicated “today” travel mode, weather service integration, and transfer-duration conflict warnings.
- **REJECTED:** Shared/group boats.
- **REJECTED as authoritative source:** Unverified confident prices/reviews. Estimates should link to a source and state exclusions.

## Operational, privacy, security, performance, and reliability context

- **CONFIRMED:** Trip state, versions, and author name are client-side; no normal-operation server persistence exists.
- **CONFIRMED:** A full shared itinerary is encoded in `?t=` and can appear in browser history, referrers, analytics, messages, and server logs.
- **CONFIRMED:** Collaboration room IDs are unauthenticated bearer links. Anyone with the link can view/edit while peers are connected.
- **CONFIRMED:** P2P collaboration depends on WebRTC signaling availability and uses last-write-wins whole-state strings rather than field-level CRDT merges.
- **CONFIRMED:** A previous stale-draft crash led to `normalizeTripState` and an App Router error boundary; recovery must never regress.
- **CONFIRMED:** Leaflet on the overview is lazy-loaded near viewport intersection.
- **CONFIRMED:** Maps and remote hotel imagery require network access; there is no offline tile or image cache.
- **CONFIRMED:** Do not expose `.env.local` values. It is ignored and currently exists locally.

## External services and infrastructure

| Service | Purpose | Required? |
|---|---|---|
| Vercel | Production hosting and optional server routes | Production only |
| OpenStreetMap Nominatim | Keyless hotel place lookup | Only hotel lookup |
| OpenStreetMap + CARTO tiles | Leaflet maps | Map pages |
| Booking.com/hotel CDNs | Remote property photography and booking links | Hotel imagery/links |
| Viator, operator sites, Tripadvisor, Booking.com | Review, operator, rate-source links | Source navigation only |
| Yjs + y-webrtc public signaling | P2P state/version sync | Optional collaboration |
| OpenAI Responses API | Dormant optional chat route | Not used by UI; requires `OPENAI_API_KEY` |
| Google Fonts via `next/font/google` | Manrope and Cormorant Garamond | Build/runtime framework behavior |

## Environment assumptions

- **CONFIRMED:** Node.js 22+ and npm are documented; `package.json` does not enforce an `engines` field.
- **CONFIRMED:** No required environment variables for standard local/production behavior.
- **CONFIRMED optional variables:** `OPENAI_API_KEY`, `NEXT_PUBLIC_SIGNALING_URLS`, `SCREENSHOT_BASE_URL`.
- **CONFIRMED:** App commands run from `/workspace/italy-escape`.
- **CONFIRMED:** Vercel Root Directory must be `italy-escape`.

## Critical context that must survive this conversation

1. The repository, not prior chat claims, is authoritative for implementation.
2. Current v2 production is public and must not overwrite v1’s deployment.
3. Earlier plan artifacts live outside Git under `/opt/cursor/artifacts/plans/`; they are historical, not canonical.
4. The context files under `docs/ai/` become canonical project memory after this handoff.
5. Confirmed unresolved risks are tracked in `KNOWN_ISSUES.md`; especially empty-destinations migration, oversized share links, custom hotel coordinates not being persisted, API hardening, and dependency advisories.
