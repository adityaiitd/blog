# Known issues and risks

Severity definitions:

- **Critical:** confirmed data/correctness failure with broad user impact.
- **High:** likely broken core feature, security/cost exposure, or major reliability risk.
- **Medium:** incorrect edge behavior, fragile integration, or maintainability risk.
- **Low:** cleanup, documentation, or minor robustness gap.

## KI-001 — Empty destinations survive migration as empty

- **Severity:** Critical
- **Status:** verified
- **Evidence:** Direct probe on `2026-07-26`: `normalizeTripState({...freshInitialTripState(), destinations: []}).destinations.length === 0`.
- **Reproduction:**
  ```bash
  npx tsx -e "import { freshInitialTripState } from './src/data/index.ts'; import { normalizeTripState } from './src/lib/migrate.ts'; const s=freshInitialTripState(); console.log(normalizeTripState({...s,destinations:[]}).destinations.length)"
  ```
- **Relevant files:** `src/lib/migrate.ts:113-116`, `src/data/places.ts`.
- **Likely cause:** The condition evaluates fallback defaults, but the true branch returns `input.destinations`.
- **Impact:** Maps lose pins; route/boat place lookups fail.
- **Proposed fix:** Merge input/default destinations by ID and test empty/partial/duplicate cases.

## KI-002 — Share URLs are too large

- **Severity:** High
- **Status:** verified
- **Evidence:** Default encoded payload length is `32,005` characters.
- **Reproduction:** See probe in `NEXT_STEPS.md` or run `encodeTripState(freshInitialTripState()).length`.
- **Relevant files:** `src/lib/shareState.ts`, `src/data/hotels.ts`.
- **Likely cause:** Full state includes static hotel photo URL arrays and all seed metadata.
- **Impact:** Link truncation/failure in email, SMS, proxies, QR codes, or browsers.
- **Proposed fix:** Versioned delta serialization relative to seed; exclude unchanged static media/content.

## KI-003 — Shared-state validation is shallow

- **Severity:** High
- **Status:** verified by code inspection
- **Evidence:** `shareState.ts` uses `z.array(z.any())` for every nested collection and `z.any()` for tax settings.
- **Relevant files:** `src/lib/shareState.ts`.
- **Likely cause:** Early implementation optimized for migration speed.
- **Impact:** Malformed/crafted URL data can pass top-level validation and crash or exhaust the UI.
- **Proposed fix:** Strict nested schemas, count/length bounds, ID/coordinate/rate refinements, then migration.

## KI-004 — Custom hotel coordinates are discarded

- **Severity:** High
- **Status:** verified
- **Evidence:** `/api/place-lookup` returns `lat`/`lng`; `AddHotel.add()` dispatches name/rate/address/website but no destination coordinates.
- **Reproduction:** Add a Nominatim-matched hotel; inspect `TripState.destinations` or `/map`.
- **Relevant files:** `src/app/api/place-lookup/route.ts`, `src/components/hotels/AddHotel.tsx`, `src/lib/tripReducer.ts`.
- **Impact:** Added hotel cannot appear as its own map pin despite UI/docs claiming it will.
- **Proposed fix:** Add a hotel lodging destination relation and persist coordinates.

## KI-005 — Public API routes lack abuse controls

- **Severity:** High
- **Status:** verified
- **Evidence:** No auth, rate limit, body/query cap, or request budget in either route.
- **Relevant files:** `src/app/api/place-lookup/route.ts`, `src/app/api/chat/route.ts`.
- **Impact:** Nominatim proxy can be abused/throttled; OpenAI route becomes a cost vector if a key is configured.
- **Proposed fix:** Query/body limits, per-IP/edge throttling, caching, explicit route removal or authorization.

## KI-006 — OpenAI route is dormant and sends full trip state

- **Severity:** High if enabled; Low while no key is configured
- **Status:** verified
- **Evidence:** `ChatPanel` never fetches `/api/chat`; route sends `{message,state}` to OpenAI.
- **Relevant files:** `src/app/api/chat/route.ts`, `src/components/chat/ChatPanel.tsx`.
- **Impact:** Dead integration today; privacy/cost risk if `OPENAI_API_KEY` is set.
- **Proposed fix:** Remove route until authorized, or add consent, minimization, auth/rate limiting, validation, and UI wiring.

