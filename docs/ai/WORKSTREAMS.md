# Workstreams

## WS-01 — Core itinerary and editing

- **Status:** COMPLETE
- **Objective:** Keep dates, days, activities, stays, and routes editable from one canonical state.
- **Completed:** Typed model, reducer actions, undo/redo, date shifts, night reflow, DnD day/activity editing, booking details, weather buffer.
- **Work in progress:** None.
- **Remaining:** Fix the rare night-reduction desynchronization described in `KNOWN_ISSUES.md`.
- **Dependencies:** `TripState`, `tripReducer`, `schedule`, `TripProvider`.
- **Relevant files:** `src/lib/types.ts`, `tripReducer.ts`, `schedule.ts`, `components/itinerary/ItineraryPlanner.tsx`.
- **Blockers:** None.
- **Acceptance criteria:** Every stay-night change leaves `days.length === 2 + sum(stay.nights)`, preserves boat activities, and all derived dates remain sequential.
- **Recommended next action:** Add invariant tests, then fix shrink logic.

## WS-02 — Leg order and connection rebuilding

- **Status:** COMPLETE, with model divergence debt
- **Objective:** Reorder regional chapters and cascade days, dates, boats, flights, trains, and cars.
- **Completed:** `moveStay`, day segmentation, route rebuild, overview controls, tests for airport/station routing.
- **Work in progress:** None.
- **Remaining:** Decide whether route legs are always derived or user-editable/stored; reconcile seed `transfers.ts` with rebuilt output.
- **Dependencies:** Stay hub metadata, destinations, route costs.
- **Relevant files:** `src/lib/legOrder.ts`, `src/components/site/LegOrder.tsx`, `src/data/transfers.ts`.
- **Known blockers:** Product decision on preserving manually edited route legs after reorder.
- **Acceptance criteria:** Any permutation of three stays produces valid airport/rail connections and preserves region day blocks.
- **Recommended next action:** Add permutation tests and document overwrite semantics for manual route edits.

## WS-03 — Hotels, split stays, and lookup

- **Status:** ACTIVE
- **Objective:** Compare luxury/value properties, assign hotels per night, show real details, and add arbitrary hotels.
- **Completed:** Night dropdowns, split recommendations, galleries, links, ratings/rates, under-$500 options, Nominatim lookup.
- **Work in progress:** None currently.
- **Remaining:** Persist lookup coordinates as destinations/map pins; enforce/communicate 4.5+ recommendation rule; validate external links; fill missing photos/reviews.
- **Dependencies:** Nominatim, remote CDNs, hotel seed data, map destination model.
- **Relevant files:** `src/data/hotels.ts`, `HotelStoryPlanner.tsx`, `AddHotel.tsx`, `/api/place-lookup`, `splitStay.ts`.
- **Blockers:** Need a data-model decision for one stay with multiple hotel coordinates.
- **Acceptance criteria:** Adding a hotel stores address and coordinates, creates a selectable map pin, survives URL/local migration, and updates all totals.
- **Recommended next action:** Design `HotelOption.destinationId` or per-night lodging coordinates before implementation.

## WS-04 — Private boat planning

- **Status:** COMPLETE
- **Objective:** Offer private, appropriately sized half/full-day operator options for two with source links and live totals.
- **Completed:** Four excursions, multiple private options, durations, prices, ratings/source links, inclusions/exclusions, gratuity, weather and backup.
- **Work in progress:** None.
- **Remaining:** Update boat map origins to actual selected lodging/departure port; periodically re-verify static prices/links.
- **Dependencies:** External operator links, map waypoints, hotel assignment.
- **Relevant files:** `src/data/boatTrips.ts`, `BoatPlanner.tsx`, `costCalculator.ts`.
- **Blockers:** No live operator API; prices remain estimates.
- **Acceptance criteria:** Selecting any option recalculates charter, gratuity, VAT, scenarios, target, map label, print output.
- **Recommended next action:** Add freshness/verified-at metadata and link check tooling.

## WS-05 — Budget and target management

- **Status:** COMPLETE
- **Objective:** Keep the two-person plan understandable and under the configurable target.
- **Completed:** Hotels, boats, cars, internal flight, train, restaurants, spa, international economy, taxes/service, contingency, scenarios, per-night/person metrics, ranked levers.
- **Work in progress:** None.
- **Remaining:** Decide whether “recommended” should include an extra 8% on top of contingency; add currency support only if user reauthorizes.
- **Dependencies:** Cost categories and selected hotel/boat options.
- **Relevant files:** `costCalculator.ts`, `CostCalculator.tsx`, `BudgetTarget.tsx`, `data/costs.ts`.
- **Blockers:** Static estimates, not live quotes.
- **Acceptance criteria:** All upstream edits update every budget display consistently; tests cover target and lever ordering.
- **Recommended next action:** Add cross-view invariant tests rather than new UI.

## WS-06 — Maps and spatial planning

