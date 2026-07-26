"use client";

import { Plus, Trash2 } from "lucide-react";
import { EditableNumber, EditableText, Field } from "@/components/edit/Editable";
import { useTrip } from "@/components/site/TripProvider";
import { Button } from "@/components/ui/Button";
import { calculateCosts, hotelTotal, money } from "@/lib/costCalculator";
import type { RouteLeg } from "@/lib/types";

export function CostCalculator() {
  const { state, dispatch } = useTrip();
  const summary = calculateCosts(state);
  return (
    <>
      <div className="mb-14 grid gap-8 md:grid-cols-2 md:items-end">
        <div><p className="eyebrow mb-4">The investment</p><h1 className="section-title">Clarity for<br />every indulgence.</h1></div>
        <div className="grid grid-cols-2 gap-5 md:justify-self-end">
          <Field label="Travelers"><EditableNumber value={state.travelers} min={1} max={20} onChange={(value) => dispatch({ type: "set-travelers", value })} label="Number of travelers" /></Field>
          <Field label="Contingency"><EditableNumber value={state.contingencyPercent} max={100} onChange={(value) => dispatch({ type: "set-contingency", value })} label="Contingency percentage" suffix="%" /></Field>
        </div>
      </div>
      <section className="mb-12 border-y border-[var(--line)] py-6">
        <p className="eyebrow mb-4">Taxes & fees — included in every scenario</p>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Hotel city tax · person/night"><EditableNumber value={state.taxSettings.cityTaxPerPersonNight} onChange={(cityTaxPerPersonNight) => dispatch({ type: "update-tax-settings", patch: { cityTaxPerPersonNight } })} label="City tax per person per night" prefix="$" /></Field>
          <Field label="Boat charter VAT"><EditableNumber value={state.taxSettings.boatVatPercent} max={100} onChange={(boatVatPercent) => dispatch({ type: "update-tax-settings", patch: { boatVatPercent } })} label="Boat VAT" suffix="%" /></Field>
          <Field label="Restaurant service"><EditableNumber value={state.taxSettings.diningServicePercent} max={100} onChange={(diningServicePercent) => dispatch({ type: "update-tax-settings", patch: { diningServicePercent } })} label="Restaurant service charge" suffix="%" /></Field>
        </div>
      </section>
      <section className="mb-16 grid gap-px bg-[var(--line)] sm:grid-cols-3">
        <div className="bg-[var(--paper)] p-7"><p className="eyebrow">Baseline</p><p className="mt-4 font-serif text-5xl">{money(summary.baseline)}</p><p className="mt-2 text-xs text-[var(--muted)]">Current choices + contingency</p></div>
        <div className="on-ink bg-[var(--ink)] p-7"><p className="eyebrow on-ink opacity-65">Recommended</p><p className="mt-4 font-serif text-5xl">{money(summary.recommended)}</p><p className="mt-2 text-xs opacity-65">Space for considered upgrades</p></div>
        <div className="bg-[var(--paper)] p-7"><p className="eyebrow">Splurge</p><p className="mt-4 font-serif text-5xl">{money(summary.splurge)}</p><p className="mt-2 text-xs text-[var(--muted)]">Premium scenario multipliers</p></div>
      </section>
      <section className="mb-16">
        <div className="mb-5"><p className="eyebrow mb-2">Flights</p><h2 className="font-serif text-4xl">Economy, door to door</h2></div>
        {state.routeLegs.filter((leg) => leg.mode.includes("flight")).map((leg) => (
          <div key={leg.id} className="grid gap-3 border-t border-[var(--line)] py-4 sm:grid-cols-[1fr_12rem_10rem] sm:items-center">
            <div><p className="font-medium">{state.destinations.find((place) => place.id === leg.fromId)?.shortName} → {state.destinations.find((place) => place.id === leg.toId)?.shortName}</p><p className="text-xs text-[var(--muted)]">{leg.details}</p></div>
            <select value={leg.cabin ?? "economy"} onChange={(event) => dispatch({ type: "update-route", id: leg.id, patch: { cabin: event.target.value as RouteLeg["cabin"] } })} className="rounded-md bg-transparent p-2 text-sm"><option value="economy">Economy</option><option value="premium-economy">Premium economy</option><option value="business">Business</option></select>
            <EditableNumber value={leg.pricePerPerson ?? 0} onChange={(pricePerPerson) => dispatch({ type: "update-route", id: leg.id, patch: { pricePerPerson } })} label="Flight price per person" prefix="$" suffix="/ person" />
          </div>
        ))}
      </section>
      <section className="mb-16">
        <div className="mb-3 flex h-4 overflow-hidden rounded-full bg-[var(--surface)]" aria-label="Budget allocation">
          {summary.categories.filter((item) => item.calculatedAmount > 0).map((item) => <i key={item.id} title={`${item.name}: ${money(item.calculatedAmount)}`} style={{ background: item.color, width: `${item.calculatedAmount / summary.subtotal * 100}%` }} />)}
        </div>
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-[10px] uppercase tracking-wider text-[var(--muted)]">{summary.categories.map((item) => <span key={item.id} className="flex items-center gap-1.5"><i className="size-2 rounded-full" style={{ background: item.color }} />{item.name}</span>)}</div>
      </section>
      <section className="mb-16">
        <div className="mb-5 flex items-end justify-between"><div><p className="eyebrow mb-2">Editable assumptions</p><h2 className="font-serif text-4xl">Trip ledger</h2></div><Button variant="outline" size="sm" onClick={() => dispatch({ type: "add-cost" })}><Plus size={14} />Add category</Button></div>
        <div className="border-t border-[var(--line)]">
          {summary.categories.map((category) => (
            <div key={category.id} className="grid grid-cols-[1fr_8rem_3rem] items-center gap-4 border-b border-[var(--line)] py-4">
              <EditableText value={category.name} onChange={(name) => dispatch({ type: "update-cost", id: category.id, patch: { name } })} label="Cost category name" />
              {category.derived ? <div className="text-right"><strong>{money(category.calculatedAmount)}</strong><p className="text-[9px] uppercase text-[var(--muted)]">Live from {category.derived}</p></div> : <EditableNumber value={category.amount ?? 0} onChange={(amount) => dispatch({ type: "update-cost", id: category.id, patch: { amount } })} label={`${category.name} amount`} prefix="$" />}
              <Button variant="danger" size="icon" onClick={() => dispatch({ type: "delete-cost", id: category.id })} aria-label={`Delete ${category.name}`}><Trash2 size={14} /></Button>
            </div>
          ))}
        </div>
      </section>
      <section className="mb-16 grid gap-5 border-y border-[var(--line)] py-8 sm:grid-cols-3">
        <div><p className="eyebrow">Cost per hotel night</p><p className="mt-2 font-serif text-4xl">{money(summary.perNight)}</p></div>
        <div><p className="eyebrow">Cost per person</p><p className="mt-2 font-serif text-4xl">{money(summary.perPerson)}</p></div>
        <div><p className="eyebrow">Pre-contingency subtotal</p><p className="mt-2 font-serif text-4xl">{money(summary.subtotal)}</p></div>
      </section>
      <section>
        <p className="eyebrow mb-3">Hotel combination differences</p><h2 className="mb-6 font-serif text-4xl">The room for choice</h2>
        {state.stays.map((stay) => {
          const selected = state.hotels.find((hotel) => hotel.id === stay.hotelId);
          const selectedTotal = selected ? hotelTotal(selected, stay.nights) : 0;
          return <div key={stay.id} className="mb-5 border-t border-[var(--line)] pt-3"><h3 className="mb-2 text-sm font-semibold">{stay.region}</h3>{state.hotels.filter((hotel) => hotel.region === stay.region).map((hotel) => <div key={hotel.id} className="flex justify-between py-1 text-sm text-[var(--muted)]"><span>{hotel.name}</span><span>{money(hotelTotal(hotel, stay.nights) - selectedTotal)} vs. selected</span></div>)}</div>;
        })}
      </section>
    </>
  );
}
