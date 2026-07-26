# Prioritized next steps

Do not start product expansion before the P0 items are resolved. The repository is currently buildable and deployed; priorities below address verified correctness and reliability gaps.

## P0 — required to restore correctness or unblock development

### P0.1 Fix empty-destinations migration

- **Desired outcome:** `normalizeTripState()` must retain/restore all required default destinations when input has `destinations: []`, missing destinations, or partial custom destinations.
- **Why it matters:** Direct probe returned `emptyDestinationMigration=0`; maps and route lookups can silently lose every place.
- **Relevant files:** `italy-escape/src/lib/migrate.ts`, `src/lib/__tests__/migrate.test.ts`, `src/data/places.ts`.
- **Dependencies:** None.
- **Acceptance criteria:**
  - Empty input yields at least all seed destinations.
  - Partial input merges by ID, preserving custom edits and adding missing defaults.
  - Waypoints are not duplicated.
  - Existing stale-draft fixtures still pass.
- **Validation commands:**
  ```bash
  npm test -- src/lib/__tests__/migrate.test.ts
  npm run typecheck
  npm run build
  ```
- **Safe independently:** Yes.
- **User decision required:** No.

### P0.2 Replace oversized full-state share payload

- **Desired outcome:** Typical share URLs remain safely below common transport/proxy limits (target `<8,000` characters; preferably `<4,000`) while preserving all user edits.
- **Why it matters:** Seed encoding is confirmed at `32,005` characters. Links can truncate in messaging, email, proxies, QR codes, or browsers.
- **Relevant files:** `src/lib/shareState.ts`, `src/lib/types.ts`, `src/lib/migrate.ts`, `src/lib/__tests__/shareState.test.ts`, `src/components/share/ShareBar.tsx`.
- **Dependencies:** Decide compact serialization shape; no server is required if seed metadata can be referenced by ID/version.
- **Suggested implementation:** Serialize a versioned delta from `initialTripState` rather than the full media-rich state. Exclude seed photo arrays/static descriptions unless edited.
- **Acceptance criteria:**
  - Full round trip preserves changed dates, order, nights, hotel additions, prices, boats, activities, costs.
  - Seed share payload below target.
  - Old `schemaVersion:1` links still migrate.
  - Invalid/truncated links fall back with a warning.
- **Validation commands:**
  ```bash
  npm test -- src/lib/__tests__/shareState.test.ts src/lib/__tests__/migrate.test.ts
  npm run typecheck
  npm run build
  ```
- **Safe independently:** Mostly; serialization/migration work should be isolated in one commit.
- **User decision required:** Only if a server short-link service is preferred. Default recommendation: client-side delta.

## P1 — required for the current milestone

### P1.1 Deeply validate URL and peer state

- **Desired outcome:** Replace nested `z.any()` with strict schemas/refinements for every shared entity; reject pathological sizes/counts before migration/render.
- **Why it matters:** URL and peer data are untrusted. Current shallow validation can pass malformed nested state and crash or exhaust resources.
- **Relevant files:** `src/lib/shareState.ts`, `src/lib/types.ts`, `src/lib/migrate.ts`, `src/lib/collab.ts`.
- **Dependencies:** Compact share schema from P0.2 should be designed first.
- **Acceptance criteria:** Tests cover missing fields, wrong types, huge arrays, duplicate IDs, invalid coordinates, invalid URLs, negative rates/nights.
- **Validation commands:**
  ```bash
  npm test -- src/lib/__tests__/shareState.test.ts src/lib/__tests__/migrate.test.ts
  npm run typecheck
  ```
- **Safe independently:** After P0.2.
- **User decision required:** No.

### P1.2 Persist custom hotel coordinates and map pins

