import type { TripState } from "./types";
import { hotelsTotal } from "./costCalculator";

export interface TripDiff {
  label: string;
  before: string;
  after: string;
}

export function diffTrips(before: TripState, after: TripState): TripDiff[] {
  const diffs: TripDiff[] = [];
  if (before.startDate !== after.startDate) diffs.push({ label: "Start date", before: before.startDate, after: after.startDate });
  const beforeNights = before.stays.reduce((sum, stay) => sum + stay.nights, 0);
  const afterNights = after.stays.reduce((sum, stay) => sum + stay.nights, 0);
  if (beforeNights !== afterNights) diffs.push({ label: "Hotel nights", before: String(beforeNights), after: String(afterNights) });
  const oldHotels = before.stays.map((stay) => before.hotels.find((hotel) => hotel.id === stay.hotelId)?.name).join(", ");
  const newHotels = after.stays.map((stay) => after.hotels.find((hotel) => hotel.id === stay.hotelId)?.name).join(", ");
  if (oldHotels !== newHotels) diffs.push({ label: "Hotel selections", before: oldHotels, after: newHotels });
  const oldHotelTotal = Math.round(hotelsTotal(before.hotels, before.stays));
  const newHotelTotal = Math.round(hotelsTotal(after.hotels, after.stays));
  if (oldHotelTotal !== newHotelTotal) diffs.push({ label: "Hotel total", before: `$${oldHotelTotal.toLocaleString()}`, after: `$${newHotelTotal.toLocaleString()}` });
  const oldActivities = before.days.reduce((sum, day) => sum + day.activities.length, 0);
  const newActivities = after.days.reduce((sum, day) => sum + day.activities.length, 0);
  if (oldActivities !== newActivities) diffs.push({ label: "Activities", before: String(oldActivities), after: String(newActivities) });
  const oldTiers = before.stays.map((stay) => `${stay.region}: ${stay.tier ?? "luxury"}`).join(", ");
  const newTiers = after.stays.map((stay) => `${stay.region}: ${stay.tier ?? "luxury"}`).join(", ");
  if (oldTiers !== newTiers) diffs.push({ label: "Plan tier", before: oldTiers, after: newTiers });
  const oldBoats = before.boats.map((boat) => `${boat.dayId}:${boat.budget}`).join("|");
  const newBoats = after.boats.map((boat) => `${boat.dayId}:${boat.budget}`).join("|");
  if (oldBoats !== newBoats) diffs.push({ label: "Boat plans", before: "Previous schedule", after: "Dates or budgets updated" });
  if (before.travelers !== after.travelers) diffs.push({ label: "Travelers", before: String(before.travelers), after: String(after.travelers) });
  if (before.contingencyPercent !== after.contingencyPercent) diffs.push({ label: "Contingency", before: `${before.contingencyPercent}%`, after: `${after.contingencyPercent}%` });
  return diffs;
}
