import { describe, expect, it } from "vitest";
import { freshInitialTripState } from "@/data";
import { normalizeTripState } from "../migrate";
import type { TripState } from "../types";

/** The production crash: a saved draft holding a hotel that no longer ships with the app. */
const staleDraft = {
  schemaVersion: 1, title: "Our Italy Escape", startDate: "2026-08-30", travelers: 2,
  destinations: [], routeLegs: [], days: [], boats: [], costs: [], contingencyPercent: 7,
  hotels: [{ id: "ferraioli", region: "Amalfi Coast", name: "Palazzo Ferraioli", nightlyRate: 350, tier: "value" }],
  stays: [{ id: "stay-amalfi", region: "Amalfi Coast", destinationId: "amalfi", hotelId: "ferraioli", nights: 5, tier: "value", nightHotelIds: ["ferraioli", "ferraioli", "ferraioli", "ferraioli", "ferraioli"] }],
} as unknown as TripState;

describe("draft migration", () => {
  it("completes a retired hotel instead of leaving undefined fields behind", () => {
    const hotel = normalizeTripState(staleDraft).hotels.find((item) => item.id === "ferraioli");
    expect(hotel).toBeDefined();
    expect(Array.isArray(hotel!.photos)).toBe(true);
    expect(Array.isArray(hotel!.pools)).toBe(true);
    expect(hotel!.reviewUrl).toMatch(/^https:\/\//);
  });

  it("keeps every current hotel available alongside the saved one", () => {
    const ids = normalizeTripState(staleDraft).hotels.map((hotel) => hotel.id);
    freshInitialTripState().hotels.forEach((hotel) => expect(ids).toContain(hotel.id));
  });

  it("repairs night assignments that point at missing hotels", () => {
    const stay = normalizeTripState({ ...staleDraft, hotels: [] } as unknown as TripState).stays[0];
    stay.nightHotelIds?.forEach((id) => expect(id).not.toBe("ferraioli"));
    expect(stay.nightHotelIds).toHaveLength(stay.nights);
  });

  it("restores seeded content when arrays are missing entirely", () => {
    const recovered = normalizeTripState({ schemaVersion: 1, startDate: "2026-08-30", travelers: 2 } as unknown as TripState);
    expect(recovered.days.length).toBeGreaterThan(0);
    expect(recovered.boats.length).toBeGreaterThan(0);
    expect(recovered.hotels.every((hotel) => Array.isArray(hotel.photos))).toBe(true);
  });
});
