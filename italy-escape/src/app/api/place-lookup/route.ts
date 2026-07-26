import { NextResponse } from "next/server";

export interface PlaceMatch {
  name: string;
  address: string;
  lat: number;
  lng: number;
  category: string;
  website?: string;
  phone?: string;
  stars?: string;
}

interface NominatimResult {
  name?: string;
  display_name?: string;
  lat: string;
  lon: string;
  type?: string;
  address?: Record<string, string>;
  extratags?: Record<string, string>;
}

const line = (address: Record<string, string> = {}) =>
  [address.road, address.suburb, address.city ?? address.town ?? address.village, address.state, address.country]
    .filter(Boolean).join(", ");

/**
 * Looks a hotel up by name against OpenStreetMap. Free, keyless, and it returns the real
 * address and coordinates so a hand-added hotel is a proper pin rather than a text label.
 */
export async function GET(request: Request) {
  const query = new URL(request.url).searchParams.get("q")?.trim();
  if (!query || query.length < 3) return NextResponse.json({ matches: [] });

  // Extra words like a region label make the geocoder miss, so try the plainest form first.
  const attempts = [query, `${query}, Italy`, query.split(/\s+/).slice(0, 3).join(" ")]
    .filter((value, index, all) => value.length >= 3 && all.indexOf(value) === index);

  try {
    let results: NominatimResult[] = [];
    for (const attempt of attempts) {
      const url = new URL("https://nominatim.openstreetmap.org/search");
      url.searchParams.set("q", attempt);
      url.searchParams.set("format", "jsonv2");
      url.searchParams.set("addressdetails", "1");
      url.searchParams.set("extratags", "1");
      url.searchParams.set("limit", "5");

      const response = await fetch(url, {
        headers: { "User-Agent": "ItalyEscapePlanner/1.0 (private trip planning tool)" },
        next: { revalidate: 86400 },
      });
      if (!response.ok) continue;
      results = (await response.json()) as NominatimResult[];
      if (results.length > 0) break;
    }

    const matches: PlaceMatch[] = results.map((result) => ({
      name: result.name || result.display_name?.split(",")[0] || query,
      address: line(result.address) || result.display_name || "",
      lat: Number(result.lat),
      lng: Number(result.lon),
      category: result.type ?? "place",
      website: result.extratags?.website ?? result.extratags?.["contact:website"],
      phone: result.extratags?.phone ?? result.extratags?.["contact:phone"],
      stars: result.extratags?.stars,
    }));
    return NextResponse.json({ matches });
  } catch {
    return NextResponse.json({ matches: [], error: "Lookup failed" }, { status: 200 });
  }
}
