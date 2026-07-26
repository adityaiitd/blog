import type { Destination } from "@/lib/types";

export const destinations: Destination[] = [
  { id: "jfk", name: "John F. Kennedy International Airport", shortName: "JFK", kind: "airport", lat: 40.6413, lng: -73.7781, region: "New York" },
  { id: "olbia", name: "Olbia Costa Smeralda Airport", shortName: "Olbia", kind: "airport", lat: 40.8987, lng: 9.5176, region: "Sardinia" },
  { id: "cala-di-volpe", name: "Cala di Volpe", shortName: "Cala di Volpe", kind: "hotel", lat: 41.086, lng: 9.535, region: "Sardinia", image: "/images/cala-di-volpe.webp" },
  { id: "florence-airport", name: "Amerigo Vespucci Airport", shortName: "Florence Airport", kind: "airport", lat: 43.81, lng: 11.2051, region: "Tuscany" },
  { id: "como", name: "COMO Castello Del Nero", shortName: "Castello Del Nero", kind: "hotel", lat: 43.5571, lng: 11.1727, region: "Tuscany", image: "/images/tuscany.webp" },
  { id: "firenze-smn", name: "Firenze Santa Maria Novella", shortName: "Firenze S.M.N.", kind: "station", lat: 43.7765, lng: 11.2478, region: "Tuscany" },
  { id: "napoli-centrale", name: "Napoli Centrale", shortName: "Napoli Centrale", kind: "station", lat: 40.8522, lng: 14.2723, region: "Campania" },
  { id: "amalfi", name: "Amalfi", shortName: "Amalfi", kind: "port", lat: 40.634, lng: 14.6027, region: "Amalfi Coast", image: "/images/amalfi.webp" },
  { id: "naples-airport", name: "Naples International Airport", shortName: "Naples Airport", kind: "airport", lat: 40.886, lng: 14.2908, region: "Campania" },
  { id: "ewr", name: "Newark Liberty International Airport", shortName: "Newark", kind: "airport", lat: 40.6895, lng: -74.1745, region: "New York" },
];
