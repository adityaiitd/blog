"use client";

import type { TripState } from "./types";

export interface CollaborationSession {
  destroy: () => void;
  publish: (state: TripState) => void;
}

/** Optional peer-to-peer sync. The app remains fully usable if signaling is unavailable. */
export async function connectCollaboration(
  room: string,
  initial: TripState,
  onRemoteState: (state: TripState) => void,
  onPeers: (count: number) => void,
): Promise<CollaborationSession> {
  const Y = await import("yjs");
  const { WebrtcProvider } = await import("y-webrtc");
  const doc = new Y.Doc();
  const map = doc.getMap<string>("trip");
  let applyingRemote = false;
  const provider = new WebrtcProvider(`italy-escape-${room}`, doc, {
    signaling: process.env.NEXT_PUBLIC_SIGNALING_URLS?.split(",").filter(Boolean),
  });
  const awarenessHandler = () => onPeers(provider.awareness.getStates().size);
  provider.awareness.on("change", awarenessHandler);
  map.observe(() => {
    const value = map.get("state");
    if (!value || applyingRemote) return;
    try { onRemoteState(JSON.parse(value) as TripState); } catch { /* Ignore malformed peer data. */ }
  });
  if (!map.has("state")) map.set("state", JSON.stringify(initial));
  return {
    publish(state) {
      applyingRemote = true;
      map.set("state", JSON.stringify(state));
      applyingRemote = false;
    },
    destroy() {
      provider.awareness.off("change", awarenessHandler);
      provider.destroy();
      doc.destroy();
    },
  };
}
