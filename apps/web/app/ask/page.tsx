"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { LocationGate } from "../../components/LocationGate";
import { ApiError, api } from "../../lib/api";
import { useI18n } from "../../lib/i18n";
import { useOrigin } from "../../lib/origin";

const PROMPTS = [
  "Open potholes within 20 km",
  "Waterlogging near me",
  "Open manholes in this circle",
];

export default function AskPage() {
  const { t } = useI18n();
  const { origin, setOrigin, ready, block } = useOrigin();
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<{ kind: string; id: string; title: string; href: string }[]>([]);

  async function onSubmit(ev: FormEvent) {
    ev.preventDefault();
    if (!origin || !q.trim() || busy) return;
    setBusy(true);
    try {
      const res = await api<{
        answer: string;
        sources: { kind: string; id: string; title: string; href: string }[];
      }>("/v1/ask", {
        method: "POST",
        body: JSON.stringify({ q, lat: origin.lat, lng: origin.lng }),
      });
      const empty = res.sources.length === 0 && res.answer.includes("have that in the data");
      setAnswer(empty ? t("ask_empty") : res.answer);
      setSources(res.sources);
    } catch (e) {
      setAnswer(e instanceof ApiError ? e.message : "Ask failed");
      setSources([]);
    } finally {
      setBusy(false);
    }
  }

  if (!ready) return <main className="page">{t("loading")}</main>;
  if (!origin) return <LocationGate onReady={setOrigin} initial={block} />;

  return (
    <main className="page ask-wrap">
      <h1>{t("ask_title")}</h1>
      <p className="muted ask-lead">{t("ask_body")}</p>
      <section className="ask-sheet">
        <form className="ask-box" onSubmit={onSubmit}>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("ask_placeholder")} />
          <button className="send" type="submit" aria-label={t("ask_btn")}>
            ↑
          </button>
        </form>
        {busy ? <p className="muted">Looking through tickets in your circle…</p> : null}
        {answer ? (
          <article className="answer">
            <p>{answer}</p>
          </article>
        ) : (
          <div className="prompt-list">
            {PROMPTS.map((item) => (
              <button key={item} type="button" onClick={() => setQ(item)}>
                {item}
              </button>
            ))}
          </div>
        )}
        {sources.length > 0 ? (
          <div className="source-list">
            <h2>Tickets used</h2>
            {sources.map((s) => (
              <Link key={s.id} href={s.href} className="source-row">
                <strong>{s.id}</strong>
                <span>{s.title}</span>
              </Link>
            ))}
          </div>
        ) : null}
        <p className="ask-foot">Answers are based on tickets within your 20 km circle.</p>
      </section>
    </main>
  );
}
