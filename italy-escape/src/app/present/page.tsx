"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, X } from "lucide-react";
import { useTrip } from "@/components/site/TripProvider";
import { calculateCosts, money } from "@/lib/costCalculator";

const chapters = [
  { region: "Sardinia", image: "/images/la-maddalena.webp", line: "Five nights between granite coves and the open sea." },
  { region: "Tuscany", image: "/images/val-dorcia.webp", line: "Four nights of vineyards, Florence and unhurried mornings." },
  { region: "Amalfi Coast", image: "/images/positano.webp", line: "Five nights suspended between cliff and Mediterranean." },
];

export default function PresentPage() {
  const { state } = useTrip();
  const [slide, setSlide] = useState(0);
  const current = chapters[slide];
  const cost = calculateCosts(state);
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === "ArrowRight") setSlide((value) => Math.min(chapters.length - 1, value + 1));
      if (event.key === "ArrowLeft") setSlide((value) => Math.max(0, value - 1));
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);
  const stay = state.stays.find((item) => item.region === current.region);
  const hotel = state.hotels.find((item) => item.id === stay?.hotelId);
  return (
    <main className="fixed inset-0 z-[3000] bg-black text-white">
      <Image src={current.image} alt={current.region} fill priority sizes="100vw" className="object-cover" />
      <div className="absolute inset-0 bg-black/35" />
      <Link href="/" className="absolute right-5 top-5 z-10 rounded-full bg-black/25 p-3 backdrop-blur" aria-label="Close presentation"><X /></Link>
      <div className="relative flex h-full flex-col justify-end p-7 md:p-16">
        <p className="mb-4 text-xs uppercase tracking-[.25em]">Chapter {slide + 1} of {chapters.length}</p>
        <h1 className="font-serif text-[clamp(5rem,14vw,12rem)] leading-[.7] tracking-[-.06em]">{current.region}</h1>
        <div className="mt-10 grid max-w-5xl gap-5 border-t border-white/50 pt-5 md:grid-cols-3">
          <p className="text-lg">{current.line}</p>
          <p className="text-sm">{hotel?.name}<br /><span className="text-white/70">{stay?.nights} nights</span></p>
          <p className="text-sm">Recommended trip budget<br /><span className="font-serif text-3xl">{money(cost.recommended)}</span></p>
        </div>
        <div className="mt-8 flex items-center gap-3">
          <button onClick={() => setSlide(Math.max(0, slide - 1))} disabled={slide === 0} className="rounded-full border border-white/50 p-3 disabled:opacity-30" aria-label="Previous chapter"><ArrowLeft /></button>
          <button onClick={() => setSlide(Math.min(chapters.length - 1, slide + 1))} disabled={slide === chapters.length - 1} className="rounded-full border border-white/50 p-3 disabled:opacity-30" aria-label="Next chapter"><ArrowRight /></button>
          <span className="ml-3 text-xs text-white/70">Use arrow keys to navigate</span>
        </div>
      </div>
    </main>
  );
}