## KI-007 — High-severity production dependency advisories

- **Severity:** High
- **Status:** verified by `npm audit --omit=dev`
- **Evidence:** 3 high advisories:
  - Next-bundled `postcss@8.4.31` (`GHSA-qx2v-qp2m-jg93`, `GHSA-6g55-p6wh-862q`, `GHSA-r28c-9q8g-f849`)
  - Next-bundled `sharp@0.34.5` (2026 libvips CVEs)
- **Relevant files:** `package.json`, `package-lock.json`.
- **Constraint:** npm proposes `npm audit fix --force` to Next `9.3.3`, an invalid breaking downgrade. Earlier override experimentation was reverted.
- **Proposed fix:** Track stable Next release with patched bundled dependencies; do not force-fix.

## KI-008 — Unsaved indicator baseline may use the wrong version

- **Severity:** Medium
- **Status:** verified by code inspection
- **Evidence:** `TripProvider.tsx:72` checks for any pinned version but serializes `history[0]`, which may be a newer autosave.
- **Relevant files:** `src/components/site/TripProvider.tsx`.
- **Impact:** “Unsaved changes” can be wrong.
- **Proposed fix:** Select the latest pinned version explicitly; update signature after restore/save.

## KI-009 — `saveDraft` is not guarded

- **Severity:** Medium
- **Status:** verified
- **Evidence:** `storage.ts:18-19` calls `localStorage.setItem` without `try/catch`; other storage writes are guarded.
- **Impact:** Quota/private-mode errors can throw in a state-change effect.
- **Proposed fix:** Catch quota/security errors and surface non-blocking persistence status.

## KI-010 — Full state copies can exhaust localStorage

- **Severity:** Medium
- **Status:** verified by architecture/code
- **Evidence:** Up to 200 versions each contain complete `TripState`; photos/links inflate each copy.
- **Relevant files:** `storage.ts`, `TripProvider.tsx`.
- **Impact:** Quota pressure, history trimming, draft write failure/data loss.
- **Proposed fix:** Store deltas/compressed snapshots and monitor quota; guard draft writes.

## KI-011 — Collaboration is last-write-wins whole-state replacement

- **Severity:** Medium
- **Status:** verified
- **Evidence:** Yjs map stores JSON strings; remote `state` calls reducer `replace`.
- **Relevant files:** `collab.ts`, `TripProvider.tsx`.
- **Impact:** Concurrent edits can silently overwrite each other; Yjs is only transport, not semantic merge.
- **Privacy:** Anyone with room URL can receive state/version/author data.
- **Proposed fix:** Sync domain operations or CRDT fields, add conflict indicators, document bearer-link model.

## KI-012 — Reducing nights can desynchronize stays and days

- **Severity:** Medium
- **Status:** suspected from verified code path; not reproduced in handoff
- **Evidence:** Shrink loop skips days with boat activities and may remove fewer days than `abs(delta)`, while stay nights still decrease.
- **Relevant files:** `tripReducer.ts:64-75`.
- **Impact:** Day count/date range may not match hotel nights; region block segmentation becomes fragile.
- **Proposed fix:** Enforce invariant or block/reassign boat day before reducing.

## KI-013 — Tier and whole-hotel selection destroy mixed night assignments

- **Severity:** Medium
- **Status:** verified by code inspection
- **Evidence:** `set-region-tier` fills every `nightHotelIds` entry with one hotel. `select-hotel` does the same when the user clicks “Use for this leg.”
- **Relevant files:** `tripReducer.ts:88-107`, `ValuePlanner.tsx`, `HotelStoryPlanner.tsx`, `splitStay.ts`.
- **Impact:** A carefully designed signature/boat-base split is lost.
- **Additional contradiction:** Chat says hotel and boat estimates update together, but reducer does not change selected boat options.
- **Proposed fix:** Define value semantics and preserve role-based splits.

## KI-014 — Seed route legs and derived route legs diverge

- **Severity:** Medium
- **Status:** verified
- **Evidence:** `transfers.ts` includes Palau-specific legs; `rebuildRouteLegs()` creates generic connections and replaces all legs after reorder.
- **Impact:** Manual route edits/seed details can disappear on reorder; behavior differs before/after first reorder.
- **Proposed fix:** Make routes fully derived with overrides, or define which fields survive rebuild.

