"use client";

import { useEffect, useRef } from "react";
import { hyderabad } from "../lib/cities";

export type Pin = {
  public_id: string;
  type: string;
  status: string;
  lat: number;
  lng: number;
  title: string;
  confirmation_count: number;
  distance_m?: number | null;
  ward?: string;
  circle_label?: string;
  thumb?: string | null;
  days_open?: number;
  severity?: string;
};

export const PIN_COLORS: Record<string, string> = {
  waterlogging: "#3b82f6",
  open_manhole: "#ff7a45",
  garbage: "#f5a524",
  streetlight: "#f5c542",
  pothole: "#ff4d4f",
  dug_road: "#a78bfa",
  dumping: "#fb7185",
  stagnant_water: "#22c55e",
};

type Props = {
  pins: Pin[];
  onSelect?: (id: string) => void;
  draggable?: boolean;
  center?: { lat: number; lng: number };
  onDrop?: (lat: number, lng: number) => void;
  origin?: { lat: number; lng: number } | null;
  lockRadius?: boolean;
  radiusM?: number;
  height?: string;
  selectedId?: string | null;
};

export function WardMap({
  pins,
  onSelect,
  draggable,
  center,
  onDrop,
  origin,
  lockRadius,
  radiusM = 20000,
  height = "100%",
  selectedId = null,
}: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<import("leaflet").Map | null>(null);
  const pinsRef = useRef(pins);
  const selectRef = useRef(onSelect);
  const dropRef = useRef(onDrop);
  const selectedRef = useRef(selectedId);
  pinsRef.current = pins;
  selectRef.current = onSelect;
  dropRef.current = onDrop;
  selectedRef.current = selectedId;

  const originKey = origin ? `${origin.lat.toFixed(5)},${origin.lng.toFixed(5)}` : "";
  const centerRef = useRef(center);
  centerRef.current = center;

  useEffect(() => {
    let alive = true;
    let timer = 0;
    let onResize: (() => void) | undefined;
    const el = ref.current;
    if (!el) return;

    (async () => {
      const L = await import("leaflet");
      await import("leaflet/dist/leaflet.css");
      if (!alive || !ref.current) return;
      const spot = centerRef.current;
      const here = lockRadius && origin ? origin : spot || origin || hyderabad.center;
      const map = L.map(ref.current, {
        zoomControl: false,
        zoomSnap: 0.25,
        minZoom: 11,
        maxZoom: 19,
      });
      map.setView([here.lat, here.lng], 13);
      mapRef.current = map;
      L.control.zoom({ position: "topright" }).addTo(map);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap",
        maxZoom: 19,
      }).addTo(map);

      const frameCircle = () => {
        if (!map.getContainer()?.isConnected || !ring) return;
        map.invalidateSize();
        const narrow = window.innerWidth < 900;
        const home = !!map.getContainer().closest(".atlas");
        const dockEl = document.querySelector(".dock-list");
        const dockRight = dockEl ? dockEl.getBoundingClientRect().right : 0;
        const padLeft = home && !narrow ? Math.max(dockRight + 28, 400) : 28;
        map.setMaxBounds(ring.getBounds().pad(4));
        map.fitBounds(ring.getBounds(), {
          paddingTopLeft: [padLeft, narrow ? 96 : 128],
          paddingBottomRight: [36, narrow ? Math.round(window.innerHeight * 0.5) : 96],
          animate: false,
        });
      };

      let ring: import("leaflet").Circle | undefined;
      if (lockRadius && origin) {
        L.circle([origin.lat, origin.lng], {
          radius: radiusM,
          color: "#8eb7ff",
          weight: 16,
          opacity: 0.28,
          fill: false,
          interactive: false,
        }).addTo(map);
        ring = L.circle([origin.lat, origin.lng], {
          radius: radiusM,
          color: "#4c8dff",
          weight: 3,
          fillColor: "#2f6bff",
          fillOpacity: 0.22,
          interactive: false,
        }).addTo(map);
        const north = origin.lat + radiusM / 111320;
        L.marker([north, origin.lng], {
          interactive: false,
          icon: L.divIcon({
            className: "km-tag",
            html: "<span>20 km</span>",
            iconSize: [72, 28],
            iconAnchor: [36, 14],
          }),
        }).addTo(map);
        frameCircle();
      } else {
        const { sw, ne } = hyderabad.bounds;
        map.setMaxBounds([
          [sw.lat, sw.lng],
          [ne.lat, ne.lng],
        ]);
        map.setView([here.lat, here.lng], 16);
      }

      if (origin) {
        const you = L.marker([origin.lat, origin.lng], {
          interactive: false,
          icon: L.divIcon({
            className: "you-pin",
            html: `<span class="you-dot"></span><span class="you-label">YOU</span>`,
            iconSize: [46, 46],
            iconAnchor: [23, 23],
          }),
        });
        you.addTo(map);
      }

      const pinsLayer = L.layerGroup().addTo(map);
      const draw = () => {
        pinsLayer.clearLayers();
        for (const pin of pinsRef.current) {
          const picked = pin.public_id === selectedRef.current;
          const marker = L.marker([pin.lat, pin.lng], {
            icon: dotIcon(L, pin, picked),
            zIndexOffset: picked ? 1000 : 0,
          });
          const dist =
            pin.distance_m != null
              ? pin.distance_m < 1000
                ? `${pin.distance_m} m`
                : `${(pin.distance_m / 1000).toFixed(1)} km`
              : "";
          marker.bindTooltip(
            `${pin.title}${dist ? ` · ${dist}` : ""}`,
            { direction: "top", offset: [0, -8], opacity: 1 },
          );
          marker.on("click", () => selectRef.current?.(pin.public_id));
          marker.addTo(pinsLayer);
          if (picked) marker.openTooltip();
        }
      };
      draw();
      map.on("zoomend", draw);

      let dropMarker: import("leaflet").Marker | undefined;
      if (draggable) {
        dropMarker = L.marker([here.lat, here.lng], {
          draggable: false,
          icon: L.divIcon({
            className: "drop-pin",
            html: `<span class="pin-drop"></span><em>Drag to adjust location</em>`,
            iconSize: [28, 36],
            iconAnchor: [14, 34],
          }),
        }).addTo(map);
        map.on("click", (e: { latlng: { lat: number; lng: number } }) => {
          dropMarker?.setLatLng(e.latlng);
          dropRef.current?.(e.latlng.lat, e.latlng.lng);
        });
      }

      const focusPin = () => {
        const id = selectedRef.current;
        const pin = pinsRef.current.find((item) => item.public_id === id);
        if (!pin || !map.getContainer()?.isConnected) return;
        map.flyTo([pin.lat, pin.lng], 16, { animate: false });
      };
      onResize = () => {
        frameCircle();
        focusPin();
      };
      window.addEventListener("resize", onResize);
      timer = window.setTimeout(() => {
        if (!alive || !map.getContainer()?.isConnected) return;
        frameCircle();
        focusPin();
      }, 160);
    })();

    return () => {
      alive = false;
      window.clearTimeout(timer);
      if (onResize) window.removeEventListener("resize", onResize);
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [originKey, draggable, lockRadius, radiusM]);

  useEffect(() => {
    const map = mapRef.current;
    map?.fire("zoomend");
    if (!map || !selectedId) return;
    const pin = pins.find((item) => item.public_id === selectedId);
    if (!pin || !map.getContainer()?.isConnected) return;
    map.flyTo([pin.lat, pin.lng], 16, { animate: true });
  }, [JSON.stringify(pins), selectedId]);

  return <div ref={ref} className="ward-map" style={{ height, width: "100%" }} />;
}

function dotIcon(L: typeof import("leaflet"), pin: Pin, picked = false) {
  const color = colorOf(pin.type);
  const size = picked ? 40 : 26;
  const height = picked ? 52 : 34;
  return L.divIcon({
    className: picked ? "dot-pin selected" : "dot-pin",
    html: `<svg width="${size}" height="${height}" viewBox="0 0 26 34" aria-hidden="true"><path d="M13 33s11-12.2 11-19A11 11 0 1 0 2 14c0 6.8 11 19 11 19z" fill="${color}" stroke="${picked ? "#4c8dff" : "#fff"}" stroke-width="${picked ? 2.4 : 1.4}"/><circle cx="13" cy="13.5" r="4" fill="#fff"/></svg>`,
    iconSize: [size, height],
    iconAnchor: [size / 2, height - 1],
  });
}

function colorOf(type: string) {
  return PIN_COLORS[type] || "#e4a15a";
}
