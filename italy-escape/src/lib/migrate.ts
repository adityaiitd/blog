import { freshInitialTripState } from "@/data";
import type { TripState } from "./types";

/** Upgrades v1 share links and local drafts without discarding personal edits. */
export function normalizeTripState(input: TripState): TripState {
  const defaults = freshInitialTripState();
  return {
    ...defaults,
    ...input,
    taxSettings: input.taxSettings ?? defaults.taxSettings,
    stays: input.stays.map((stay) => ({ ...stay, tier: stay.tier ?? "luxury" })),
    hotels: [
      ...input.hotels.map((hotel) => ({ ...defaults.hotels.find((candidate) => candidate.id === hotel.id), ...hotel, tier: hotel.tier ?? "luxury" as const })),
      ...defaults.hotels.filter((hotel) => !input.hotels.some((candidate) => candidate.id === hotel.id)),
    ],
    routeLegs: input.routeLegs.map((leg) => ({
      ...leg,
      cabin: leg.cabin ?? (leg.mode.includes("flight") ? "economy" : undefined),
      pricePerPerson: leg.pricePerPerson ?? (leg.mode === "international-flight" ? 575 : undefined),
    })),
    days: input.days.map((day) => ({
      ...day,
      activities: day.activities.map((activity) => ({
        ...activity,
        venue: activity.venue ?? (activity.boatId ? "boat" : "public"),
        entryFee: activity.entryFee ?? 0,
        purpose: activity.purpose ?? (activity.boatId ? "sail" : activity.venue === "hotel" ? "relax" : activity.venue === "transit" ? "travel" : "see"),
        rationale: activity.rationale ?? "Chosen to add a strong sense of place without overloading the day.",
      })),
    })),
    boats: input.boats.map((boat) => {
      const fallback = defaults.boats.find((candidate) => candidate.id === boat.id);
      return {
        ...fallback,
        ...boat,
        waypointIds: boat.waypointIds ?? fallback?.waypointIds ?? [],
        valueBudget: boat.valueBudget ?? Math.round(boat.budget * .5),
        valueVessel: boat.valueVessel ?? "Shared charter",
      };
    }),
    destinations: input.destinations.some((place) => place.waypoint)
      ? input.destinations
      : [...input.destinations, ...defaults.destinations.filter((place) => place.waypoint)],
    costs: [
      ...input.costs,
      ...defaults.costs.filter((category) => !input.costs.some((candidate) => candidate.id === category.id)),
    ],
  };
}
