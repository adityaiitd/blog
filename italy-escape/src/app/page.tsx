"use client";

import Image from "next/image";
import { ArrowDown } from "lucide-react";
import { EditableDate, EditableText } from "@/components/edit/Editable";
import { RouteEditor } from "@/components/edit/RouteEditor";
import { BudgetTarget } from "@/components/costs/BudgetTarget";
import { RouteMap } from "@/components/map/RouteMap";
import { ShareBar } from "@/components/share/ShareBar";
import { useTrip } from "@/components/site/TripProvider";
import { formattedDayDate } from "@/lib/schedule";

export default function Home() {
  const { state, dispatch, hydrationError } = useTrip();
  return (
    <main>
      <section className="relative min-h-[82vh] overflow-hidden">
        <Image src="/images/costa-smeralda.webp" alt="Aerial view of the turquoise coves of Costa Smeralda" fill priority sizes="100vw" className="object-cover" />
        <div className="absolute inset-0 bg-black/25" />
        <div className="relative mx-auto flex min-h-[82vh] max-w-[1500px] flex-col justify-end px-5 py-12 text-white md:px-10 md:py-16">
          <p className="mb-5 text-xs uppercase tracking-[.25em]">A private journey · Italy</p>
          <EditableText value={state.title} onChange={(value) => dispatch({ type: "set-title", value })} label="Trip title" className="max-w-5xl border-white/20 font-serif text-[clamp(3.4rem,8vw,8rem)] leading-[.82] tracking-[-.05em] text-white hover:border-white/50 focus:bg-black/20" />
          <div className="mt-10 flex flex-wrap items-end gap-6 border-t border-white/40 pt-5">
            <div><p className="mb-1 text-[10px] uppercase tracking-[.2em] text-white/70">Departure</p><EditableDate value={state.startDate} onChange={(value) => dispatch({ type: "set-start-date", value })} label="Trip start date" className="w-auto text-white scheme-dark" /></div>
            <p className="text-sm">{formattedDayDate(state.startDate, 0, "MMMM d")} — {formattedDayDate(state.startDate, state.days.length - 1, "MMMM d, yyyy")}</p>
            <a href="#route" className="ml-auto flex items-center gap-2 text-xs uppercase tracking-wider">Explore route <ArrowDown size={15} /></a>
          </div>
        </div>
      </section>
      <section id="route" className="page-shell">
        {hydrationError && <p role="alert" className="mb-8 border-l-2 border-[var(--terracotta)] pl-4 text-sm">{hydrationError}</p>}
        <div className="mb-12 grid gap-8 md:grid-cols-2 md:items-end">
          <div><p className="eyebrow mb-4">The grand route</p><h1 className="section-title">Three chapters,<br />one Italian summer.</h1></div>
          <div className="max-w-xl md:justify-self-end"><p className="mb-8 text-lg leading-8 text-[var(--muted)]">Fourteen hotel nights from Sardinia’s crystalline coves through the vineyards of Tuscany to the vertical drama of Amalfi. Every stop, connection and estimate is yours to change.</p><ShareBar /></div>
        </div>
        <div className="mb-10"><BudgetTarget compact /></div>
        <div className="mb-10 grid gap-px bg-[var(--line)] md:grid-cols-3">{state.stays.map((stay, index) => { const hotelNames = [...new Set((stay.nightHotelIds ?? Array(stay.nights).fill(stay.hotelId)).map((id) => state.hotels.find((hotel) => hotel.id === id)?.name).filter(Boolean))]; const boatDays = state.boats.filter((boat) => boat.region === stay.region).length; return <article key={stay.id} className="bg-[var(--paper)] p-6"><p className="eyebrow">Chapter {index + 1} · {stay.nights} nights</p><h2 className="mt-2 font-serif text-3xl">{stay.region}</h2><p className="mt-3 text-sm leading-6 text-[var(--muted)]">{index === 0 ? "Sea, beach and island-hopping" : index === 1 ? "Wine country, art and restorative hotel time" : "Coastal villages, two sails and a final pool day"}</p><p className="mt-4 text-xs"><b>Sleep:</b> {hotelNames.join(" → ")}</p>{boatDays > 0 && <p className="mt-1 text-xs"><b>At sea:</b> {boatDays} days</p>}</article>; })}</div>
        <RouteMap />
        <details className="mt-12 border-y border-[var(--line)] py-5"><summary className="cursor-pointer text-sm font-medium">Advanced: edit airports, transfers and route legs</summary><RouteEditor /></details>
      </section>
    </main>
  );
}
