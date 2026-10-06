"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LocationGate } from "../../components/LocationGate";
import { WardMap } from "../../components/WardMap";
import { ApiError, api, apiForm } from "../../lib/api";
import { insideRadius } from "../../lib/cities";
import { useI18n, type CopyKey } from "../../lib/i18n";
import { useOrigin } from "../../lib/origin";

const TYPES = [
  "waterlogging",
  "open_manhole",
  "garbage",
  "streetlight",
  "pothole",
  "dug_road",
  "dumping",
  "stagnant_water",
] as const;
const SEVERITIES = ["blocks_road", "night_danger", "smell"] as const;

export default function ReportPage() {
  const router = useRouter();
  const { t } = useI18n();
  const { origin, setOrigin, ready, block } = useOrigin();
  const [lat, setLat] = useState(0);
  const [lng, setLng] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [mediaId, setMediaId] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [suggested, setSuggested] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [typ, setTyp] = useState("");
  const [severity, setSeverity] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [body, setBody] = useState("");
  const [err, setErr] = useState("");
  const [photoIssue, setPhotoIssue] = useState("");
  const [checkNote, setCheckNote] = useState("");
  const [busy, setBusy] = useState("");
  const [step, setStep] = useState(1);
  const [preview, setPreview] = useState("");

  useEffect(() => {
    api("/v1/auth/me").catch(() => router.push("/signin?next=/report"));
  }, [router]);

  useEffect(() => {
    if (!origin) return;
    setLat(origin.lat);
    setLng(origin.lng);
  }, [origin]);

  useEffect(() => {
    if (!jobId) return;
    let n = 0;
    const timer = setInterval(async () => {
      n += 1;
      const job = await api<{
        status: string;
        suggested_type: string | null;
        confidence: number | null;
        unrelated?: boolean;
      }>(`/v1/vision/${jobId}`);
      if (job.status === "succeeded" || job.status === "failed" || n > 20) {
        clearInterval(timer);
        setBusy("");
        applyVision(job);
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [jobId]);

  function photoRejected(job: { status?: string; suggested_type: string | null; unrelated?: boolean }) {
    return !!job.unrelated || (job.status === "succeeded" && !job.suggested_type);
  }

  function applyVision(job: { status?: string; suggested_type: string | null; confidence: number | null; unrelated?: boolean }) {
    if (job.status === "failed") {
      setPhotoIssue("");
      setCheckNote(t("photo_check_busy"));
      setSuggested(null);
      setConfidence(null);
      return;
    }
    setCheckNote("");
    if (photoRejected(job)) {
      setPhotoIssue(t("bad_photo"));
      setSuggested(null);
      setConfidence(job.confidence);
      setTyp("");
      setConfirmed(false);
      return;
    }
    setPhotoIssue("");
    setSuggested(job.suggested_type);
    setConfidence(job.confidence);
    if (job.suggested_type && (job.confidence || 0) >= 0.45) setTyp(job.suggested_type);
  }

  async function upload(chosen: File) {
    setErr("");
    setPhotoIssue("");
    setBusy("Uploading photo…");
    const form = new FormData();
    form.append("file", chosen);
    try {
      const res = await apiForm<{ media_id: string; job_id: string }>("/v1/uploads", form);
      setMediaId(res.media_id);
      setJobId(res.job_id);
      setBusy("Looking at your photo…");
      for (let n = 0; n < 20; n += 1) {
        const job = await api<{
          status: string;
          suggested_type: string | null;
          confidence: number | null;
          unrelated?: boolean;
        }>(`/v1/vision/${res.job_id}`);
        if (job.status === "succeeded" || job.status === "failed") {
          setBusy("");
          applyVision(job);
          return !photoRejected(job);
        }
        await new Promise((resolve) => setTimeout(resolve, 800));
      }
      setBusy("");
      return true;
    } catch (e) {
      setBusy("");
      setErr(e instanceof ApiError ? e.message : "Upload failed");
      return false;
    }
  }

  function pickPhoto(next: File | null) {
    setFile(next);
    setPreview(next ? URL.createObjectURL(next) : "");
    setPhotoIssue("");
    setCheckNote("");
    setSuggested(null);
    setConfidence(null);
    setMediaId(null);
    setJobId(null);
    setConfirmed(false);
    setTyp("");
  }

  function dropPin(nextLat: number, nextLng: number) {
    if (!origin) return;
    if (!insideRadius(nextLat, nextLng, origin.lat, origin.lng)) {
      setErr(t("radius_block"));
      return;
    }
    setErr("");
    setLat(nextLat);
    setLng(nextLng);
  }

  async function onSubmit(ev: FormEvent) {
    ev.preventDefault();
    if (!origin) return;
    setErr("");
    try {
      const res = await api<{ action: string; ticket: { public_id: string } }>("/v1/reports", {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({
          lat,
          lng,
          origin_lat: origin.lat,
          origin_lng: origin.lng,
          type: typ,
          severity,
          body,
          media_id: mediaId,
          category_confirmed: confirmed,
        }),
      });
      router.push(`/issues/${res.ticket.public_id}?action=${res.action}`);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Submit failed");
    }
  }

  if (!ready) return <main className="page">{t("locating")}</main>;
  if (!origin) return <LocationGate onReady={setOrigin} initial={block} />;

  const confLabel =
    confidence == null ? "" : confidence >= 0.75 ? "high" : confidence >= 0.45 ? "medium" : "low";

  return (
    <main className="wizard hide-chrome">
      <section className="phone">
        <ol className="stepper" aria-label="Progress">
          {(
            [
              [1, "photo"],
              [2, "pin"],
              [3, "type_step"],
            ] as const
          ).map(([n, key]) => (
            <li key={n} className={step === n ? "on" : step > n ? "done" : ""}>
              <span>{n}</span>
              {t(key)}
            </li>
          ))}
        </ol>
        <h1>{step === 1 ? t("photo") : step === 2 ? "Select the exact location" : "Issue Details"}</h1>
        <p className="lede">
          {step === 2
            ? "Drag the pin to mark the issue location. Pin must be within 20 km of Hyderabad."
            : step === 3
              ? "Tell us more about the issue"
              : t("pin_help")}
        </p>
        {photoIssue ? <div className="banner warn">{photoIssue}</div> : null}
        {checkNote ? <p className="muted">{checkNote}</p> : null}
        {err ? <div className="banner">{err}</div> : null}
        {busy ? <p className="muted">{busy}</p> : null}
        {suggested && confLabel && step === 3 ? (
          <div className="suggest">
            Suggested: <strong>{t(suggested as CopyKey)}</strong> · {confLabel}
          </div>
        ) : null}

        {step === 1 ? (
          <label className="drop">
            {preview ? <img src={preview} alt="Selected street photo" className="photo" /> : <span className="shutter" aria-hidden />}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              capture="environment"
              onChange={(e) => pickPhoto(e.target.files?.[0] || null)}
            />
          </label>
        ) : null}

        {step === 2 ? (
          <div className="map-frame tall">
            <WardMap pins={[]} draggable origin={origin} lockRadius center={{ lat, lng }} onDrop={dropPin} height="100%" />
          </div>
        ) : null}

        {step === 3 ? (
          <form id="report-form" onSubmit={onSubmit}>
            <div className="photo-row">
              {preview ? <img src={preview} alt="" /> : <span className="thumb" />}
              <label className="add-photo">
                + Add more photos
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={async (e) => {
                    const next = e.target.files?.[0] || null;
                    pickPhoto(next);
                    if (next) await upload(next);
                  }}
                />
              </label>
            </div>
            <p className="field-label">Issue Type</p>
            <div className="pill-row">
              {TYPES.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={typ === item ? "choice on" : "choice"}
                  onClick={() => {
                    setTyp(item);
                    setConfirmed(true);
                  }}
                >
                  {t(item)}
                </button>
              ))}
            </div>
            <p className="field-label">{t("severity")}</p>
            <div className="pill-row">
              {SEVERITIES.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={severity === item ? "choice on" : "choice"}
                  onClick={() => setSeverity(item)}
                >
                  {t(item)}
                </button>
              ))}
            </div>
            <p className="field-label">Description</p>
            <textarea
              rows={4}
              maxLength={250}
              value={body}
              placeholder="E.g. Large pothole near signal, causing trouble for vehicles..."
              onChange={(e) => setBody(e.target.value)}
            />
            <p className="count">{body.trim().length}/250</p>
          </form>
        ) : null}

        {step === 3 && !photoIssue && (!confirmed || !severity || body.trim().length < 20) ? (
          <p className="photo-warn">
            Choose the issue type, how serious it is, and write at least 20 characters. The photo must be one of those street problems.
          </p>
        ) : null}
        <div className="report-bar">
          {step > 1 ? (
            <button type="button" className="plain" onClick={() => setStep(step - 1)}>
              {t("back")}
            </button>
          ) : (
            <span />
          )}
          {step === 1 ? (
            <button
              type="button"
              className="btn red"
              disabled={!file || !!busy}
              onClick={async () => {
                if (!file) return;
                const ok = await upload(file);
                if (ok) setStep(2);
              }}
            >
              {t("next")}
            </button>
          ) : null}
          {step === 2 ? (
            <button type="button" className="btn red" onClick={() => setStep(3)}>
              {t("next")} →
            </button>
          ) : null}
          {step === 3 ? (
            <button
              className="btn red"
              type="submit"
              form="report-form"
              disabled={!!photoIssue || !confirmed || !severity || body.trim().length < 20}
            >
              {t("submit")}
            </button>
          ) : null}
        </div>
      </section>
    </main>
  );
}
