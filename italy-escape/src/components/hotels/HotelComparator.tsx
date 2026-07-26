"use client";

import Image from "next/image";
import { Plus, Trash2 } from "lucide-react";
import { useTrip } from "@/components/site/TripProvider";
import { Button } from "@/components/ui/Button";
import { EditableNumber, EditableText, Field } from "@/components/edit/Editable";
import { HOTEL_BUDGET_RANGE, INITIAL_HOTEL_BENCHMARK } from "@/data";
import { hotelTotal, hotelsTotal, money } from "@/lib/costCalculator";
import type { RoomLevel } from "@/lib/types";
import { cn } from "@/lib/utils";

const regionImages: Record<string, string> = {
  Sardinia: "/images/cala-di-volpe.webp",
  Tuscany: "/images/tuscany.webp",
  "Amalfi Coast": "/images/amalfi.webp",
};

export function HotelComparator() {
  const { state, dispatch } = useTrip();
  const total = hotelsTotal(state.hotels, state.stays);
  return (
    <>
      <div className="mb-14 grid gap-8 md:grid-cols-2 md:items-end">
        <div><p className="eyebrow mb-4">Where we’ll stay</p><h1 className="section-title">Three remarkable<br />Italian addresses.</h1></div>
        <div className="md:justify-self-end"><p className="text-sm uppercase tracking-wider text-[var(--muted)]">Current hotel total</p><p className="font-serif text-6xl">{money(total)}</p><p className="mt-2 text-sm text-[var(--muted)]">{money(total - INITIAL_HOTEL_BENCHMARK)} vs. initial benchmark</p></div>
      </div>
      <div className="mb-16 border-y border-[var(--line)] py-6">
        <div className="mb-2 flex justify-between text-xs"><span>Recommended real-world hotel budget</span><span>{money(HOTEL_BUDGET_RANGE[0])}–{money(HOTEL_BUDGET_RANGE[1])}</span></div>
        <div className="relative h-2 bg-[var(--surface)]"><div className="absolute left-[40%] h-full w-[35%] bg-[var(--olive)]" /><i className="absolute top-[-5px] h-4 w-px bg-[var(--ink)]" style={{ left: `${Math.min(100, total / 40000 * 100)}%` }} /></div>
      </div>
      {state.stays.map((stay, sectionIndex) => {
        const options = state.hotels.filter((hotel) => hotel.region === stay.region);
        return (
          <section key={stay.id} className="mb-24">
            <div className="relative mb-8 h-[260px] overflow-hidden md:h-[390px]"><Image src={regionImages[stay.region]} alt={`${stay.region} landscape`} fill sizes="100vw" className="object-cover" /><div className="absolute inset-0 bg-black/20" /><div className="absolute bottom-6 left-6 text-white"><p className="eyebrow !text-white/80">Chapter {sectionIndex + 1}</p><h2 className="font-serif text-6xl">{stay.region}</h2></div></div>
            <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
              <Field label="Nights"><EditableNumber value={stay.nights} min={0} max={30} onChange={(nights) => dispatch({ type: "update-stay", id: stay.id, patch: { nights } })} label={`${stay.region} nights`} suffix="nights" className="w-32" /></Field>
              <Button variant="outline" size="sm" onClick={() => dispatch({ type: "add-hotel", region: stay.region })}><Plus size={14} />Add hotel option</Button>
            </div>
            <div className="border-t border-[var(--line)]">
              {options.map((hotel) => {
                const selected = hotel.id === stay.hotelId;
                return (
                  <div key={hotel.id} className={cn("grid gap-4 border-b border-[var(--line)] py-6 lg:grid-cols-[2fr_.7fr_1fr_.8fr_.8fr_.7fr_auto] lg:items-center", selected && "bg-[color:var(--surface)/.55] px-4")}>
                    <div className="flex items-start gap-3"><input type="radio" name={stay.id} checked={selected} onChange={() => dispatch({ type: "select-hotel", stayId: stay.id, hotelId: hotel.id })} aria-label={`Select ${hotel.name}`} className="mt-3" /><EditableText value={hotel.name} onChange={(name) => dispatch({ type: "update-hotel", id: hotel.id, patch: { name } })} label="Hotel name" className="font-serif text-2xl" /></div>
                    <Field label="Nightly rate"><EditableNumber value={hotel.nightlyRate} onChange={(nightlyRate) => dispatch({ type: "update-hotel", id: hotel.id, patch: { nightlyRate } })} label={`${hotel.name} nightly rate`} prefix="$" /></Field>
                    <Field label="Room level"><select value={hotel.selectedRoom} onChange={(e) => dispatch({ type: "update-hotel", id: hotel.id, patch: { selectedRoom: e.target.value as RoomLevel } })} className="rounded-md bg-transparent px-2 py-2 text-sm"><option value="entry">Entry</option><option value="sea-view">Recommended sea view</option><option value="suite">Suite</option></select></Field>
                    <Field label="Refundable"><EditableNumber value={hotel.refundablePremium} max={100} onChange={(refundablePremium) => dispatch({ type: "update-hotel", id: hotel.id, patch: { refundablePremium } })} label="Refundable premium" suffix="%" /></Field>
                    <Field label="Tax & fees"><EditableNumber value={hotel.taxRate} max={100} onChange={(taxRate) => dispatch({ type: "update-hotel", id: hotel.id, patch: { taxRate } })} label="Taxes and fees" suffix="%" /></Field>
                    <Field label="Comp nights"><EditableNumber value={hotel.complimentaryNights} max={stay.nights} onChange={(complimentaryNights) => dispatch({ type: "update-hotel", id: hotel.id, patch: { complimentaryNights } })} label="Complimentary nights" /></Field>
                    <div className="flex items-center gap-2"><strong className="min-w-24 text-right text-sm">{money(hotelTotal(hotel, stay.nights))}</strong><Button variant="danger" size="icon" disabled={selected} onClick={() => dispatch({ type: "delete-hotel", id: hotel.id })} aria-label={`Delete ${hotel.name}`}><Trash2 size={14} /></Button></div>
                  </div>
                );
              })}
            </div>
          </section>
        );
      })}
    </>
  );
}
