import type { RouteLeg } from "@/lib/types";

export const routeLegs: RouteLeg[] = [
  { id: "r1", fromId: "jfk", toId: "olbia", mode: "international-flight", departure: "20:00", arrival: "12:00", carrier: "", details: "Overnight economy flight", cost: 0, status: "idea", cabin: "economy", pricePerPerson: 575 },
  { id: "r2", fromId: "olbia", toId: "cala-di-volpe", mode: "private-car", details: "Private airport transfer · 35 min", cost: 250, status: "idea" },
  { id: "r3", fromId: "cala-di-volpe", toId: "olbia", mode: "private-car", details: "Private airport transfer", cost: 250, status: "idea" },
  { id: "r4", fromId: "olbia", toId: "florence-airport", mode: "internal-flight", details: "Olbia to Florence", cost: 700, status: "idea", cabin: "economy", pricePerPerson: 350 },
  { id: "r5", fromId: "florence-airport", toId: "como", mode: "private-car", details: "Private transfer · 45 min", cost: 250, status: "idea" },
  { id: "r6", fromId: "como", toId: "firenze-smn", mode: "private-car", details: "Private transfer to station", cost: 250, status: "idea" },
  { id: "r7", fromId: "firenze-smn", toId: "napoli-centrale", mode: "train", details: "Frecciarossa · Business class", cost: 300, status: "idea" },
  { id: "r8", fromId: "napoli-centrale", toId: "amalfi", mode: "private-car", details: "Private transfer · 90 min", cost: 450, status: "idea" },
  { id: "r9", fromId: "amalfi", toId: "naples-airport", mode: "private-car", details: "Private airport transfer", cost: 550, status: "idea" },
  { id: "r10", fromId: "naples-airport", toId: "ewr", mode: "international-flight", details: "Nonstop economy flight to Newark", cost: 0, status: "idea", cabin: "economy", pricePerPerson: 575 },
];
