"use client";

import type { TripState, TripVersion } from "./types";

export interface CollaborationSession {
  destroy: () => void;
  publish: (state: TripState) => void;
  publishVersions: (versions: TripVersion[]) => void;
}

interface CollaborationHandlers {
  onRemoteState: (state: TripState) => void;
  onRemoteVersions: (versions: TripVersion[]) => void;
  onPeers: (count: number) => void;
}

/**
 * Optional peer-to-peer sync so both of you edit and save the same trip from a shared link.
 * The app is fully usable if signalling is unavailable; it simply falls back to solo editing.
 */
export async function connectCollaboration(
  room: string,
  initial: TripState,
  handlers: CollaborationHandlers,
): Promise<CollaborationSession> {
  const Y = await import("yjs");
  const { WebrtcProvider } = await import("y-webrtc");
  const doc = new Y.Doc();
  const map = doc.getMap<string>("trip");
  let applyingLocal = false;
  const provider = new WebrtcProvider(`italy-escape-${room}`, doc, {
    signaling: process.env.NEXT_PUBLIC_SIGNALING_URLS?.split(",").filter(Boolean),
  });

  const awarenessHandler = () => handlers.onPeers(provider.awareness.getStates().size);
  provider.awareness.on("change", awarenessHandler);

  map.observe((event) => {
    if (applyingLocal) return;
    if (event.keysChanged.has("state")) {
      const value = map.get("state");
      if (value) { try { handlers.onRemoteState(JSON.parse(value) as TripState); } catch { /* Ignore malformed peer data. */ } }
    }
    if (event.keysChanged.has("versions")) {
      const value = map.get("versions");
      if (value) { try { handlers.onRemoteVersions(JSON.parse(value) as TripVersion[]); } catch { /* Ignore malformed peer data. */ } }
    }
  });

  if (!map.has("state")) map.set("state", JSON.stringify(initial));

  const write = (key: string, value: unknown) => {
    applyingLocal = true;
    map.set(key, JSON.stringify(value));
    applyingLocal = false;
  };

  return {
    publish: (state) => write("state", state),
    publishVersions: (versions) => write("versions", versions),
    destroy() {
      provider.awareness.off("change", awarenessHandler);
      provider.destroy();
      doc.destroy();
    },
  };
}
