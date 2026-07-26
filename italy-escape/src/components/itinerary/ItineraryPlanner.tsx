"use client";

import { useState } from "react";
import { DndContext, KeyboardSensor, PointerSensor, closestCenter, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core";
import { SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { CalendarDays, Check, CloudSun, GripVertical, List, Plus, SlidersHorizontal, Trash2 } from "lucide-react";
import { useTrip } from "@/components/site/TripProvider";
import { Button } from "@/components/ui/Button";
import { EditableDate, EditableNumber, EditableText } from "@/components/edit/Editable";
import { formattedDayDate } from "@/lib/schedule";
import type { Activity, ActivityVenue, ItineraryDay } from "@/lib/types";
import { cn } from "@/lib/utils";

function ActivityRow({ day, activity }: { day: ItineraryDay; activity: Activity }) {
  const { state, dispatch } = useTrip();
  const weatherBuffer = state.days.find((candidate) => candidate.weatherBuffer);
  return (
    <div
      draggable={Boolean(activity.boatId)}
      onDragStart={(event) => { event.dataTransfer.setData("activity", JSON.stringify({ dayId: day.id, activityId: activity.id })); }}
      className="group border-t border-[var(--line)] py-4"
    >
      <div className="flex items-start gap-2">
        {activity.boatId && <GripVertical size={16} className="mt-2 shrink-0 text-[var(--sea)]" aria-label="Boat excursion can be dragged" />}
        <div className="min-w-0 flex-1">
          <EditableText value={activity.title} onChange={(title) => dispatch({ type: "update-activity", dayId: day.id, activityId: activity.id, patch: { title } })} label="Activity title" className="font-medium" />
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            <input aria-label="Activity time" type="time" value={activity.time?.match(/^\d\d:\d\d$/) ? activity.time : ""} onChange={(event) => dispatch({ type: "update-activity", dayId: day.id, activityId: activity.id, patch: { time: event.target.value } })} className="rounded-md bg-transparent px-2 py-1 text-xs" />
            <EditableText value={activity.location ?? ""} onChange={(location) => dispatch({ type: "update-activity", dayId: day.id, activityId: activity.id, patch: { location } })} label="Activity location" className="text-xs text-[var(--muted)]" />
            <select value={activity.venue} onChange={(event) => dispatch({ type: "update-activity", dayId: day.id, activityId: activity.id, patch: { venue: event.target.value as ActivityVenue } })} className="rounded-md bg-transparent px-2 py-1 text-xs"><option value="hotel">At hotel</option><option value="boat">On a boat</option><option value="public">Public sight / activity</option><option value="transit">In transit</option></select>
            {activity.venue === "public" && <EditableNumber value={activity.entryFee ?? 0} onChange={(entryFee) => dispatch({ type: "update-activity", dayId: day.id, activityId: activity.id, patch: { entryFee } })} label="Public activity entry fee" prefix="$" suffix="entry" />}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs">
            <button onClick={() => dispatch({ type: "update-activity", dayId: day.id, activityId: activity.id, patch: { booked: !activity.booked } })} className={cn("flex items-center gap-1", activity.booked ? "text-[var(--olive)]" : "text-[var(--muted)]")}><Check size={14} />{activity.booked ? "Booked" : "Mark booked"}</button>
            <button onClick={() => dispatch({ type: "update-activity", dayId: day.id, activityId: activity.id, patch: { weatherDependent: !activity.weatherDependent } })} className={cn("flex items-center gap-1", activity.weatherDependent ? "text-[var(--sea)]" : "text-[var(--muted)]")}><CloudSun size={14} />Weather</button>
            {activity.boatId && weatherBuffer && weatherBuffer.id !== day.id && <button className="text-[var(--sea)] underline underline-offset-2" onClick={() => dispatch({ type: "move-activity", fromDayId: day.id, toDayId: weatherBuffer.id, activityId: activity.id })}>Move to buffer day</button>}
            <button onClick={() => dispatch({ type: "delete-activity", dayId: day.id, activityId: activity.id })} className="ml-auto text-[var(--muted)] hover:text-red-700" aria-label={`Delete ${activity.title}`}><Trash2 size={14} /></button>
          </div>
          {activity.booked && <EditableText value={activity.confirmation ?? ""} onChange={(confirmation) => dispatch({ type: "update-activity", dayId: day.id, activityId: activity.id, patch: { confirmation } })} label="Reservation confirmation" className="mt-2 text-xs" />}
        </div>
      </div>
    </div>
  );
}

function SortableDay({ day, compact = false }: { day: ItineraryDay; compact?: boolean }) {
  const { state, dispatch } = useTrip();
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: day.id });
  return (
    <article
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        const value = event.dataTransfer.getData("activity");
        if (!value) return;
        try { const parsed = JSON.parse(value); dispatch({ type: "move-activity", fromDayId: parsed.dayId, toDayId: day.id, activityId: parsed.activityId }); } catch { /* Ignore external drops. */ }
      }}
      className={cn("relative border-t border-[var(--line)] py-7", isDragging && "z-10 bg-[var(--surface)] opacity-80", day.weatherBuffer && "border-t-2 border-[var(--sea)] bg-[color:var(--surface)/.45] px-4")}
    >
      <div className={cn("grid gap-5", !compact && "md:grid-cols-[10rem_1fr_2.1fr]")}>
        <div>
          <button className="no-print cursor-grab text-[var(--muted)]" {...attributes} {...listeners} aria-label={`Reorder ${day.title}`}><GripVertical size={16} /></button>
          <p className="mt-2 text-xs uppercase tracking-[.14em] text-[var(--muted)]">{formattedDayDate(state.startDate, day.offset, "EEE · MMM d")}</p>
          {day.weatherBuffer && <span className="mt-3 inline-block rounded-full bg-[var(--sea)] px-2 py-1 text-[9px] uppercase tracking-wider text-white">Weather buffer</span>}
        </div>
        <div>
          <EditableText value={day.title} onChange={(title) => dispatch({ type: "update-day", id: day.id, patch: { title } })} label="Day title" className="font-serif text-3xl leading-none" />
          <EditableText value={day.summary} onChange={(summary) => dispatch({ type: "update-day", id: day.id, patch: { summary } })} label="Day summary" multiline className="mt-2 min-h-16 text-sm leading-6 text-[var(--muted)]" />
          <label className="mt-3 flex items-center gap-2 text-xs text-[var(--muted)]"><input type="checkbox" checked={day.booked} onChange={(e) => dispatch({ type: "update-day", id: day.id, patch: { booked: e.target.checked } })} /> Day fully booked</label>
        </div>
        <div>
          {day.activities.length === 0 ? <p className="py-5 text-sm italic text-[var(--muted)]">Nothing planned yet. Leave it open or add an activity.</p> : day.activities.map((activity) => <ActivityRow key={activity.id} day={day} activity={activity} />)}
          <Button variant="quiet" size="sm" onClick={() => dispatch({ type: "add-activity", dayId: day.id })}><Plus size={14} />Add activity</Button>
          <EditableText value={day.notes} onChange={(notes) => dispatch({ type: "update-day", id: day.id, patch: { notes } })} label="Personal notes" multiline className="mt-3 text-xs italic text-[var(--muted)]" />
        </div>
      </div>
    </article>
  );
}

