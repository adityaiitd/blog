import type { BoatExcursion, BoatOption } from "@/lib/types";

/**
 * Private charters only, priced per boat for two guests, from operators' own published
 * 2026 rates. Euro prices are converted at 1.08; the original figure is kept on each option.
 */
const eur = (amount: number) => Math.round(amount * 1.08);

const laMaddalena: BoatOption[] = [
  {
    id: "holidoit-full", operator: "Holidoit · private dinghy day", label: "Full day · 7 hours", hours: 7,
    price: eur(1100), priceNote: "€1,100 per boat, 1–13 September rate", maxGuests: 8,
    rating: 5, reviewCount: 28, reviewSource: "Holidoit",
    url: "https://www.holidoit.com/en/e/tour-gommone-giornaliero-arcipelago-la-maddalena-da-palau",
    includes: ["Private skipper", "Fuel", "National park fee", "Sardinian aperitif", "Snorkel gear"],
    excludes: ["Lunch"],
  },
  {
    id: "datourist-half", operator: "DaTourist · private gommone", label: "Half day · 4 hours", hours: 4,
    price: eur(400), priceNote: "€400 per boat, 24 Aug – 7 Sep rate, fuel included", maxGuests: 8,
    rating: 0, reviewCount: 0, reviewSource: "Operator site",
    url: "https://www.datourist.net/product/da-palau-escursione-privata-in-gommone-nellarcipelago-di-la-maddalena-2/",
    includes: ["Private skipper", "Fuel", "Swim stops"],
    excludes: ["Park fee", "Lunch"],
    note: "The operator publishes a full seasonal price list, so this figure is easy to confirm.",
  },
  {
    id: "boating-sardinia", operator: "Boating Sardinia · Captain Carlo", label: "Full day with lunch aboard", hours: 8,
    price: 1213, priceNote: "From about $1,213 per boat, up to 6 guests", maxGuests: 6,
    rating: 5, reviewCount: 111, reviewSource: "Viator & Tripadvisor",
    url: "https://www.viator.com/tours/Sardinia/Full-Day-Private-Tour-of-the-archipelago-of-La-Maddalena/d24293-415692P1",
    includes: ["Private skipper", "Lunch aboard with wine", "Snorkel gear", "Customised route"],
    excludes: ["Park fee"],
    note: "100% five-star across 111 reviews; reviewers single out Carlo by name.",
  },
  {
    id: "holidoit-exclusive", operator: "Holidoit · luxury dinghy", label: "Full day · 7.5 hours, premium boat", hours: 7.5,
    price: eur(1500), priceNote: "€1,500 per boat, September rate", maxGuests: 8,
    rating: 5, reviewCount: 57, reviewSource: "Holidoit",
    url: "https://www.holidoit.com/en/e/escursione-esclusiva-in-gommone-di-lusso",
    includes: ["Private skipper", "Fuel", "Park fee", "Aperitif", "Snorkel gear"],
    excludes: ["Lunch"],
  },
];

const tavolara: BoatOption[] = [
  {
    id: "datourist-half-2", operator: "DaTourist · private gommone", label: "Half day · 4 hours", hours: 4,
    price: eur(400), priceNote: "€400 per boat, 24 Aug – 7 Sep rate, fuel included", maxGuests: 8,
    rating: 0, reviewCount: 0, reviewSource: "Operator site",
    url: "https://www.datourist.net/product/da-palau-escursione-privata-in-gommone-nellarcipelago-di-la-maddalena-2/",
    includes: ["Private skipper", "Fuel", "Swim stops"],
    excludes: ["Park fee", "Lunch"],
  },
  {
    id: "escursi-half", operator: "Escursì · private gommone", label: "Half day, morning or afternoon", hours: 4,
    price: eur(450), priceNote: "€450 per boat, up to 8 guests", maxGuests: 8,
    rating: 0, reviewCount: 0, reviewSource: "Operator site",
    url: "https://www.escursi.com/esperienze/gite-in-barca/palau-tour-privato-gommone-arcipelago-maddalena",
    includes: ["Private skipper", "Clubman 26 or Lomac dinghy", "Swim stops"],
    excludes: ["Fuel surcharge on longer routes", "Lunch"],
  },
  {
    id: "seapassion-private", operator: "Sea Passion · private tour", label: "Custom duration, max 6 aboard", hours: 4,
    price: eur(420), priceNote: "€250–600 depending on boat and season", maxGuests: 6,
    rating: 0, reviewCount: 0, reviewSource: "Operator site",
    url: "https://seapassion.it/noleggio-tour-in-gommone-palau-arcipelago-la-maddalena/",
    includes: ["Private skipper", "Park fee", "Insurance", "Custom itinerary"],
    excludes: ["Fuel"],
  },
];

