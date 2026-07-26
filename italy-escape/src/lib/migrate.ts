import { freshInitialTripState } from "@/data";
import type { TripState } from "./types";

/** Upgrades v1 share links and local drafts without discarding personal edits. */
export function normalizeTripState(input: TripState): TripState {
  const defaults = freshInitialTripState();
  return {
    ...defaults,
    ...input,
    taxSettings: input.taxSettings ?? defaults.taxSettings,
    budgetTarget: input.budgetTarget ?? defaults.budgetTarget,
    stays: input.stays.map((stay) => ({ ...stay, tier: stay.tier ?? "luxury" })),
    hotels: [
      ...input.hotels.map((hotel) => {
        const fallback = defaults.hotels.find((candidate) => candidate.id === hotel.id);
        return {
          ...fallback,
          ...hotel,
          tier: hotel.tier ?? "luxury" as const,
          role: hotel.role ?? fallback?.role ?? "signature",
          rating: hotel.rating ?? fallback?.rating ?? 0,
          ratingScale: hotel.ratingScale ?? fallback?.ratingScale ?? 5,
          reviewCount: hotel.reviewCount ?? fallback?.reviewCount ?? 0,
          reviewSource: hotel.reviewSource ?? fallback?.reviewSource ?? "Tripadvisor",
          reviewUrl: hotel.reviewUrl ?? fallback?.reviewUrl ?? `https://www.tripadvisor.com/Search?q=${encodeURIComponent(hotel.name)}`,
          verified: hotel.verified ?? fallback?.verified ?? false,
        };
      }),
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
    // Charter pricing moved to operator options, so older drafts adopt the current catalogue.
    boats: defaults.boats.map((fallback) => {
      const saved = input.boats.find((candidate) => candidate.id === fallback.id);
      if (!saved) return fallback;
      return {
        ...fallback,
        dayId: saved.dayId ?? fallback.dayId,
        backupDayId: saved.backupDayId ?? fallback.backupDayId,
        captain: saved.captain ?? fallback.captain,
        departureTime: saved.departureTime ?? fallback.departureTime,
        lunchArrangement: saved.lunchArrangement ?? fallback.lunchArrangement,
        vegetarianRequired: saved.vegetarianRequired ?? fallback.vegetarianRequired,
        weatherStatus: saved.weatherStatus ?? fallback.weatherStatus,
        status: saved.status ?? fallback.status,
        selectedOptionId: fallback.options.some((option) => option.id === saved.selectedOptionId)
          ? saved.selectedOptionId
          : fallback.selectedOptionId,
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
