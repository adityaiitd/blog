import type { TripState, TripVersion } from "./types";
import { diffTrips } from "./versions";

export const DRAFT_KEY = "italy-escape:draft:v1";
export const VERSIONS_KEY = "italy-escape:versions:v1";
export const HISTORY_KEY = "italy-escape:history:v2";
export const HISTORY_RETENTION_MS = 5 * 24 * 60 * 60 * 1000;

export function loadDraft(): TripState | undefined {
  try {
    const value = localStorage.getItem(DRAFT_KEY);
    return value ? JSON.parse(value) as TripState : undefined;
  } catch {
    return undefined;
  }
}

export function saveDraft(state: TripState) {
  localStorage.setItem(DRAFT_KEY, JSON.stringify(state));
}

export function loadVersions(): TripVersion[] {
  try {
    return JSON.parse(localStorage.getItem(VERSIONS_KEY) ?? "[]") as TripVersion[];
  } catch {
    return [];
  }
}

export function saveVersions(versions: TripVersion[]) {
  localStorage.setItem(VERSIONS_KEY, JSON.stringify(versions));
}

export function pruneHistory(versions: TripVersion[], now = Date.now()) {
  const kept = versions.filter((version) => version.pinned || now - new Date(version.createdAt).getTime() <= HISTORY_RETENTION_MS);
  const pinned = kept.filter((version) => version.pinned);
  const recent = kept.filter((version) => !version.pinned).slice(0, Math.max(0, 200 - pinned.length));
  return [...pinned, ...recent].sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

export function loadHistory(): TripVersion[] {
  try {
    const history = JSON.parse(localStorage.getItem(HISTORY_KEY) ?? "[]") as TripVersion[];
    const legacy = loadVersions().map((version) => ({ ...version, pinned: true }));
    const existing = new Set(history.map((version) => version.id));
    return pruneHistory([...history, ...legacy.filter((version) => !existing.has(version.id))]);
  } catch {
    return [];
  }
}

export function saveHistory(versions: TripVersion[]) {
  const pruned = pruneHistory(versions);
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(pruned));
  } catch {
    const pinned = pruned.filter((version) => version.pinned);
    const recent = pruned.filter((version) => !version.pinned).slice(0, 40);
    try { localStorage.setItem(HISTORY_KEY, JSON.stringify([...pinned, ...recent])); } catch { /* Named versions may fill private-browser quotas; editing still works. */ }
  }
}

export const AUTHOR_KEY = "italy-escape:author";

export function loadAuthor(): string {
  try { return localStorage.getItem(AUTHOR_KEY) ?? ""; } catch { return ""; }
}

export function saveAuthor(name: string) {
  try { localStorage.setItem(AUTHOR_KEY, name); } catch { /* Private mode. */ }
}

/** Merges two histories by id, newest first, so both partners converge on one timeline. */
export function mergeVersions(a: TripVersion[], b: TripVersion[]) {
  const byId = new Map<string, TripVersion>();
  [...a, ...b].forEach((version) => byId.set(version.id, version));
  return pruneHistory([...byId.values()]);
}

export function recordAutoVersion(state: TripState) {
  const history = loadHistory();
  const latest = history.find((version) => !version.pinned);
  if (latest && JSON.stringify(latest.state) === JSON.stringify(state)) return history;
  const changes = latest ? diffTrips(latest.state, state) : [];
  const summary = changes.length ? changes.slice(0, 2).map((change) => `${change.label}: ${change.after}`).join(" · ") : "Itinerary edited";
  const next = [{ id: crypto.randomUUID(), name: "Autosaved", createdAt: new Date().toISOString(), state: structuredClone(state), pinned: false, summary }, ...history];
  saveHistory(next);
  return pruneHistory(next);
}
