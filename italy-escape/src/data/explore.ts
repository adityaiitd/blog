export type SpotKind = "eat" | "see" | "calm" | "beach" | "drink";

export interface Spot {
  id: string;
  name: string;
  kind: SpotKind;
  region: string;
  near: string;
  why: string;
  tip: string;
  url: string;
}

/**
 * Curated from local and slow-travel guides rather than top-ten lists: the emphasis is on
 * places worth the detour and on quiet alternatives to the obvious stops.
 */
export const spots: Spot[] = [
  // Sardinia
  { id: "san-pantaleo", name: "San Pantaleo village", kind: "calm", region: "Sardinia", near: "20 min from Cala di Volpe",
    why: "A granite village of artists' studios and a single beautiful square, cooler and quieter than the coast. The whole place turns pink at sunset.",
    tip: "Thursday morning is the artisan market, May to October. Arrive early for parking and start with a coffee on the square.",
    url: "https://www.sardegnaturismo.it/en/explore/san-pantaleo-0" },
  { id: "spiaggia-principe", name: "Spiaggia del Principe", kind: "beach", region: "Sardinia", near: "15 min from Cala di Volpe",
    why: "Widely held to be the most beautiful beach in Sardinia: fine white sand in a crescent between granite headlands.",
    tip: "A 10–15 minute walk from the car park keeps the crowds down. Go before 10am in high season.",
    url: "https://sardiniabella.com/en/costa-smeralda-guide-things-to-see-and-do/" },
  { id: "liscia-ruja", name: "Liscia Ruja", kind: "beach", region: "Sardinia", near: "10 min from Cala di Volpe",
    why: "The longest beach on the Costa Smeralda at 800 metres, so it never feels packed even in season.",
    tip: "The southern end is quietest. Easiest beach day if you want space without a hike.",
    url: "https://strictlysardinia.com/san-pantaleo-sardinia-guide/" },
  { id: "razza-di-juncu", name: "Cala Razza di Juncu", kind: "beach", region: "Sardinia", near: "15 min from Cala di Volpe",
    why: "Small coves framed by pink granite, the water almost unreally clear. The locals' pick over the famous names.",
    tip: "Limited parking; pairs well with a late-afternoon swim after the day boats have gone.",
    url: "https://strictlysardinia.com/san-pantaleo-sardinia-guide/" },
  { id: "porto-cervo", name: "Porto Cervo old port", kind: "drink", region: "Sardinia", near: "15 min from Cala di Volpe",
    why: "Worth one evening for the yacht-watching and the Aga Khan-era architecture, even if you do not shop.",
    tip: "Go for aperitivo around 7pm and eat elsewhere; the piazzetta is the point, not the restaurants.",
    url: "https://sardiniabella.com/en/costa-smeralda-guide-things-to-see-and-do/" },
  { id: "cugnana-trails", name: "Cugnana massif trails", kind: "calm", region: "Sardinia", near: "From San Pantaleo",
    why: "Marked trekking paths through cork woods and granite, with the emerald coast laid out below.",
    tip: "Early morning only in September. Proper shoes; the granite is slick after rain.",
    url: "https://www.sardegnaturismo.it/en/explore/san-pantaleo-0" },

  // Tuscany
  { id: "greve-panzano", name: "Greve and Panzano in Chianti", kind: "see", region: "Tuscany", near: "20–30 min from Castello del Nero",
    why: "The two most rewarding Chianti market towns: an arcaded triangular piazza at Greve, and Panzano's butcher-led food culture.",
    tip: "Panzano is a lunch town. Greve has the better wine shops for taking bottles home.",
    url: "https://www.visittuscany.com/en/destinations/greve-in-chianti/" },
  { id: "badia-passignano", name: "Badia a Passignano", kind: "calm", region: "Tuscany", near: "15 min from Castello del Nero",
    why: "An 11th-century abbey surrounded by Antinori vineyards. One of the quietest beautiful places in Chianti.",
    tip: "The cypress avenue at golden hour is the photograph. Cellar visits need booking ahead.",
    url: "https://www.visittuscany.com/en/attractions/the-abbey-of-passignano/" },
  { id: "siena-contrade", name: "Siena, away from the Campo", kind: "see", region: "Tuscany", near: "45 min from Castello del Nero",
    why: "The Campo is unavoidable, but the contrada streets behind it and the view from the Facciatone are where Siena is actually itself.",
    tip: "Go late afternoon and stay for dinner; the day-trip coaches leave around 5pm.",
    url: "https://www.visittuscany.com/en/destinations/siena/" },
  { id: "val-dorcia-drive", name: "Val d'Orcia back roads", kind: "calm", region: "Tuscany", near: "1h 15m from Castello del Nero",
    why: "Pienza to Montalcino via the unpaved white roads, past the cypress lines everyone photographs and mostly without the crowds.",
    tip: "Do it as a slow single day, not an add-on. Stop in Pienza for pecorino.",
    url: "https://www.visittuscany.com/en/destinations/val-dorcia/" },
  { id: "florence-oltrarno", name: "Florence: Oltrarno", kind: "see", region: "Tuscany", near: "45 min from Castello del Nero",
    why: "Across the river the artisan workshops still work. Santo Spirito's square in the evening is the antidote to the Duomo queues.",
    tip: "Pair the guided morning with a free Oltrarno afternoon rather than a second museum.",
    url: "https://www.visittuscany.com/en/destinations/florence/" },

  // Amalfi Coast
  { id: "lo-scoglio", name: "Lo Scoglio da Tommaso", kind: "eat", region: "Amalfi Coast", near: "Marina del Cantone, Nerano",
    why: "The family-run institution where spaghetti alla Nerano is at its best, on a terrace built over the water. Farm and sea to table, since 1958.",
    tip: "Book well ahead on +39 081 808 1026 and arrive by boat: it is the natural lunch stop on your Nerano day.",
    url: "https://www.loscoglio.net/" },
  { id: "da-adolfo", name: "Da Adolfo, Laurito", kind: "eat", region: "Amalfi Coast", near: "Beach below Positano",
    why: "Reached only by the restaurant's own gozzo from Positano pier. Mozzarella grilled on lemon leaves, feet in the sand.",
    tip: "Phone reservations only, +39 089 875022. The free boat with the red fish leaves the pier from 10am.",
    url: "https://www.daadolfo.com/" },
  { id: "ravello-gardens", name: "Villa Cimbrone and Villa Rufolo", kind: "see", region: "Amalfi Coast", near: "Ravello, 30 min from Amalfi",
    why: "The Terrace of Infinity at Cimbrone is the single best view on the coast, and Rufolo's gardens hold the summer concerts.",
    tip: "Cimbrone opens at 9am; the first hour is nearly empty and the light is best.",
    url: "https://villacimbrone.com/en/" },
  { id: "path-of-gods", name: "Sentiero degli Dei", kind: "calm", region: "Amalfi Coast", near: "Bomerano to Nocelle",
    why: "The Path of the Gods, walked downhill from Bomerano, gives you the coast from above with almost no one on it early.",
    tip: "Start by 8am in September. Roughly three hours, then the steps down to Positano or a bus from Nocelle.",
    url: "https://www.amalficoast.com/en/experiences/path-of-the-gods" },
  { id: "atrani", name: "Atrani", kind: "calm", region: "Amalfi Coast", near: "10 min walk from Amalfi",
    why: "The smallest town in southern Italy, one headland from Amalfi and almost entirely free of its crowds. A single quiet piazza by the sea.",
    tip: "Walk over for an evening drink in Piazza Umberto I after the day boats have left Amalfi.",
    url: "https://www.amalficoast.com/en/discover/atrani" },
  { id: "furore-fjord", name: "Fiordo di Furore", kind: "see", region: "Amalfi Coast", near: "15 min from Praiano",
    why: "A cleft in the cliffs with a fishing hamlet and a bridge overhead; far more striking from the water than the road.",
    tip: "Ask your skipper to slow through it. There is almost nowhere to park on the road above.",
    url: "https://www.amalficoast.com/en/discover/furore" },
  { id: "marina-di-praia", name: "Marina di Praia", kind: "beach", region: "Amalfi Coast", near: "Below Hotel Onda Verde",
    why: "A tiny cove between cliffs, with a couple of good seafood tables and swimming straight off the rocks.",
    tip: "This is the cove your boats leave from, so it doubles as a swim on non-boat afternoons.",
    url: "https://www.amalficoast.com/en/discover/praiano" },
];
