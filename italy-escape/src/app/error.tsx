"use client";

import { useEffect } from "react";
import { DRAFT_KEY } from "@/lib/storage";

/** A corrupt saved draft must never leave a blank page: offer a one-click recovery. */
export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  useEffect(() => { console.error(error); }, [error]);
  return (
    <main className="page-shell max-w-2xl">
      <p className="eyebrow mb-4">Something went wrong</p>
      <h1 className="font-serif text-5xl">This page hit an error.</h1>
      <p className="mt-6 text-[var(--muted)]">
        This is usually a saved draft from an older version of the planner. Clearing it restores the
        current itinerary; your shared links keep working.
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <button onClick={reset} className="on-ink rounded-full bg-[var(--ink)] px-5 py-3 text-sm">Try again</button>
        <button
          onClick={() => { try { localStorage.removeItem(DRAFT_KEY); } catch { /* Private mode. */ } window.location.href = "/"; }}
          className="rounded-full border border-[var(--line)] px-5 py-3 text-sm"
        >
          Clear saved draft and reload
        </button>
      </div>
    </main>
  );
}
