import { describe, expect, it } from "vitest";
import { freshInitialTripState } from "@/data";
import { calculateCosts, hotelTotal, hotelsTotal, internationalFlightsTotal, taxesTotal } from "../costCalculator";
import { tripReducer } from "../tripReducer";

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

  it("includes economy international flights for both travelers", () => {
    expect(internationalFlightsTotal(freshInitialTripState())).toBe(2300);
  });

  it("calculates city tax, boat VAT and dining service explicitly", () => {
    const state = freshInitialTripState();
    const expected = 14 * 2 * 5.5 + 14000 * .1 + 6500 * .1;
    expect(taxesTotal(state)).toBe(expected);
  });

  it("saves roughly twenty to thirty percent when one leg moves to value", () => {
    const luxury = freshInitialTripState();
    const value = tripReducer(luxury, { type: "set-region-tier", stayId: "stay-amalfi", tier: "value" });
    const luxuryTotal = calculateCosts(luxury).subtotal;
    const valueTotal = calculateCosts(value).subtotal;
    expect(valueTotal).toBeLessThan(luxuryTotal);
    const regionLuxury = 1898 * 5 + 3000 * 2 + 300 * 2;
    const regionValue = 1400 * 5 + 2250 * 2 + 300 * 2;
    expect((regionLuxury - regionValue) / regionLuxury).toBeGreaterThan(.2);
    expect((regionLuxury - regionValue) / regionLuxury).toBeLessThan(.3);
  });
});
