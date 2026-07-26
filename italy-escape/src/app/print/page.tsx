"use client";

import { useEffect } from "react";
import { useTrip } from "@/components/site/TripProvider";
import { calculateCosts, hotelTotal, money } from "@/lib/costCalculator";
import { formattedDayDate } from "@/lib/schedule";
import { Button } from "@/components/ui/Button";

export default function PrintPage() {
  const { state } = useTrip();
  const total = calculateCosts(state);
  useEffect(() => { document.title = `${state.title} — Print`; }, [state.title]);
  return (
    <main className="page-shell max-w-5xl">
      <div className="no-print mb-8 flex justify-end"><Button onClick={() => window.print()}>Open print dialog / Save PDF</Button></div>
      <header className="mb-12 border-b border-[var(--ink)] pb-8"><p className="eyebrow">Private itinerary</p><h1 className="mt-4 font-serif text-6xl leading-none">{state.title}</h1><p className="mt-6">{formattedDayDate(state.startDate, 0)} — {formattedDayDate(state.startDate, state.days.length - 1, "MMMM d, yyyy")}</p></header>
      <section><h2 className="mb-5 font-serif text-4xl">Day by day</h2>{state.days.map((day) => <article key={day.id} className="grid grid-cols-[8rem_1fr] border-t border-[var(--line)] py-4"><p className="text-xs uppercase">{formattedDayDate(state.startDate, day.offset, "EEE, MMM d")}</p><div><h3 className="font-serif text-2xl">{day.title}</h3><p className="text-sm text-[var(--muted)]">{day.summary}</p>{day.activities.map((activity) => <p key={activity.id} className="mt-1 text-xs">• {activity.title}{activity.booked ? " · Booked" : ""}</p>)}</div></article>)}</section>
      <section className="print-break pt-8"><h2 className="mb-5 font-serif text-4xl">Hotels & budget</h2>{state.stays.map((stay) => { const hotel = state.hotels.find((item) => item.id === stay.hotelId); return hotel && <div key={stay.id} className="flex justify-between border-t border-[var(--line)] py-4"><span>{stay.region} · {hotel.name} · {stay.nights} nights</span><strong>{money(hotelTotal(hotel, stay.nights))}</strong></div>; })}<div className="mt-8 flex justify-between border-t-2 border-[var(--ink)] py-4 font-serif text-3xl"><span>Recommended trip budget</span><strong>{money(total.recommended)}</strong></div></section>
    </main>
  );
}
