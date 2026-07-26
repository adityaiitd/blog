import type { HotelOption, Stay } from "@/lib/types";

const roomMultipliers = { entry: 1, "sea-view": 1.25, suite: 1.75 } as const;

export const hotels: HotelOption[] = [
  { id: "cala", region: "Sardinia", name: "Cala di Volpe", nightlyRate: 1927, roomMultipliers: { ...roomMultipliers }, selectedRoom: "entry", refundablePremium: 0, taxRate: 0, complimentaryNights: 0, recommended: true },
  { id: "romazzino", region: "Sardinia", name: "Romazzino, A Belmond Hotel", nightlyRate: 2650, roomMultipliers: { ...roomMultipliers }, selectedRoom: "entry", refundablePremium: 0, taxRate: 0, complimentaryNights: 0 },
  { id: "como-hotel", region: "Tuscany", name: "COMO Castello Del Nero", nightlyRate: 861, roomMultipliers: { ...roomMultipliers }, selectedRoom: "entry", refundablePremium: 0, taxRate: 0, complimentaryNights: 0, recommended: true },
  { id: "rosewood", region: "Tuscany", name: "Castiglion del Bosco, A Rosewood Hotel", nightlyRate: 1904, roomMultipliers: { ...roomMultipliers }, selectedRoom: "entry", refundablePremium: 0, taxRate: 0, complimentaryNights: 0 },
  { id: "anantara", region: "Amalfi Coast", name: "Anantara Convento di Amalfi", nightlyRate: 1898, roomMultipliers: { ...roomMultipliers }, selectedRoom: "entry", refundablePremium: 0, taxRate: 0, complimentaryNights: 0, recommended: true },
  { id: "santa-caterina", region: "Amalfi Coast", name: "Hotel Santa Caterina", nightlyRate: 1700, roomMultipliers: { ...roomMultipliers }, selectedRoom: "entry", refundablePremium: 0, taxRate: 0, complimentaryNights: 0 },
  { id: "caruso", region: "Amalfi Coast", name: "Caruso, A Belmond Hotel", nightlyRate: 2460, roomMultipliers: { ...roomMultipliers }, selectedRoom: "entry", refundablePremium: 0, taxRate: 0, complimentaryNights: 0 },
];

export const stays: Stay[] = [
  { id: "stay-sardinia", region: "Sardinia", destinationId: "cala-di-volpe", hotelId: "cala", nights: 5 },
  { id: "stay-tuscany", region: "Tuscany", destinationId: "como", hotelId: "como-hotel", nights: 4 },
  { id: "stay-amalfi", region: "Amalfi Coast", destinationId: "amalfi", hotelId: "anantara", nights: 5 },
];
