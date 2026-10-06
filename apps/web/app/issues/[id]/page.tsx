"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { WardMap } from "../../../components/WardMap";
import { ApiError, api, type Ticket } from "../../../lib/api";
import { useI18n, type CopyKey } from "../../../lib/i18n";
import { requestFix } from "../../../lib/origin";

export default function IssuePage() {
  const params = useParams<{ id: string }>();
  const { t } = useI18n();
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [err, setErr] = useState("");
  const [note, setNote] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api<Ticket>(`/v1/tickets/${params.id}`)
      .then(setTicket)
      .catch(() => setErr("No ticket with that id."));
  }, [params.id]);

  async function stillThere() {
    setNote("");
    try {
      const fix = await requestFix();
      const res = await api<{ ticket: Ticket }>(`/v1/tickets/${params.id}/confirm`, {
        method: "POST",
        body: JSON.stringify(fix),
      });
      setTicket(res.ticket);
    } catch (e) {
      setNote(e instanceof ApiError ? e.message : t("location_denied"));
    }
  }

  async function share() {
    const url = window.location.href;
    const title = ticket?.title || "FixMyTown";
    if (navigator.share) {
      await navigator.share({ title, url });
      return;
    }
    await navigator.clipboard.writeText(url);
    setCopied(true);
  }

  if (err) return <main className="page">{err}</main>;
  if (!ticket) return <main className="page">{t("loading")}</main>;

  const before = ticket.media.find((m) => m.kind !== "fix");
  const after = ticket.media.find((m) => m.kind === "fix");
  const resolvedAt = ticket.timeline?.find((e) => e.type === "resolved")?.at;

  return (
    <main className="page issue-layout">
      <section>
        {before ? <img className="hero-photo" src={`/backend${before.url}`} alt="" /> : <div className="hero-photo empty" />}
        <div className="title-row">
          <h1>
            {t(ticket.type as CopyKey)} · {ticket.ward}
          </h1>
          {ticket.severity ? <span className={`sev ${ticket.severity}`}>{t(ticket.severity as CopyKey)}</span> : null}
        </div>
        <p className="muted">
          {ticket.ward}
          {ticket.circle_label ? ` · ${ticket.circle_label}` : ""} · {ticket.public_id}
        </p>
        <p className="muted">
          {t("in_circle")} · {ticket.days_open ?? 0} {t("days")}
        </p>
        <p>{ticket.body}</p>
        <div className="action-row">
          {ticket.status === "open" || ticket.status === "in_review" ? (
            <button type="button" className="choice" onClick={stillThere}>
              {t("still_there")}
            </button>
          ) : null}
          <span className="count-pill">{ticket.confirmation_count}</span>
          <button type="button" className="choice" onClick={share}>
            {copied ? t("copied") : t("share")}
          </button>
        </div>
        {note ? <div className="banner">{note}</div> : null}
        <h2>{t("fix_photo")}</h2>
        {after ? (
          <img className="fix-photo" src={`/backend${after.url}`} alt="" />
        ) : (
          <p className="muted">A fix photo appears here once the issue is resolved.</p>
        )}
        {ticket.resolve_note ? <p>{ticket.resolve_note}</p> : null}
        {ticket.status === "resolved" && resolvedAt ? (
          <p className="ok-line">Resolved {new Date(resolvedAt).toLocaleDateString()}</p>
        ) : null}
      </section>
      <aside className="issue-side">
        <div className="map-frame">
          <WardMap
            pins={[
              {
                public_id: ticket.public_id,
                type: ticket.type,
                status: ticket.status,
                lat: ticket.lat,
                lng: ticket.lng,
                title: ticket.title,
                confirmation_count: ticket.confirmation_count,
                ward: ticket.ward,
              },
            ]}
            center={{ lat: ticket.lat, lng: ticket.lng }}
            height="100%"
          />
        </div>
        <h2>Status</h2>
        <p>
          <span className={`pill ${ticket.status}`}>{ticket.status.replace("_", " ")}</span>
          <span className="muted"> {ticket.days_open ?? 0} {t("days")}</span>
        </p>
        <ul className="timeline">
          {(ticket.timeline || []).map((e, i) => (
            <li key={i}>{e.type.replaceAll("_", " ")}</li>
          ))}
        </ul>
        <h2>Reported</h2>
        <p className="muted">
          {ticket.confirmation_count} {t("confirms")}
        </p>
        <h2>Nearby</h2>
        {(ticket.nearby || []).length === 0 ? (
          <p className="muted">{t("nothing_near")}</p>
        ) : (
          (ticket.nearby || []).map((n) => (
            <p key={n.public_id}>
              <Link href={`/issues/${n.public_id}`}>
                {t(n.type as CopyKey)} · {n.ward} · {n.meters} m
              </Link>
            </p>
          ))
        )}
      </aside>
    </main>
  );
}
