import { describe, expect, it } from "vitest";
import { freshInitialTripState } from "@/data";
import { calculateCosts, hotelTotal, hotelsTotal } from "../costCalculator";

describe("cost calculator", () => {
  it("matches the initial hotel benchmark", () => {
    const state = freshInitialTripState();
    expect(hotelsTotal(state.hotels, state.stays)).toBe(22569);
  });

  it("applies room level, premium, tax and complimentary nights", () => {
    const state = freshInitialTripState();
    const hotel = { ...state.hotels[0], selectedRoom: "sea-view" as const, refundablePremium: 10, taxRate: 20, complimentaryNights: 1 };
    expect(hotelTotal(hotel, 5)).toBeCloseTo(1927 * 1.25 * 1.1 * 4 * 1.2);
  });

  it("produces ordered scenarios and useful per-person figures", () => {
    const result = calculateCosts(freshInitialTripState());
    expect(result.recommended).toBeGreaterThan(result.baseline);
    expect(result.splurge).toBeGreaterThan(result.recommended);
    expect(result.perPerson).toBe(result.baseline / 2);
    expect(Number.isFinite(result.perNight)).toBe(true);
  });
});
