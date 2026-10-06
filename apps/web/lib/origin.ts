"use client";

import { useEffect, useState } from "react";
import { cityAt, hyderabad } from "./cities";

const KEY = "ww_origin";

export type Origin = { lat: number; lng: number; label: "live" | "preview" };

export function readOrigin(): Origin | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Origin;
    if (!cityAt(parsed.lat, parsed.lng)) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function writeOrigin(origin: Origin) {
  sessionStorage.setItem(KEY, JSON.stringify(origin));
}

export function requestFix(): Promise<{ lat: number; lng: number }> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("unsupported"));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => reject(new Error("denied")),
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 20000 },
    );
  });
}

export function previewOrigin(): Origin {
  return { lat: hyderabad.center.lat, lng: hyderabad.center.lng, label: "preview" };
}

export function useOrigin() {
  const [origin, setOriginState] = useState<Origin | null>(null);
  const [ready, setReady] = useState(false);
  const [block, setBlock] = useState("");

  function setOrigin(next: Origin) {
    writeOrigin(next);
    setOriginState(next);
    setBlock("");
  }

  useEffect(() => {
    const saved = readOrigin();
    if (saved) {
      setOriginState(saved);
      setReady(true);
      return;
    }
    requestFix()
      .then((fix) => {
        if (!cityAt(fix.lat, fix.lng)) {
          setBlock("outside");
          return;
        }
        const next = { ...fix, label: "live" as const };
        writeOrigin(next);
        setOriginState(next);
      })
      .catch(() => setBlock("denied"))
      .finally(() => setReady(true));
  }, []);

  return { origin, setOrigin, ready, block };
}
