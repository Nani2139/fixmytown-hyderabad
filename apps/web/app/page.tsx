"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { LocationGate } from "../components/LocationGate";
import { WardMap, type Pin } from "../components/WardMap";
import { ApiError, api, type Ticket } from "../lib/api";
import { formatDistance } from "../lib/cities";
import { useI18n, type CopyKey } from "../lib/i18n";
import { requestFix, useOrigin } from "../lib/origin";
import { cityAt } from "../lib/cities";

type Feat = { geometry: { coordinates: [number, number] }; properties: Pin };
type Brief = {
  ward: string;
  circle: string;
  open_2km: number;
  open_20km: number;
  fixed_yesterday: number;
  headline: { public_id: string; type: string; ward: string; meters: number | null; title: string } | null;
};

export default function HomePage() {
  const router = useRouter();
  const { t } = useI18n();
  const { origin, setOrigin, ready, block } = useOrigin();
  const [chip, setChip] = useState<"all" | "pothole" | "garbage" | "severe">("all");
  const [pins, setPins] = useState<Pin[]>([]);
  const [brief, setBrief] = useState<Brief | null>(null);
  const [wake, setWake] = useState("");
  const [query, setQuery] = useState("");
  const [focus, setFocus] = useState<string | null>(null);
  const [focusPin, setFocusPin] = useState<Pin | null>(null);
  const [statsOpen, setStatsOpen] = useState(false);

  useEffect(() => {
    setFocus(new URLSearchParams(window.location.search).get("focus"));
  }, []);

  useEffect(() => {
    if (!focus) {
      setFocusPin(null);
      return;
    }
    api<Ticket>(`/v1/tickets/${focus}`)
      .then((ticket) =>
        setFocusPin({
          public_id: ticket.public_id,
          type: ticket.type,
          status: ticket.status,
          lat: ticket.lat,
          lng: ticket.lng,
          title: ticket.title,
          confirmation_count: ticket.confirmation_count,
          ward: ticket.ward,
          circle_label: ticket.circle_label,
          thumb: ticket.media[0]?.url || null,
          days_open: ticket.days_open,
          severity: ticket.severity,
        }),
      )
      .catch(() => setFocusPin(null));
  }, [focus]);

  useEffect(() => {
    if (!origin) return;
    const q = new URLSearchParams({
      lat: String(origin.lat),
      lng: String(origin.lng),
      radius_km: "20",
      status: "open",
    });
    if (chip === "pothole" || chip === "garbage") q.set("type", chip);
    api<{ features: Feat[] }>(`/v1/map?${q}`)
      .then((data) => {
        setWake("");
        setPins(
          data.features.map((f) => ({
            ...f.properties,
            lng: f.geometry.coordinates[0],
            lat: f.geometry.coordinates[1],
          })),
        );
      })
      .catch((e) => setWake(e instanceof ApiError ? e.message : "Map failed"));
    api<Brief>(`/v1/brief?lat=${origin.lat}&lng=${origin.lng}`)
      .then(setBrief)
      .catch(() => setBrief(null));
  }, [origin, chip]);

  async function recenter() {
    try {
      const fix = await requestFix();
      if (!cityAt(fix.lat, fix.lng)) {
        setWake(t("outside"));
        return;
      }
      setOrigin({ ...fix, label: "live" });
    } catch {
      setWake(t("location_denied"));
    }
  }

  if (!ready) {
    return (
      <main className="gate">
        <p className="muted">{t("locating")}</p>
      </main>
    );
  }
  if (!origin) return <LocationGate onReady={setOrigin} initial={block} />;

  const shown = pins.filter((p) => {
    if (chip === "severe" && p.severity !== "blocks_road") return false;
    const blob = `${p.ward || ""} ${p.circle_label || ""} ${p.type} ${p.public_id} ${p.title || ""}`.toLowerCase();
    return blob.includes(query.trim().toLowerCase());
  });
  const mapPins =
    focusPin && !shown.some((pin) => pin.public_id === focusPin.public_id) ? [...shown, focusPin] : shown;

  return (
    <div className="atlas">
      <WardMap
        pins={mapPins}
        origin={origin}
        lockRadius
        selectedId={focus}
        onSelect={(id) => router.push(`/issues/${id}`)}
      />
      <aside className="dock-list">
        <input
          className="finder"
          value={query}
          placeholder={t("search")}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="chip-row">
          {(
            [
              ["all", t("all")],
              ["pothole", t("potholes")],
              ["garbage", t("litter")],
              ["severe", t("severe")],
            ] as const
          ).map(([id, label]) => (
            <button key={id} className={chip === id ? "filter on" : "filter"} onClick={() => setChip(id)}>
              {label}
            </button>
          ))}
        </div>
        {wake ? <div className="banner">{wake}</div> : null}
        <div className="dock-scroll">
          {shown.length === 0 ? (
            <img className="empty-issues" src="/brand/no-issues.jpg" alt="No issues nearby" />
          ) : null}
          {shown.map((p) => (
            <Link
              key={p.public_id}
              href={`/issues/${p.public_id}`}
              className={p.public_id === focus ? "issue-card on" : "issue-card"}
            >
              {p.thumb ? <img src={`/backend${p.thumb}`} alt="" /> : <span className="thumb" />}
              <span>
                <strong>
                  {t(p.type as CopyKey)} · {p.ward}
                </strong>
                <span className="meta">
                  {formatDistance(p.distance_m)} · {t("active")} {p.days_open ?? 0} {t("days_word")}
                </span>
                <span className="still">
                  {t("still_there_short")}
                  <b>{p.confirmation_count}</b>
                </span>
              </span>
            </Link>
          ))}
        </div>
        <p className="dock-note">{t("circle_note")}</p>
      </aside>
      {brief ? (
        <div className={statsOpen ? "map-stats open" : "map-stats"}>
          <button
            type="button"
            className="stats-toggle"
            aria-expanded={statsOpen}
            onClick={() => setStatsOpen((open) => !open)}
          >
            {statsOpen ? "×" : t("stats")}
          </button>
          {statsOpen ? (
            <>
              <span>
                <b>{brief.open_2km}</b> {t("open_nearby")}
              </span>
              <span>
                <b>{brief.open_20km}</b> {t("in_circle")}
              </span>
              <span>
                <b>{brief.fixed_yesterday}</b> {t("fixed_line")}
              </span>
            </>
          ) : null}
        </div>
      ) : null}
      <button type="button" className="locate" onClick={recenter} aria-label={t("recenter")}>
        <span />
      </button>
      <Link className="btn red report-fab" href="/report">
        + {t("report_issue")}
      </Link>
    </div>
  );
}