const capri: BoatOption[] = [
  {
    id: "waves-of-capri", operator: "Waves of Capri · skipper Enzo", label: "Half day · 4 hours around Capri", hours: 4,
    price: eur(379), priceNote: "€379 per boat, max 6 guests", maxGuests: 6,
    rating: 0, reviewCount: 0, reviewSource: "Capri.com",
    url: "https://www.capri.com/en/s/SU938",
    includes: ["Private skipper", "Faraglioni, Green and White grottoes", "Swim stops", "Towels and snorkel masks", "Fuel"],
    excludes: ["Ferry from Amalfi, about €25 each", "Blue Grotto entry"],
    note: "Taking the ferry across and chartering on Capri costs far less than a private crossing from Amalfi, and gives you more time on the water.",
  },
  {
    id: "vincenzo-capri", operator: "Vincenzo Capri Boats", label: "Traditional gozzo · 2 to 6 hours", hours: 3,
    price: eur(300), priceNote: "From €300 per boat, max 6 guests", maxGuests: 6,
    rating: 0, reviewCount: 0, reviewSource: "Capri.com",
    url: "https://www.capri.com/en/s/SYL5W",
    includes: ["Private skipper", "Blue Grotto stop on 3h+ tours", "Swim stops", "Fuel and insurance"],
    excludes: ["Ferry from Amalfi", "Blue Grotto ticket"],
  },
  {
    id: "amazing-capri", operator: "Amazing Capri Tour · skipper Paolo", label: "Half day · 4 hours", hours: 4,
    price: eur(420), priceNote: "€420 per boat, max 6 guests", maxGuests: 6,
    rating: 0, reviewCount: 0, reviewSource: "Operator site",
    url: "https://amazingcapritour.com/tours/",
    includes: ["Private skipper", "Sail around the island", "Blue Grotto optional", "Swim stops"],
    excludes: ["Ferry from Amalfi", "Blue Grotto ticket"],
  },
  {
    id: "viator-amalfi-capri", operator: "Private charter direct from Amalfi", label: "Full day, no ferry needed", hours: 6,
    price: eur(1090), priceNote: "From €1,090 per boat, up to 5 guests", maxGuests: 5,
    rating: 4.9, reviewCount: 99, reviewSource: "Viator",
    url: "https://www.viator.com/tours/Amalfi/Amalfi-to-Capri-Private-Boat-Tour/d33601-6405P22",
    includes: ["Private skipper", "Departs Amalfi's Darsena pier", "Refreshments", "Swim stops"],
    excludes: ["Capri docking fee, about €100", "Blue Grotto entry"],
    note: "The convenient option: step aboard in Amalfi. You pay roughly triple for the crossing itself.",
  },
];