## KI-015 — Map origins can be wrong

- **Severity:** Medium
- **Status:** verified
- **Evidence:** `TripMapClient` uses hard-coded boat origins (`cala-di-volpe` and `amalfi`).
- **Impact:** Palau/Praiano/custom hotel assignments do not update boat geometry.
- **Proposed fix:** Store explicit departure destination per selected boat option or infer from lodging/departure port data.

## KI-016 — README contradicts seed data and image behavior

- **Severity:** Medium documentation defect
- **Status:** verified
- **Evidence:**
  - README says Palazzo Ferraioli; seed uses Hotel Onda Verde.
  - README says local generated editorial images and official-gallery links; hotel cards now directly use remote real property imagery.
  - README says lookup attaches coordinates/pin; implementation discards coordinates.
- **Relevant files:** `README.md`, `data/hotels.ts`, `AddHotel.tsx`.
- **Proposed fix:** Update README after P1.2 data-model decision.

## KI-017 — Recommendation rating floor is not enforced

- **Severity:** Medium
- **Status:** verified
- **Evidence:** Many hotel/operator entries have `rating: 0`; schema/reducer/UI does not block recommendation.
- **Impact:** Latest 4.5+ user rule can regress through seed or user actions.
- **Proposed fix:** Separate “verified recommendation” from catalog option; validate only active recommended entries or display “unverified.”

## KI-018 — External image/link availability and copyright dependence

- **Severity:** Medium
- **Status:** inherent/verified
- **Evidence:** Remote patterns include Booking.com, Belmond, Rosewood, and hotel CDNs; source URLs can change/block.
- **Impact:** Broken images/links, legal/terms risk, network latency.
- **Proposed fix:** Confirm licensing/terms; implement graceful image fallback and automated link checks. Do not silently download copyrighted assets.

## KI-019 — No automated CI or test pyramid

- **Severity:** Medium
- **Status:** verified
- **Evidence:** No `.github/workflows`; no component/API/collab tests; screenshot script is manual.
- **Impact:** Regressions depend on an agent remembering the quality gate.
- **Proposed fix:** Add CI and targeted component/route/E2E tests.

## KI-020 — External links omit explicit `noopener`

- **Severity:** Low
- **Status:** verified by audit
- **Evidence:** Links commonly use `rel="noreferrer"` rather than `noopener noreferrer`.
- **Impact:** Minor tabnabbing compatibility risk in older environments.
- **Proposed fix:** Standardize a safe external-link component.

## KI-021 — Dead code and unused dependencies

- **Severity:** Low
- **Status:** verified
- **Evidence:** Unreferenced `HotelComparator.tsx`; unused `saveVersions`, `ShareableTripState`; Radix/CVA/Testing Library dependencies have no source imports.
- **Impact:** install size/confusion.
- **Proposed fix:** remove in a dedicated cleanup commit after confirming no intended near-term use.

## KI-022 — Explore source-link quality varies

- **Severity:** Low
- **Status:** verified by inspection
- **Evidence:** Liscia Ruja, Razza di Juncu, and Cugnana trails reuse broad San Pantaleo guides.
- **Impact:** “More on this” may not land on exact place detail.
- **Proposed fix:** verify and replace with exact official/authoritative pages.

## KI-023 — No offline map/content support

- **Severity:** Low
- **Status:** verified
- **Evidence:** live CARTO/OSM tiles and remote imagery; no service worker/offline region.
- **Impact:** Travel-time usefulness drops with poor connectivity.
- **Proposed fix:** optional future PWA/offline itinerary; map tile caching requires policy review.

## KI-024 — Google Font availability/privacy dependency

- **Severity:** Low
- **Status:** verified
- **Evidence:** `next/font/google` for Manrope and Cormorant Garamond.
- **Impact:** Build/runtime external dependency and privacy considerations.
- **Proposed fix:** self-host font files if required.

## KI-025 — `npm ls` reports extraneous transitive packages

- **Severity:** Low
- **Status:** verified
- **Evidence:** `@emnapi/core`, `@emnapi/wasi-threads`, `@napi-rs/wasm-runtime`, `@tybys/wasm-util` listed extraneous.
- **Impact:** Local install hygiene; likely native tooling residue.
- **Proposed fix:** fresh `npm ci` in clean environment and compare; do not remove manually.
