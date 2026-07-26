"use client";

import { useState } from "react";
import { Clock, RotateCcw, Save, Users, X } from "lucide-react";
import { useTrip } from "@/components/site/TripProvider";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

/** Anyone holding the link can name themselves and save; saves sync to everyone in the room. */
export function SaveBar() {
  const { versions, saveVersion, restoreVersion, author, setAuthor, unsavedChanges, peers } = useTrip();
  const [open, setOpen] = useState(false);
  const [naming, setNaming] = useState(false);
  const [label, setLabel] = useState("");
  const [who, setWho] = useState(author);

  const commit = () => {
    const name = who.trim();
    if (name && name !== author) setAuthor(name);
    saveVersion(label, name);
    setLabel("");
    setNaming(false);
  };

  return (
    <div className="no-print flex flex-wrap items-center gap-2">
      <Button size="sm" variant={unsavedChanges ? "primary" : "outline"} onClick={() => setNaming(true)}>
        <Save size={14} />{unsavedChanges ? "Save changes" : "Save version"}
      </Button>
      <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
        <Clock size={14} />History{versions.length ? ` (${versions.filter((version) => version.pinned).length})` : ""}
      </Button>
      {peers > 0 && <span className="flex items-center gap-1 text-xs text-[var(--olive)]"><Users size={13} />{peers} editing</span>}
      {unsavedChanges && <span className="text-xs text-[var(--terracotta)]">Unsaved changes</span>}

      {naming && (
        <div className="fixed inset-0 z-[2100] grid place-items-center bg-black/45 p-4" role="dialog" aria-modal="true" aria-label="Save this version">
          <div className="w-full max-w-md bg-[var(--paper)] p-6 shadow-2xl">
            <h2 className="font-serif text-3xl">Save this version</h2>
            <label className="mt-5 block text-xs uppercase tracking-wider text-[var(--muted)]">
              Your name
              <input value={who} onChange={(event) => setWho(event.target.value)} placeholder="e.g. Aditya" className="mt-1 w-full border border-[var(--line)] bg-transparent px-3 py-2 text-sm normal-case tracking-normal text-[var(--ink)]" />
            </label>
            <label className="mt-4 block text-xs uppercase tracking-wider text-[var(--muted)]">
              What changed (optional)
              <input value={label} onChange={(event) => setLabel(event.target.value)} placeholder="Moved Amalfi boat days earlier" className="mt-1 w-full border border-[var(--line)] bg-transparent px-3 py-2 text-sm normal-case tracking-normal text-[var(--ink)]" />
            </label>
            <div className="mt-6 flex justify-end gap-2">
              <Button size="sm" variant="quiet" onClick={() => setNaming(false)}>Cancel</Button>
              <Button size="sm" onClick={commit}>Save</Button>
            </div>
          </div>
        </div>
      )}

      {open && (
        <div className="fixed inset-0 z-[2100] grid place-items-center bg-black/45 p-4" role="dialog" aria-modal="true" aria-label="Version history">
          <div className="max-h-[85vh] w-full max-w-2xl overflow-auto bg-[var(--paper)] p-6 shadow-2xl">
            <div className="mb-6 flex items-start justify-between">
              <div>
                <h2 className="font-serif text-4xl">Version history</h2>
                <p className="mt-1 text-xs text-[var(--muted)]">Saved versions are kept; automatic snapshots are kept for five days.</p>
              </div>
              <Button variant="quiet" size="icon" onClick={() => setOpen(false)} aria-label="Close"><X /></Button>
            </div>
            {versions.length === 0 ? (
              <p className="text-[var(--muted)]">Nothing saved yet. Make a change and press Save.</p>
            ) : versions.map((version) => (
              <section key={version.id} className={cn("relative ml-3 border-l border-[var(--line)] py-4 pl-6 before:absolute before:-left-1 before:top-6 before:size-2 before:rounded-full", version.pinned ? "before:bg-[var(--olive)]" : "before:bg-[var(--line)]")}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="font-medium">{version.name}</h3>
                    <p className="text-xs text-[var(--muted)]">
                      {new Date(version.createdAt).toLocaleString()}
                      {version.author ? ` · ${version.author}` : ""}
                      {version.pinned ? "" : " · autosave"}
                    </p>
                    {version.summary && <p className="mt-1 text-xs">{version.summary}</p>}
                  </div>
                  <Button size="sm" variant="outline" onClick={() => { restoreVersion(version.id); setOpen(false); }}>
                    <RotateCcw size={13} />Restore
                  </Button>
                </div>
              </section>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
