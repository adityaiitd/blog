"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { freshInitialTripState } from "@/data";
import { connectCollaboration, type CollaborationSession } from "@/lib/collab";
import { decodeTripState } from "@/lib/shareState";
import { loadDraft, recordAutoVersion, saveDraft } from "@/lib/storage";
import { tripReducer } from "@/lib/tripReducer";
import { normalizeTripState } from "@/lib/migrate";
import type { TripAction, TripState } from "@/lib/types";

interface TripContextValue {
  state: TripState;
  dispatch: (action: TripAction) => void;
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  reset: () => void;
  hydrationError?: string;
  peers: number;
}

const TripContext = createContext<TripContextValue | null>(null);

export function TripProvider({ children }: { children: React.ReactNode }) {
  const [state, baseDispatch] = useReducer(tripReducer, undefined, freshInitialTripState);
  const [hydrated, setHydrated] = useState(false);
  const [hydrationError, setHydrationError] = useState<string>();
  const [peers, setPeers] = useState(0);
  const [historyState, setHistoryState] = useState({ canUndo: false, canRedo: false });
  const undoStack = useRef<TripState[]>([]);
  const redoStack = useRef<TripState[]>([]);
  const stateRef = useRef(state);
  const collab = useRef<CollaborationSession | null>(null);
  const lastAutoState = useRef<string | null>(null);

  useEffect(() => { stateRef.current = state; }, [state]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams(window.location.search);
      const encoded = params.get("t");
      // A damaged draft or link must never take the page down; fall back to the seeded trip.
      try {
        if (encoded) {
          const result = decodeTripState(encoded);
          if (result.state) baseDispatch({ type: "replace", state: normalizeTripState(result.state) });
          else setHydrationError(result.error);
        } else {
          const draft = loadDraft();
          if (draft?.schemaVersion === 1) baseDispatch({ type: "replace", state: normalizeTripState(draft) });
        }
      } catch {
        setHydrationError("Your saved draft was from an older version, so the original itinerary was restored.");
      }
      setHydrated(true);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    const timer = window.setTimeout(() => saveDraft(state), 350);
    collab.current?.publish(state);
    return () => window.clearTimeout(timer);
  }, [state, hydrated]);

  useEffect(() => {
    if (!hydrated) return;
    const serialized = JSON.stringify(state);
    if (lastAutoState.current === null) { lastAutoState.current = serialized; return; }
    if (lastAutoState.current === serialized) return;
    const timer = window.setTimeout(() => {
      recordAutoVersion(state);
      lastAutoState.current = serialized;
    }, 4000);
    return () => window.clearTimeout(timer);
  }, [state, hydrated]);

  useEffect(() => {
    if (!hydrated) return;
    const room = new URLSearchParams(window.location.search).get("room");
    if (!room) return;
    let cancelled = false;
    connectCollaboration(room, stateRef.current, (remote) => {
      if (!cancelled) baseDispatch({ type: "replace", state: remote });
    }, setPeers).then((session) => {
      if (cancelled) session.destroy();
      else collab.current = session;
    }).catch(() => setPeers(0));
    return () => { cancelled = true; collab.current?.destroy(); collab.current = null; };
  }, [hydrated]);

  const dispatch = useCallback((action: TripAction) => {
    undoStack.current.push(structuredClone(stateRef.current));
    if (undoStack.current.length > 50) undoStack.current.shift();
    redoStack.current = [];
    baseDispatch(action);
    setHistoryState({ canUndo: true, canRedo: false });
  }, []);

  const undo = useCallback(() => {
    const previous = undoStack.current.pop();
    if (!previous) return;
    redoStack.current.push(structuredClone(stateRef.current));
    baseDispatch({ type: "replace", state: previous });
    setHistoryState({ canUndo: undoStack.current.length > 0, canRedo: true });
  }, []);
  const redo = useCallback(() => {
    const next = redoStack.current.pop();
    if (!next) return;
    undoStack.current.push(structuredClone(stateRef.current));
    baseDispatch({ type: "replace", state: next });
    setHistoryState({ canUndo: true, canRedo: redoStack.current.length > 0 });
  }, []);
  const reset = useCallback(() => dispatch({ type: "replace", state: freshInitialTripState() }), [dispatch]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "z") return;
      event.preventDefault();
      if (event.shiftKey) redo(); else undo();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [undo, redo]);

  const value = useMemo(() => ({
    state, dispatch, undo, redo,
    canUndo: historyState.canUndo,
    canRedo: historyState.canRedo,
    reset, hydrationError, peers,
  }), [state, dispatch, undo, redo, reset, hydrationError, peers, historyState]);

  return <TripContext.Provider value={value}>{children}</TripContext.Provider>;
}

export function useTrip() {
  const context = useContext(TripContext);
  if (!context) throw new Error("useTrip must be used inside TripProvider");
  return context;
}
