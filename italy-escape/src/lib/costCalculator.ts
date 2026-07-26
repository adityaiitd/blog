import { recommendedNightAssignments } from "./splitStay";
import type { CostCategory, HotelOption, Stay, TripAction, TripState } from "./types";

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
    const assignments = stay.nightHotelIds?.length ? stay.nightHotelIds.slice(0, stay.nights) : Array(stay.nights).fill(stay.hotelId);
    const nightsByHotel = assignments.reduce<Record<string, number>>((counts, hotelId) => ({ ...counts, [hotelId]: (counts[hotelId] ?? 0) + 1 }), {});
    return sum + Object.entries(nightsByHotel).reduce((hotelSum, [hotelId, nights]) => {
      const hotel = hotels.find((candidate) => candidate.id === hotelId);
      return hotelSum + (hotel ? hotelTotal(hotel, nights) : 0);
    }, 0);
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

export interface BudgetLever {
  id: string;
  label: string;
  detail: string;
  savings: number;
  actions: TripAction[];
}

export interface BudgetStatus {
  target: number;
  total: number;
  difference: number;
  withinTarget: boolean;
  percentOfTarget: number;
  levers: BudgetLever[];
}

/**
 * Ranks concrete, reversible ways to reach the target. Each lever is expressed as normal
 * trip actions so applying one is an ordinary edit that undo can reverse.
 */
export function fitToTarget(state: TripState): BudgetStatus {
  const total = calculateCosts(state).baseline;
  const target = state.budgetTarget;
  const levers: BudgetLever[] = [];
  const contingency = 1 + Math.max(0, state.contingencyPercent) / 100;

  for (const stay of state.stays) {
    const current = hotelsTotal(state.hotels, [stay]);
    const suggested = recommendedNightAssignments(stay, state);
    const proposed = hotelsTotal(state.hotels, [{ ...stay, nightHotelIds: suggested }]);
    const savings = (current - proposed) * contingency;
    if (savings > 1) {
      const baseName = state.hotels.find((hotel) => hotel.id === suggested.find((id) => id !== stay.hotelId))?.name;
      levers.push({
        id: `split-${stay.id}`,
        label: `Move ${stay.region} boat nights to ${baseName ?? "a harbour base"}`,
        detail: "Keeps the signature hotel for the days you actually use it.",
        savings,
        actions: suggested.map((hotelId, nightIndex) => ({ type: "assign-stay-night", stayId: stay.id, nightIndex, hotelId })),
      });
    }
  }

  for (const boat of state.boats) {
    const savings = (boat.budget - boat.valueBudget) * contingency * (1 + state.taxSettings.boatVatPercent / 100);
    if (boat.valueBudget < boat.budget) {
      levers.push({
        id: `boat-${boat.id}`,
        label: `Use the smaller boat for ${boat.name}`,
        detail: `${boat.valueVessel} instead of ${boat.vesselType}.`,
        savings,
        actions: [{ type: "update-boat", id: boat.id, patch: { budget: boat.valueBudget, vesselType: boat.valueVessel } }],
      });
    }
  }

  const dining = state.costs.find((category) => category.id === "restaurants");
  if (dining?.amount && dining.amount > 3500) {
    const reduced = Math.max(3500, Math.round(dining.amount * 0.85));
    levers.push({
      id: "dining",
      label: "Trim the dining allowance by 15 percent",
      detail: "Keeps the special dinners, assumes lighter lunches.",
      savings: (dining.amount - reduced) * contingency * (1 + state.taxSettings.diningServicePercent / 100),
      actions: [{ type: "update-cost", id: dining.id, patch: { amount: reduced } }],
    });
  }

  return {
    target,
    total,
    difference: total - target,
    withinTarget: total <= target,
    percentOfTarget: target > 0 ? total / target * 100 : 0,
    levers: levers.sort((a, b) => b.savings - a.savings),
  };
}
