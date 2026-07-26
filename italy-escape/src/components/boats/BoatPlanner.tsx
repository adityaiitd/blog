"use client";

import Image from "next/image";
import { Anchor, Check, Clock, ExternalLink, Star, Users } from "lucide-react";
import { EditableNumber, EditableText, Field } from "@/components/edit/Editable";
import { useTrip } from "@/components/site/TripProvider";
import { formattedDayDate } from "@/lib/schedule";
import { boatCharter, boatGratuity, boatsTotal, money, selectedOption } from "@/lib/costCalculator";
import type { BookingStatus, WeatherStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

export function BoatPlanner() {
  const { state, dispatch } = useTrip();
  const total = boatsTotal(state);
  return (
    <>
      <div className="mb-14 grid gap-8 md:grid-cols-2 md:items-end">
        <div>
          <p className="eyebrow mb-4">Days at sea · private boats only</p>
          <h1 className="section-title">Four passages,<br />chosen operator by operator.</h1>
        </div>
        <div className="md:justify-self-end">
          <p className="text-sm text-[var(--muted)]">Charters + gratuity, for the two of you</p>
          <p className="font-serif text-6xl">{money(total)}</p>
        </div>
      </div>

      <div className="relative mb-12 h-[300px] overflow-hidden md:h-[440px]">
        <Image src="/images/capri.webp" alt="A boat passing the Faraglioni rocks of Capri" fill sizes="100vw" className="object-cover" />
        <div className="absolute bottom-6 left-6 flex items-center gap-2 text-white"><Anchor /><span className="text-xs uppercase tracking-[.2em]">Private days on the Mediterranean</span></div>
      </div>

      <section className="mb-14 grid gap-6 border-y border-[var(--line)] py-7 md:grid-cols-[1fr_1.4fr]">
        <div><p className="eyebrow">Why this is far cheaper now</p><h2 className="mt-2 font-serif text-3xl">Private, but sized for two.</h2></div>
        <p className="text-sm leading-7 text-[var(--muted)]">
          A $4,000 day assumes a crewed yacht for a large group. For two people the right boat is a private skippered gommone or gozzo, and operators publish those rates openly: €400 for a half day in Palau, €379 for four private hours around Capri. Two of your four days do not need to be full days at all. Every option below is a private boat, priced per boat, with a link to the operator&rsquo;s own page.
        </p>
      </section>

      <div className="grid gap-x-8 gap-y-14 xl:grid-cols-2">
        {state.boats.map((boat, index) => {
          const day = state.days.find((candidate) => candidate.id === boat.dayId);
          const current = selectedOption(boat);
          return (
            <article key={boat.id} className="border-t border-[var(--line)] pt-6">
              <div className="mb-5 flex items-start gap-4">
                <span className="font-serif text-4xl text-[var(--muted)]">0{index + 1}</span>
                <div className="flex-1">
                  <EditableText value={boat.name} onChange={(name) => dispatch({ type: "update-boat", id: boat.id, patch: { name } })} label="Excursion name" className="font-serif text-3xl" />
                  <p className="px-2 text-xs uppercase tracking-wider text-[var(--muted)]">{boat.region} · {day && formattedDayDate(state.startDate, day.offset, "EEE, MMM d")}</p>
                </div>
              </div>

              <p className="mb-5 text-sm leading-6"><b>Why this shape of day:</b> {boat.priceRationale}</p>

              <p className="eyebrow mb-3">Choose your operator</p>
              <div className="grid gap-2">
                {boat.options.map((option) => {
                  const chosen = option.id === boat.selectedOptionId;
                  return (
                    <button
                      key={option.id}
                      onClick={() => dispatch({ type: "update-boat", id: boat.id, patch: { selectedOptionId: option.id } })}
                      aria-pressed={chosen}
                      className={cn("w-full border p-4 text-left transition", chosen ? "border-[var(--ink)] bg-[color:var(--surface)/.6]" : "border-[var(--line)] hover:border-[var(--muted)]")}
                    >
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <span className="flex items-center gap-2 text-sm font-medium">{chosen && <Check size={14} className="text-[var(--olive)]" />}{option.operator}</span>
                        <strong className="font-serif text-xl">{money(option.price)}</strong>
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[var(--muted)]">
                        <span className="flex items-center gap-1"><Clock size={11} />{option.label}</span>
                        <span className="flex items-center gap-1"><Users size={11} />up to {option.maxGuests}</span>
                        {option.rating > 0 && <span className="flex items-center gap-1"><Star size={11} className="fill-[var(--olive)] text-[var(--olive)]" />{option.rating} · {option.reviewCount || "reviewed"} {option.reviewCount ? "reviews" : ""} on {option.reviewSource}</span>}
                      </div>
                      <p className="mt-2 text-xs text-[var(--muted)]">{option.priceNote}</p>
                      {option.note && <p className="mt-1 text-xs text-[var(--olive)]">{option.note}</p>}
                    </button>
                  );
                })}
              </div>

              {current && (
                <div className="mt-5 border-t border-[var(--line)] pt-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <a href={current.url} target="_blank" rel="noreferrer" className="on-ink inline-flex items-center gap-1.5 rounded-full bg-[var(--ink)] px-4 py-2 text-xs">Open {current.operator.split(" · ")[0]} <ExternalLink size={11} /></a>
                    <span className="text-xs text-[var(--muted)]">{money(boatCharter(boat))} charter + {money(boatGratuity(boat))} gratuity</span>
                  </div>
                  <p className="mt-3 text-xs leading-5 text-[var(--muted)]"><b>Included:</b> {current.includes.join(" · ")}</p>
                  <p className="mt-1 text-xs leading-5 text-[var(--terracotta)]"><b>Not included:</b> {current.excludes.join(" · ")}</p>
                </div>
              )}

              <details className="mt-5">
                <summary className="cursor-pointer text-xs uppercase tracking-wider text-[var(--muted)]">Edit day, times and booking status</summary>
                <div className="mt-5 grid grid-cols-2 gap-5">
                  <Field label="Date"><select value={boat.dayId} onChange={(e) => dispatch({ type: "update-boat", id: boat.id, patch: { dayId: e.target.value } })} className="rounded-md bg-transparent p-2 text-sm">{state.days.map((item) => <option key={item.id} value={item.id}>{formattedDayDate(state.startDate, item.offset, "MMM d")} · {item.title}</option>)}</select></Field>
                  <Field label="Backup day"><select value={boat.backupDayId ?? ""} onChange={(e) => dispatch({ type: "update-boat", id: boat.id, patch: { backupDayId: e.target.value } })} className="rounded-md bg-transparent p-2 text-sm"><option value="">None</option>{state.days.map((item) => <option key={item.id} value={item.id}>{formattedDayDate(state.startDate, item.offset, "MMM d")}{item.weatherBuffer ? " · weather buffer" : ""}</option>)}</select></Field>
                  <Field label="Departure"><input type="time" value={boat.departureTime} onChange={(e) => dispatch({ type: "update-boat", id: boat.id, patch: { departureTime: e.target.value } })} className="rounded-md bg-transparent p-2" /></Field>
                  <Field label="Gratuity"><EditableNumber value={boat.gratuityPercent} max={30} onChange={(gratuityPercent) => dispatch({ type: "update-boat", id: boat.id, patch: { gratuityPercent } })} label="Gratuity percent" suffix="%" /></Field>
                  <Field label="Captain"><EditableText value={boat.captain} onChange={(captain) => dispatch({ type: "update-boat", id: boat.id, patch: { captain } })} label="Captain" /></Field>
                  <Field label="Lunch"><EditableText value={boat.lunchArrangement} onChange={(lunchArrangement) => dispatch({ type: "update-boat", id: boat.id, patch: { lunchArrangement } })} label="Lunch arrangement" /></Field>
                  <Field label="Weather"><select value={boat.weatherStatus} onChange={(e) => dispatch({ type: "update-boat", id: boat.id, patch: { weatherStatus: e.target.value as WeatherStatus } })} className="rounded-md bg-transparent p-2 text-sm"><option value="forecast-pending">Forecast pending</option><option value="go">Good to go</option><option value="watch">Weather watch</option><option value="cancelled">Cancelled</option></select></Field>
                  <Field label="Booking"><select value={boat.status} onChange={(e) => dispatch({ type: "update-boat", id: boat.id, patch: { status: e.target.value as BookingStatus } })} className="rounded-md bg-transparent p-2 text-sm"><option value="idea">Idea</option><option value="requested">Requested</option><option value="booked">Booked</option></select></Field>
                  <label className="col-span-2 flex items-center gap-2 text-xs"><input type="checkbox" checked={boat.vegetarianRequired} onChange={(e) => dispatch({ type: "update-boat", id: boat.id, patch: { vegetarianRequired: e.target.checked } })} /> Vegetarian meal required</label>
                </div>
              </details>
            </article>
          );
        })}
      </div>
    </>
  );
}