const amalfiCoast: BoatOption[] = [
  {
    id: "positano-boat-tour-half", operator: "Positano Boat Tour", label: "Half day · 4 hours, traditional gozzo", hours: 4,
    price: eur(768), priceNote: "€768 per boat, max 10 guests", maxGuests: 10,
    rating: 4.99, reviewCount: 0, reviewSource: "Positano.com",
    url: "https://www.positano.com/en/s/SMFAE",
    includes: ["Private local skipper", "Furore Fjord and Pandora Grotto", "Swim stops", "Drinks aboard", "Fuel"],
    excludes: ["Lunch ashore"],
  },
  {
    id: "positanoboats-nerano", operator: "Positano Boats", label: "Half day · Amalfi, Nerano and Li Galli", hours: 4,
    price: eur(1000), priceNote: "From €1,000 per boat, max 12 guests", maxGuests: 12,
    rating: 0, reviewCount: 0, reviewSource: "Operator site",
    url: "https://www.positanoboats.info/en/private-tours/amalfi-nerano-and-li-galli",
    includes: ["Private skipper", "Water, soft drinks, beer and Prosecco", "Swim stops"],
    excludes: ["Lunch in Nerano"],
    note: "Departures available from Praiano's Marina di Praia, the cove directly below Onda Verde.",
  },
  {
    id: "misal-full", operator: "Misal Sorrento Charter", label: "Full day · 7 hours, Positano and Nerano", hours: 7,
    price: eur(1200), priceNote: "Quoted on request; comparable boats run €1,000–1,400", maxGuests: 8,
    rating: 0, reviewCount: 0, reviewSource: "Operator site",
    url: "https://www.misalcharter.com/en/positano-and-nerano",
    includes: ["English-speaking skipper", "Li Galli, Crapolla fjord, Isca", "Lunch stop in Nerano"],
    excludes: ["Lunch"],
  },
];

export const boatTrips: BoatExcursion[] = [
  {
    id: "boat-sardinia-1", name: "La Maddalena & Caprera", region: "Sardinia", dayId: "day-4",
    departureTime: "09:30", captain: "", lunchArrangement: "Beach club lunch ashore", vegetarianRequired: true,
    weatherStatus: "forecast-pending", backupDayId: "day-3", gratuityPercent: 10, status: "idea",
    waypointIds: ["caprera", "cala-coticcio", "budelli", "spargi", "la-maddalena"],
    options: laMaddalena, selectedOptionId: "holidoit-full",
    priceRationale: "The one day worth a full seven hours: the western islands are far enough out that a half day would rush them.",
  },
  {
    id: "boat-sardinia-2", name: "Mortorio, Molara & Tavolara", region: "Sardinia", dayId: "day-5",
    departureTime: "09:30", captain: "", lunchArrangement: "Lunch aboard", vegetarianRequired: true,
    weatherStatus: "forecast-pending", backupDayId: "day-3", gratuityPercent: 10, status: "idea",
    waypointIds: ["mortorio", "soffi", "molara", "tavolara"],
    options: tavolara, selectedOptionId: "datourist-half",
    priceRationale: "These islands sit close to shore, so four hours covers them comfortably and leaves the afternoon free.",
  },
  {
    id: "boat-amalfi-1", name: "Capri & Faraglioni", region: "Amalfi Coast", dayId: "day-11",
    departureTime: "09:00", captain: "", lunchArrangement: "Lunch on Capri", vegetarianRequired: true,
    weatherStatus: "forecast-pending", backupDayId: "day-13", gratuityPercent: 10, status: "idea",
    waypointIds: ["capri", "faraglioni"],
    options: capri, selectedOptionId: "waves-of-capri",
    priceRationale: "Ferry over, then charter on the island. You skip paying a skipper to make the crossing twice.",
  },
  {
    id: "boat-amalfi-2", name: "Positano & Nerano", region: "Amalfi Coast", dayId: "day-12",
    departureTime: "09:30", captain: "", lunchArrangement: "Lunch in Nerano", vegetarianRequired: true,
    weatherStatus: "forecast-pending", backupDayId: "day-13", gratuityPercent: 10, status: "idea",
    waypointIds: ["conca", "furore", "praiano", "positano", "nerano"],
    options: amalfiCoast, selectedOptionId: "positano-boat-tour-half",
    priceRationale: "A local coastal run, so a half day is plenty and the boat leaves from the cove below your hotel.",
  },
];
