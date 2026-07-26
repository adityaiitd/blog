"use client";

import { useState } from "react";
import { Check, Loader2, MapPin, Plus, Search } from "lucide-react";
import { useTrip } from "@/components/site/TripProvider";
import { Button } from "@/components/ui/Button";
import type { PlaceMatch } from "@/app/api/place-lookup/route";
import type { Stay } from "@/lib/types";

/** Type a hotel name, look up its real address and pin, then save it against this leg. */
export function AddHotel({ stay }: { stay: Stay }) {
  const { dispatch } = useTrip();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [rate, setRate] = useState(500);
  const [status, setStatus] = useState<"idle" | "searching" | "done">("idle");
  const [matches, setMatches] = useState<PlaceMatch[]>([]);
  const [chosen, setChosen] = useState<PlaceMatch | null>(null);
  const [added, setAdded] = useState("");

  const search = async () => {
    if (query.trim().length < 3) return;
    setStatus("searching");
    setChosen(null);
    try {
      const response = await fetch(`/api/place-lookup?q=${encodeURIComponent(query.trim())}`);
      const data = await response.json();
      setMatches(data.matches ?? []);
    } catch {
      setMatches([]);
    }
    setStatus("done");
  };

  const add = () => {
    const name = chosen?.name ?? query.trim();
    if (!name) return;
    dispatch({
      type: "add-hotel",
      region: stay.region,
      patch: {
        name,
        nightlyRate: rate,
        viewSummary: chosen?.address ?? "",
        whyPick: chosen
          ? `Added by you. ${chosen.address}${chosen.stars ? ` · ${chosen.stars}-star listing` : ""}.`
          : "Added by you. Use the links to check rooms, rates and reviews.",
        officialUrl: chosen?.website ?? `https://duckduckgo.com/?q=${encodeURIComponent(`${name} official site`)}`,
        rateNote: chosen?.phone ? `Listed phone: ${chosen.phone}. Confirm the live rate before booking.` : "Confirm the live rate before booking.",
      },
    });
    setAdded(name);
    setQuery(""); setMatches([]); setChosen(null); setStatus("idle");
    window.setTimeout(() => { setAdded(""); setOpen(false); }, 2200);
  };

  if (!open) {
    return (
      <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
        <Plus size={14} />Add a hotel by name
      </Button>
    );
  }

  return (
    <div className="w-full border border-[var(--line)] p-4">
      <p className="eyebrow mb-3">Add a hotel to {stay.region}</p>
      <div className="flex flex-wrap gap-2">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); search(); } }}
          placeholder="e.g. Le Sirenuse"
          aria-label="Hotel name"
          className="min-w-52 flex-1 border border-[var(--line)] bg-transparent px-3 py-2 text-sm"
        />
        <label className="flex items-center border border-[var(--line)] px-2 text-sm">
          <span className="text-[var(--muted)]">$</span>
          <input type="number" value={rate} min={0} onChange={(event) => setRate(Number(event.target.value) || 0)} aria-label="Nightly rate" className="w-20 bg-transparent px-1 py-2" />
          <span className="text-xs text-[var(--muted)]">/night</span>
        </label>
        <Button size="sm" variant="outline" onClick={search} disabled={status === "searching"}>
          {status === "searching" ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}Look up
        </Button>
        <Button size="sm" onClick={add} disabled={!query.trim()}>Add to {stay.region}</Button>
        <Button size="sm" variant="quiet" onClick={() => setOpen(false)}>Close</Button>
      </div>

      {status === "done" && matches.length === 0 && (
        <p className="mt-3 text-xs text-[var(--muted)]">
          No map match found. You can still add it by name and the booking and review links will work.
        </p>
      )}

      {matches.length > 0 && (
        <div className="mt-3 grid gap-2">
          <p className="text-xs text-[var(--muted)]">Pick the right property to attach its address and map pin:</p>
          {matches.map((match) => (
            <button
              key={`${match.lat}-${match.lng}`}
              onClick={() => setChosen(match)}
              className={`flex items-start gap-2 border p-3 text-left text-xs ${chosen === match ? "border-[var(--ink)] bg-[color:var(--surface)/.6]" : "border-[var(--line)]"}`}
            >
              {chosen === match ? <Check size={13} className="mt-0.5 text-[var(--olive)]" /> : <MapPin size={13} className="mt-0.5 text-[var(--muted)]" />}
              <span>
                <strong>{match.name}</strong>
                <span className="block text-[var(--muted)]">{match.address}</span>
                {match.website && <span className="block text-[var(--olive)]">{match.website}</span>}
              </span>
            </button>
          ))}
        </div>
      )}

      {added && <p role="status" className="mt-3 text-xs text-[var(--olive)]">{added} added to {stay.region}. Assign it to any night above.</p>}
    </div>
  );
}
