"use client";

import { ArrowDown, ArrowUp, Plane, TrainFront } from "lucide-react";
import { addDays, format, parseISO } from "date-fns";
import { useTrip } from "@/components/site/TripProvider";
import { Button } from "@/components/ui/Button";
import { hotelsTotal, money } from "@/lib/costCalculator";
import { EditableNumber } from "@/components/edit/Editable";

/** Reordering a leg here re-flows the dates, days, boats and every connection after it. */
export function LegOrder() {
  const { state, dispatch } = useTrip();
  const starts = state.stays.map((_, index) =>
    1 + state.stays.slice(0, index).reduce((sum, previous) => sum + previous.nights, 0));

  return (
    <section className="mb-12 border-y border-[var(--line)] py-7">
      <div className="mb-6 grid gap-3 md:grid-cols-[1fr_auto] md:items-end">
        <div>
          <p className="eyebrow mb-2">The order of the trip</p>
          <h2 className="font-serif text-4xl">Decide which leg you start with.</h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            Move a chapter and everything follows: dates shift, the day-by-day reshuffles, boat days
            travel with their region, and the flights, trains and transfers between them are rebuilt.
          </p>
        </div>
      </div>

      <ol className="grid gap-2">
        {state.stays.map((stay, index) => {
          const hotelNames = [...new Set((stay.nightHotelIds ?? [stay.hotelId])
            .map((id) => state.hotels.find((hotel) => hotel.id === id)?.name).filter(Boolean))];
          const next = state.stays[index + 1];
          const flying = next && (stay.region === "Sardinia" || next.region === "Sardinia");
          const start = starts[index];
          return (
            <li key={stay.id}>
              <div className="grid gap-3 border border-[var(--line)] p-4 sm:grid-cols-[2.5rem_1fr_auto_auto] sm:items-center">
                <span className="font-serif text-3xl text-[var(--muted)]">{index + 1}</span>
                <div>
                  <h3 className="font-serif text-2xl">{stay.region}</h3>
                  <p className="text-xs text-[var(--muted)]">
                    {format(addDays(parseISO(state.startDate), start), "MMM d")} – {format(addDays(parseISO(state.startDate), start + stay.nights), "MMM d")}
                    {" · "}{hotelNames.join(" → ")}
                  </p>
                </div>
                <label className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-[var(--muted)]">
                  Nights
                  <EditableNumber value={stay.nights} min={0} max={30}
                    onChange={(nights) => dispatch({ type: "update-stay", id: stay.id, patch: { nights } })}
                    label={`${stay.region} nights`} className="w-16" />
                  <span className="ml-2 text-sm normal-case tracking-normal text-[var(--ink)]">{money(hotelsTotal(state.hotels, [stay]))}</span>
                </label>
                <div className="flex gap-1">
                  <Button size="icon" variant="quiet" aria-label={`Move ${stay.region} earlier`} disabled={index === 0}
                    onClick={() => dispatch({ type: "move-stay", stayId: stay.id, direction: -1 })}><ArrowUp size={16} /></Button>
                  <Button size="icon" variant="quiet" aria-label={`Move ${stay.region} later`} disabled={index === state.stays.length - 1}
                    onClick={() => dispatch({ type: "move-stay", stayId: stay.id, direction: 1 })}><ArrowDown size={16} /></Button>
                </div>
              </div>
              {next && (
                <p className="flex items-center gap-2 py-2 pl-6 text-xs text-[var(--muted)]">
                  {flying ? <Plane size={13} /> : <TrainFront size={13} />}
                  {flying ? "Internal flight" : "High-speed train"} to {next.region}, with private cars at both ends
                </p>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
