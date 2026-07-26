"use client";

import Image from "next/image";
import { addDays, format, parseISO } from "date-fns";
import { ExternalLink, Eye, Hotel, Sparkles, Waves } from "lucide-react";
import { useTrip } from "@/components/site/TripProvider";
import { Button } from "@/components/ui/Button";
import { EditableNumber } from "@/components/edit/Editable";
import { hotelTotal, hotelsTotal, money } from "@/lib/costCalculator";
import type { HotelOption } from "@/lib/types";

function HotelCard({ hotel, selected, nights, onSelect, onRateChange }: { hotel: HotelOption; selected: boolean; nights: number; onSelect: () => void; onRateChange: (value: number) => void }) {
  return (
    <article className={`overflow-hidden border ${selected ? "border-[var(--ink)]" : "border-[var(--line)]"}`}>
      <div className="relative h-52"><Image src={hotel.image} alt={`Editorial destination view for ${hotel.region}`} fill sizes="(min-width:1024px) 30vw,100vw" className="object-cover" /><div className="absolute inset-0 bg-black/15" /><span className="absolute left-4 top-4 rounded-full bg-[color:var(--paper)] px-3 py-1 text-[9px] uppercase tracking-wider">{hotel.tier}</span></div>
      <div className="p-5">
        <div className="flex items-start justify-between gap-3"><div><h3 className="font-serif text-2xl">{hotel.name}</h3><p className="mt-1 text-xs text-[var(--muted)]">{hotel.viewSummary}</p></div><input type="radio" checked={selected} onChange={onSelect} aria-label={`Select ${hotel.name}`} /></div>
        <p className="mt-4 text-sm leading-6">{hotel.whyPick}</p>
        <div className="mt-4 flex flex-wrap gap-2 text-[9px] uppercase tracking-wider">{hotel.pools.length > 0 && <span className="flex items-center gap-1 rounded-full bg-[var(--surface)] px-2 py-1"><Waves size={11} />{hotel.pools[0]}</span>}{hotel.rooftop && <span className="rounded-full bg-[var(--surface)] px-2 py-1">Rooftop</span>}{hotel.waterfront && <span className="rounded-full bg-[var(--surface)] px-2 py-1">Waterfront</span>}</div>
        <div className="mt-5 border-t border-[var(--line)] pt-4"><p className="eyebrow">Room to price</p><p className="mt-1 text-sm font-medium">{hotel.roomRecommendation}</p><p className="mt-2 text-xs text-[var(--muted)]">{hotel.rateNote}</p></div>
        <div className="mt-5 flex items-end justify-between gap-3"><div><EditableNumber value={hotel.nightlyRate} onChange={onRateChange} label={`${hotel.name} nightly rate`} prefix="$" suffix="/ night" className="w-40 font-serif text-xl" /><p className="mt-1 text-xs">{money(hotelTotal(hotel, nights))} for {nights} nights</p></div><div className="flex gap-2"><a href={hotel.roomsUrl} target="_blank" rel="noreferrer"><Button size="sm" variant="outline">Rooms <ExternalLink size={12} /></Button></a><a href={hotel.officialUrl} target="_blank" rel="noreferrer"><Button size="sm">Official site <ExternalLink size={12} /></Button></a></div></div>
      </div>
    </article>
  );
}

