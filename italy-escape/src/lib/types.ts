export type DestinationKind = "airport" | "station" | "hotel" | "port" | "city";
export type TransportMode = "international-flight" | "internal-flight" | "private-car" | "train" | "boat";
export type BookingStatus = "idea" | "requested" | "booked";
export type RoomLevel = "entry" | "sea-view" | "suite";
export type WeatherStatus = "forecast-pending" | "go" | "watch" | "cancelled";

export interface Destination {
  id: string;
  name: string;
  shortName: string;
  kind: DestinationKind;
  lat: number;
  lng: number;
  region: string;
  image?: string;
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
}

export interface Stay {
  id: string;
  region: string;
  destinationId: string;
  hotelId: string;
  nights: number;
}

export interface BoatExcursion {
  id: string;
  name: string;
  region: string;
  dayId: string;
  departureTime: string;
  returnTime: string;
  vesselType: string;
  captain: string;
  fuelIncluded: boolean;
  lunchArrangement: string;
  vegetarianRequired: boolean;
  weatherStatus: WeatherStatus;
  backupDayId?: string;
  budget: number;
  gratuity: number;
  status: BookingStatus;
}

export interface CostCategory {
  id: string;
  name: string;
  amount: number | null;
  scenarioMultiplier: number;
  color: string;
  derived?: "hotels" | "boats" | "transport";
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
}

export type ShareableTripState = TripState;

export interface TripVersion {
  id: string;
  name: string;
  createdAt: string;
  state: TripState;
}

export type TripAction =
  | { type: "replace"; state: TripState }
  | { type: "set-start-date"; value: string }
  | { type: "set-title"; value: string }
  | { type: "set-travelers"; value: number }
  | { type: "update-day"; id: string; patch: Partial<ItineraryDay> }
  | { type: "add-activity"; dayId: string }
  | { type: "update-activity"; dayId: string; activityId: string; patch: Partial<Activity> }
  | { type: "delete-activity"; dayId: string; activityId: string }
  | { type: "move-activity"; fromDayId: string; toDayId: string; activityId: string }
  | { type: "reorder-days"; activeId: string; overId: string }
  | { type: "update-stay"; id: string; patch: Partial<Stay> }
  | { type: "update-hotel"; id: string; patch: Partial<HotelOption> }
  | { type: "select-hotel"; stayId: string; hotelId: string }
  | { type: "add-hotel"; region: string }
  | { type: "delete-hotel"; id: string }
  | { type: "update-boat"; id: string; patch: Partial<BoatExcursion> }
  | { type: "update-cost"; id: string; patch: Partial<CostCategory> }
  | { type: "add-cost" }
  | { type: "delete-cost"; id: string }
  | { type: "set-contingency"; value: number }
  | { type: "update-destination"; id: string; patch: Partial<Destination> }
  | { type: "add-destination"; patch?: Partial<Destination> }
  | { type: "delete-destination"; id: string }
  | { type: "update-route"; id: string; patch: Partial<RouteLeg> }
  | { type: "add-route" }
  | { type: "delete-route"; id: string };
