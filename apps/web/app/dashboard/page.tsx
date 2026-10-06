"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type Me, type Ticket } from "../../lib/api";
import { useI18n, type CopyKey } from "../../lib/i18n";

const TABS = ["open", "in_review", "resolved"] as const;

export default function DashboardPage() {
  const router = useRouter();
  const { t, lang, setLang } = useI18n();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [me, setMe] = useState<Me["user"] | null>(null);
  const [tab, setTab] = useState<(typeof TABS)[number]>("open");
  const [mail, setMail] = useState(true);

  useEffect(() => {
    api<Me>("/v1/auth/me")
      .then((d) => setMe(d.user))
      .catch(() => router.push("/signin?next=/dashboard"));
    api<{ tickets: Ticket[] }>("/v1/me/tickets")
      .then((d) => setTickets(d.tickets))
      .catch(() => setTickets([]));
    setMail(localStorage.getItem("ww_mail") !== "0");
  }, [router]);

  const shown = tickets.filter((ticket) => ticket.status === tab);

  return (
    <main className="page stack">
      <section>
        <div className="tab-bar">
          {TABS.map((key) => (
            <button key={key} className={tab === key ? "on" : ""} onClick={() => setTab(key)}>
              {key === "open" ? `${t("open_issues")} (${tickets.filter((x) => x.status === "open").length})` : key === "in_review" ? "In Review" : "Resolved"}
            </button>
          ))}
          <Link className="btn red slim" href="/report">
            + {t("report_issue")}
          </Link>
        </div>
        <div className="ticket-list">
          {shown.length === 0 ? <p className="muted">{t("empty")}</p> : null}
          {shown.map((ticket) => (
            <Link key={ticket.public_id} href={`/issues/${ticket.public_id}`} className="ticket-card">
              {ticket.media[0] ? <img src={`/backend${ticket.media[0].url}`} alt="" /> : <span className="thumb" />}
              <span>
                <strong>
                  {t(ticket.type as CopyKey)} · {ticket.ward}
                </strong>
                <span className="meta">
                  {ticket.circle_label ? `${ticket.circle_label} · ` : ""}
                  {ticket.days_open ?? 0} {t("days")}
                </span>
                {ticket.severity ? <span className={`sev ${ticket.severity}`}>{t(ticket.severity as CopyKey)}</span> : null}
              </span>
              <span className={`pill ${ticket.status}`}>{ticket.status.replace("_", " ")}</span>
            </Link>
          ))}
        </div>
      </section>
      <section className="profile-block" id="profile">
        <h2>Profile & Settings</h2>
        <div className="who">
          <span className="avatar lg">{me?.email[0]?.toUpperCase()}</span>
          <span>
            <strong>{me?.email?.split("@")[0]}</strong>
            <span className="meta">{me?.email}</span>
          </span>
        </div>
        <div className="stat-pills">
          <div>
            <b>{tickets.length}</b>
            <span>Reports</span>
          </div>
          <div>
            <b>{tickets.filter((x) => x.status === "resolved").length}</b>
            <span>Resolved</span>
          </div>
          <div>
            <b>{tickets.reduce((n, x) => n + x.confirmation_count, 0)}</b>
            <span>Updates</span>
          </div>
        </div>
        <div className="setting">
          <span>Language</span>
          <button type="button" className="choice" onClick={() => setLang(lang === "en" ? "te" : "en")}>
            {lang === "en" ? "English" : "తెలుగు"}
          </button>
        </div>
        <div className="setting">
          <span>
            Location Access
            <small>Allow location to find nearby issues</small>
          </span>
          <Link href="/">On</Link>
        </div>
        <div className="setting">
          <span>
            Email Notifications
            <small>Updates on your reported issues</small>
          </span>
          <button
            type="button"
            className={mail ? "switch on" : "switch"}
            aria-pressed={mail}
            onClick={() => {
              const next = !mail;
              setMail(next);
              localStorage.setItem("ww_mail", next ? "1" : "0");
            }}
          />
        </div>
      </section>
    </main>
  );
}
