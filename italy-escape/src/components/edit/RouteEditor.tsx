"use client";

import { Plus, Trash2 } from "lucide-react";
import { useTrip } from "@/components/site/TripProvider";
import { Button } from "@/components/ui/Button";
import { EditableNumber, EditableText } from "./Editable";
import type { BookingStatus, TransportMode } from "@/lib/types";

export function RouteEditor() {
  const { state, dispatch } = useTrip();
  return (
    <section className="mt-20">
      <div className="mb-8 flex items-end justify-between gap-4">
        <div><p className="eyebrow mb-3">Every connection</p><h2 className="font-serif text-5xl">Route ledger</h2></div>
        <Button variant="outline" size="sm" onClick={() => dispatch({ type: "add-route" })}><Plus size={14} />Add leg</Button>
      </div>
      <div className="border-t border-[var(--line)]">
        {state.routeLegs.map((leg, index) => (
          <div key={leg.id} className="grid gap-3 border-b border-[var(--line)] py-5 md:grid-cols-[2rem_1fr_1fr_10rem_1.4fr_7rem_3rem] md:items-center">
            <span className="text-xs text-[var(--muted)]">{String(index + 1).padStart(2, "0")}</span>
            <select aria-label={`Origin for route ${index + 1}`} value={leg.fromId} onChange={(e) => dispatch({ type: "update-route", id: leg.id, patch: { fromId: e.target.value } })} className="rounded-md bg-transparent p-2 text-sm">{state.destinations.map((place) => <option key={place.id} value={place.id}>{place.shortName}</option>)}</select>
            <select aria-label={`Destination for route ${index + 1}`} value={leg.toId} onChange={(e) => dispatch({ type: "update-route", id: leg.id, patch: { toId: e.target.value } })} className="rounded-md bg-transparent p-2 text-sm">{state.destinations.map((place) => <option key={place.id} value={place.id}>{place.shortName}</option>)}</select>
            <select aria-label={`Transport mode for route ${index + 1}`} value={leg.mode} onChange={(e) => dispatch({ type: "update-route", id: leg.id, patch: { mode: e.target.value as TransportMode } })} className="rounded-md bg-transparent p-2 text-xs uppercase">{(["international-flight", "internal-flight", "private-car", "train", "boat"] as TransportMode[]).map((mode) => <option key={mode} value={mode}>{mode.replaceAll("-", " ")}</option>)}</select>
            <EditableText value={leg.details} onChange={(details) => dispatch({ type: "update-route", id: leg.id, patch: { details } })} label="Route details" className="text-sm" />
            <EditableNumber value={leg.cost} onChange={(cost) => dispatch({ type: "update-route", id: leg.id, patch: { cost } })} label="Route cost" prefix="$" />
            <Button variant="danger" size="icon" onClick={() => dispatch({ type: "delete-route", id: leg.id })} aria-label="Delete route leg"><Trash2 size={15} /></Button>
            <div className="grid gap-2 md:col-start-2 md:col-span-5 sm:grid-cols-4">
              <EditableText value={leg.carrier ?? ""} onChange={(carrier) => dispatch({ type: "update-route", id: leg.id, patch: { carrier } })} label="Carrier or vehicle" className="text-xs" />
              <input aria-label="Departure time" type="time" value={leg.departure ?? ""} onChange={(e) => dispatch({ type: "update-route", id: leg.id, patch: { departure: e.target.value } })} className="rounded-md bg-transparent px-2 text-xs" />
              <input aria-label="Arrival time" type="time" value={leg.arrival ?? ""} onChange={(e) => dispatch({ type: "update-route", id: leg.id, patch: { arrival: e.target.value } })} className="rounded-md bg-transparent px-2 text-xs" />
              <select aria-label="Route booking status" value={leg.status} onChange={(e) => dispatch({ type: "update-route", id: leg.id, patch: { status: e.target.value as BookingStatus } })} className="rounded-md bg-transparent px-2 text-xs uppercase"><option value="idea">Idea</option><option value="requested">Requested</option><option value="booked">Booked</option></select>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
