"use client";

import Link from "next/link";
import { useState } from "react";
import { Copy, MonitorPlay, Printer, RotateCcw, Save, Users, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useTrip } from "@/components/site/TripProvider";
import { shareUrl } from "@/lib/shareState";
import { loadVersions, saveVersions } from "@/lib/storage";
import type { TripVersion } from "@/lib/types";
import { diffTrips } from "@/lib/versions";

export function ShareBar() {
  const { state, dispatch, reset } = useTrip();
  const [message, setMessage] = useState("");
  const [versions, setVersions] = useState<TripVersion[]>([]);
  const [open, setOpen] = useState(false);
  const copy = async (collaborate = false) => {
    let url = shareUrl(state, window.location.href);
    if (collaborate) {
      const next = new URL(url);
      next.searchParams.set("room", crypto.randomUUID().slice(0, 10));
      url = next.toString();
    }
    await navigator.clipboard.writeText(url);
    setMessage(collaborate ? "Collaboration link copied" : "Shareable itinerary copied");
    window.setTimeout(() => setMessage(""), 2500);
  };
  const save = () => {
    const name = window.prompt("Name this version", `Italy escape · ${new Date().toLocaleDateString()}`);
    if (!name) return;
    const next = [{ id: crypto.randomUUID(), name, createdAt: new Date().toISOString(), state: structuredClone(state) }, ...loadVersions()];
    setVersions(next); saveVersions(next); setOpen(true);
  };
  const openVersions = () => { setVersions(loadVersions()); setOpen(true); };
  return (
    <div className="no-print">
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm" onClick={() => copy()}><Copy size={14} />Copy link</Button>
        <Button variant="outline" size="sm" onClick={() => copy(true)}><Users size={14} />Collaborate</Button>
        <Button variant="outline" size="sm" onClick={save}><Save size={14} />Save version</Button>
        <Button variant="quiet" size="sm" onClick={openVersions}>Versions</Button>
        <Link href="/present"><Button variant="outline" size="sm"><MonitorPlay size={14} />Present</Button></Link>
        <Link href="/print"><Button variant="outline" size="sm"><Printer size={14} />Print / PDF</Button></Link>
        <Button variant="quiet" size="sm" onClick={() => window.confirm("Reset every edit to the original itinerary?") && reset()}><RotateCcw size={14} />Reset</Button>
      </div>
      {message && <p role="status" className="mt-3 text-xs text-[var(--olive)]">{message}</p>}
      {open && (
        <div className="fixed inset-0 z-[2000] grid place-items-center bg-black/45 p-4" role="dialog" aria-modal="true" aria-label="Saved versions">
          <div className="max-h-[85vh] w-full max-w-2xl overflow-auto bg-[var(--paper)] p-6 shadow-2xl">
            <div className="mb-6 flex items-center justify-between"><h2 className="font-serif text-4xl">Saved versions</h2><Button variant="quiet" size="icon" onClick={() => setOpen(false)}><X /></Button></div>
            {versions.length === 0 ? <p className="text-[var(--muted)]">No versions saved yet.</p> : versions.map((version) => {
              const diffs = diffTrips(version.state, state);
              return <section key={version.id} className="border-t border-[var(--line)] py-5">
                <div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="font-medium">{version.name}</h3><p className="text-xs text-[var(--muted)]">{new Date(version.createdAt).toLocaleString()}</p></div><Button size="sm" variant="outline" onClick={() => { dispatch({ type: "replace", state: version.state }); setOpen(false); }}>Restore</Button></div>
                <div className="mt-3 grid gap-1 text-xs text-[var(--muted)]">{diffs.length === 0 ? "No changes from current draft" : diffs.slice(0, 4).map((diff) => <p key={diff.label}><b>{diff.label}:</b> {diff.before} → {diff.after}</p>)}</div>
              </section>;
            })}
          </div>
        </div>
      )}
    </div>
  );
}
