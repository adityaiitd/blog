import type { ItineraryDay, RouteLeg, Stay, TripState } from "./types";

interface Segments {
  leading: ItineraryDay[];
  byStay: Map<string, ItineraryDay[]>;
  trailing: ItineraryDay[];
}

/**
 * Splits the itinerary into the outbound day, one block per stay, and the return day,
 * so a whole leg can be picked up and moved without losing the days inside it.
 */
export function segmentDays(state: TripState): Segments {
  const sorted = [...state.days].sort((a, b) => a.offset - b.offset);
  const leading = sorted.slice(0, 1);
  const byStay = new Map<string, ItineraryDay[]>();
  let cursor = 1;
  for (const stay of state.stays) {
    byStay.set(stay.id, sorted.slice(cursor, cursor + stay.nights));
    cursor += stay.nights;
  }
  return { leading, byStay, trailing: sorted.slice(cursor) };
}

/** Connections are derived from the order of the legs, not stored, so they cannot drift. */
export function rebuildRouteLegs(stays: Stay[], previous: RouteLeg[]): RouteLeg[] {
  if (stays.length === 0) return previous;
  const priced = (mode: RouteLeg["mode"]) => previous.find((leg) => leg.mode === mode);
  const carCost = priced("private-car")?.cost ?? 250;
  const legs: RouteLeg[] = [];
  const first = stays[0];
  const last = stays[stays.length - 1];

  legs.push({
    id: "leg-out", fromId: "jfk", toId: first.flightHubId, mode: "international-flight",
    departure: "20:00", arrival: "12:00", carrier: "", details: "Overnight economy flight",
    cost: 0, status: "idea", cabin: "economy", pricePerPerson: priced("international-flight")?.pricePerPerson ?? 575,
  });
  legs.push({
    id: `leg-${first.id}-in`, fromId: first.flightHubId, toId: first.destinationId, mode: "private-car",
    details: first.transferNote, cost: carCost, status: "idea",
  });

  stays.forEach((stay, index) => {
    const next = stays[index + 1];
    if (!next) return;
    // Sardinia is an island, so any hop touching it flies; two mainland legs take the train.
    const flying = !stay.railHubId || !next.railHubId;
    const from = flying ? stay.flightHubId : stay.railHubId!;
    const to = flying ? next.flightHubId : next.railHubId!;
    legs.push({
      id: `leg-${stay.id}-out`, fromId: stay.destinationId, toId: from, mode: "private-car",
      details: `Private car for the ${flying ? "flight" : "train"} to ${next.region}`, cost: carCost, status: "idea",
    });
    legs.push(flying
      ? {
        id: `leg-${stay.id}-${next.id}`, fromId: from, toId: to, mode: "internal-flight",
        details: `${stay.region} to ${next.region}`, cost: priced("internal-flight")?.cost ?? 700,
        status: "idea", cabin: "economy", pricePerPerson: priced("internal-flight")?.pricePerPerson ?? 350,
      }
      : {
        id: `leg-${stay.id}-${next.id}`, fromId: from, toId: to, mode: "train",
        details: "Frecciarossa high-speed train", cost: priced("train")?.cost ?? 300, status: "idea",
      });
    legs.push({
      id: `leg-${next.id}-in`, fromId: to, toId: next.destinationId, mode: "private-car",
      details: next.transferNote, cost: carCost, status: "idea",
    });
  });

  legs.push({
    id: `leg-${last.id}-final`, fromId: last.destinationId, toId: last.flightHubId, mode: "private-car",
    details: "Private transfer for the flight home", cost: carCost, status: "idea",
  });
  legs.push({
    id: "leg-home", fromId: last.flightHubId, toId: "ewr", mode: "international-flight",
    details: "Nonstop economy flight home", cost: 0, status: "idea", cabin: "economy",
    pricePerPerson: previous.filter((leg) => leg.mode === "international-flight").at(-1)?.pricePerPerson ?? 575,
  });
  return legs;
}

/** Moves one leg earlier or later and re-flows everything that depends on the order. */
export function moveStay(state: TripState, stayId: string, direction: -1 | 1): TripState {
  const index = state.stays.findIndex((stay) => stay.id === stayId);
  const target = index + direction;
  if (index < 0 || target < 0 || target >= state.stays.length) return state;

  const { leading, byStay, trailing } = segmentDays(state);
  const stays = [...state.stays];
  [stays[index], stays[target]] = [stays[target], stays[index]];

  const days = [...leading, ...stays.flatMap((stay) => byStay.get(stay.id) ?? []), ...trailing]
    .map((day, offset) => ({ ...day, offset }));

  return { ...state, stays, days, routeLegs: rebuildRouteLegs(stays, state.routeLegs) };
}
