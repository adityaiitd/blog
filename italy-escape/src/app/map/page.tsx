import { TripMap } from "@/components/map/TripMap";

export default function MapPage() {
  return <main className="page-shell"><div className="mb-10"><p className="eyebrow mb-4">The whole journey</p><h1 className="section-title">Hotels, boats<br />and every connection.</h1><p className="mt-6 max-w-2xl text-[var(--muted)]">Toggle layers to see where you sleep, when you are at sea, and how each chapter connects. Select a marker to edit it.</p></div><TripMap /></main>;
}
