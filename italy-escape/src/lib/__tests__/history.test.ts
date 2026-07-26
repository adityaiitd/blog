import { describe, expect, it } from "vitest";
import { freshInitialTripState } from "@/data";
import { HISTORY_RETENTION_MS, pruneHistory } from "../storage";
import type { TripVersion } from "../types";

describe("version history", () => {
  const version = (id: string, age: number, pinned = false): TripVersion => ({
    id, name: id, createdAt: new Date(1_000_000 - age).toISOString(), state: freshInitialTripState(), pinned,
  });

  it("prunes autosaves older than five days", () => {
    const result = pruneHistory([version("recent", 1000), version("old", HISTORY_RETENTION_MS + 1)], 1_000_000);
    expect(result.map((item) => item.id)).toEqual(["recent"]);
  });

  it("keeps pinned versions beyond the retention window", () => {
    const result = pruneHistory([version("saved", HISTORY_RETENTION_MS * 2, true)], 1_000_000);
    expect(result[0].id).toBe("saved");
  });
});
