# FixMyTown

Live site: https://fixmytown.vercel.app

Civic street-issue map for **Hyderabad**. Your live location opens a **20 km** circle. You only see, report, and ask about issues inside that circle.

Issue types: waterlogging, open manhole, garbage black spot, streetlight out, pothole, road left dug, illegal dumping, stagnant water. Each report carries a GHMC circle, a ward, and a severity. Vision suggests a category. You confirm. Duplicates within 50 m attach as +1. “Still there” works only within 400 m of the pin. Marking an issue fixed requires a photo of the repair.

## Run locally

Terminal 1 — API (starts empty; reports you file are the only pins):

```powershell
cd apps\api
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"
uvicorn wardwatch_api.main:app --reload --app-dir src
```

http://127.0.0.1:8000/docs

Terminal 2 — web:

```powershell
cd apps\web
npm install
npm run dev
```

http://localhost:3000

If you are outside Hyderabad, the map stays closed. Use **Preview from Charminar** to open the circle. It starts empty until you file a report.

Optional vision worker (API already runs jobs in the background):

```powershell
cd apps\api
.\.venv\Scripts\activate
python -m wardwatch_api.worker
```

## Sign in

The site uses **Continue with Google** (Firebase). The first Google sign-in creates the profile. Apple is left off: Firebase can do it, but it needs an Apple Developer account, a Services ID, and a private key.

Put the Firebase web app values in `apps/api/.env`, then restart the API:

`FIREBASE_API_KEY`, `FIREBASE_AUTH_DOMAIN`, `FIREBASE_PROJECT_ID`, `FIREBASE_APP_ID`

In the Firebase console, enable Authentication → Google, and add `localhost` as an authorized domain.

`ADMIN_EMAILS` — comma-separated Gmail addresses that should see the admin queue.

## Optional keys (never commit)

Put these in `apps/api/.env` (that file stays off git):

`GEMINI_API_KEY` — photo labels on a new report, and the embeddings Ask stores for search. Without it, you pick the type yourself and Ask uses keyword search only.  
`GROQ_API_KEY` — Ask writes a sentence from the tickets hybrid search found. Without it, Ask lists those tickets.

## Tests

```powershell
cd apps\api
.\.venv\Scripts\pytest
```

Covers health, ready, auth, status machine, duplicate merge, 20 km rejection, still-there distance, and Ask retrieval (keyword rank, vector rank, RRF, refuse when nothing matches).

## Live

Website: https://fixmytown.vercel.app

API: https://fixmytown-api.onrender.com
