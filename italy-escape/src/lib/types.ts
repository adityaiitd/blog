export type DestinationKind = "airport" | "station" | "hotel" | "port" | "city";
export type TransportMode = "international-flight" | "internal-flight" | "private-car" | "train" | "boat";
export type BookingStatus = "idea" | "requested" | "booked";
export type RoomLevel = "entry" | "sea-view" | "suite";
export type WeatherStatus = "forecast-pending" | "go" | "watch" | "cancelled";
export type TripTier = "luxury" | "value";
/** Signature hotels earn resort days; boat bases keep money out of rooms you barely use. */
export type HotelRole = "signature" | "boat-base";

/** Real photographs served from the property's own CDN or its Booking.com listing. */
export interface HotelPhoto {
  url: string;
  caption: string;
  credit: string;
}

/** A bookable private charter with a published, checkable price. */
export interface BoatOption {
  id: string;
  operator: string;
  label: string;
  hours: number;
  price: number;
  priceNote: string;
  maxGuests: number;
  rating: number;
  reviewCount: number;
  reviewSource: string;
  url: string;
  includes: string[];
  excludes: string[];
  note?: string;
}
export type ActivityVenue = "hotel" | "boat" | "public" | "transit";
export type ActivityPurpose = "eat" | "see" | "walk" | "relax" | "travel" | "sail";

export interface Destination {
  id: string;
  name: string;
  shortName: string;
  kind: DestinationKind;
  lat: number;
  lng: number;
  region: string;
  image?: string;
  waypoint?: boolean;
}

export interface RouteLeg {
  id: string;
  fromId: string;
  toId: string;
  mode: TransportMode;
  departure?: string;
  arrival?: string;
  carrier?: string;
  details: string;
  cost: number;
  status: BookingStatus;
  cabin?: "economy" | "premium-economy" | "business";
  pricePerPerson?: number;
}

export interface Activity {
  id: string;
  title: string;
  time?: string;
  location?: string;
  duration?: string;
  cost: number;
  booked: boolean;
  confirmation?: string;
  notes?: string;
  weatherDependent: boolean;
  boatId?: string;
  venue: ActivityVenue;
  entryFee?: number;
  purpose: ActivityPurpose;
  rationale: string;
}

export interface ItineraryDay {
  id: string;
  offset: number;
  title: string;
  summary: string;
  locationId?: string;
  activities: Activity[];
  notes: string;
  weatherBuffer: boolean;
  booked: boolean;
}

export interface HotelOption {
  id: string;
  region: string;
  name: string;
  nightlyRate: number;
  roomMultipliers: Record<RoomLevel, number>;
  selectedRoom: RoomLevel;
  refundablePremium: number;
  taxRate: number;
  complimentaryNights: number;
  recommended?: boolean;
  tier: TripTier;
  officialUrl: string;
  roomsUrl: string;
  image: string;
  pools: string[];
  viewSummary: string;
  rooftop: boolean;
  waterfront: boolean;
  whyPick: string;
  roomRecommendation: string;
  rateNote: string;
  bestFor: string[];
  role: HotelRole;
  rating: number;
  ratingScale: 5 | 10;
  reviewCount: number;
  reviewSource: string;
  reviewUrl: string;
  verified: boolean;
  bookingUrl: string;
  photos: HotelPhoto[];
}

export interface Stay {
  id: string;
  region: string;
  destinationId: string;
  hotelId: string;
  nights: number;
  tier: TripTier;
  nightHotelIds?: string[];
}

export interface BoatExcursion {
  id: string;
  name: string;
  region: string;
  dayId: string;
  departureTime: string;
  captain: string;
  lunchArrangement: string;
  vegetarianRequired: boolean;
  weatherStatus: WeatherStatus;
  backupDayId?: string;
  gratuityPercent: number;
  status: BookingStatus;
  waypointIds: string[];
  priceRationale: string;
  options: BoatOption[];
  selectedOptionId: string;
}

export interface CostCategory {
  id: string;
  name: string;
  amount: number | null;
  scenarioMultiplier: number;
  color: string;
  derived?: "hotels" | "boats" | "transport" | "international-flights" | "taxes";
}

export interface TripState {
  schemaVersion: 1;
  title: string;
  startDate: string;
  travelers: number;
  destinations: Destination[];
  routeLegs: RouteLeg[];
  stays: Stay[];
  hotels: HotelOption[];
  days: ItineraryDay[];
  boats: BoatExcursion[];
  costs: CostCategory[];
  contingencyPercent: number;
  budgetTarget: number;
  taxSettings: {
    cityTaxPerPersonNight: number;
    boatVatPercent: number;
    diningServicePercent: number;
  };
}

export type ShareableTripState = TripState;

export interface TripVersion {
  id: string;
  name: string;
  createdAt: string;
  state: TripState;
  pinned?: boolean;
  summary?: string;
}

export type TripAction =
  | { type: "replace"; state: TripState }
  | { type: "set-start-date"; value: string }
  | { type: "set-title"; value: string }
  | { type: "set-travelers"; value: number }
  | { type: "update-day"; id: string; patch: Partial<ItineraryDay> }
  | { type: "add-activity"; dayId: string; patch?: Partial<Activity> }
  | { type: "update-activity"; dayId: string; activityId: string; patch: Partial<Activity> }
  | { type: "delete-activity"; dayId: string; activityId: string }
  | { type: "move-activity"; fromDayId: string; toDayId: string; activityId: string }
  | { type: "reorder-days"; activeId: string; overId: string }
  | { type: "update-stay"; id: string; patch: Partial<Stay> }
  | { type: "set-region-tier"; stayId: string; tier: TripTier }
  | { type: "assign-stay-night"; stayId: string; nightIndex: number; hotelId: string }
  | { type: "update-hotel"; id: string; patch: Partial<HotelOption> }
  | { type: "select-hotel"; stayId: string; hotelId: string }
  | { type: "add-hotel"; region: string }
  | { type: "delete-hotel"; id: string }
  | { type: "update-boat"; id: string; patch: Partial<BoatExcursion> }
  | { type: "update-cost"; id: string; patch: Partial<CostCategory> }
  | { type: "add-cost" }
  | { type: "delete-cost"; id: string }
  | { type: "set-contingency"; value: number }
  | { type: "set-budget-target"; value: number }
  | { type: "update-tax-settings"; patch: Partial<TripState["taxSettings"]> }
  | { type: "update-destination"; id: string; patch: Partial<Destination> }
  | { type: "add-destination"; patch?: Partial<Destination> }
  | { type: "delete-destination"; id: string }
  | { type: "update-route"; id: string; patch: Partial<RouteLeg> }
  | { type: "add-route" }
  | { type: "delete-route"; id: string };
