import { BadgeCheck, ExternalLink, Star } from "lucide-react";

/** Prices here are researched estimates, never live quotes, so every one links to its source. */
export function VerifyChip({ verified, sourceName, sourceUrl, label = "Estimate" }: {
  verified: boolean; sourceName: string; sourceUrl: string; label?: string;
}) {
  return (
    <a
      href={sourceUrl}
      target="_blank"
      rel="noreferrer"
      className="inline-flex items-center gap-1 rounded-full border border-[var(--line)] px-2 py-1 text-[10px] uppercase tracking-wider text-[var(--muted)] transition hover:border-[var(--ink)] hover:text-[var(--ink)]"
    >
      {verified ? <BadgeCheck size={12} className="text-[var(--olive)]" /> : null}
      {verified ? `${label} · checked on ${sourceName}` : `${label} · verify`}
      <ExternalLink size={10} />
    </a>
  );
}

export function ReviewBadge({ rating, scale, count, source, url }: {
  rating: number; scale: 5 | 10; count: number; source: string; url: string;
}) {
  if (!rating || !count) {
    return (
      <a href={url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-[11px] text-[var(--muted)] underline underline-offset-2">
        Check reviews <ExternalLink size={10} />
      </a>
    );
  }
  return (
    <a href={url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-full bg-[var(--surface)] px-2.5 py-1 text-[11px] transition hover:bg-[var(--line)]">
      <Star size={12} className="fill-[var(--olive)] text-[var(--olive)]" />
      <strong>{rating}</strong>
      <span className="text-[var(--muted)]">/{scale} · {count.toLocaleString()} reviews · {source}</span>
      <ExternalLink size={10} className="text-[var(--muted)]" />
    </a>
  );
}
