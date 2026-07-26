import { compressToEncodedURIComponent, decompressFromEncodedURIComponent } from "lz-string";
import { z } from "zod";
import type { TripState } from "./types";

const tripSchema = z.object({
  schemaVersion: z.literal(1),
  title: z.string(),
  startDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  travelers: z.number().int().min(1).max(20),
  destinations: z.array(z.any()),
  routeLegs: z.array(z.any()),
  stays: z.array(z.any()),
  hotels: z.array(z.any()),
  days: z.array(z.any()),
  boats: z.array(z.any()),
  costs: z.array(z.any()),
  contingencyPercent: z.number(),
  budgetTarget: z.number().optional(),
  taxSettings: z.any().optional(),
});

export function encodeTripState(state: TripState) {
  return compressToEncodedURIComponent(JSON.stringify(state));
}

export function decodeTripState(encoded: string): { state?: TripState; error?: string } {
  try {
    const decompressed = decompressFromEncodedURIComponent(encoded);
    if (!decompressed) return { error: "This itinerary link is empty or damaged." };
    const parsed = tripSchema.safeParse(JSON.parse(decompressed));
    if (!parsed.success) return { error: "This itinerary link uses invalid or unsupported data." };
    return { state: parsed.data as TripState };
  } catch {
    return { error: "We could not read this itinerary link. Your local draft is unchanged." };
  }
}

export function shareUrl(state: TripState, baseUrl: string) {
  const url = new URL(baseUrl);
  url.searchParams.set("t", encodeTripState(state));
  return url.toString();
}