const venueLabel = { hotel: "At hotel", boat: "On the water", public: "Out exploring", transit: "In transit" } as const;
const venueClass = { hotel: "bg-[#8c7658]", boat: "bg-[var(--sea)]", public: "bg-[var(--olive)]", transit: "bg-[#557080]" } as const;

function SimpleDay({ day }: { day: ItineraryDay }) {
  const { state, dispatch } = useTrip();
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: day.id });
  const venues = [...new Set(day.activities.map((activity) => activity.venue))];
  const stay = state.stays.find((candidate) => candidate.destinationId === day.locationId);
  const hotel = state.hotels.find((candidate) => candidate.id === stay?.hotelId);
  return (
    <article ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition }} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { const value = event.dataTransfer.getData("activity"); if (!value) return; try { const parsed = JSON.parse(value); dispatch({ type: "move-activity", fromDayId: parsed.dayId, toDayId: day.id, activityId: parsed.activityId }); } catch { /* Ignore external drops. */ } }} className={cn("border-t border-[var(--line)] py-5", isDragging && "bg-[var(--surface)] opacity-70", day.weatherBuffer && "border-t-2 border-[var(--sea)]")}>
      <div className="grid gap-3 sm:grid-cols-[2rem_7rem_1fr_13rem] sm:items-center">
        <button {...attributes} {...listeners} className="cursor-grab text-[var(--muted)]" aria-label={`Reorder ${day.title}`}><GripVertical size={15} /></button>
        <p className="text-xs uppercase tracking-wider text-[var(--muted)]">{formattedDayDate(state.startDate, day.offset, "EEE · MMM d")}</p>
        <div><h2 className="font-serif text-2xl">{day.title}</h2><p className="mt-1 text-sm text-[var(--muted)]">{day.summary}</p><div className="mt-2 flex flex-wrap gap-1">{venues.map((venue) => <span key={venue} className={cn("rounded-full px-2 py-1 text-[9px] uppercase tracking-wider text-white", venueClass[venue])}>{venueLabel[venue]}</span>)}{day.weatherBuffer && <span className="rounded-full border border-[var(--sea)] px-2 py-1 text-[9px] uppercase text-[var(--sea)]">Weather buffer</span>}</div></div>
        <div><p className="eyebrow">Where we sleep</p><p className="mt-1 text-sm">{day.offset === 0 ? "Overnight flight" : day.offset === state.days.length - 1 ? "Home" : hotel?.name ?? "In transit"}</p></div>
      </div>
      <details className="ml-0 mt-4 sm:ml-[11rem]"><summary className="cursor-pointer text-xs uppercase tracking-wider text-[var(--muted)]">View details & edit</summary><div className="mt-4 max-w-3xl">{day.activities.map((activity) => <ActivityRow key={activity.id} day={day} activity={activity} />)}<Button variant="quiet" size="sm" onClick={() => dispatch({ type: "add-activity", dayId: day.id })}><Plus size={14} />Add activity</Button></div></details>
    </article>
  );
}

