import { describe, expect, it } from "vitest";
import { freshInitialTripState } from "@/data";
import { dateForOffset, reorderDays, totalNights } from "../schedule";

describe("schedule", () => {
  it("calculates dates across month boundaries", () => {
    expect(dateForOffset("2026-08-30", 15).toISOString().slice(0, 10)).toBe("2026-09-14");
  });

  it("totals the fourteen hotel nights", () => {
    expect(totalNights(freshInitialTripState().stays)).toBe(14);
  });

  it("reflows offsets after a reorder", () => {
    const days = freshInitialTripState().days;
    const next = reorderDays(days, "day-3", "day-5");
    expect(next.map((day) => day.offset)).toEqual(next.map((_, index) => index));
    expect(next.findIndex((day) => day.id === "day-3")).toBe(5);
  });

  it("seeds explicit hotel, boat, public and transit activities", () => {
    const venues = new Set(freshInitialTripState().days.flatMap((day) => day.activities.map((activity) => activity.venue)));
    expect([...venues].sort()).toEqual(["boat", "hotel", "public", "transit"]);
  });
});
