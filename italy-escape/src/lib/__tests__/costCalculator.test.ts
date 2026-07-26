import { describe, expect, it } from "vitest";
import { freshInitialTripState } from "@/data";
import { boatCharter, calculateCosts, fitToTarget, hotelTotal, hotelsTotal, internationalFlightsTotal, taxesTotal } from "../costCalculator";
import { tripReducer } from "../tripReducer";

describe("cost calculator", () => {
  it("prices the seeded split stays night by night", () => {
    const state = freshInitialTripState();
    // Sardinia 3 resort + 2 harbour nights, Tuscany one base, Amalfi 3 harbour + 2 resort nights.
    expect(hotelsTotal(state.hotels, [state.stays[0]])).toBe(3 * 1927 + 2 * 280);
    expect(hotelsTotal(state.hotels, [state.stays[1]])).toBe(4 * 861);
    expect(hotelsTotal(state.hotels, [state.stays[2]])).toBe(3 * 330 + 2 * 1898);
    expect(hotelsTotal(state.hotels, state.stays)).toBe(14571);
  });

  it("keeps every boat-base hotel under the $400 nightly ceiling", () => {
    const bases = freshInitialTripState().hotels.filter((hotel) => hotel.role === "boat-base");
    expect(bases.length).toBeGreaterThan(0);
    bases.forEach((hotel) => expect(hotel.nightlyRate).toBeLessThanOrEqual(400));
  });

  it("only recommends properties rated 4.5 or better where a rating is published", () => {
    freshInitialTripState().hotels
      .filter((hotel) => hotel.recommended && hotel.verified)
      .forEach((hotel) => expect(hotel.rating).toBeGreaterThanOrEqual(4.5));
  });

  it("offers only private charters, each linked to its operator", () => {
    freshInitialTripState().boats.forEach((boat) => {
      expect(boat.options.length).toBeGreaterThan(1);
      boat.options.forEach((option) => {
        expect(option.url).toMatch(/^https:\/\//);
        expect(option.price).toBeGreaterThan(0);
        expect(option.maxGuests).toBeGreaterThanOrEqual(2);
      });
    });
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
    const charters = state.boats.reduce((sum, boat) => sum + boatCharter(boat), 0);
    expect(taxesTotal(state)).toBe(14 * 2 * 5.5 + charters * .1 + 5600 * .1);
  });

  it("keeps the seeded trip under the $35,000 target for two people", () => {
    const status = fitToTarget(freshInitialTripState());
    expect(status.target).toBe(35000);
    expect(status.withinTarget).toBe(true);
    expect(status.total).toBeLessThan(35000);
    expect(status.total).toBeGreaterThan(30000);
  });

  it("ranks levers by savings and each one actually reduces the total", () => {
    const state = freshInitialTripState();
    const { levers } = fitToTarget(state);
    expect(levers.length).toBeGreaterThan(0);
    expect(levers.map((lever) => lever.savings)).toEqual([...levers.map((lever) => lever.savings)].sort((a, b) => b - a));
    const applied = levers[0].actions.reduce(tripReducer, state);
    expect(calculateCosts(applied).baseline).toBeLessThan(calculateCosts(state).baseline);
  });

  it("reports the shortfall when the target is lowered below the plan", () => {
    const state = { ...freshInitialTripState(), budgetTarget: 25000 };
    const status = fitToTarget(state);
    expect(status.withinTarget).toBe(false);
    expect(status.difference).toBeGreaterThan(0);
  });
});
