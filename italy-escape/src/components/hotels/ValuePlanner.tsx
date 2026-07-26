"use client";

import Image from "next/image";
import { Check, Sparkles, WalletCards } from "lucide-react";
import { useTrip } from "@/components/site/TripProvider";
import { Button } from "@/components/ui/Button";
import { hotelTotal, hotelsTotal, money } from "@/lib/costCalculator";
import type { TripTier } from "@/lib/types";

const image: Record<string, string> = { Sardinia: "/images/cala-di-volpe.webp", Tuscany: "/images/val-dorcia.webp", "Amalfi Coast": "/images/positano.webp" };

export function ValuePlanner() {
  const { state, dispatch } = useTrip();
  const regions = state.stays.map((stay) => {
    const luxury = state.hotels.find((hotel) => hotel.region === stay.region && hotel.tier === "luxury" && hotel.recommended) ?? state.hotels.find((hotel) => hotel.region === stay.region && hotel.tier === "luxury");
    const value = state.hotels.find((hotel) => hotel.region === stay.region && hotel.tier === "value" && hotel.recommended) ?? state.hotels.find((hotel) => hotel.region === stay.region && hotel.tier === "value");
    const boats = state.boats.filter((boat) => boat.region === stay.region);
    const luxuryTotal = (luxury ? hotelTotal(luxury, stay.nights) : 0) + boats.reduce((sum, boat) => sum + boat.budget + boat.gratuity, 0);
    const valueTotal = (value ? hotelTotal(value, stay.nights) : 0) + boats.reduce((sum, boat) => sum + boat.valueBudget + boat.gratuity, 0);
    const currentBoats = boats.reduce((sum, boat) => sum + (stay.tier === "value" ? boat.valueBudget : boat.budget) + boat.gratuity, 0);
    const currentTotal = hotelsTotal(state.hotels, [stay]) + currentBoats;
    return { stay, luxury, value, luxuryTotal, valueTotal, currentTotal, savings: luxuryTotal - valueTotal };
  });
  const luxuryTrip = regions.reduce((sum, region) => sum + region.luxuryTotal, 0);
  const selectedTrip = regions.reduce((sum, region) => sum + region.currentTotal, 0);
  return (
    <>
      <div className="mb-12 grid gap-8 md:grid-cols-2 md:items-end">
        <div><p className="eyebrow mb-4">A considered alternative</p><h1 className="section-title">Keep the magic.<br />Choose where to save.</h1></div>
        <div className="md:justify-self-end"><p className="eyebrow">Savings from luxury plan</p><p className="font-serif text-6xl text-[var(--olive)]">{money(luxuryTrip - selectedTrip)}</p><p className="mt-2 text-sm text-[var(--muted)]">{luxuryTrip ? Math.round((luxuryTrip - selectedTrip) / luxuryTrip * 100) : 0}% less across selected legs</p></div>
      </div>
      <p className="mb-12 max-w-3xl text-lg leading-8 text-[var(--muted)]">Switch only the chapters you want. Value keeps the route and dates, selecting a thoughtful hotel and a smaller or shared boat—typically 20–30% below that chapter’s luxury budget.</p>
      <div className="grid gap-10">
        {regions.map(({ stay, luxury, value, luxuryTotal, valueTotal, savings }) => (
          <article key={stay.id} className="grid overflow-hidden border border-[var(--line)] lg:grid-cols-[.8fr_1.2fr]">
            <div className="relative min-h-[280px]"><Image src={image[stay.region]} alt={stay.region} fill sizes="(min-width:1024px) 40vw,100vw" className="object-cover" /><div className="absolute inset-0 bg-black/25" /><h2 className="absolute bottom-6 left-6 font-serif text-5xl text-white">{stay.region}</h2></div>
            <div className="p-6 md:p-9">
              <div className="mb-7 flex rounded-full border border-[var(--line)] p-1">
                {(["luxury", "value"] as TripTier[]).map((tier) => <button key={tier} onClick={() => dispatch({ type: "set-region-tier", stayId: stay.id, tier })} className={`flex flex-1 items-center justify-center gap-2 rounded-full px-4 py-3 text-xs uppercase tracking-wider ${stay.tier === tier ? "on-ink bg-[var(--ink)]" : ""}`}>{tier === "luxury" ? <Sparkles size={14} /> : <WalletCards size={14} />}{tier}</button>)}
              </div>
              <div className="grid gap-5 sm:grid-cols-2">
                <div className={stay.tier === "luxury" ? "opacity-100" : "opacity-55"}><p className="eyebrow mb-2">Luxury</p><h3 className="font-serif text-2xl">{luxury?.name}</h3><p className="mt-3 text-sm">{money(luxuryTotal)} · hotel + boats</p></div>
                <div className={stay.tier === "value" ? "opacity-100" : "opacity-55"}><p className="eyebrow mb-2">One tier below</p><h3 className="font-serif text-2xl">{value?.name}</h3><p className="mt-3 text-sm">{money(valueTotal)} · hotel + boats</p></div>
              </div>
              <div className="mt-7 flex flex-wrap items-center justify-between gap-4 border-t border-[var(--line)] pt-5"><p className="flex items-center gap-2 text-sm text-[var(--olive)]"><Check size={15} />Same dates, route and core experiences</p><strong>Save {money(savings)} · {Math.round(savings / luxuryTotal * 100)}%</strong></div>
              {stay.tier === "value" && <div className="mt-5"><p className="eyebrow mb-2">Other value hotels</p><div className="flex flex-wrap gap-2">{state.hotels.filter((hotel) => hotel.region === stay.region && hotel.tier === "value").map((hotel) => <Button key={hotel.id} size="sm" variant={hotel.id === stay.hotelId ? "primary" : "outline"} onClick={() => dispatch({ type: "select-hotel", stayId: stay.id, hotelId: hotel.id })}>{hotel.name}</Button>)}</div></div>}
            </div>
          </article>
        ))}
      </div>
    </>
  );
}