- **Status:** ACTIVE
- **Objective:** Show route, hotels, boats, and transport spatially with editable markers and synced list.
- **Completed:** Two Leaflet views, route styles, layers, side selection, marker editing, lazy overview load.
- **Work in progress:** None.
- **Remaining:** Fix custom hotel pins, dynamic boat origins, empty-destination migration, duplicated map logic.
- **Dependencies:** Destination completeness, external CARTO/OSM connectivity.
- **Relevant files:** `MapClient.tsx`, `TripMapClient.tsx`, `RouteMap.tsx`, `places.ts`.
- **Blockers:** Hotel coordinate model.
- **Acceptance criteria:** Every selected lodging and departure point has a valid pin; migrations never remove defaults; maps fail gracefully offline.
- **Recommended next action:** Fix migration P0 before spatial enhancements.

## WS-07 — Sharing, saves, history, and collaboration

- **Status:** ACTIVE
- **Objective:** Share a customized trip, co-edit with spouse, save named versions, and restore changes.
- **Completed:** URL state, local draft/history, author attribution, global Save/History UI, 5-day autosaves, P2P sync and peer count.
- **Work in progress:** None.
- **Remaining:** Shrink share links, correct saved-signature baseline, guard draft saves, improve simultaneous edit semantics, clarify persistence limitations.
- **Dependencies:** Browser storage, URL support, signaling.
- **Relevant files:** `shareState.ts`, `storage.ts`, `TripProvider.tsx`, `collab.ts`, `SaveBar.tsx`, `ShareBar.tsx`.
- **Known blockers:** No backend means no durable asynchronous shared save store.
- **Acceptance criteria:** Links work across common messaging/email paths; simultaneous edits do not silently overwrite; quota/private mode cannot crash the app.
- **Recommended next action:** Redesign compact share serialization first.

## WS-08 — Trip assistant

- **Status:** COMPLETE for deterministic commands; DEFERRED for LLM
- **Objective:** Edit/query the trip conversationally without making normal operation depend on paid AI.
- **Completed:** Local parser for tiers, nights, dates, travelers, contingency, boat moves, split stays, budget target, activities, review summaries.
- **Work in progress:** None.
- **Remaining:** Either remove dormant OpenAI route or explicitly wire/harden it after user decision.
- **Dependencies:** `TripAction`, cost/split derivations.
- **Relevant files:** `ChatPanel.tsx`, `chatCommands.ts`, `/api/chat`.
- **Blockers:** Security/cost decision for public LLM endpoint.
- **Acceptance criteria:** Unsupported phrases are honest; supported actions are previewable or undoable as one logical change.
- **Recommended next action:** Decide remove versus harden; do not expose key before rate limiting/auth.

## WS-09 — Curated places and presentation

- **Status:** COMPLETE
- **Objective:** Explain restaurants, sights, calm spots, beaches, and present/print the trip.
- **Completed:** `/explore`, add-to-trip, `/present`, `/print`.
- **Work in progress:** None.
- **Remaining:** Periodic link/content verification; correct duplicate/mismatched explore source URLs.
- **Dependencies:** Static editorial data and external links.
- **Relevant files:** `data/explore.ts`, `ExploreGuide.tsx`, `present/page.tsx`, `print/page.tsx`.
- **Blockers:** None.
- **Acceptance criteria:** Links correspond to the named place; added spot lands in the intended regional day.
- **Recommended next action:** Audit explore links as a small independent task.

## WS-10 — Reliability, security, and release engineering

- **Status:** ACTIVE
- **Objective:** Prevent production crashes/data loss and automate validation.
- **Completed:** strict TypeScript, lint, 47 pure-lib tests, migration tests, App Router error recovery, screenshot/console QA, production build.
- **Work in progress:** This handoff.
- **Remaining:** Fix confirmed migration bug, audit advisories, API throttling, deep share validation, CI, component/API/E2E tests, CSP/security headers.
- **Dependencies:** Upstream Next releases, deployment environment.
- **Relevant files:** `package.json`, `shareState.ts`, `migrate.ts`, API routes, tests, `scripts/screenshots.mjs`.
- **Blockers:** Next’s bundled vulnerable transitive versions have no safe stable npm audit fix today.
- **Acceptance criteria:** CI enforces lint/type/test/build; no known P0 bugs; APIs bounded; URL/draft/peer state fully validated.
- **Recommended next action:** Fix and test empty-destinations migration immediately.

## WS-11 — Documentation and canonical memory

- **Status:** COMPLETE for initial handoff; ACTIVE by policy
- **Objective:** Replace dependence on the historical conversation with durable repository context.
- **Completed:** `docs/ai/PROJECT_CONTEXT.md`, `CURRENT_STATE.md`, `DECISIONS.md`, `ARCHITECTURE.md`, `WORKSTREAMS.md`, `NEXT_STEPS.md`, `KNOWN_ISSUES.md`, `SESSION_LOG.md`, `CONTEXT_MANIFEST.yaml`.
- **Remaining:** Update after material decisions, releases, blockers, or architectural changes.
- **Dependencies:** Repository evidence.
- **Relevant files:** `docs/ai/*`.
- **Blockers:** None.
- **Acceptance criteria:** A new agent can proceed without reading the old conversation; current branch/state/risks remain accurate.
- **Recommended next action:** Re-read relevant files at every new task start and update them before handoff.
