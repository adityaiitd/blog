import { describe, expect, it } from "vitest";
import { freshInitialTripState } from "@/data";
import { decodeTripState, encodeTripState, shareUrl } from "../shareState";

describe("share state", () => {
  it("round-trips the full editable trip", () => {
    const state = freshInitialTripState();
    state.title = "A changed title";
    const decoded = decodeTripState(encodeTripState(state));
    expect(decoded.error).toBeUndefined();
    expect(decoded.state).toEqual(state);
  });

  it("handles invalid links without throwing", () => {
    expect(decodeTripState("not-valid").error).toBeTruthy();
  });

  it("preserves unrelated URL parameters", () => {
    const url = new URL(shareUrl(freshInitialTripState(), "https://example.com/?room=ours"));
    expect(url.searchParams.get("room")).toBe("ours");
    expect(url.searchParams.get("t")).toBeTruthy();
  });
});
