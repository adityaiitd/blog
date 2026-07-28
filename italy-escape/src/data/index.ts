import { boatTrips } from "./boatTrips";
import { costs } from "./costs";
import { hotels, stays } from "./hotels";
import { itinerary } from "./itinerary";
import { destinations } from "./places";
import { routeLegs } from "./transfers";
import type { TripState } from "@/lib/types";

export const INITIAL_HOTEL_BENCHMARK = 22569;
export const HOTEL_BUDGET_RANGE = [25000, 31000] as const;

export const initialTripState: TripState = {
  schemaVersion: 1,
  title: "Our Italy Escape — Sardinia, Tuscany and Amalfi",
  startDate: "2026-08-30",
  travelers: 2,
  destinations,
  routeLegs,
  stays,
  hotels,
  days: itinerary,
  boats: boatTrips,
  costs,
  contingencyPercent: 10,
};

export const freshInitialTripState = (): TripState =>
  structuredClone(initialTripState);
