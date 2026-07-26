import { addDays, format, parseISO } from "date-fns";
import type { ItineraryDay, Stay, TripState } from "./types";

export function dateForOffset(startDate: string, offset: number): Date {
  return addDays(parseISO(startDate), offset);
}

export function formattedDayDate(startDate: string, offset: number, pattern = "EEEE, MMMM d") {
  return format(dateForOffset(startDate, offset), pattern);
}

export function totalNights(stays: Stay[]) {
  return stays.reduce((sum, stay) => sum + Math.max(0, stay.nights), 0);
}

/** Reflows day offsets while preserving stable IDs and user content. */
export function reflowDays(days: ItineraryDay[]): ItineraryDay[] {
  return days.map((day, offset) => ({ ...day, offset }));
}

export function reorderDays(days: ItineraryDay[], activeId: string, overId: string) {
  const from = days.findIndex((day) => day.id === activeId);
  const to = days.findIndex((day) => day.id === overId);
  if (from < 0 || to < 0 || from === to) return days;
  const next = [...days];
  const [moved] = next.splice(from, 1);
  next.splice(to, 0, moved);
  return reflowDays(next);
}

export function tripEndDate(state: TripState) {
  return dateForOffset(state.startDate, Math.max(0, state.days.length - 1));
}
