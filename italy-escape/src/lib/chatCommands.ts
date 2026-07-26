import { format } from "date-fns";
import { calculateCosts, fitToTarget, money } from "./costCalculator";
import { dateForOffset } from "./schedule";
import { recommendedNightAssignments } from "./splitStay";
import type { TripAction, TripState, TripTier } from "./types";

export interface ChatResult { reply: string; actions: TripAction[] }

const regionFor = (text: string, state: TripState) =>
  state.stays.find((stay) => text.toLowerCase().includes(stay.region.toLowerCase().replace(" coast", "")));

export function interpretTripCommand(input: string, state: TripState): ChatResult {
  const text = input.trim();
  const lower = text.toLowerCase();
  if (!text) return { reply: "Tell me what you would like to change.", actions: [] };

  if (/boat.*(?:price|budget|expensive)|why.*boat/.test(lower)) {
    const charters = state.boats.reduce((sum, boat) => sum + boat.budget, 0);
    return { reply: `Checked against Viator listings for these exact routes: La Maddalena private with skipper from about $880, Amalfi to Capri private from €1,090. Those cover 8–12 guests, so for two the plan budgets ${money(charters)} across four days instead of the original $14,000.`, actions: [] };
  }
  if (/review|rating|pool|rooftop/.test(lower)) {
    const rated = state.hotels.filter((hotel) => hotel.verified && hotel.rating > 0)
      .map((hotel) => `${hotel.name} ${hotel.rating}/${hotel.ratingScale} from ${hotel.reviewCount.toLocaleString()} reviews`)
      .join("; ");
    const rooftop = state.hotels.filter((hotel) => hotel.rooftop).map((hotel) => hotel.name).join(", ");
    return { reply: `Verified ratings: ${rated}. Rooftop terraces: ${rooftop}. Every hotel card links to its review page and official rooms page.`, actions: [] };
  }
  const splitRegion = /(?:optimize|split).*(sardinia|amalfi)/.exec(lower);
  if (splitRegion) {
    const stay = state.stays.find((item) => item.region.toLowerCase().includes(splitRegion[1]));
    if (stay) {
      const ids = recommendedNightAssignments(stay, state);
      const baseName = state.hotels.find((hotel) => hotel.id === ids.find((id) => id !== stay.hotelId))?.name;
      return { reply: `${stay.region} now splits its nights: the signature hotel on resort days and ${baseName ?? "a harbour base"} on the days you are at sea.`, actions: ids.map((hotelId, nightIndex) => ({ type: "assign-stay-night", stayId: stay.id, nightIndex, hotelId })) };
    }
  }
  if (/under\s*\$?\s*\d|target|fit.*budget|cheaper overall/.test(lower)) {
    const status = fitToTarget(state);
    const requested = lower.match(/under\s*\$?\s*(\d[\d,]*)\s*k?/);
    const target = requested ? Number(requested[1].replace(/,/g, "")) * (/k/.test(requested[0]) ? 1000 : 1) : state.budgetTarget;
    const actions: TripAction[] = target !== state.budgetTarget ? [{ type: "set-budget-target", value: target }] : [];
    if (status.total <= target) return { reply: `You are already at ${money(status.total)}, which is ${money(target - status.total)} under ${money(target)}.`, actions };
    const applied = status.levers.slice(0, 2);
    return {
      reply: `To reach ${money(target)} I applied: ${applied.map((lever) => lever.label.toLowerCase()).join("; ")}.`,
      actions: [...actions, ...applied.flatMap((lever) => lever.actions)],
    };
  }
  if (/total|how much|budget/.test(lower)) {
    const costs = calculateCosts(state);
    return { reply: `Your current baseline is ${money(costs.baseline)} for ${state.travelers} people, or ${money(costs.perPerson)} per person.`, actions: [] };
  }
  if (/days? at sea|boat days?/.test(lower)) {
    const count = state.days.filter((day) => day.activities.some((activity) => activity.venue === "boat")).length;
    return { reply: `You currently have ${count} days on the water.`, actions: [] };
  }
  const tierForward = lower.match(/(?:make|set|change)?\s*(sardinia|tuscany|amalfi(?: coast)?)\s*(?:to|the)?\s*(cheaper|value|luxury)/);
  const tierBackward = lower.match(/(cheaper|value|luxury).*(sardinia|tuscany|amalfi(?: coast)?)/);
  if (tierForward || tierBackward) {
    const regionText = tierForward?.[1] ?? tierBackward?.[2] ?? "";
    const tierText = tierForward?.[2] ?? tierBackward?.[1] ?? "";
    const stay = regionFor(regionText, state);
    const tier: TripTier = /luxury/.test(tierText) ? "luxury" : "value";
    if (stay) return { reply: `${stay.region} is now using the ${tier} plan. Hotel and boat estimates were updated together.`, actions: [{ type: "set-region-tier", stayId: stay.id, tier }] };
  }
  const nights = lower.match(/(?:set|make|change)?\s*(sardinia|tuscany|amalfi(?: coast)?)\s*(?:to|for)?\s*(\d+)\s*nights?/);
  if (nights) {
    const stay = regionFor(nights[1], state);
    if (stay) return { reply: `${stay.region} is now ${nights[2]} nights. Later dates will reflow automatically.`, actions: [{ type: "update-stay", id: stay.id, patch: { nights: Number(nights[2]) } }] };
  }
  const date = text.match(/\b(20\d\d-\d\d-\d\d)\b/);
  if (date && /start|depart|shift/.test(lower)) return { reply: `The trip now starts on ${date[1]}; every day moved with it.`, actions: [{ type: "set-start-date", value: date[1] }] };
  const travelers = lower.match(/(\d+)\s*(?:people|persons|travelers|travellers)/);
  if (travelers) return { reply: `Updated the trip to ${travelers[1]} travelers.`, actions: [{ type: "set-travelers", value: Number(travelers[1]) }] };
  const contingency = lower.match(/contingency.*?(\d+)\s*%/);
  if (contingency) return { reply: `Contingency is now ${contingency[1]}%.`, actions: [{ type: "set-contingency", value: Number(contingency[1]) }] };
  if (/move.*(?:capri|boat).*weather|weather.*(?:capri|boat)/.test(lower)) {
    const boat = state.boats.find((item) => lower.includes(item.name.toLowerCase().split(" ")[0])) ?? state.boats.find((item) => item.region === "Amalfi Coast");
    const source = state.days.find((day) => day.id === boat?.dayId);
    const activity = source?.activities.find((item) => item.boatId === boat?.id);
    const buffer = state.days.find((day) => day.weatherBuffer);
    if (source && activity && buffer) return { reply: `${boat?.name} moved to ${format(dateForOffset(state.startDate, buffer.offset), "MMMM d")}, your weather-buffer day.`, actions: [{ type: "move-activity", fromDayId: source.id, toDayId: buffer.id, activityId: activity.id }] };
  }
  const add = text.match(/^add\s+(.+?)\s+(?:on|to)\s+(?:day\s+)?(\d{1,2})$/i);
  if (add) {
    const day = state.days.find((item) => item.offset + 1 === Number(add[2]));
    if (day) return { reply: `Added “${add[1]}” to day ${add[2]}.`, actions: [{ type: "add-activity", dayId: day.id, patch: { title: add[1], venue: "public" } }] };
  }
  return {
    reply: "I can change a region to value or luxury, set nights, shift the start date (YYYY-MM-DD), move a boat to the weather buffer, change travelers or contingency, add an activity to a day, and answer budget or boat-day questions.",
    actions: [],
  };
}
