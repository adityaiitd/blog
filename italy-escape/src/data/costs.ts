import type { CostCategory } from "@/lib/types";

export const costs: CostCategory[] = [
  { id: "hotels", name: "Hotels", amount: 22569, scenarioMultiplier: 1.2, color: "#8c7658", derived: "hotels" },
  { id: "boats", name: "Boat charters", amount: 14000, scenarioMultiplier: 1.15, color: "#447a7b", derived: "boats" },
  { id: "transport", name: "Ground transfers", amount: 2300, scenarioMultiplier: 1.15, color: "#9b624c", derived: "transport" },
  { id: "internal-flight", name: "Internal flight", amount: 700, scenarioMultiplier: 1.25, color: "#a99466" },
  { id: "train", name: "High-speed train", amount: 300, scenarioMultiplier: 1.2, color: "#6f7455" },
  { id: "restaurants", name: "Restaurants", amount: 6500, scenarioMultiplier: 1.3, color: "#ba795f" },
  { id: "spa", name: "Spa", amount: 2500, scenarioMultiplier: 1.35, color: "#8d6d83" },
  { id: "international", name: "International flights", amount: null, scenarioMultiplier: 1.2, color: "#557080" },
];