- **Desired outcome:** A hotel selected from Nominatim creates a real destination/pin and maps the relevant night assignments to it.
- **Why it matters:** UI/README claim a proper pin, but `AddHotel` currently discards `lat`/`lng`.
- **Relevant files:** `src/components/hotels/AddHotel.tsx`, `src/lib/types.ts`, `tripReducer.ts`, `data/places.ts`, `MapClient.tsx`, `TripMapClient.tsx`, `/api/place-lookup`.
- **Dependencies:** Data-model choice: add `HotelOption.destinationId` or introduce lodging points keyed by hotel.
- **Acceptance criteria:** Added hotel survives share/migration, appears on `/map`, and is selected when its night is selected; deleting unassigned custom hotel cleans orphan destination.
- **Validation commands:**
  ```bash
  npm test -- src/lib/__tests__/legOrder.test.ts src/lib/__tests__/migrate.test.ts
  npm run typecheck
  npm run build
  npm run screenshots
  ```
- **Safe independently:** No; touches model, migration, reducer, and maps.
- **User decision required:** Whether one stay should show multiple hotel pins simultaneously. Recommendation: yes, one per assigned hotel.

### P1.3 Correct save/draft reliability

- **Desired outcome:** Private mode/quota failures never throw; unsaved indicator compares against latest pinned save; history remains bounded without silently losing pinned versions.
- **Why it matters:** `saveDraft` is unguarded, and `TripProvider` compares to `history[0]` after only checking that *some* pinned version exists.
- **Relevant files:** `src/lib/storage.ts`, `src/components/site/TripProvider.tsx`, `src/components/share/SaveBar.tsx`, history tests.
- **Dependencies:** None.
- **Acceptance criteria:** Tests cover quota exceptions, autosave newer than pinned save, restore then edit, no pinned history, private mode.
- **Validation commands:**
  ```bash
  npm test -- src/lib/__tests__/history.test.ts
  npm run typecheck
  ```
- **Safe independently:** Yes.
- **User decision required:** No.

### P1.4 Bound public API routes or remove dormant chat API

- **Desired outcome:** Nominatim proxy has query-length/rate limits and one upstream request per user intent; OpenAI route is removed or explicitly protected and connected.
- **Why it matters:** Both endpoints are unauthenticated. OpenAI route would be a cost-abuse vector if a key is configured; place lookup can violate Nominatim usage policy.
- **Relevant files:** `src/app/api/place-lookup/route.ts`, `src/app/api/chat/route.ts`, `ChatPanel.tsx`.
- **Dependencies:** User decision for OpenAI route.
- **Acceptance criteria:** Request size/count limits, graceful 429/503 handling, mocked route tests, no secret sent client-side.
- **Validation commands:**
  ```bash
  npm test
  npm run typecheck
  npm run build
  ```
- **Safe independently:** Place lookup hardening is independent; OpenAI decision is not.
- **User decision required:** Keep/harden LLM route or remove it. Current recommendation: remove until explicitly needed.

### P1.5 Resolve production dependency advisories

- **Desired outcome:** Stable dependency set with no known high-severity production advisories, or a documented accepted exception with compensating controls.
- **Why it matters:** `npm audit --omit=dev` reports 3 high advisories in Next’s bundled PostCSS and Sharp versions.
- **Relevant files:** `package.json`, `package-lock.json`.
- **Dependencies:** Upstream stable Next release that bundles patched versions; do not run `npm audit fix --force` because it proposes Next `9.3.3`.
- **Acceptance criteria:** Clean audit or explicit risk acceptance tied to upstream issue/version; full quality gate passes after update.
- **Validation commands:**
  ```bash
  npm view next version
  npm audit --omit=dev
  npm run lint && npm run typecheck && npm test && npm run build
  ```
- **Safe independently:** Yes, on a dedicated dependency commit.
- **User decision required:** If no stable patched release exists, accept temporary risk versus testing a preview release.

## P2 — important but not immediately blocking

### P2.1 Reconcile value-tier behavior with night splits

