"use client";

import Image from "next/image";
import { useState } from "react";
import { addDays, format, parseISO } from "date-fns";
import { Anchor, ExternalLink, Sparkles, Waves } from "lucide-react";
import { useTrip } from "@/components/site/TripProvider";
import { Button } from "@/components/ui/Button";
import { ReviewBadge, VerifyChip } from "@/components/ui/VerifyChip";
import { EditableNumber } from "@/components/edit/Editable";
import { hotelTotal, hotelsTotal, money } from "@/lib/costCalculator";
import { recommendedNightAssignments } from "@/lib/splitStay";
import type { HotelOption, Stay } from "@/lib/types";
import { cn } from "@/lib/utils";

const regionIntro: Record<string, string> = {
  Sardinia: "Three nights living well at the resort, then two harbour nights for the sailing days.",
  Tuscany: "One base for all four nights, so you unpack once and use the pool and spa properly.",
  "Amalfi Coast": "Arrive and sail from a harbour-side base, then move up to the cliffside pool for the last two nights.",
};

function HotelCard({ hotel, nightsUsed, onSelect, onRateChange }: {
  hotel: HotelOption; nightsUsed: number; onSelect: () => void; onRateChange: (value: number) => void;
}) {
  const inUse = nightsUsed > 0;
  const [active, setActive] = useState(0);
  const photos = hotel.photos?.length ? hotel.photos : [{ url: hotel.image, caption: `${hotel.region} landscape`, credit: "Destination image" }];
  const photo = photos[Math.min(active, photos.length - 1)];
  return (
    <article className={cn("overflow-hidden border transition", inUse ? "border-[var(--ink)]" : "border-[var(--line)]")}>
      <div className="relative h-64">
        <Image src={photo.url} alt={`${hotel.name} — ${photo.caption}`} fill sizes="(min-width:1280px) 45vw, 100vw" className="object-cover" />
        <span className="absolute left-4 top-4 flex items-center gap-1 rounded-full bg-[var(--paper)] px-3 py-1 text-[9px] uppercase tracking-wider">
          {hotel.role === "signature" ? <Sparkles size={11} /> : <Anchor size={11} />}
          {hotel.role === "boat-base" ? "Boat-day base" : hotel.role === "value-stay" ? "Under $500" : "Signature stay"}
        </span>
        {inUse && <span className="on-ink absolute right-4 top-4 rounded-full bg-[var(--ink)] px-3 py-1 text-[9px] uppercase tracking-wider">{nightsUsed} {nightsUsed === 1 ? "night" : "nights"}</span>}
        <div className="absolute inset-x-0 bottom-0 flex items-end justify-between gap-3 bg-gradient-to-t from-black/70 to-transparent p-3">
          <p className="text-xs text-white">{photo.caption} <span className="text-white/60">· {photo.credit}</span></p>
        </div>
      </div>
      {photos.length > 1 && (
        <div className="flex gap-2 overflow-x-auto border-b border-[var(--line)] p-2">
          {photos.map((item, index) => (
            <button key={item.url} onClick={() => setActive(index)} aria-label={`Show photo: ${item.caption}`} aria-current={index === active} className={cn("relative h-14 w-20 shrink-0 overflow-hidden border", index === active ? "border-[var(--ink)]" : "border-transparent opacity-70 hover:opacity-100")}>
              <Image src={item.url} alt="" fill sizes="80px" className="object-cover" />
            </button>
          ))}
        </div>
      )}
      <div className="p-5">
        <h3 className="font-serif text-2xl">{hotel.name}</h3>
        <div className="mt-2"><ReviewBadge rating={hotel.rating} scale={hotel.ratingScale} count={hotel.reviewCount} source={hotel.reviewSource} url={hotel.reviewUrl} /></div>
        <p className="mt-4 text-sm leading-6">{hotel.whyPick}</p>
        <p className="mt-3 text-xs text-[var(--muted)]">{hotel.viewSummary}</p>
        <div className="mt-3 flex flex-wrap gap-2 text-[9px] uppercase tracking-wider">
          {(hotel.pools ?? []).map((pool) => <span key={pool} className="flex items-center gap-1 rounded-full bg-[var(--surface)] px-2 py-1"><Waves size={11} />{pool}</span>)}
          {hotel.rooftop && <span className="rounded-full bg-[var(--surface)] px-2 py-1">Rooftop</span>}
          {hotel.waterfront && <span className="rounded-full bg-[var(--surface)] px-2 py-1">On the water</span>}
        </div>
        <div className="mt-5 border-t border-[var(--line)] pt-4">
          <p className="eyebrow">Room to ask for</p>
          <p className="mt-1 text-sm font-medium">{hotel.roomRecommendation}</p>
          <p className="mt-2 text-xs text-[var(--muted)]">{hotel.rateNote}</p>
        </div>
        <div className="mt-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <EditableNumber value={hotel.nightlyRate} onChange={onRateChange} label={`${hotel.name} nightly rate`} prefix="$" suffix="/ night" className="w-40 font-serif text-xl" />
            <div className="mt-2"><VerifyChip verified={hotel.verified} sourceName={hotel.reviewSource} sourceUrl={hotel.reviewUrl} /></div>
          </div>
          <Button size="sm" variant={inUse ? "primary" : "outline"} onClick={onSelect}>{inUse ? "In the plan" : "Use for this leg"}</Button>
        </div>
        {inUse && <p className="mt-3 text-xs text-[var(--muted)]">{money(hotelTotal(hotel, nightsUsed))} for {nightsUsed} {nightsUsed === 1 ? "night" : "nights"}</p>}
        <div className="mt-4 flex flex-wrap gap-2 border-t border-[var(--line)] pt-4">
          <a href={hotel.officialUrl} target="_blank" rel="noreferrer"><Button size="sm" variant="outline">Official site <ExternalLink size={12} /></Button></a>
          <a href={hotel.roomsUrl} target="_blank" rel="noreferrer"><Button size="sm" variant="outline">Rooms &amp; photos <ExternalLink size={12} /></Button></a>
          <a href={hotel.bookingUrl} target="_blank" rel="noreferrer"><Button size="sm" variant="outline">Check rates <ExternalLink size={12} /></Button></a>
          <a href={hotel.reviewUrl} target="_blank" rel="noreferrer"><Button size="sm" variant="outline">Reviews <ExternalLink size={12} /></Button></a>
        </div>
      </div>
    </article>
  );
}

