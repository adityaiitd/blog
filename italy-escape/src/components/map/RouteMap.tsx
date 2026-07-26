"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";

const placeholder = (
  <div className="grid h-[66vh] min-h-[520px] animate-pulse place-items-center bg-[var(--surface)] text-sm text-[var(--muted)]">
    Preparing your route map…
  </div>
);

const MapClient = dynamic(() => import("./MapClient"), { ssr: false, loading: () => placeholder });

/** Leaflet is the heaviest thing on the page, so it only loads once the map scrolls into view. */
export function RouteMap() {
  const holder = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = holder.current;
    if (!node || visible) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVisible(true); observer.disconnect(); } },
      { rootMargin: "300px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [visible]);

  return <div ref={holder}>{visible ? <MapClient /> : placeholder}</div>;
}
