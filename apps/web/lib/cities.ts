import cities from "../../../packages/geo/cities.json";

export type City = (typeof cities)[number];

export const hyderabad = cities[0];
export const RADIUS_KM = hyderabad.radiusKm;

export function cityAt(lat: number, lng: number): City | null {
  const { sw, ne } = hyderabad.bounds;
  if (lat >= sw.lat && lat <= ne.lat && lng >= sw.lng && lng <= ne.lng) return hyderabad;
  return null;
}

export function haversineM(lat1: number, lng1: number, lat2: number, lng2: number) {
  const r = 6371000;
  const p1 = (lat1 * Math.PI) / 180;
  const p2 = (lat2 * Math.PI) / 180;
  const dp = ((lat2 - lat1) * Math.PI) / 180;
  const dl = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
  return 2 * r * Math.asin(Math.sqrt(a));
}

export function insideRadius(
  lat: number,
  lng: number,
  originLat: number,
  originLng: number,
  km = RADIUS_KM,
) {
  return haversineM(lat, lng, originLat, originLng) <= km * 1000;
}

export function formatDistance(meters: number | null | undefined) {
  if (meters == null) return "";
  if (meters < 1000) return `${Math.max(1, Math.round(meters))} m`;
  return `${(meters / 1000).toFixed(1)} km`;
}
