import { describe, expect, it } from "vitest";
import { freshInitialTripState } from "@/data";
import { tripReducer } from "../tripReducer";

describe("trip reducer", () => {
  it("moves a boat activity and updates its excursion day", () => {
    const state = freshInitialTripState();
    const next = tripReducer(state, { type: "move-activity", fromDayId: "day-11", toDayId: "day-13", activityId: "a-11" });
    expect(next.days.find((day) => day.id === "day-13")?.activities.some((activity) => activity.id === "a-11")).toBe(true);
    expect(next.boats.find((boat) => boat.id === "boat-amalfi-1")?.dayId).toBe("day-13");
  });

  it("adds a day and reflows following dates when nights increase", () => {
    const state = freshInitialTripState();
    const next = tripReducer(state, { type: "update-stay", id: "stay-sardinia", patch: { nights: 6 } });
    expect(next.days).toHaveLength(state.days.length + 1);
    expect(next.days.map((day) => day.offset)).toEqual(next.days.map((_, index) => index));
    expect(next.stays[0].nights).toBe(6);
  });

  it("prevents deleting a selected hotel", () => {
    const state = freshInitialTripState();
    expect(tripReducer(state, { type: "delete-hotel", id: "cala" }).hotels).toHaveLength(state.hotels.length);
  });

  it("switches only the requested region to its recommended value hotel", () => {
    const state = freshInitialTripState();
    const next = tripReducer(state, { type: "set-region-tier", stayId: "stay-amalfi", tier: "value" });
    expect(next.stays.find((stay) => stay.id === "stay-amalfi")).toMatchObject({ tier: "value", hotelId: "marina-riviera" });
    expect(next.stays.find((stay) => stay.id === "stay-sardinia")?.tier).toBe("luxury");
  });
});