- **Desired outcome:** Switching tier does not unexpectedly replace a carefully tuned mixed hotel assignment unless clearly confirmed.
- **Why it matters:** `set-region-tier` and whole-leg `select-hotel` currently fill every night with one hotel; chat also claims boats change when they do not.
- **Relevant files:** `tripReducer.ts`, `ValuePlanner.tsx`, `chatCommands.ts`, `splitStay.ts`.
- **Dependencies:** Product semantics decision.
- **Acceptance criteria:** UI copy and reducer behavior match; regression tests cover mixed splits.
- **Safe independently:** No.
- **User decision required:** Should “value” mean all nights value, or preserve signature/boat-base mix? Recommendation: preserve mix and select value within each role.

### P2.2 Fix stay-night reduction invariants

- **Desired outcome:** Reducing nights always removes exactly the requested number of days or blocks with a clear error; boat activities are reassigned safely.
- **Why it matters:** Current loop skips boat days and can fail to remove enough days, leaving stay/day counts inconsistent.
- **Relevant files:** `tripReducer.ts`, `schedule.ts`, reducer tests.
- **Dependencies:** Define where displaced boat activities go.
- **Acceptance criteria:** Invariant tests across all stays and 0–30 nights.
- **Safe independently:** Yes after behavior decision.
- **User decision required:** If removing a boat day, move it to weather buffer, cancel it, or block the change. Recommendation: prompt/block in UI; reducer remains deterministic.

### P2.3 Add CI and test pyramid

- **Desired outcome:** Every PR runs lint, typecheck, unit tests, build; component/API/E2E tests cover critical flows.
- **Why it matters:** Current gates are manual; prior production crash demonstrates need.
- **Relevant files:** new `.github/workflows/ci.yml`, Vitest config, tests, Playwright config.
- **Dependencies:** None.
- **Acceptance criteria:** CI green on branch; tests cover TripProvider hydration, stale drafts, AddHotel lookup, save/history, collaboration fallback, route handlers.
- **Safe independently:** Yes.
- **User decision required:** Screenshot artifacts in CI or local-only. Recommendation: CI smoke E2E, local full screenshots.

### P2.4 Correct map origin and map-code duplication

- **Desired outcome:** Boat paths originate at selected departure hotels/ports; shared map abstractions remove duplicated tile/style logic.
- **Why it matters:** Current origins are hard-coded to Cala di Volpe/Amalfi and can be wrong for Palau/Praiano assignments.
- **Relevant files:** `MapClient.tsx`, `TripMapClient.tsx`, `places.ts`, hotel coordinate work.
- **Dependencies:** P1.2 custom hotel coordinate model.
- **Acceptance criteria:** Map labels/paths update when night assignments or leg order change.
- **Safe independently:** No, after P1.2.
- **User decision required:** None after model choice.

### P2.5 Correct docs/content drift and review-source integrity

- **Desired outcome:** README and static content match Onda Verde seed; recommendation floor is enforceable; explore links map to exact places.
- **Why it matters:** Current README names retired Palazzo Ferraioli, and several explore links are generic/duplicated.
- **Relevant files:** `README.md`, `data/hotels.ts`, `data/explore.ts`, verification UI.
- **Dependencies:** None.
- **Acceptance criteria:** Link checker passes; no active recommended entry below 4.5; docs match seed.
- **Safe independently:** Yes.
- **User decision required:** Whether rating must be Tripadvisor specifically or equivalent verified review platforms are acceptable.

## P3 — optional, cleanup, or future work

### P3.1 Remove dead code and unused dependencies

- Remove unreferenced `HotelComparator.tsx`, `saveVersions`, `ShareableTripState`, `tripEndDate`, unused Radix/CVA/Testing Library packages if still unused.
- Validate with `npm ls`, lint, typecheck, tests, build.
- **Safe independently:** Yes, one cleanup commit.

### P3.2 Decide discoverability of `/value`

- Add it back to navigation/cross-links or deprecate/remove it.
- **User decision required:** Yes; later UX work removed it from nav but route remains.

### P3.3 Optional travel features

- Currency toggle, `.ics` export, today mode, weather integration, cancellation/payment schedule.
- **Status:** deferred; only implement after explicit user prioritization.
