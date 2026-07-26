"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const base = "w-full rounded-md border border-transparent bg-transparent px-2 py-1.5 transition hover:border-[var(--line)] focus:border-[var(--olive)] focus:bg-[var(--paper)] focus:outline-none";

export function EditableText({ value, onChange, label, className, multiline = false }: {
  value: string; onChange: (value: string) => void; label: string; className?: string; multiline?: boolean;
}) {
  const [draft, setDraft] = useState(value);
  useEffect(() => setDraft(value), [value]);
  const commit = () => onChange(draft.trim() || value);
  if (multiline) return <textarea aria-label={label} value={draft} onChange={(e) => setDraft(e.target.value)} onBlur={commit} onKeyDown={(e) => { if (e.key === "Escape") setDraft(value); }} className={cn(base, "min-h-20 resize-y", className)} />;
  return <input aria-label={label} value={draft} onChange={(e) => setDraft(e.target.value)} onBlur={commit} onKeyDown={(e) => { if (e.key === "Enter") e.currentTarget.blur(); if (e.key === "Escape") { setDraft(value); e.currentTarget.blur(); } }} className={cn(base, className)} />;
}

export function EditableNumber({ value, onChange, label, prefix, suffix, min = 0, max = 1_000_000, className }: {
  value: number; onChange: (value: number) => void; label: string; prefix?: string; suffix?: string; min?: number; max?: number; className?: string;
}) {
  return (
    <label className={cn("inline-flex items-center rounded-md border border-transparent hover:border-[var(--line)] focus-within:border-[var(--olive)]", className)}>
      {prefix && <span className="pl-2 text-[var(--muted)]">{prefix}</span>}
      <input aria-label={label} type="number" value={Number.isFinite(value) ? value : 0} min={min} max={max} onChange={(e) => onChange(Math.min(max, Math.max(min, e.target.valueAsNumber || 0)))} className="min-w-0 flex-1 bg-transparent px-1 py-1.5 outline-none" />
      {suffix && <span className="pr-2 text-xs text-[var(--muted)]">{suffix}</span>}
    </label>
  );
}

export function EditableDate({ value, onChange, label, className }: { value: string; onChange: (value: string) => void; label: string; className?: string }) {
  return <input aria-label={label} type="date" value={value} onChange={(event) => onChange(event.target.value)} className={cn(base, className)} />;
}

export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="grid gap-1 text-xs uppercase tracking-[.14em] text-[var(--muted)]"><span>{label}</span>{children}</label>;
}
