import { describe, expect, it } from "vitest";
import { freshInitialTripState } from "@/data";
import { moveStay, rebuildRouteLegs } from "../legOrder";
import { tripReducer } from "../tripReducer";
import { hotelsTotal } from "../costCalculator";

describe("leg reordering", () => {
  it("moves a leg and keeps its days, in order, with it", () => {
    const state = freshInitialTripState();
    const amalfiDayTitles = state.days.slice(10, 15).map((day) => day.title);
    const moved = moveStay(state, "stay-amalfi", -1);

    expect(moved.stays.map((stay) => stay.region)).toEqual(["Sardinia", "Amalfi Coast", "Tuscany"]);
    // Amalfi now runs straight after Sardinia's five nights.
    expect(moved.days.slice(6, 11).map((day) => day.title)).toEqual(amalfiDayTitles);
    expect(moved.days.map((day) => day.offset)).toEqual(moved.days.map((_, index) => index));
    expect(moved.days).toHaveLength(state.days.length);
  });

  it("keeps boat days attached to their region", () => {
    const moved = moveStay(freshInitialTripState(), "stay-amalfi", -1);
    const capri = moved.boats.find((boat) => boat.id === "boat-amalfi-1");
    const capriDay = moved.days.find((day) => day.id === capri?.dayId);
    const amalfiStart = 1 + moved.stays[0].nights;
    expect(capriDay!.offset).toBeGreaterThanOrEqual(amalfiStart);
    expect(capriDay!.offset).toBeLessThan(amalfiStart + moved.stays[1].nights);
  });

  it("flies you into the first leg and home from the last, always via airports", () => {
    // Amalfi moved to the front: Amalfi, Sardinia, Tuscany.
    const moved = moveStay(moveStay(freshInitialTripState(), "stay-amalfi", -1), "stay-amalfi", -1);
    expect(moved.stays.map((stay) => stay.region)).toEqual(["Amalfi Coast", "Sardinia", "Tuscany"]);
    const outbound = moved.routeLegs[0];
    const home = moved.routeLegs[moved.routeLegs.length - 1];
    expect([outbound.fromId, outbound.toId]).toEqual(["jfk", "naples-airport"]);
    expect([home.fromId, home.toId]).toEqual(["florence-airport", "ewr"]);
  });

  it("uses a flight when a hop touches Sardinia and a train between mainland legs", () => {
    const state = freshInitialTripState();
    const legs = rebuildRouteLegs(state.stays, state.routeLegs);
    expect(legs.find((leg) => leg.id === "leg-stay-sardinia-stay-tuscany")?.mode).toBe("internal-flight");
    expect(legs.find((leg) => leg.id === "leg-stay-tuscany-stay-amalfi")?.mode).toBe("train");
    // The train uses stations at both ends, not airports.
    const train = legs.find((leg) => leg.mode === "train");
    expect([train?.fromId, train?.toId]).toEqual(["firenze-smn", "napoli-centrale"]);
  });

  it("leaves the hotel spend unchanged by a reorder", () => {
    const state = freshInitialTripState();
    const moved = tripReducer(state, { type: "move-stay", stayId: "stay-amalfi", direction: -1 });
    expect(hotelsTotal(moved.hotels, moved.stays)).toBe(hotelsTotal(state.hotels, state.stays));
  });

  it("refuses to move the first leg earlier", () => {
    const state = freshInitialTripState();
    expect(moveStay(state, "stay-sardinia", -1)).toBe(state);
  });
});

describe("adding a hotel by name", () => {
  it("adds it to the region with working booking and review links", () => {
    const state = freshInitialTripState();
    const next = tripReducer(state, { type: "add-hotel", region: "Amalfi Coast", patch: { name: "Le Sirenuse", nightlyRate: 1200 } });
    const added = next.hotels.find((hotel) => hotel.name === "Le Sirenuse");
    expect(added).toBeDefined();
    expect(added!.region).toBe("Amalfi Coast");
    expect(added!.nightlyRate).toBe(1200);
    expect(added!.bookingUrl).toContain("Le%20Sirenuse");
    expect(added!.reviewUrl).toContain("Le%20Sirenuse");
    expect(Array.isArray(added!.photos)).toBe(true);
  });

  it("can be assigned to a leg on creation", () => {
    const next = tripReducer(freshInitialTripState(), {
      type: "add-hotel", region: "Tuscany", patch: { name: "Villa Bordoni" }, assignToStayId: "stay-tuscany",
    });
    const stay = next.stays.find((item) => item.id === "stay-tuscany")!;
    const added = next.hotels.find((hotel) => hotel.name === "Villa Bordoni")!;
    expect(stay.hotelId).toBe(added.id);
    expect(new Set(stay.nightHotelIds)).toEqual(new Set([added.id]));
  });
});
