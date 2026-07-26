import { describe, expect, it } from "vitest";
import { freshInitialTripState } from "@/data";
import { interpretTripCommand } from "../chatCommands";

describe("trip chat commands", () => {
  it("changes one region to the value plan", () => {
    expect(interpretTripCommand("Make Amalfi cheaper", freshInitialTripState()).actions).toEqual([
      { type: "set-region-tier", stayId: "stay-amalfi", tier: "value" },
    ]);
  });

  it("changes nights with a schedule-reflow action", () => {
    expect(interpretTripCommand("Set Tuscany to 5 nights", freshInitialTripState()).actions[0]).toEqual({
      type: "update-stay", id: "stay-tuscany", patch: { nights: 5 },
    });
  });

  it("answers budget questions without editing", () => {
    const result = interpretTripCommand("What is our total budget?", freshInitialTripState());
    expect(result.actions).toHaveLength(0);
    expect(result.reply).toContain("$");
  });
});
