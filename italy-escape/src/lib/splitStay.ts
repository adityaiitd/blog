import type { Stay, TripState } from "./types";

/**
 * Assigns each night of a stay to either a signature hotel or a harbour-side boat base,
 * so nights spent entirely at sea are not charged at resort rates.
 */
export function recommendedNightAssignments(stay: Stay, state: TripState): string[] {
  const regionHotels = state.hotels.filter((hotel) => hotel.region === stay.region);
  const signature = regionHotels.find((hotel) => hotel.role === "signature" && hotel.id === stay.hotelId)
    ?? regionHotels.find((hotel) => hotel.role === "signature" && hotel.recommended)
    ?? regionHotels.find((hotel) => hotel.role === "signature");
  const boatBase = regionHotels.filter((hotel) => hotel.role === "boat-base")
    .sort((a, b) => a.nightlyRate - b.nightlyRate)
    .find((hotel) => hotel.recommended) ?? regionHotels.find((hotel) => hotel.role === "boat-base");
  if (!signature) return Array(stay.nights).fill(stay.hotelId);
  if (!boatBase) return Array(stay.nights).fill(signature.id);

  const boatCount = Math.min(state.boats.filter((boat) => boat.region === stay.region).length, Math.max(0, stay.nights - 1));
  if (boatCount === 0) return Array(stay.nights).fill(signature.id);

  // Sardinia sails at the tail of the stay; Amalfi sails at the start, right after arrival.
  const boatsAtEnd = stay.region === "Sardinia";
  const cheapNights = boatsAtEnd ? boatCount : boatCount + 1;
  const nights = Array(stay.nights).fill(signature.id) as string[];
  for (let index = 0; index < Math.min(cheapNights, stay.nights); index++) {
    nights[boatsAtEnd ? stay.nights - 1 - index : index] = boatBase.id;
  }
  return nights;
}
