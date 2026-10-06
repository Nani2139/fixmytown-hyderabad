"use client";

import Link from "next/link";
import { useState } from "react";
import { cityAt } from "../lib/cities";
import { useI18n } from "../lib/i18n";
import { previewOrigin, requestFix, type Origin } from "../lib/origin";

export function LocationGate({
  onReady,
  initial,
}: {
  onReady: (origin: Origin) => void;
  initial?: string;
}) {
  const { t, lang, setLang } = useI18n();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(initial === "outside" ? "outside" : initial === "denied" ? "denied" : "");

  async function live() {
    setBusy(true);
    setErr("");
    try {
      const fix = await requestFix();
      if (!cityAt(fix.lat, fix.lng)) {
        setErr("outside");
        return;
      }
      onReady({ ...fix, label: "live" });
    } catch {
      setErr("denied");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="gate hide-chrome">
      <section className="gate-shell">
        <header className="gate-bar">
          <Link href="/" className="brand">
            <img className="brand-logo" src="/brand/logo.png" alt="FixMyTown" />
          </Link>
          <div className="top-actions">
            <div className="lang-split">
              <button type="button" className={lang === "en" ? "on" : ""} onClick={() => setLang("en")}>
                EN
              </button>
              <span>|</span>
              <button type="button" className={lang === "te" ? "on" : ""} onClick={() => setLang("te")}>
                తెలుగు
              </button>
            </div>
            <Link href="/signin" className="avatar" aria-label={t("account")} />
          </div>
        </header>
        <section className="gate-card">
          <div className="gate-orb" aria-hidden>
            <span />
          </div>
          <h1>{t("gate_title")}</h1>
          <p className="lede">{t("gate_body")}</p>
          {err === "denied" ? <div className="banner">{t("location_denied")}</div> : null}
          <button type="button" className="btn red wide" onClick={live} disabled={busy}>
            {busy ? t("locating") : t("use_location")}
          </button>
        </section>
        <p className="or">or</p>
        <section className="gate-card skyline-card">
          <div className="skyline" aria-hidden>
            <svg viewBox="0 0 280 90">
              <path d="M20 78h240M40 78V52h16v26M70 78V40h28v38M108 78V48h18v30M140 78V28l14-16 14 16v50M178 78V46h22v32M214 78V54h18v24" />
              <path d="M140 28h28M154 12v16" />
            </svg>
          </div>
          <h2>{t("outside_title")}</h2>
          <p className="lede">{err === "outside" ? t("outside") : t("outside_body")}</p>
          <button type="button" className="btn ghost wide" onClick={() => onReady(previewOrigin())}>
            {t("preview")}
          </button>
        </section>
      </section>
    </main>
  );
}
