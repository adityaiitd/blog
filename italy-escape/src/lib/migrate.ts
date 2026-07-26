import { freshInitialTripState } from "@/data";
import type { HotelOption, TripState } from "./types";

/**
 * Older drafts and share links predate fields the UI now reads, so every record is
 * completed against the current defaults. Anything missing is filled rather than trusted,
 * because a single undefined array is enough to blank the page.
 */
function completeHotel(saved: Partial<HotelOption> & { id: string; name?: string }, fallback?: HotelOption): HotelOption {
  const name = saved.name ?? fallback?.name ?? "Hotel";
  const region = saved.region ?? fallback?.region ?? "Italy";
  const search = `https://www.tripadvisor.com/Search?q=${encodeURIComponent(name)}`;
  const image = saved.image ?? fallback?.image
    ?? (region === "Sardinia" ? "/images/costa-smeralda.webp" : region === "Tuscany" ? "/images/tuscany.webp" : "/images/amalfi.webp");
  return {
    id: saved.id,
    region,
    name,
    nightlyRate: saved.nightlyRate ?? fallback?.nightlyRate ?? 0,
    roomMultipliers: saved.roomMultipliers ?? fallback?.roomMultipliers ?? { entry: 1, "sea-view": 1.25, suite: 1.75 },
    selectedRoom: saved.selectedRoom ?? fallback?.selectedRoom ?? "entry",
    refundablePremium: saved.refundablePremium ?? fallback?.refundablePremium ?? 0,
    taxRate: saved.taxRate ?? fallback?.taxRate ?? 0,
    complimentaryNights: saved.complimentaryNights ?? fallback?.complimentaryNights ?? 0,
    recommended: saved.recommended ?? fallback?.recommended,
    tier: saved.tier ?? fallback?.tier ?? "luxury",
    officialUrl: saved.officialUrl ?? fallback?.officialUrl ?? search,
    roomsUrl: saved.roomsUrl ?? fallback?.roomsUrl ?? search,
    bookingUrl: saved.bookingUrl ?? fallback?.bookingUrl ?? `https://www.booking.com/searchresults.html?ss=${encodeURIComponent(name)}`,
    reviewUrl: saved.reviewUrl ?? fallback?.reviewUrl ?? search,
    image,
    pools: saved.pools ?? fallback?.pools ?? [],
    photos: saved.photos ?? fallback?.photos ?? [],
    viewSummary: saved.viewSummary ?? fallback?.viewSummary ?? "",
    rooftop: saved.rooftop ?? fallback?.rooftop ?? false,
    waterfront: saved.waterfront ?? fallback?.waterfront ?? false,
    whyPick: saved.whyPick ?? fallback?.whyPick ?? "",
    roomRecommendation: saved.roomRecommendation ?? fallback?.roomRecommendation ?? "",
    rateNote: saved.rateNote ?? fallback?.rateNote ?? "Confirm the live rate directly.",
    bestFor: saved.bestFor ?? fallback?.bestFor ?? [],
    role: saved.role ?? fallback?.role ?? "signature",
    rating: saved.rating ?? fallback?.rating ?? 0,
    ratingScale: saved.ratingScale ?? fallback?.ratingScale ?? 5,
    reviewCount: saved.reviewCount ?? fallback?.reviewCount ?? 0,
    reviewSource: saved.reviewSource ?? fallback?.reviewSource ?? "Tripadvisor",
    verified: saved.verified ?? fallback?.verified ?? false,
  };
}

export function normalizeTripState(input: TripState): TripState {
  const defaults = freshInitialTripState();
  const savedHotels = Array.isArray(input.hotels) ? input.hotels : [];
  const hotels = [
    ...savedHotels.map((hotel) => completeHotel(hotel, defaults.hotels.find((candidate) => candidate.id === hotel.id))),
    ...defaults.hotels.filter((hotel) => !savedHotels.some((candidate) => candidate.id === hotel.id)),
  ];
  const hotelIds = new Set(hotels.map((hotel) => hotel.id));

  return {
    ...defaults,
    ...input,
    taxSettings: input.taxSettings ?? defaults.taxSettings,
    budgetTarget: input.budgetTarget ?? defaults.budgetTarget,
    hotels,
    stays: (Array.isArray(input.stays) ? input.stays : defaults.stays).map((stay) => {
      const fallback = defaults.stays.find((candidate) => candidate.id === stay.id) ?? defaults.stays[0];
      const hotelId = hotelIds.has(stay.hotelId) ? stay.hotelId : fallback.hotelId;
      const nights = Number.isFinite(stay.nights) ? stay.nights : fallback.nights;
      const assignments = (stay.nightHotelIds ?? []).slice(0, nights).map((id) => hotelIds.has(id) ? id : hotelId);
      while (assignments.length < nights) assignments.push(hotelId);
      return { ...stay, hotelId, nights, tier: stay.tier ?? "luxury", nightHotelIds: assignments };
    }),
    routeLegs: (Array.isArray(input.routeLegs) ? input.routeLegs : defaults.routeLegs).map((leg) => ({
      ...leg,
      cabin: leg.cabin ?? (leg.mode.includes("flight") ? "economy" : undefined),
      pricePerPerson: leg.pricePerPerson ?? (leg.mode === "international-flight" ? 575 : undefined),
    })),
    days: (Array.isArray(input.days) && input.days.length ? input.days : defaults.days).map((day) => ({
      ...day,
      activities: (day.activities ?? []).map((activity) => ({
        ...activity,
        venue: activity.venue ?? (activity.boatId ? "boat" : "public"),
        entryFee: activity.entryFee ?? 0,
        purpose: activity.purpose ?? (activity.boatId ? "sail" : activity.venue === "hotel" ? "relax" : activity.venue === "transit" ? "travel" : "see"),
        rationale: activity.rationale ?? "Chosen to add a strong sense of place without overloading the day.",
      })),
    })),
    // Charter pricing moved to operator options, so older drafts adopt the current catalogue.
    boats: defaults.boats.map((fallback) => {
      const saved = (Array.isArray(input.boats) ? input.boats : []).find((candidate) => candidate.id === fallback.id);
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
        gratuityPercent: saved.gratuityPercent ?? fallback.gratuityPercent,
        selectedOptionId: fallback.options.some((option) => option.id === saved.selectedOptionId)
          ? saved.selectedOptionId
          : fallback.selectedOptionId,
      };
    }),
    destinations: (Array.isArray(input.destinations) && input.destinations.length ? input.destinations : defaults.destinations)
      .some((place) => place.waypoint)
      ? input.destinations
      : [...(input.destinations ?? []), ...defaults.destinations.filter((place) => place.waypoint)],
    costs: [
      ...(Array.isArray(input.costs) ? input.costs : []),
      ...defaults.costs.filter((category) => !(input.costs ?? []).some((candidate) => candidate.id === category.id)),
    ],
  };
}
