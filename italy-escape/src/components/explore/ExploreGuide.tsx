"use client";

import { useState } from "react";
import Image from "next/image";
import { ExternalLink, Leaf, Landmark, UtensilsCrossed, Waves, Wine } from "lucide-react";
import { spots, type SpotKind } from "@/data/explore";
import { useTrip } from "@/components/site/TripProvider";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

const kinds: { id: SpotKind | "all"; label: string }[] = [
  { id: "all", label: "Everything" },
  { id: "eat", label: "Eating" },
  { id: "see", label: "Sights" },
  { id: "calm", label: "Quiet spots" },
  { id: "beach", label: "Swimming" },
  { id: "drink", label: "Drinks" },
];

const icon = { eat: UtensilsCrossed, see: Landmark, calm: Leaf, beach: Waves, drink: Wine };
const heroImage: Record<string, string> = {
  Sardinia: "/images/costa-smeralda.webp",
  Tuscany: "/images/val-dorcia.webp",
  "Amalfi Coast": "/images/positano.webp",
};

export function ExploreGuide() {
  const { state, dispatch } = useTrip();
  const [filter, setFilter] = useState<SpotKind | "all">("all");
  const [added, setAdded] = useState<string[]>([]);

  const addToTrip = (spotId: string, name: string, region: string, kind: SpotKind) => {
    // Drop it on the first day of that region so it lands in the right stretch of the trip.
    const stayIndex = state.stays.findIndex((stay) => stay.region === region);
    if (stayIndex < 0) return;
    const offset = 1 + state.stays.slice(0, stayIndex).reduce((sum, stay) => sum + stay.nights, 0);
    const day = state.days.find((candidate) => candidate.offset === offset) ?? state.days[0];
    dispatch({
      type: "add-activity",
      dayId: day.id,
      patch: {
        title: name,
        venue: "public",
        purpose: kind === "eat" || kind === "drink" ? "eat" : kind === "calm" ? "relax" : kind === "beach" ? "relax" : "see",
        rationale: "Added from the guide; move it to whichever day suits.",
      },
    });
    setAdded((current) => [...current, spotId]);
  };

  return (
    <>
      <header className="mb-14 max-w-3xl">
        <p className="eyebrow mb-4">Beyond the hotel</p>
        <h1 className="section-title">Where to eat, wander<br />and do nothing at all.</h1>
        <p className="mt-6 text-lg leading-8 text-[var(--muted)]">
          Chosen for what is genuinely worth the detour from each of your three bases, with the quiet
          alternatives to the obvious stops. Add any of them straight onto a day.
        </p>
      </header>

      <div className="no-print mb-12 flex flex-wrap gap-2">
        {kinds.map((item) => (
          <Button key={item.id} size="sm" variant={filter === item.id ? "primary" : "outline"} onClick={() => setFilter(item.id)}>
            {item.label}
          </Button>
        ))}
      </div>

      {state.stays.map((stay) => {
        const list = spots.filter((spot) => spot.region === stay.region && (filter === "all" || spot.kind === filter));
        if (list.length === 0) return null;
        return (
          <section key={stay.id} className="mb-20">
            <div className="relative mb-8 h-[220px] overflow-hidden md:h-[300px]">
              <Image src={heroImage[stay.region] ?? "/images/amalfi.webp"} alt={stay.region} fill sizes="100vw" className="object-cover" />
              <div className="absolute inset-0 bg-black/25" />
              <div className="absolute bottom-6 left-6 text-white">
                <p className="eyebrow !text-white/75">{stay.nights} nights</p>
                <h2 className="font-serif text-5xl">{stay.region}</h2>
              </div>
            </div>
            <div className="grid gap-x-8 gap-y-6 lg:grid-cols-2">
              {list.map((spot) => {
                const Icon = icon[spot.kind];
                const isAdded = added.includes(spot.id);
                return (
                  <article key={spot.id} className="border-t border-[var(--line)] pt-5">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-[var(--olive)]">
                          <Icon size={12} />{spot.kind === "calm" ? "Quiet" : spot.kind}
                        </p>
                        <h3 className="mt-1 font-serif text-2xl">{spot.name}</h3>
                        <p className="text-xs text-[var(--muted)]">{spot.near}</p>
                      </div>
                      <Button size="sm" variant={isAdded ? "primary" : "outline"} onClick={() => addToTrip(spot.id, spot.name, spot.region, spot.kind)}>
                        {isAdded ? "Added" : "Add to trip"}
                      </Button>
                    </div>
                    <p className="mt-3 text-sm leading-6">{spot.why}</p>
                    <p className={cn("mt-2 text-xs leading-5 text-[var(--muted)]")}><b>Worth knowing:</b> {spot.tip}</p>
                    <a href={spot.url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-xs underline underline-offset-2">
                      More on this <ExternalLink size={10} />
                    </a>
                  </article>
                );
              })}
            </div>
          </section>
        );
      })}
    </>
  );
}