function NightStrip({ stay, start }: { stay: Stay; start: number }) {
  const { state, dispatch } = useTrip();
  const options = state.hotels.filter((hotel) => hotel.region === stay.region);
  const assignments = stay.nightHotelIds?.length ? stay.nightHotelIds : Array(stay.nights).fill(stay.hotelId);
  const boatDayOffsets = new Set(state.boats
    .filter((boat) => boat.region === stay.region)
    .map((boat) => state.days.find((day) => day.id === boat.dayId)?.offset));
  return (
    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
      {assignments.slice(0, stay.nights).map((hotelId, index) => {
        const hotel = state.hotels.find((item) => item.id === hotelId) ?? options[0];
        const offset = start + index;
        const isBoatNight = boatDayOffsets.has(offset) || boatDayOffsets.has(offset + 1);
        return (
          <label key={index} className={cn("border p-3", isBoatNight ? "border-[var(--sea)] bg-[color:var(--surface)/.5]" : "border-[var(--line)]")}>
            <span className="flex items-center justify-between text-[10px] uppercase tracking-wider text-[var(--muted)]">
              {format(addDays(parseISO(state.startDate), offset), "EEE, MMM d")}
              {isBoatNight && <Anchor size={11} className="text-[var(--sea)]" />}
            </span>
            <select
              value={hotelId}
              onChange={(event) => dispatch({ type: "assign-stay-night", stayId: stay.id, nightIndex: index, hotelId: event.target.value })}
              aria-label={`Hotel for the night of ${format(addDays(parseISO(state.startDate), offset), "MMMM d")}`}
              className="mt-2 w-full bg-transparent text-xs font-medium"
            >
              {options.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
            <span className="mt-1 block text-[11px] text-[var(--muted)]">{money(hotel?.nightlyRate ?? 0)}</span>
          </label>
        );
      })}
    </div>
  );
}

export function HotelStoryPlanner() {
  const { state, dispatch } = useTrip();
  const total = hotelsTotal(state.hotels, state.stays);
  const stayDates = state.stays.map((stay, index) => ({
    stay,
    start: 1 + state.stays.slice(0, index).reduce((sum, previous) => sum + previous.nights, 0),
  }));
  const applyRecommended = (stay: Stay) =>
    recommendedNightAssignments(stay, state).forEach((hotelId, nightIndex) =>
      dispatch({ type: "assign-stay-night", stayId: stay.id, nightIndex, hotelId }));

  return (
    <>
      <header className="mb-14 grid gap-8 md:grid-cols-[1fr_auto] md:items-end">
        <div>
          <p className="eyebrow mb-4">Sleep beautifully, spend deliberately</p>
          <h1 className="section-title">Pay resort rates only<br />on resort days.</h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-[var(--muted)]">
            Every night is assigned individually. Signature hotels hold the days you are actually there; harbour bases under $400 cover the days you leave at 09:30 and return at sunset.
          </p>
        </div>
        <div>
          <p className="eyebrow">Hotels in the current plan</p>
          <p className="font-serif text-5xl">{money(total)}</p>
        </div>
      </header>

      {stayDates.map(({ stay, start }, regionIndex) => {
        const options = state.hotels.filter((hotel) => hotel.region === stay.region);
        const assignments = stay.nightHotelIds?.length ? stay.nightHotelIds : Array(stay.nights).fill(stay.hotelId);
        return (
          <section key={stay.id} className="mb-24">
            <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="eyebrow">Chapter {regionIndex + 1} · {stay.nights} nights</p>
                <h2 className="font-serif text-5xl">{stay.region}</h2>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <p className="text-sm">{money(hotelsTotal(state.hotels, [stay]))}</p>
                <Button size="sm" variant="outline" onClick={() => applyRecommended(stay)}>Use recommended split</Button>
              </div>
            </div>
            <p className="mb-6 max-w-3xl text-sm leading-6 text-[var(--muted)]">{regionIntro[stay.region]}</p>
            <NightStrip stay={stay} start={start} />
            <div className="mt-8 grid gap-6 xl:grid-cols-2">
              {options.map((hotel) => (
                <HotelCard
                  key={hotel.id}
                  hotel={hotel}
                  nightsUsed={assignments.filter((id) => id === hotel.id).length}
                  onSelect={() => dispatch({ type: "select-hotel", stayId: stay.id, hotelId: hotel.id })}
                  onRateChange={(nightlyRate) => dispatch({ type: "update-hotel", id: hotel.id, patch: { nightlyRate } })}
                />
              ))}
            </div>
          </section>
        );
      })}

      <footer className="border-t border-[var(--line)] pt-6 text-xs leading-6 text-[var(--muted)]">
        Photography here is original destination artwork, not hotel imagery. Ratings link to their source and rates are planning estimates: confirm room, view, taxes and cancellation terms on each hotel’s own site before booking.
      </footer>
    </>
  );
}
