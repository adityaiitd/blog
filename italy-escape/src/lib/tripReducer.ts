import { reorderDays } from "./schedule";
import type { Activity, CostCategory, Destination, HotelOption, RouteLeg, TripAction, TripState } from "./types";

const uid = (prefix: string) => `${prefix}-${Math.random().toString(36).slice(2, 9)}`;
const clamp = (value: number, min = 0, max = 1_000_000) =>
  Math.min(max, Math.max(min, Number.isFinite(value) ? value : min));

export function tripReducer(state: TripState, action: TripAction): TripState {
  switch (action.type) {
    case "replace": return structuredClone(action.state);
    case "set-start-date": return { ...state, startDate: action.value };
    case "set-title": return { ...state, title: action.value };
    case "set-travelers": return { ...state, travelers: clamp(action.value, 1, 20) };
    case "update-day":
      return { ...state, days: state.days.map((day) => day.id === action.id ? { ...day, ...action.patch } : day) };
    case "add-activity": {
      const activity: Activity = { id: uid("activity"), title: "New activity", cost: 0, booked: false, weatherDependent: false, venue: "public", entryFee: 0, purpose: "see", rationale: "A flexible addition to shape around your energy.", ...action.patch };
      return { ...state, days: state.days.map((day) => day.id === action.dayId ? { ...day, activities: [...day.activities, activity] } : day) };
    }
    case "update-activity":
      return { ...state, days: state.days.map((day) => day.id === action.dayId ? { ...day, activities: day.activities.map((activity) => activity.id === action.activityId ? { ...activity, ...action.patch } : activity) } : day) };
    case "delete-activity":
      return { ...state, days: state.days.map((day) => day.id === action.dayId ? { ...day, activities: day.activities.filter((activity) => activity.id !== action.activityId) } : day) };
    case "move-activity": {
      const source = state.days.find((day) => day.id === action.fromDayId);
      const moved = source?.activities.find((activity) => activity.id === action.activityId);
      if (!moved) return state;
      const days = state.days.map((day) => {
        if (day.id === action.fromDayId) return { ...day, activities: day.activities.filter((activity) => activity.id !== action.activityId) };
        if (day.id === action.toDayId) return { ...day, activities: [...day.activities, moved] };
        return day;
      });
      return {
        ...state,
        days,
        boats: moved.boatId ? state.boats.map((boat) => boat.id === moved.boatId ? { ...boat, dayId: action.toDayId } : boat) : state.boats,
      };
    }
    case "reorder-days": return { ...state, days: reorderDays(state.days, action.activeId, action.overId) };
    case "update-stay": {
      const current = state.stays.find((stay) => stay.id === action.id);
      if (!current) return state;
      const nextNights = action.patch.nights === undefined ? current.nights : clamp(action.patch.nights, 0, 30);
      const stays = state.stays.map((stay) => {
        if (stay.id !== action.id) return stay;
        const nightHotelIds = (stay.nightHotelIds ?? Array(stay.nights).fill(stay.hotelId)).slice(0, nextNights);
        while (nightHotelIds.length < nextNights) nightHotelIds.push(stay.hotelId);
        return { ...stay, ...action.patch, nights: nextNights, nightHotelIds };
      });
      const delta = nextNights - current.nights;
      if (!delta) return { ...state, stays };
      const stayIndex = state.stays.findIndex((stay) => stay.id === action.id);
      const oldBoundary = 1 + state.stays.slice(0, stayIndex + 1).reduce((sum, stay) => sum + stay.nights, 0);
      const days = [...state.days];
      if (delta > 0) {
        for (let index = 0; index < delta; index++) {
          days.splice(oldBoundary + index, 0, {
            id: uid("day"), offset: 0, title: `Open day in ${current.region}`,
            summary: "A new day to shape together.", locationId: current.destinationId,
            activities: [], notes: "", weatherBuffer: false, booked: false,
          });
        }
      } else {
        for (let index = 0; index < Math.abs(delta); index++) {
          const searchEnd = Math.min(oldBoundary - index, days.length - 1);
          let removeAt = -1;
          for (let candidate = searchEnd - 1; candidate > 0; candidate--) {
            const day = days[candidate];
            if (day.locationId === current.destinationId && !day.activities.some((activity) => activity.boatId)) { removeAt = candidate; break; }
          }
          if (removeAt > 0) days.splice(removeAt, 1);
        }
      }
      return { ...state, stays, days: days.map((day, offset) => ({ ...day, offset })) };
    }
    case "assign-stay-night":
      return {
        ...state,
        stays: state.stays.map((stay) => {
          if (stay.id !== action.stayId) return stay;
          const assignments = stay.nightHotelIds?.slice(0, stay.nights) ?? Array(stay.nights).fill(stay.hotelId);
          while (assignments.length < stay.nights) assignments.push(stay.hotelId);
          assignments[action.nightIndex] = action.hotelId;
          return { ...stay, nightHotelIds: assignments };
        }),
      };
    case "set-region-tier": {
      const stay = state.stays.find((candidate) => candidate.id === action.stayId);
      if (!stay) return state;
      const hotel = state.hotels.find((candidate) => candidate.region === stay.region && candidate.tier === action.tier && candidate.recommended)
        ?? state.hotels.find((candidate) => candidate.region === stay.region && candidate.tier === action.tier);
      return {
        ...state,
        stays: state.stays.map((candidate) => candidate.id === action.stayId
          ? { ...candidate, tier: action.tier, hotelId: hotel?.id ?? candidate.hotelId, nightHotelIds: Array(candidate.nights).fill(hotel?.id ?? candidate.hotelId) }
          : candidate),
      };
    }
    case "update-hotel":
      return { ...state, hotels: state.hotels.map((hotel) => hotel.id === action.id ? { ...hotel, ...action.patch, nightlyRate: action.patch.nightlyRate === undefined ? hotel.nightlyRate : clamp(action.patch.nightlyRate) } : hotel) };
    case "select-hotel":
      return { ...state, stays: state.stays.map((stay) => {
        if (stay.id !== action.stayId) return stay;
        const tier = state.hotels.find((hotel) => hotel.id === action.hotelId)?.tier ?? stay.tier;
        return { ...stay, hotelId: action.hotelId, tier, nightHotelIds: Array(stay.nights).fill(action.hotelId) };
      }) };
    case "add-hotel": {
      const hotel: HotelOption = { id: uid("hotel"), region: action.region, name: "New hotel option", nightlyRate: 1000, roomMultipliers: { entry: 1, "sea-view": 1.25, suite: 1.75 }, selectedRoom: "entry", refundablePremium: 0, taxRate: 0, complimentaryNights: 0, tier: "luxury", officialUrl: "", roomsUrl: "", image: action.region === "Sardinia" ? "/images/costa-smeralda.webp" : action.region === "Tuscany" ? "/images/tuscany.webp" : "/images/amalfi.webp", pools: [], viewSummary: "Add view details", rooftop: false, waterfront: false, whyPick: "Add why this hotel belongs in the plan.", roomRecommendation: "Add a room recommendation", rateNote: "Verify the live rate directly.", bestFor: [] };
      return { ...state, hotels: [...state.hotels, hotel] };
    }
    case "delete-hotel":
      return state.stays.some((stay) => stay.hotelId === action.id) ? state : { ...state, hotels: state.hotels.filter((hotel) => hotel.id !== action.id) };
    case "update-boat":
      return { ...state, boats: state.boats.map((boat) => boat.id === action.id ? { ...boat, ...action.patch } : boat) };
    case "update-cost":
      return { ...state, costs: state.costs.map((cost) => cost.id === action.id ? { ...cost, ...action.patch, amount: action.patch.amount === undefined ? cost.amount : action.patch.amount === null ? null : clamp(action.patch.amount) } : cost) };
    case "add-cost": {
      const cost: CostCategory = { id: uid("cost"), name: "New category", amount: 0, scenarioMultiplier: 1.2, color: "#80766a" };
      return { ...state, costs: [...state.costs, cost] };
    }
    case "delete-cost": return { ...state, costs: state.costs.filter((cost) => cost.id !== action.id) };
    case "set-contingency": return { ...state, contingencyPercent: clamp(action.value, 0, 100) };
    case "update-tax-settings": return { ...state, taxSettings: { ...state.taxSettings, ...action.patch } };
    case "update-destination":
      return { ...state, destinations: state.destinations.map((destination) => destination.id === action.id ? { ...destination, ...action.patch } : destination) };
    case "add-destination": {
      const destination: Destination = { id: uid("place"), name: "New destination", shortName: "New stop", kind: "city", lat: 42, lng: 12, region: "Italy", ...action.patch };
      return { ...state, destinations: [...state.destinations, destination] };
    }
    case "delete-destination":
      return { ...state, destinations: state.destinations.filter((destination) => destination.id !== action.id), routeLegs: state.routeLegs.filter((leg) => leg.fromId !== action.id && leg.toId !== action.id) };
    case "update-route":
      return { ...state, routeLegs: state.routeLegs.map((route) => route.id === action.id ? { ...route, ...action.patch } : route) };
    case "add-route": {
      const first = state.destinations.at(0)?.id ?? "";
      const last = state.destinations.at(-1)?.id ?? "";
      const leg: RouteLeg = { id: uid("route"), fromId: first, toId: last, mode: "private-car", details: "New route leg", cost: 0, status: "idea" };
      return { ...state, routeLegs: [...state.routeLegs, leg] };
    }
    case "delete-route": return { ...state, routeLegs: state.routeLegs.filter((route) => route.id !== action.id) };
    default: return state;
  }
}
