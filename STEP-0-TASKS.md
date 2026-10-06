# Step 0 — your work

I wrote the **golden examples**. You copy the pattern. Do not start auth, map, or vision.

When you are done, reply in chat with: what `/health` vs `/ready` means, in your own words, plus any test output.

---

## 1. Accounts (can finish later this week)

Create free accounts. **Do not paste keys in chat.**

- [ ] Google AI Studio (Gemini) — vision later
- [ ] Groq — Ask the city later
- [ ] Neon, Upstash, Cloudflare R2, Vercel, Render — deploy later

## 2. API: `GET /ready` (main coding task)

Golden file: `apps/api/src/wardwatch_api/main.py` → `GET /health`  
Helpers: `errors.py`, `city.py`

Implement `GET /ready` in the same file, under the comment block.

| If | Then |
|---|---|
| `load_city()` works | `200` `{ "status": "ok", "service": "api", "city": "Bengaluru", "request_id": "..." }` |
| File missing or bad JSON | `503` using `error_response(..., code="NOT_READY", ...)` |

Rules:

- Reuse `request.state.request_id`
- Set `X-Request-Id` on the response
- No database
- Copy `apps/api/tests/test_health.py` → `test_ready.py` and assert 200 + city name

Run: `pytest` from `apps/api` (with venv on). Both health and ready tests should pass.

## 3. Web: `/privacy` (clone the home page)

Golden file: `apps/web/app/page.tsx`

Create `apps/web/app/privacy/page.tsx` (App Router: a folder named `privacy` with `page.tsx`).

Same tokens (the page inherits `globals.css`). Three short paragraphs:

1. Photos are stored; we strip EXIF GPS from image files.
2. Location on the map is the pin you drop (or GPS you allow), stored as lat/lng on the ticket.
3. This is a civic prototype, not a government website.

Add a link from the home page to `/privacy`. I left that for you too.

## 4. Paper (5 minutes)

Draw: Browser → Next.js → FastAPI → (later) Postgres. Bring it next time or describe it.

## Done when

- `GET /health` and `GET /ready` work
- `pytest` has tests for both
- `/` and `/privacy` render
- You can explain health vs ready without reading this file

Then we start **Step 1: sign up / sign in**. Not before.
