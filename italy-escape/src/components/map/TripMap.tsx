"use client";

import dynamic from "next/dynamic";

const Client = dynamic(() => import("./TripMapClient"), {
  ssr: false,
  loading: () => <div className="grid h-[76vh] min-h-[600px] animate-pulse place-items-center bg-[var(--surface)] text-sm text-[var(--muted)]">Plotting hotels and boat days…</div>,
});

export function TripMap() { return <Client />; }
