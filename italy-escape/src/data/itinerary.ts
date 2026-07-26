import type { Activity, ItineraryDay } from "@/lib/types";

const a = (id: string, title: string, extras: Partial<Activity> = {}): Activity => ({
  id, title, cost: 0, booked: false, weatherDependent: false,
  venue: extras.boatId ? "boat" : /flight|transfer|train|car to/i.test(title) ? "transit" : /hotel|pool|spa|resort/i.test(title) ? "hotel" : "public",
  entryFee: 0,
  ...extras,
});

export const itinerary: ItineraryDay[] = [
  { id: "day-0", offset: 0, title: "Departure", summary: "Overnight JFK to Olbia flight", locationId: "jfk", notes: "", weatherBuffer: false, booked: false, activities: [a("a-0", "Overnight flight to Olbia", { time: "Evening", location: "JFK", booked: false })] },
  { id: "day-1", offset: 1, title: "Arrive in Sardinia", summary: "Private transfer to Cala di Volpe, resort afternoon", locationId: "cala-di-volpe", notes: "", weatherBuffer: false, booked: false, activities: [a("a-1a", "Private airport transfer", { location: "Olbia → Cala di Volpe" }), a("a-1b", "Resort afternoon")] },
  { id: "day-2", offset: 2, title: "The Costa Smeralda", summary: "Beach day and Porto Cervo evening", locationId: "cala-di-volpe", notes: "", weatherBuffer: false, booked: false, activities: [a("a-2a", "Capriccioli or Liscia Ruja", { weatherDependent: true }), a("a-2b", "Porto Cervo evening")] },
  { id: "day-3", offset: 3, title: "La Maddalena by sea", summary: "Caprera, Cala Coticcio, Budelli, Spargi and La Maddalena", locationId: "cala-di-volpe", notes: "", weatherBuffer: false, booked: false, activities: [a("a-3", "Private boat: La Maddalena & Caprera", { weatherDependent: true, boatId: "boat-sardinia-1" })] },
  { id: "day-4", offset: 4, title: "San Pantaleo", summary: "Village morning, hotel pool and spa", locationId: "cala-di-volpe", notes: "", weatherBuffer: false, booked: false, activities: [a("a-4a", "San Pantaleo morning"), a("a-4b", "Pool and spa")] },
  { id: "day-5", offset: 5, title: "Islands to the south", summary: "Mortorio, Soffi, Molara and Tavolara", locationId: "cala-di-volpe", notes: "", weatherBuffer: false, booked: false, activities: [a("a-5", "Private boat: Mortorio to Tavolara", { weatherDependent: true, boatId: "boat-sardinia-2" })] },
  { id: "day-6", offset: 6, title: "Sardinia to Tuscany", summary: "Fly Olbia to Florence, transfer to Castello Del Nero", locationId: "como", notes: "", weatherBuffer: false, booked: false, activities: [a("a-6a", "Flight to Florence"), a("a-6b", "Private transfer to COMO")] },
  { id: "day-7", offset: 7, title: "Chianti", summary: "Hotel morning and half-day winery excursion", locationId: "como", notes: "", weatherBuffer: false, booked: false, activities: [a("a-7a", "Slow hotel morning"), a("a-7b", "Private Chianti winery visit")] },
  { id: "day-8", offset: 8, title: "Florence", summary: "Private guided day in Florence", locationId: "como", notes: "", weatherBuffer: false, booked: false, activities: [a("a-8", "Private guided Florence day", { location: "Florence" })] },
  { id: "day-9", offset: 9, title: "Val d’Orcia", summary: "Siena, Pienza, Val d’Orcia and Montalcino", locationId: "como", notes: "", weatherBuffer: false, booked: false, activities: [a("a-9", "Private Val d’Orcia touring day")] },
  { id: "day-10", offset: 10, title: "Tuscany to Amalfi", summary: "Car to Florence, high-speed train to Naples, private car to Amalfi", locationId: "amalfi", notes: "", weatherBuffer: false, booked: false, activities: [a("a-10a", "Car to Firenze S.M.N."), a("a-10b", "High-speed train to Naples"), a("a-10c", "Private car to Amalfi")] },
  { id: "day-11", offset: 11, title: "Capri", summary: "Faraglioni, swimming and a short Capri visit", locationId: "amalfi", notes: "", weatherBuffer: false, booked: false, activities: [a("a-11", "Private boat: Capri & Faraglioni", { weatherDependent: true, boatId: "boat-amalfi-1" })] },
  { id: "day-12", offset: 12, title: "Amalfi & Ravello", summary: "Amalfi morning, Ravello afternoon, drinks at Caruso", locationId: "amalfi", notes: "", weatherBuffer: false, booked: false, activities: [a("a-12a", "Amalfi morning"), a("a-12b", "Ravello and Caruso", { time: "Afternoon" })] },
  { id: "day-13", offset: 13, title: "A day held open", summary: "Unstructured hotel, pool and spa day", locationId: "amalfi", notes: "Reserved as a weather backup for a boat excursion.", weatherBuffer: true, booked: false, activities: [a("a-13", "Pool and spa day")] },
  { id: "day-14", offset: 14, title: "The Amalfi Coast by sea", summary: "Conca dei Marini, Furore, Praiano, Positano and Nerano", locationId: "amalfi", notes: "", weatherBuffer: false, booked: false, activities: [a("a-14", "Private boat: Positano & Nerano", { weatherDependent: true, boatId: "boat-amalfi-2" })] },
  { id: "day-15", offset: 15, title: "Homeward", summary: "Private car to Naples Airport and nonstop flight to Newark", locationId: "naples-airport", notes: "", weatherBuffer: false, booked: false, activities: [a("a-15a", "Private transfer to Naples Airport"), a("a-15b", "Nonstop flight to Newark")] },
];
