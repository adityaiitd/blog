import type { TripState, TripVersion } from "./types";

export const DRAFT_KEY = "italy-escape:draft:v1";
export const VERSIONS_KEY = "italy-escape:versions:v1";

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
