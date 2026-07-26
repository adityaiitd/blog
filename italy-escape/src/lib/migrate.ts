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
    hotels: input.hotels.map((hotel) => ({ ...hotel, tier: hotel.tier ?? "luxury" })),
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
      })),
    })),
    boats: input.boats.map((boat) => {
      const fallback = defaults.boats.find((candidate) => candidate.id === boat.id);
      return {
        ...boat,
        waypointIds: boat.waypointIds ?? fallback?.waypointIds ?? [],
        valueBudget: boat.valueBudget ?? Math.round(boat.budget * .5),
        valueVessel: boat.valueVessel ?? "Shared charter",
      };
    }),
    destinations: input.destinations.some((place) => place.waypoint)
      ? input.destinations
      : [...input.destinations, ...defaults.destinations.filter((place) => place.waypoint)],
  };
}
