"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, api, apiForm, type Ticket } from "../../lib/api";
import { useI18n, type CopyKey } from "../../lib/i18n";

type Draft = { note: string; file: File | null; err: string; busy: boolean };

const emptyDraft = (): Draft => ({ note: "", file: null, err: "", busy: false });

export default function AdminPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [err, setErr] = useState("");
  const [status, setStatus] = useState("all");
  const [type, setType] = useState("all");
  const [ward, setWard] = useState("all");
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});

  function load() {
    api<{ tickets: Ticket[] }>("/v1/admin/tickets?status=").then((d) => setTickets(d.tickets));
  }

  useEffect(() => {
    api<{ user: { role: string } }>("/v1/auth/me")
      .then((d) => {
        if (d.user.role !== "admin") setErr("Admin only.");
        else load();
      })
      .catch(() => setErr("Sign in as admin."));
  }, []);

  function draftOf(id: string) {
    return drafts[id] || emptyDraft();
  }

  function patchDraft(id: string, next: Partial<Draft>) {
    setDrafts((prev) => ({ ...prev, [id]: { ...emptyDraft(), ...prev[id], ...next } }));
  }

  function showOnMap(id: string) {
    router.push(`/?focus=${encodeURIComponent(id)}`);
  }

  async function act(id: string, next: string) {
    const draft = draftOf(id);
    const note = draft.note.trim();
    if (note.length < 20) {
      patchDraft(id, { err: t("note_short") });
      return;
    }
    if (next === "resolved" && !draft.file) {
      patchDraft(id, { err: t("need_fix_photo") });
      return;
    }
    patchDraft(id, { err: "", busy: true });
    try {
      let fix_media_id: string | undefined;
      if (next === "resolved" && draft.file) {
        const form = new FormData();
        form.append("file", draft.file);
        const uploaded = await apiForm<{ media_id: string }>("/v1/uploads", form);
        fix_media_id = uploaded.media_id;
      }
      await api(`/v1/admin/tickets/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: next, note, fix_media_id }),
      });
      setDrafts((prev) => ({ ...prev, [id]: emptyDraft() }));
      load();
    } catch (e) {
      patchDraft(id, { err: e instanceof ApiError ? e.message : "Update failed", busy: false });
    }
  }

  const wards = useMemo(() => Array.from(new Set(tickets.map((item) => item.ward).filter(Boolean))), [tickets]);
  const types = useMemo(() => Array.from(new Set(tickets.map((item) => item.type))), [tickets]);
  const today = new Date().toDateString();
  const shown = tickets.filter((ticket) => {
    if (status !== "all" && ticket.status !== status) return false;
    if (type !== "all" && ticket.type !== type) return false;
    if (ward !== "all" && ticket.ward !== ward) return false;
    return true;
  });

  if (err && tickets.length === 0) return <main className="page">{err}</main>;

  return (
    <main className="page admin-page">
      <div className="stat-row">
        <div>
          <b>{tickets.filter((x) => x.status === "open").length}</b>
          <span>Open Reports</span>
        </div>
        <div>
          <b>{tickets.filter((x) => x.status === "in_review").length}</b>
          <span>In Review</span>
        </div>
        <div>
          <b>{tickets.filter((x) => x.status === "resolved").length}</b>
          <span>Resolved</span>
        </div>
        <div>
          <b>{tickets.filter((x) => x.created_at && new Date(x.created_at).toDateString() === today).length}</b>
          <span>Today</span>
        </div>
      </div>
      <div className="admin-filters">
        <select value={ward} onChange={(e) => setWard(e.target.value)}>
          <option value="all">All Wards</option>
          {wards.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <select value={type} onChange={(e) => setType(e.target.value)}>
          <option value="all">All Types</option>
          {types.map((item) => (
            <option key={item} value={item}>
              {t(item as CopyKey)}
            </option>
          ))}
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="all">All Status</option>
          <option value="open">Open</option>
          <option value="in_review">In Review</option>
          <option value="resolved">Resolved</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>
      <div className="ticket-list">
        {shown.length === 0 ? <p className="muted">{t("empty")}</p> : null}
        {shown.map((ticket) => {
          const draft = draftOf(ticket.public_id);
          const open = ticket.status === "open" || ticket.status === "in_review";
          return (
            <article key={ticket.public_id} className="admin-card">
              <button type="button" className="admin-head" onClick={() => showOnMap(ticket.public_id)}>
                {ticket.media[0] ? <img src={`/backend${ticket.media[0].url}`} alt="" /> : <span className="thumb" />}
                <span>
                  <span className="title-row">
                    <strong>
                      {t(ticket.type as CopyKey)} · {ticket.ward}
                    </strong>
                    <span className={`pill ${ticket.status}`}>{ticket.status.replace("_", " ")}</span>
                  </span>
                  <span className="meta">
                    {ticket.days_open ?? 0} {t("days")} · {ticket.confirmation_count} {t("confirms")}
                    {ticket.circle_label ? ` · ${ticket.circle_label}` : ""}
                  </span>
                  <span className="admin-body">{ticket.body}</span>
                  <span className="tag-row">
                    <span className="choice on">{t(ticket.type as CopyKey)}</span>
                    {ticket.severity ? <span className={`sev ${ticket.severity}`}>{t(ticket.severity as CopyKey)}</span> : null}
                  </span>
                  <span className="show-map">{t("show_on_map")}</span>
                </span>
              </button>
              {open ? (
                <div className="admin-fields">
                  <label>
                    Note
                    <textarea
                      value={draft.note}
                      rows={3}
                      placeholder="At least 20 characters"
                      onChange={(e) => patchDraft(ticket.public_id, { note: e.target.value, err: "" })}
                    />
                    <small className={draft.note.trim().length >= 20 ? "ok-line" : "muted"}>
                      {draft.note.trim().length}/20
                    </small>
                  </label>
                  <label className="file-pick">
                    <span>{draft.file ? draft.file.name : t("fix_photo")}</span>
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      onChange={(e) => patchDraft(ticket.public_id, { file: e.target.files?.[0] || null, err: "" })}
                    />
                  </label>
                  {draft.err ? <p className="form-error">{draft.err}</p> : null}
                  <div className="admin-btns">
                    <button type="button" className="btn ok" disabled={draft.busy} onClick={() => act(ticket.public_id, "resolved")}>
                      {t("resolve")}
                    </button>
                    <button
                      type="button"
                      className="btn sand"
                      disabled={draft.busy || ticket.status === "in_review"}
                      onClick={() => act(ticket.public_id, "in_review")}
                    >
                      {t("review")}
                    </button>
                    <button type="button" className="btn red" disabled={draft.busy} onClick={() => act(ticket.public_id, "rejected")}>
                      {t("reject")}
                    </button>
                  </div>
                </div>
              ) : (
                <button type="button" className="btn sand wide" onClick={() => showOnMap(ticket.public_id)}>
                  {t("show_on_map")}
                </button>
              )}
            </article>
          );
        })}
      </div>
    </main>
  );
}
