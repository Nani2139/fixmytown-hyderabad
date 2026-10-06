from __future__ import annotations

import json
import math
import os
import re
import urllib.request

from sqlalchemy.orm import Session

from wardwatch_api.embed import TOKEN, embed_semantic
from wardwatch_api.geo import RADIUS_M, haversine_m
from wardwatch_api.models import Ticket
from wardwatch_api.vectors import dense_rank, ensure_indexed

REFUSE = "I don’t have that in the data."
GROQ_MODEL = "openai/gpt-oss-20b"
RRF_K = 60
TICKET_ID = re.compile(r"ww-\d{2}-\d+", re.I)
STOP = {
    "the", "a", "an", "is", "was", "are", "were", "of", "to", "in", "on", "near",
    "me", "my", "that", "this", "about", "what", "happened", "there", "any", "for",
    "and", "with", "from", "have", "has", "been", "does", "did", "how", "why",
}
STATUS_WORDS = {
    "resolved": ("resolved", "closed", "fixed"),
    "rejected": ("rejected", "closed"),
    "open": ("open",),
    "in_review": ("review",),
}


def ticket_blob(ticket: Ticket) -> str:
    words = STATUS_WORDS.get(ticket.status, (ticket.status,))
    return " ".join(
        part
        for part in (
            ticket.public_id,
            ticket.title,
            ticket.type,
            ticket.ward,
            ticket.neighborhood,
            ticket.circle,
            ticket.severity,
            " ".join(words),
            ticket.body,
            ticket.resolve_note or "",
        )
        if part
    )


def tokenize(text: str) -> list[str]:
    ids = [match.lower() for match in TICKET_ID.findall(text)]
    words = TOKEN.findall(text.lower())
    stems = [word[:-1] for word in words if len(word) > 4 and word.endswith("s")]
    return [word for word in ids + words + stems if word not in STOP]


def bm25_rank(query: str, docs: list[tuple[str, str]], k1: float = 1.5, b: float = 0.75) -> list[str]:
    """Sparse half of hybrid search. Only documents that share a term are returned."""
    q_terms = tokenize(query)
    if not q_terms or not docs:
        return []
    corpus = [(doc_id, tokenize(text)) for doc_id, text in docs]
    avgdl = sum(len(tokens) for _doc_id, tokens in corpus) / len(corpus)
    if avgdl == 0:
        return []
    df: dict[str, int] = {}
    for _doc_id, tokens in corpus:
        for term in set(tokens):
            df[term] = df.get(term, 0) + 1
    scored: list[tuple[float, str]] = []
    total = len(corpus)
    for doc_id, tokens in corpus:
        if not tokens:
            continue
        tf: dict[str, int] = {}
        for term in tokens:
            tf[term] = tf.get(term, 0) + 1
        score = 0.0
        for term in q_terms:
            freq = tf.get(term)
            if not freq:
                continue
            n = df.get(term, 0)
            idf = math.log(1 + (total - n + 0.5) / (n + 0.5))
            denom = freq + k1 * (1 - b + b * len(tokens) / avgdl)
            score += idf * (freq * (k1 + 1)) / denom
        if score > 0:
            scored.append((score, doc_id))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [doc_id for _score, doc_id in scored]


def rrf(rankings: list[list[str]], k: int = RRF_K) -> list[str]:
    """Reciprocal rank fusion. A ticket in both the vector list and the keyword list wins."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [doc_id for doc_id, _score in ordered]


def _exact_ids(question: str, tickets: list[Ticket]) -> list[str]:
    wanted = {match.lower() for match in TICKET_ID.findall(question)}
    if not wanted:
        return []
    return [ticket.public_id for ticket in tickets if ticket.public_id.lower() in wanted]


def hybrid_rank(question: str, tickets: list[Ticket]) -> list[Ticket]:
    if not tickets:
        return []
    blobs = [(ticket.public_id, ticket_blob(ticket)) for ticket in tickets]
    by_id = {ticket.public_id: ticket for ticket in tickets}
    sparse = bm25_rank(question, blobs)[:8]
    exact = _exact_ids(question, tickets)
    dense: list[str] = []
    query_vec = embed_semantic(question, "RETRIEVAL_QUERY")
    if query_vec:
        try:
            ensure_indexed(blobs)
            dense = dense_rank(query_vec, set(by_id))
        except Exception:
            dense = []
    order = rrf([ranking for ranking in (dense, sparse, exact) if ranking])
    return [by_id[public_id] for public_id in order[:5] if public_id in by_id]


def ask_city(
    db: Session,
    question: str,
    type_filter: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
) -> dict:
    tickets = []
    for ticket in db.query(Ticket).all():
        if lat is not None and lng is not None and haversine_m(lat, lng, ticket.lat, ticket.lng) > RADIUS_M:
            continue
        if type_filter and ticket.type != type_filter:
            continue
        tickets.append(ticket)
    ranked = hybrid_rank(question, tickets)
    if not ranked:
        return {"answer": REFUSE, "sources": []}

    top = [
        (
            "ticket",
            {
                "public_id": ticket.public_id,
                "title": ticket.title,
                "status": ticket.status,
                "type": ticket.type,
                "body": ticket.body,
                "resolve_note": ticket.resolve_note,
                "neighborhood": ticket.neighborhood,
                "ward": ticket.ward,
                "circle": ticket.circle,
            },
        )
        for ticket in ranked
    ]
    answer = _generate(question, top)
    if "have that in the data" in answer:
        return {"answer": REFUSE, "sources": []}
    sources = [
        {
            "kind": "ticket",
            "id": row["public_id"],
            "title": row["title"],
            "href": f"/issues/{row['public_id']}",
        }
        for _kind, row in top
    ]
    return {"answer": answer, "sources": sources}


def _listed(top: list) -> str:
    lines = ["From tickets in this circle:"]
    for _kind, row in top[:5]:
        lines.append(f"- {row['public_id']}: {row['title']} ({row['status']})")
    return "\n".join(lines)


def _generate(question: str, top: list) -> str:
    key = os.getenv("GROQ_API_KEY", "").strip()
    excerpts = []
    for _kind, row in top:
        excerpts.append(
            f"{row['public_id']} ({row['type']}, {row['status']}, {row.get('ward') or row['neighborhood']}, {row.get('circle') or ''}): {row['body']}"
            + (f" Note: {row['resolve_note']}" if row.get("resolve_note") else "")
        )
    context = "\n".join(excerpts)
    if not key:
        return _listed(top)

    prompt = (
        "Answer only from the rows below. Cite ticket ids like WW-24-0001. "
        "Resolved means the issue is closed and fixed. Say that plainly when the row is resolved, and include the note. "
        "If the rows are about a different subject entirely, say exactly: "
        f"{REFUSE}\n\nROWS:\n{context}\n\nQUESTION: {question}"
    )
    body = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are FixMyTown Ask. Use only provided rows."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": "FixMyTown/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode())
        text = (payload["choices"][0]["message"].get("content") or "").strip()
        return text or _listed(top)
    except Exception:
        return _listed(top)
