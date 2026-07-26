import type { BoatExcursion } from "@/lib/types";

/**
 * Budgets are anchored to public Viator listings for these exact routes, sized for a party
 * of two rather than the 8-12 guests those "per group" headline prices assume.
 */
export const boatTrips: BoatExcursion[] = [
  {
    id: "boat-sardinia-1", name: "La Maddalena & Caprera", region: "Sardinia", dayId: "day-4",
    departureTime: "09:30", returnTime: "17:30", vesselType: "Private RIB or day boat with skipper",
    captain: "", fuelIncluded: true, lunchArrangement: "Beach club lunch ashore", vegetarianRequired: true,
    weatherStatus: "forecast-pending", backupDayId: "day-3", budget: 1100, gratuity: 110, status: "idea",
    waypointIds: ["caprera", "cala-coticcio", "budelli", "spargi", "la-maddalena"],
    valueBudget: 620, valueVessel: "Private small boat, up to 6",
    priceSourceUrl: "https://www.viator.com/tours/Sardinia/Full-Day-Private-Tour-of-the-archipelago-of-La-Maddalena/d24293-415692P1",
    priceSourceName: "Viator", rating: 5, reviewCount: 53, verified: true,
    priceRationale: "Viator lists this private full-day skippered tour from about $880, with private catamarans near €1,300. $1,100 buys a comfortable private boat for two with fuel headroom.",
    excludes: ["La Maddalena national park fee", "Lunch ashore"],
  },
  {
    id: "boat-sardinia-2", name: "Mortorio, Molara & Tavolara", region: "Sardinia", dayId: "day-5",
    departureTime: "09:30", returnTime: "17:30", vesselType: "Private RIB with skipper",
    captain: "", fuelIncluded: true, lunchArrangement: "Lunch aboard", vegetarianRequired: true,
    weatherStatus: "forecast-pending", backupDayId: "day-3", budget: 1000, gratuity: 100, status: "idea",
    waypointIds: ["mortorio", "soffi", "molara", "tavolara"],
    valueBudget: 530, valueVessel: "Private small boat, up to 6",
    priceSourceUrl: "https://www.viator.com/tours/Sardinia/Private-Catamaran-Tour-in-the-Maddalena-Archipelago/d24293-28557P37",
    priceSourceName: "Viator", rating: 5, reviewCount: 22, verified: true,
    priceRationale: "A shorter run than the archipelago day. Comparable private skippered boats list from roughly $530 to $1,300, so $1,000 is mid-range rather than superyacht.",
    excludes: ["Tavolara marine reserve fee"],
  },
  {
    id: "boat-amalfi-1", name: "Capri & Faraglioni", region: "Amalfi Coast", dayId: "day-11",
    departureTime: "09:00", returnTime: "17:00", vesselType: "Private gozzo with skipper",
    captain: "", fuelIncluded: true, lunchArrangement: "Lunch on Capri", vegetarianRequired: true,
    weatherStatus: "forecast-pending", backupDayId: "day-13", budget: 1300, gratuity: 130, status: "idea",
    waypointIds: ["capri", "faraglioni"],
    valueBudget: 1090, valueVessel: "Private open boat, up to 5",
    priceSourceUrl: "https://www.viator.com/tours/Amalfi/Amalfi-to-Capri-Private-Boat-Tour/d33601-6405P22",
    priceSourceName: "Viator", rating: 4.9, reviewCount: 99, verified: true,
    priceRationale: "Viator's Amalfi-to-Capri private tour starts at €1,090 for up to five guests; larger boats reach €1,800. $1,300 covers a full day with a comfortable boat.",
    excludes: ["Capri docking fee, around €100", "Blue Grotto entry, around €18 each", "Lunch on Capri"],
  },
  {
    id: "boat-amalfi-2", name: "Positano & Nerano", region: "Amalfi Coast", dayId: "day-12",
    departureTime: "09:30", returnTime: "17:30", vesselType: "Private gozzo with skipper",
    captain: "", fuelIncluded: true, lunchArrangement: "Lunch in Nerano", vegetarianRequired: true,
    weatherStatus: "forecast-pending", backupDayId: "day-13", budget: 1150, gratuity: 115, status: "idea",
    waypointIds: ["conca", "furore", "praiano", "positano", "nerano"],
    valueBudget: 900, valueVessel: "Small-group coastal cruise",
    priceSourceUrl: "https://www.viator.com/tours/Positano/Capri-Private-Boat-Tour-from-Positano-or-Praiano-or-Amalfi/d33602-6439P6",
    priceSourceName: "Viator", rating: 5, reviewCount: 81, verified: true,
    priceRationale: "A coastal day stays local, so it prices below the Capri crossing. Published private gozzo days run roughly €950–€1,400.",
    excludes: ["Lunch in Nerano", "Marine park fees"],
  },
];
