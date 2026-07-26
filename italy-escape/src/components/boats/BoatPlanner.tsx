"use client";

import Image from "next/image";
import { Anchor, CloudSun, ExternalLink, Fuel, Leaf } from "lucide-react";
import { EditableNumber, EditableText, Field } from "@/components/edit/Editable";
import { useTrip } from "@/components/site/TripProvider";
import { formattedDayDate } from "@/lib/schedule";
import { boatsTotal, money } from "@/lib/costCalculator";
import type { BookingStatus, WeatherStatus } from "@/lib/types";

export function BoatPlanner() {
  const { state, dispatch } = useTrip();
  const total = boatsTotal(state);
  return (
    <>
      <div className="mb-14 grid gap-8 md:grid-cols-2 md:items-end">
        <div><p className="eyebrow mb-4">Days at sea</p><h1 className="section-title">Four passages,<br />weather permitting.</h1></div>
        <div className="md:justify-self-end"><p className="text-sm text-[var(--muted)]">Charters + estimated gratuity</p><p className="font-serif text-6xl">{money(total)}</p></div>
      </div>
      <div className="relative mb-14 h-[320px] overflow-hidden md:h-[480px]"><Image src="/images/capri.webp" alt="A boat passing the Faraglioni rocks of Capri" fill sizes="100vw" className="object-cover" /><div className="absolute bottom-6 left-6 flex items-center gap-2 text-white"><Anchor /><span className="text-xs uppercase tracking-[.2em]">Private days on the Mediterranean</span></div></div>
      <section className="mb-14 grid gap-6 border-y border-[var(--line)] py-7 md:grid-cols-[1fr_1.4fr]"><div><p className="eyebrow">Budget check</p><h2 className="mt-2 font-serif text-3xl">The original $14,000 was too high.</h2></div><p className="text-sm leading-7 text-[var(--muted)]">Published 2026 private-charter checks put quality RIBs in Sardinia around €700–€2,500 and full-day Amalfi gozzos around €1,400–€1,900. The revised plan uses private mid-size boats with fuel buffers—not superyachts. Shared/smaller alternatives remain editable.</p></section>
      <div className="grid gap-x-8 gap-y-12 lg:grid-cols-2">
        {state.boats.map((boat, index) => {
          const day = state.days.find((candidate) => candidate.id === boat.dayId);
          const tier = state.stays.find((stay) => stay.region === boat.region)?.tier ?? "luxury";
          return (
            <article key={boat.id} className="border-t border-[var(--line)] pt-6">
              <div className="mb-6 flex items-start gap-4"><span className="font-serif text-4xl text-[var(--muted)]">0{index + 1}</span><div className="flex-1"><EditableText value={boat.name} onChange={(name) => dispatch({ type: "update-boat", id: boat.id, patch: { name } })} label="Excursion name" className="font-serif text-3xl" /><p className="px-2 text-xs uppercase tracking-wider text-[var(--muted)]">{boat.region}</p></div></div>
              <div className="mb-5 grid gap-4 bg-[var(--surface)] p-5 sm:grid-cols-3"><div><p className="eyebrow">When</p><p className="mt-1 text-sm font-medium">{day && formattedDayDate(state.startDate, day.offset, "EEE, MMM d")} · {boat.departureTime}–{boat.returnTime}</p></div><div><p className="eyebrow">Vessel</p><p className="mt-1 text-sm font-medium">{tier === "value" ? boat.valueVessel : boat.vesselType}</p></div><div><p className="eyebrow">Estimate</p><p className="mt-1 font-serif text-2xl">{money((tier === "value" ? boat.valueBudget : boat.budget) + boat.gratuity)}</p></div></div>
              <p className="mb-3 text-sm leading-6"><b>Why this day:</b> {boat.region === "Sardinia" ? "These islands and swimming coves are inaccessible by road. Grouping both sails at Sardinia’s tail makes a cheaper final hotel split possible." : "The coast’s vertical scale reads best from the sea. Both sails are grouped first so the final Anantara nights can be used for its pool and spa."}</p>
              <p className="mb-5 text-xs leading-5 text-[var(--muted)]">{boat.priceRationale} <a href={boat.priceSourceUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 underline">Price reference <ExternalLink size={11} /></a></p>
              <details><summary className="cursor-pointer text-xs uppercase tracking-wider text-[var(--muted)]">Edit charter details</summary><div className="mt-5">
              <div className="grid grid-cols-2 gap-5">
                <Field label="Date"><select value={boat.dayId} onChange={(e) => dispatch({ type: "update-boat", id: boat.id, patch: { dayId: e.target.value } })} className="rounded-md bg-transparent p-2 text-sm">{state.days.map((item) => <option key={item.id} value={item.id}>{formattedDayDate(state.startDate, item.offset, "MMM d")} · {item.title}</option>)}</select></Field>
                <Field label="Backup day"><select value={boat.backupDayId ?? ""} onChange={(e) => dispatch({ type: "update-boat", id: boat.id, patch: { backupDayId: e.target.value } })} className="rounded-md bg-transparent p-2 text-sm"><option value="">None</option>{state.days.map((item) => <option key={item.id} value={item.id}>{formattedDayDate(state.startDate, item.offset, "MMM d")}{item.weatherBuffer ? " · weather buffer" : ""}</option>)}</select></Field>
                <Field label="Departure"><input type="time" value={boat.departureTime} onChange={(e) => dispatch({ type: "update-boat", id: boat.id, patch: { departureTime: e.target.value } })} className="rounded-md bg-transparent p-2" /></Field>
                <Field label="Return"><input type="time" value={boat.returnTime} onChange={(e) => dispatch({ type: "update-boat", id: boat.id, patch: { returnTime: e.target.value } })} className="rounded-md bg-transparent p-2" /></Field>
                <Field label={`Vessel · ${tier}`}><EditableText value={tier === "value" ? boat.valueVessel : boat.vesselType} onChange={(value) => dispatch({ type: "update-boat", id: boat.id, patch: tier === "value" ? { valueVessel: value } : { vesselType: value } })} label="Vessel type" /></Field>
                <Field label="Captain"><EditableText value={boat.captain} onChange={(captain) => dispatch({ type: "update-boat", id: boat.id, patch: { captain } })} label="Captain" /></Field>
                <Field label={`Charter budget · ${tier}`}><EditableNumber value={tier === "value" ? boat.valueBudget : boat.budget} onChange={(value) => dispatch({ type: "update-boat", id: boat.id, patch: tier === "value" ? { valueBudget: value } : { budget: value } })} label="Charter budget" prefix="$" /></Field>
                <Field label="Estimated gratuity"><EditableNumber value={boat.gratuity} onChange={(gratuity) => dispatch({ type: "update-boat", id: boat.id, patch: { gratuity } })} label="Gratuity" prefix="$" /></Field>
                <Field label="Weather"><select value={boat.weatherStatus} onChange={(e) => dispatch({ type: "update-boat", id: boat.id, patch: { weatherStatus: e.target.value as WeatherStatus } })} className="rounded-md bg-transparent p-2 text-sm"><option value="forecast-pending">Forecast pending</option><option value="go">Good to go</option><option value="watch">Weather watch</option><option value="cancelled">Cancelled</option></select></Field>
                <Field label="Booking"><select value={boat.status} onChange={(e) => dispatch({ type: "update-boat", id: boat.id, patch: { status: e.target.value as BookingStatus } })} className="rounded-md bg-transparent p-2 text-sm"><option value="idea">Idea</option><option value="requested">Requested</option><option value="booked">Booked</option></select></Field>
              </div>
              <div className="mt-5"><Field label="Lunch arrangement"><EditableText value={boat.lunchArrangement} onChange={(lunchArrangement) => dispatch({ type: "update-boat", id: boat.id, patch: { lunchArrangement } })} label="Lunch arrangement" /></Field></div>
              <div className="mt-5 flex flex-wrap gap-5 text-xs">
                <label className="flex items-center gap-2"><Fuel size={15} /><input type="checkbox" checked={boat.fuelIncluded} onChange={(e) => dispatch({ type: "update-boat", id: boat.id, patch: { fuelIncluded: e.target.checked } })} /> Fuel included</label>
                <label className="flex items-center gap-2"><Leaf size={15} /><input type="checkbox" checked={boat.vegetarianRequired} onChange={(e) => dispatch({ type: "update-boat", id: boat.id, patch: { vegetarianRequired: e.target.checked } })} /> Vegetarian meal</label>
                <span className="flex items-center gap-2 text-[var(--sea)]"><CloudSun size={15} />{boat.weatherStatus.replace("-", " ")}</span>
              </div>
              </div></details>
              {day && <p className="mt-5 text-xs text-[var(--muted)]">Scheduled {formattedDayDate(state.startDate, day.offset)}</p>}
            </article>
          );
        })}
      </div>
    </>
  );
}
