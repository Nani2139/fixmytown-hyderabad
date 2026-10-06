"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type Me, type Ticket } from "../../lib/api";
import { useI18n } from "../../lib/i18n";

export default function AccountPage() {
  const router = useRouter();
  const { t, lang, setLang } = useI18n();
  const [me, setMe] = useState<Me["user"] | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [mail, setMail] = useState(true);

  useEffect(() => {
    api<Me>("/v1/auth/me")
      .then((d) => setMe(d.user))
      .catch(() => router.push("/signin?next=/account"));
    api<{ tickets: Ticket[] }>("/v1/me/tickets")
      .then((d) => setTickets(d.tickets))
      .catch(() => setTickets([]));
    setMail(localStorage.getItem("ww_mail") !== "0");
  }, [router]);

  async function signOut() {
    await api("/v1/auth/signout", { method: "POST" });
    router.push("/");
    router.refresh();
  }

  if (!me) return <main className="page">{t("loading")}</main>;

  return (
    <main className="page">
      <section className="profile-block">
        <h2>Profile & Settings</h2>
        <div className="who">
          <span className="avatar lg">{me.email[0]?.toUpperCase()}</span>
          <span>
            <strong>{me.email.split("@")[0]}</strong>
            <span className="meta">{me.email}</span>
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
        <div className="profile-links">
          <Link href="/dashboard">{t("tickets")}</Link>
          {me.role === "admin" ? <Link href="/admin">{t("admin")}</Link> : null}
          <button type="button" className="logout" onClick={signOut}>
            {t("sign_out")}
          </button>
        </div>
      </section>
    </main>
  );
}
