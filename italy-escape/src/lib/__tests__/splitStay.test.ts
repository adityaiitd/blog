import { describe, expect, it } from "vitest";
import { freshInitialTripState } from "@/data";
import { recommendedNightAssignments } from "../splitStay";

describe("split stay recommendations", () => {
  it("puts Sardinia's harbour nights at the end, matching its sailing days", () => {
    const state = freshInitialTripState();
    const stay = state.stays.find((item) => item.region === "Sardinia")!;
    expect(recommendedNightAssignments(stay, state)).toEqual(["cala", "cala", "cala", "vecchia-fonte", "vecchia-fonte"]);
  });

  it("puts Amalfi's harbour nights first, covering arrival and both sailing days", () => {
    const state = freshInitialTripState();
    const stay = state.stays.find((item) => item.region === "Amalfi Coast")!;
    expect(recommendedNightAssignments(stay, state)).toEqual(["ferraioli", "ferraioli", "ferraioli", "anantara", "anantara"]);
  });

  it("leaves a region with no boat days on a single hotel", () => {
    const state = freshInitialTripState();
    const stay = state.stays.find((item) => item.region === "Tuscany")!;
    expect(new Set(recommendedNightAssignments(stay, state)).size).toBe(1);
  });
});
