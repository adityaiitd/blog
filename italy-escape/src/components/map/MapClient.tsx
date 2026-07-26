"use client";

import { useMemo, useState } from "react";
import L from "leaflet";
import { MapContainer, Marker, Polyline, TileLayer, Tooltip, useMapEvents } from "react-leaflet";
import { Pencil, X } from "lucide-react";
import { useTrip } from "@/components/site/TripProvider";
import { Button } from "@/components/ui/Button";
import { EditableNumber, EditableText, Field } from "@/components/edit/Editable";
import type { Destination, TransportMode } from "@/lib/types";
import { useTheme } from "next-themes";

const style: Record<TransportMode, L.PathOptions> = {
  "international-flight": { color: "#516b78", weight: 2, dashArray: "14 10", opacity: .8 },
  "internal-flight": { color: "#9c7755", weight: 2, dashArray: "7 7", opacity: .9 },
  "private-car": { color: "#8d5b4b", weight: 3, opacity: .85 },
  train: { color: "#5f674e", weight: 4, dashArray: "2 7", opacity: .95 },
  boat: { color: "#347a7e", weight: 3, dashArray: "10 5 2 5", opacity: .95 },
};

function curve(a: Destination, b: Destination, mode: TransportMode): [number, number][] {
  if (!mode.includes("flight")) return [[a.lat, a.lng], [b.lat, b.lng]];
  const steps = 28;
  const bend = Math.min(18, Math.abs(b.lng - a.lng) * .12);
  return Array.from({ length: steps + 1 }, (_, index) => {
    const t = index / steps;
    return [
      a.lat + (b.lat - a.lat) * t + Math.sin(Math.PI * t) * bend,
      a.lng + (b.lng - a.lng) * t,
    ];
  });
}

function MapClick({ editing }: { editing: boolean }) {
  const { dispatch } = useTrip();
  useMapEvents({
    dblclick(event) {
      if (!editing) return;
      dispatch({ type: "add-destination", patch: { lat: event.latlng.lat, lng: event.latlng.lng } });
    },
  });
  return null;
}

export default function MapClient() {
  const { state, dispatch } = useTrip();
  const { resolvedTheme } = useTheme();
  const [selected, setSelected] = useState<string>();
  const [editing, setEditing] = useState(false);
  const destination = state.destinations.find((place) => place.id === selected);
  const placeById = useMemo(() => new Map(state.destinations.map((place) => [place.id, place])), [state.destinations]);
  const tile = resolvedTheme === "dark"
    ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
    : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";

  return (
    <div className="relative h-[66vh] min-h-[520px] overflow-hidden bg-[var(--surface)]">
      <MapContainer center={[42.1, 6.5]} zoom={4} minZoom={2} className="h-full w-full" scrollWheelZoom>
        <TileLayer url={tile} attribution="&copy; OpenStreetMap &copy; CARTO" />
        <MapClick editing={editing} />
        {state.routeLegs.map((leg) => {
          const from = placeById.get(leg.fromId); const to = placeById.get(leg.toId);
          if (!from || !to) return null;
          return <Polyline key={leg.id} positions={curve(from, to, leg.mode)} pathOptions={style[leg.mode]}><Tooltip>{leg.details}</Tooltip></Polyline>;
        })}
        {state.destinations.filter((place) => !place.waypoint).map((place, index) => (
          <Marker
            key={place.id}
            position={[place.lat, place.lng]}
            draggable={editing}
            icon={L.divIcon({ className: "map-marker", html: String(index + 1), iconSize: [27, 27] })}
            eventHandlers={{
              click: () => setSelected(place.id),
              dragend: (event) => {
                const point = event.target.getLatLng();
                dispatch({ type: "update-destination", id: place.id, patch: { lat: point.lat, lng: point.lng } });
              },
            }}
            title={place.name}
          ><Tooltip direction="top">{place.shortName}</Tooltip></Marker>
        ))}
      </MapContainer>
      <div className="absolute left-4 top-4 z-[500] flex gap-2">
        <Button size="sm" variant={editing ? "primary" : "outline"} onClick={() => setEditing(!editing)}><Pencil size={14} />{editing ? "Editing map" : "Edit map"}</Button>
      </div>
      <div className="absolute bottom-4 left-4 z-[500] flex max-w-[calc(100%-2rem)] flex-wrap gap-x-4 gap-y-1 rounded-sm bg-[color:var(--paper)/.92] px-4 py-3 text-[10px] uppercase tracking-wider shadow-lg backdrop-blur">
        {(Object.keys(style) as TransportMode[]).map((mode) => <span key={mode} className="flex items-center gap-2"><i className="block w-6 border-t-2" style={{ borderColor: String(style[mode].color), borderTopStyle: mode === "private-car" ? "solid" : "dashed" }} />{mode.replaceAll("-", " ")}</span>)}
      </div>
      {destination && (
        <aside className="absolute inset-x-3 bottom-3 z-[600] max-h-[72%] overflow-auto border border-[var(--line)] bg-[color:var(--paper)/.97] p-5 shadow-2xl backdrop-blur md:inset-auto md:right-5 md:top-5 md:w-[370px]">
          <div className="mb-5 flex items-start gap-3">
            <EditableText value={destination.name} onChange={(name) => dispatch({ type: "update-destination", id: destination.id, patch: { name, shortName: name } })} label="Destination name" className="font-serif text-3xl" />
            <Button size="icon" variant="quiet" onClick={() => setSelected(undefined)} aria-label="Close destination panel"><X size={18} /></Button>
          </div>
          <div className="mb-5 grid grid-cols-2 gap-4">
            <Field label="Region"><EditableText value={destination.region} onChange={(region) => dispatch({ type: "update-destination", id: destination.id, patch: { region } })} label="Destination region" /></Field>
            <Field label="Place type"><select value={destination.kind} onChange={(event) => dispatch({ type: "update-destination", id: destination.id, patch: { kind: event.target.value as Destination["kind"] } })} className="rounded-md bg-transparent p-2 text-sm"><option value="airport">Airport</option><option value="station">Station</option><option value="hotel">Hotel</option><option value="port">Port</option><option value="city">City</option></select></Field>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Latitude"><EditableNumber value={destination.lat} min={-90} max={90} onChange={(lat) => dispatch({ type: "update-destination", id: destination.id, patch: { lat } })} label="Latitude" /></Field>
            <Field label="Longitude"><EditableNumber value={destination.lng} min={-180} max={180} onChange={(lng) => dispatch({ type: "update-destination", id: destination.id, patch: { lng } })} label="Longitude" /></Field>
          </div>
          <div className="mt-6 border-t border-[var(--line)] pt-5">
            <p className="eyebrow mb-2">Journey details</p>
            {state.stays.filter((stay) => stay.destinationId === destination.id).map((stay) => {
              const hotel = state.hotels.find((item) => item.id === stay.hotelId);
              return <p key={stay.id} className="text-sm">{stay.nights} nights at {hotel?.name}</p>;
            })}
            {state.days.filter((day) => day.locationId === destination.id).slice(0, 4).map((day) => <p key={day.id} className="mt-2 text-sm text-[var(--muted)]">{day.title} — {day.summary}</p>)}
          </div>
          {editing && <Button variant="danger" size="sm" className="mt-6" onClick={() => { dispatch({ type: "delete-destination", id: destination.id }); setSelected(undefined); }}>Remove destination</Button>}
        </aside>
      )}
    </div>
  );
}