export function HotelStoryPlanner() {
  const { state, dispatch } = useTrip();
  const total = hotelsTotal(state.hotels, state.stays);
  let startOffset = 1;
  const stayDates = state.stays.map((stay) => { const start = startOffset; startOffset += stay.nights; return { stay, start }; });
  const applySmartSplit = (stayId: string) => {
    const stay = state.stays.find((item) => item.id === stayId);
    if (!stay) return;
    const ids = stay.region === "Sardinia"
      ? ["cala", "cala", "cala", "gabbiano", "gabbiano"]
      : stay.region === "Amalfi Coast"
        ? ["marina-riviera", "marina-riviera", "marina-riviera", "anantara", "anantara"]
        : Array(stay.nights).fill(stay.hotelId);
    ids.slice(0, stay.nights).forEach((hotelId, nightIndex) => dispatch({ type: "assign-stay-night", stayId, nightIndex, hotelId }));
  };
  return (
    <>
      <header className="mb-14 grid gap-8 md:grid-cols-[1fr_auto] md:items-end"><div><p className="eyebrow mb-4">Sleep beautifully, spend deliberately</p><h1 className="section-title">A hotel should earn<br />the hours you give it.</h1><p className="mt-6 max-w-2xl text-lg leading-8 text-[var(--muted)]">See the pool, the view, the room to request and exactly why each property belongs. Official links open real galleries and live rates.</p></div><div><p className="eyebrow">Current hotel plan</p><p className="font-serif text-5xl">{money(total)}</p></div></header>
      <section className="mb-16 border-y border-[var(--line)] py-7">
        <div className="grid gap-5 lg:grid-cols-[1fr_1fr_auto] lg:items-center"><div><p className="eyebrow">Smarter split-stay strategy</p><h2 className="mt-2 font-serif text-3xl">Pay for the resort when you are there.</h2></div><p className="text-sm leading-6 text-[var(--muted)]">One hotel move per coast: finish Sardinia near a practical boat base; begin Amalfi beside the harbour, then move to the infinity-pool hotel when the schedule slows.</p><div className="flex flex-wrap gap-2"><Button size="sm" onClick={() => applySmartSplit("stay-sardinia")}>Optimize Sardinia</Button><Button size="sm" onClick={() => applySmartSplit("stay-amalfi")}>Optimize Amalfi</Button></div></div>
      </section>
      {stayDates.map(({ stay, start }, regionIndex) => {
        const options = state.hotels.filter((hotel) => hotel.region === stay.region);
        const assignments = stay.nightHotelIds?.length ? stay.nightHotelIds : Array(stay.nights).fill(stay.hotelId);
        return <section key={stay.id} className="mb-24">
          <div className="mb-7 flex flex-wrap items-end justify-between gap-4"><div><p className="eyebrow">Chapter {regionIndex + 1}</p><h2 className="font-serif text-5xl">{stay.region}</h2></div><p className="max-w-lg text-sm text-[var(--muted)]">{stay.region === "Sardinia" ? "Use Cala di Volpe for resort and beach time; a lower-cost waterfront base makes more sense for the final two full boat days." : stay.region === "Tuscany" ? "Keep one base: unpack once. COMO’s pool and spa are used on two slower half-days, so the spend is defensible." : "Start walkable to Amalfi harbour for two boat days, then move once to Anantara for pool, spa and Ravello."}</p></div>
          <div className="mb-8 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">{assignments.map((hotelId, index) => { const hotel = state.hotels.find((item) => item.id === hotelId) ?? options[0]; return <label key={index} className="border border-[var(--line)] p-3"><span className="eyebrow">{format(addDays(parseISO(state.startDate), start + index), "EEE, MMM d")}</span><select value={hotelId} onChange={(event) => dispatch({ type: "assign-stay-night", stayId: stay.id, nightIndex: index, hotelId: event.target.value })} className="mt-2 w-full bg-transparent text-xs font-medium"><option value={hotel.id}>{hotel.name}</option>{options.filter((item) => item.id !== hotel.id).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>; })}</div>
          <div className="mb-5 flex items-center gap-2 text-xs text-[var(--muted)]"><Eye size={14} />Editorial destination photography is shown here; use each official-site button for current property and room galleries.</div>
          <div className="grid gap-6 xl:grid-cols-2">{options.map((hotel) => <HotelCard key={hotel.id} hotel={hotel} selected={assignments.includes(hotel.id)} nights={assignments.filter((id) => id === hotel.id).length || stay.nights} onSelect={() => dispatch({ type: "select-hotel", stayId: stay.id, hotelId: hotel.id })} onRateChange={(nightlyRate) => dispatch({ type: "update-hotel", id: hotel.id, patch: { nightlyRate } })} />)}</div>
        </section>;
      })}
      <footer className="flex items-center gap-2 border-t border-[var(--line)] pt-6 text-xs text-[var(--muted)]"><Sparkles size={14} /><Hotel size={14} />Rates are planning estimates, not live quotes. Verify room, view, taxes and cancellation terms on the linked official site.</footer>
    </>
  );
}