export function ItineraryPlanner() {
  const { state, dispatch } = useTrip();
  const [view, setView] = useState<"simple" | "timeline" | "calendar">("simple");
  const sensors = useSensors(useSensor(PointerSensor), useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }));
  const onDragEnd = ({ active, over }: DragEndEvent) => { if (over) dispatch({ type: "reorder-days", activeId: String(active.id), overId: String(over.id) }); };
  const venueCounts = (["hotel", "boat", "public", "transit"] as const).map((venue) => ({ venue, count: state.days.filter((day) => day.activities.some((activity) => activity.venue === venue)).length }));
  return (
    <>
      <div className="mb-12 grid gap-8 md:grid-cols-[1fr_auto] md:items-end">
        <div><p className="eyebrow mb-4">Day by day</p><h1 className="section-title">The art of<br />a well-paced escape.</h1></div>
        <div className="flex flex-wrap items-end gap-3">
          <label className="grid gap-1 text-[10px] uppercase tracking-wider text-[var(--muted)]">Shift entire trip<EditableDate value={state.startDate} onChange={(value) => dispatch({ type: "set-start-date", value })} label="Trip start date" /></label>
          <Button size="sm" variant={view === "simple" ? "primary" : "outline"} onClick={() => setView("simple")}><List size={16} />Simple</Button>
          <Button size="icon" variant={view === "timeline" ? "primary" : "outline"} onClick={() => setView("timeline")} aria-label="Timeline view"><List size={16} /></Button>
          <Button size="icon" variant={view === "calendar" ? "primary" : "outline"} onClick={() => setView("calendar")} aria-label="Advanced calendar view"><CalendarDays size={16} /></Button>
        </div>
      </div>
      <div className="mb-10 flex flex-wrap gap-3 border-y border-[var(--line)] py-4">{venueCounts.map(({ venue, count }) => <span key={venue} className="flex items-center gap-2 text-xs"><i className={cn("size-2 rounded-full", venueClass[venue])} />{count} days {venueLabel[venue].toLowerCase()}</span>)}<span className="ml-auto flex items-center gap-1 text-xs text-[var(--muted)]"><SlidersHorizontal size={13} />Open a day to edit</span></div>
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
        <SortableContext items={state.days.map((day) => day.id)} strategy={verticalListSortingStrategy}>
          <div className={view === "calendar" ? "grid gap-3 sm:grid-cols-2 xl:grid-cols-3" : ""}>{state.days.map((day) => view === "simple" ? <SimpleDay key={day.id} day={day} /> : <SortableDay key={day.id} day={day} compact={view === "calendar"} />)}</div>
        </SortableContext>
      </DndContext>
    </>
  );
}
