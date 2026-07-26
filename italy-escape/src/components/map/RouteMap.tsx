"use client";

import dynamic from "next/dynamic";

const MapClient = dynamic(() => import("./MapClient"), {
  ssr: false,
  loading: () => <div className="grid h-[66vh] min-h-[520px] animate-pulse place-items-center bg-[var(--surface)] text-sm text-[var(--muted)]">Preparing your route map…</div>,
});

export function RouteMap() {
  return <MapClient />;
}
