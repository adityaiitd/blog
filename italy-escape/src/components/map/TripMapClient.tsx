"use client";

import { Fragment, useMemo, useState } from "react";
import L from "leaflet";
import { MapContainer, Marker, Polyline, TileLayer, Tooltip } from "react-leaflet";
import { Anchor, BedDouble, Route, X } from "lucide-react";
import { useTheme } from "next-themes";
import { addDays, format, parseISO } from "date-fns";
import { useTrip } from "@/components/site/TripProvider";
import { Button } from "@/components/ui/Button";
import { EditableNumber, EditableText, Field } from "@/components/edit/Editable";
import { hotelTotal, money } from "@/lib/costCalculator";
import type { TransportMode } from "@/lib/types";

const routeStyle: Record<TransportMode, L.PathOptions> = {
  "international-flight": { color: "#557080", weight: 2, dashArray: "13 9" },
  "internal-flight": { color: "#a07857", weight: 2, dashArray: "6 6" },
  "private-car": { color: "#9b624c", weight: 3 },
  train: { color: "#6f7455", weight: 4, dashArray: "2 7" },
  boat: { color: "#39777b", weight: 3, dashArray: "9 4 2 4" },
};

type Selection = { kind: "hotel"; id: string } | { kind: "boat"; id: string };

export default function TripMapClient() {
  const { state, dispatch } = useTrip();
  const { resolvedTheme } = useTheme();
  const [layers, setLayers] = useState({ hotels: true, boats: true, transport: true });
  const [selected, setSelected] = useState<Selection>();
  const places = useMemo(() => new Map(state.destinations.map((place) => [place.id, place])), [state.destinations]);
  const tile = resolvedTheme === "dark" ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";
  const hotelSelection = selected?.kind === "hotel" ? state.hotels.find((hotel) => hotel.id === selected.id) : undefined;
  const boatSelection = selected?.kind === "boat" ? state.boats.find((boat) => boat.id === selected.id) : undefined;
  const staysWithDates = state.stays.map((stay, index) => {
    const start = 1 + state.stays.slice(0, index).reduce((sum, previous) => sum + previous.nights, 0);
    return { stay, start, end: start + stay.nights };
  });
  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_20rem]">
    <div className="relative h-[76vh] min-h-[600px] overflow-hidden">
      <MapContainer center={[41.4, 11.4]} zoom={6} className="h-full w-full">
        <TileLayer url={tile} attribution="&copy; OpenStreetMap &copy; CARTO" />
        {layers.transport && state.routeLegs.map((leg) => {
          const from = places.get(leg.fromId); const to = places.get(leg.toId);
          return from && to ? <Polyline key={leg.id} positions={[[from.lat, from.lng], [to.lat, to.lng]]} pathOptions={routeStyle[leg.mode]}><Tooltip>{leg.details}</Tooltip></Polyline> : null;
        })}
        {layers.hotels && staysWithDates.map(({ stay, start, end }) => {
          const place = places.get(stay.destinationId);
          const assignedIds = [...new Set(stay.nightHotelIds?.length ? stay.nightHotelIds : [stay.hotelId])];
          const assignedHotels = assignedIds.map((id) => state.hotels.find((item) => item.id === id)).filter(Boolean);
          const hotel = assignedHotels[0];
          if (!place || !hotel) return null;
          const label = `${assignedHotels.map((item) => item!.name).join(" → ")} · ${format(addDays(parseISO(state.startDate), start), "MMM d")}–${format(addDays(parseISO(state.startDate), end), "MMM d")}`;
          return <Marker key={stay.id} position={[place.lat, place.lng]} icon={L.divIcon({ className: "map-marker map-marker-hotel", html: "H" })} eventHandlers={{ click: () => setSelected({ kind: "hotel", id: hotel.id }) }}><Tooltip permanent direction="top">{label}</Tooltip></Marker>;
        })}
        {layers.boats && state.boats.map((boat) => {
          const origin = places.get(boat.region === "Sardinia" ? "cala-di-volpe" : "amalfi");
          const points = [origin, ...boat.waypointIds.map((id) => places.get(id)), origin].filter(Boolean).map((place) => [place!.lat, place!.lng] as [number, number]);
          const day = state.days.find((item) => item.id === boat.dayId);
          const label = `${boat.name} · ${day ? format(addDays(parseISO(state.startDate), day.offset), "MMM d") : ""}`;
          return <Fragment key={boat.id}>{points.length > 1 && <Polyline positions={points} pathOptions={routeStyle.boat}><Tooltip>{label}</Tooltip></Polyline>}{points[1] && <Marker position={points[1]} icon={L.divIcon({ className: "map-marker map-marker-boat", html: "B" })} eventHandlers={{ click: () => setSelected({ kind: "boat", id: boat.id }) }}><Tooltip permanent direction="top">{label}</Tooltip></Marker>}</Fragment>;
        })}
      </MapContainer>
      <div className="absolute left-4 top-4 z-[500] flex flex-wrap gap-2">
        <Button size="sm" variant={layers.hotels ? "primary" : "outline"} onClick={() => setLayers({ ...layers, hotels: !layers.hotels })}><BedDouble size={14} />Hotels</Button>
        <Button size="sm" variant={layers.boats ? "primary" : "outline"} onClick={() => setLayers({ ...layers, boats: !layers.boats })}><Anchor size={14} />Boats</Button>
        <Button size="sm" variant={layers.transport ? "primary" : "outline"} onClick={() => setLayers({ ...layers, transport: !layers.transport })}><Route size={14} />Transport</Button>
      </div>
      {(hotelSelection || boatSelection) && <aside className="absolute bottom-4 right-4 z-[600] w-[calc(100%-2rem)] max-w-md bg-[color:var(--paper)/.97] p-6 shadow-2xl backdrop-blur">
        <div className="mb-5 flex justify-between"><p className="eyebrow">{hotelSelection ? "Hotel stay" : "Boat day"}</p><Button variant="quiet" size="icon" onClick={() => setSelected(undefined)}><X size={17} /></Button></div>
        {hotelSelection && (() => { const stay = state.stays.find((item) => item.hotelId === hotelSelection.id); return <><EditableText value={hotelSelection.name} onChange={(name) => dispatch({ type: "update-hotel", id: hotelSelection.id, patch: { name } })} label="Hotel name" className="font-serif text-3xl" /><div className="mt-5 grid grid-cols-2 gap-4"><Field label="Nightly rate"><EditableNumber value={hotelSelection.nightlyRate} onChange={(nightlyRate) => dispatch({ type: "update-hotel", id: hotelSelection.id, patch: { nightlyRate } })} label="Nightly rate" prefix="$" /></Field><div><p className="eyebrow">Stay total</p><strong>{money(hotelTotal(hotelSelection, stay?.nights ?? 0))}</strong></div></div></>; })()}
        {boatSelection && (() => { const tier = state.stays.find((stay) => stay.region === boatSelection.region)?.tier ?? "luxury"; return <><EditableText value={boatSelection.name} onChange={(name) => dispatch({ type: "update-boat", id: boatSelection.id, patch: { name } })} label="Boat name" className="font-serif text-3xl" /><p className="mt-2 text-sm text-[var(--muted)]">{boatSelection.departureTime}–{boatSelection.returnTime} · {tier === "value" ? boatSelection.valueVessel : boatSelection.vesselType}</p><div className="mt-5"><Field label={`Charter budget · ${tier}`}><EditableNumber value={tier === "value" ? boatSelection.valueBudget : boatSelection.budget} onChange={(value) => dispatch({ type: "update-boat", id: boatSelection.id, patch: tier === "value" ? { valueBudget: value } : { budget: value } })} label="Boat budget" prefix="$" /></Field></div></>; })()}
      </aside>}
    </div>
    <aside className="max-h-[76vh] overflow-y-auto border border-[var(--line)] p-4" aria-label="Trip stops">
      <p className="eyebrow mb-3">Where you sleep</p>
      {staysWithDates.map(({ stay, start, end }) => {
        const ids = [...new Set(stay.nightHotelIds?.length ? stay.nightHotelIds : [stay.hotelId])];
        return <div key={stay.id} className="mb-4 border-t border-[var(--line)] pt-3">
          <p className="text-[10px] uppercase tracking-wider text-[var(--muted)]">{format(addDays(parseISO(state.startDate), start), "MMM d")}–{format(addDays(parseISO(state.startDate), end), "MMM d")}</p>
          {ids.map((id) => {
            const hotel = state.hotels.find((item) => item.id === id);
            const nights = (stay.nightHotelIds ?? []).filter((value) => value === id).length || stay.nights;
            return hotel && <button key={id} onClick={() => setSelected({ kind: "hotel", id })} className={`mt-2 block w-full text-left text-sm ${hotelSelection?.id === id ? "font-semibold text-[var(--ink)]" : "text-[var(--muted)]"}`}>
              {hotel.name}<span className="block text-xs">{nights} {nights === 1 ? "night" : "nights"} · {money(hotel.nightlyRate)}/night</span>
            </button>;
          })}
        </div>;
      })}
      <p className="eyebrow mb-3 mt-6">Days at sea</p>
      {state.boats.map((boat) => {
        const day = state.days.find((item) => item.id === boat.dayId);
        return <button key={boat.id} onClick={() => setSelected({ kind: "boat", id: boat.id })} className={`mb-3 block w-full border-t border-[var(--line)] pt-3 text-left text-sm ${boatSelection?.id === boat.id ? "font-semibold text-[var(--ink)]" : "text-[var(--muted)]"}`}>
          {boat.name}<span className="block text-xs">{day ? format(addDays(parseISO(state.startDate), day.offset), "EEE, MMM d") : ""} · {money(boat.budget)}</span>
        </button>;
      })}
    </aside>
    </div>
  );
}
