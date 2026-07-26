import type { CostCategory, HotelOption, Stay, TripState } from "./types";

export const money = (value: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);

export function hotelTotal(hotel: HotelOption, nights: number) {
  const paidNights = Math.max(0, nights - Math.max(0, hotel.complimentaryNights));
  const roomRate = hotel.nightlyRate * hotel.roomMultipliers[hotel.selectedRoom];
  const refundable = roomRate * (1 + hotel.refundablePremium / 100);
  return refundable * paidNights * (1 + hotel.taxRate / 100);
}

export function hotelsTotal(hotels: HotelOption[], stays: Stay[]) {
  return stays.reduce((sum, stay) => {
    const hotel = hotels.find((candidate) => candidate.id === stay.hotelId);
    return sum + (hotel ? hotelTotal(hotel, stay.nights) : 0);
  }, 0);
}

export function boatsTotal(state: TripState) {
  return state.boats.reduce((sum, boat) => {
    const tier = state.stays.find((stay) => stay.region === boat.region)?.tier ?? "luxury";
    return sum + (tier === "value" ? boat.valueBudget : boat.budget) + boat.gratuity;
  }, 0);
}

export function transportTotal(state: TripState) {
  return state.routeLegs.reduce((sum, leg) => sum + (Number.isFinite(leg.cost) ? leg.cost : 0), 0);
}

export function internationalFlightsTotal(state: TripState) {
  return state.routeLegs
    .filter((leg) => leg.mode === "international-flight")
    .reduce((sum, leg) => sum + (leg.pricePerPerson ?? 0) * state.travelers, 0);
}

export function taxesTotal(state: TripState) {
  const cityTax = state.stays.reduce((sum, stay) => sum + stay.nights, 0)
    * state.travelers * state.taxSettings.cityTaxPerPersonNight;
  const boatBase = state.boats.reduce((sum, boat) => {
    const tier = state.stays.find((stay) => stay.region === boat.region)?.tier ?? "luxury";
    return sum + (tier === "value" ? boat.valueBudget : boat.budget);
  }, 0);
  const boatVat = boatBase * state.taxSettings.boatVatPercent / 100;
  const dining = state.costs.find((category) => category.id === "restaurants")?.amount ?? 0;
  const diningService = dining * state.taxSettings.diningServicePercent / 100;
  return cityTax + boatVat + diningService;
}

export function categoryAmount(category: CostCategory, state: TripState) {
  if (category.derived === "hotels") return hotelsTotal(state.hotels, state.stays);
  if (category.derived === "boats") return boatsTotal(state);
  if (category.derived === "transport") {
    return state.routeLegs
      .filter((leg) => leg.mode === "private-car")
      .reduce((sum, leg) => sum + leg.cost, 0);
  }
  if (category.derived === "international-flights") return internationalFlightsTotal(state);
  if (category.derived === "taxes") return taxesTotal(state);
  return category.amount ?? 0;
}

export interface CostSummary {
  subtotal: number;
  baseline: number;
  recommended: number;
  splurge: number;
  perNight: number;
  perPerson: number;
  categories: Array<CostCategory & { calculatedAmount: number }>;
}

export function calculateCosts(state: TripState): CostSummary {
  const categories = state.costs.map((category) => ({
    ...category,
    calculatedAmount: categoryAmount(category, state),
  }));
  const subtotal = categories.reduce((sum, category) => sum + category.calculatedAmount, 0);
  const baseline = subtotal * (1 + Math.max(0, state.contingencyPercent) / 100);
  const splurgeSubtotal = categories.reduce(
    (sum, category) => sum + category.calculatedAmount * category.scenarioMultiplier,
    0,
  );
  const recommended = subtotal * 1.08 * (1 + Math.max(0, state.contingencyPercent) / 100);
  const splurge = splurgeSubtotal * (1 + Math.max(0, state.contingencyPercent) / 100);
  const nights = Math.max(1, state.stays.reduce((sum, stay) => sum + stay.nights, 0));
  const travelers = Math.max(1, state.travelers);
  return { subtotal, baseline, recommended, splurge, perNight: baseline / nights, perPerson: baseline / travelers, categories };
}
