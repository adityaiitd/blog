"use client";

import Link from "next/link";
import { useState } from "react";
import { Copy, MonitorPlay, Printer, RotateCcw, Users } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useTrip } from "@/components/site/TripProvider";
import { shareUrl } from "@/lib/shareState";

export function ShareBar() {
  const { state, reset } = useTrip();
  const [message, setMessage] = useState("");

  const copy = async (collaborate = false) => {
    const url = new URL(shareUrl(state, window.location.href));
    if (collaborate && !url.searchParams.get("room")) {
      url.searchParams.set("room", crypto.randomUUID().slice(0, 10));
    }
    await navigator.clipboard.writeText(url.toString());
    setMessage(collaborate
      ? "Collaboration link copied. Anyone opening it can edit and save with you."
      : "Shareable itinerary copied.");
    window.setTimeout(() => setMessage(""), 3500);
  };

  return (
    <div className="no-print">
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm" onClick={() => copy()}><Copy size={14} />Copy link</Button>
        <Button variant="outline" size="sm" onClick={() => copy(true)}><Users size={14} />Share to edit together</Button>
        <Link href="/present"><Button variant="outline" size="sm"><MonitorPlay size={14} />Present</Button></Link>
        <Link href="/print"><Button variant="outline" size="sm"><Printer size={14} />Print / PDF</Button></Link>
        <Button variant="quiet" size="sm" onClick={() => window.confirm("Reset every edit to the original itinerary?") && reset()}><RotateCcw size={14} />Reset</Button>
      </div>
      {message && <p role="status" className="mt-3 text-xs text-[var(--olive)]">{message}</p>}
    </div>
  );
}
