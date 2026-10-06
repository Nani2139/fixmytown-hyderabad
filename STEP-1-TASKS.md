# Step 1 — your work (auth)

Golden examples are already in the repo. Copy them. No map. No vision.

Accounts (Gemini, Groq, Neon, …) and the architecture sketch can continue in parallel. They are not a gate for this step.

## Golden files (read first)

| Pattern | File |
|---|---|
| Table | `apps/api/src/wardwatch_api/models.py` (`users`) |
| DB session | `apps/api/src/wardwatch_api/db.py` |
| Password + cookie | `apps/api/src/wardwatch_api/security.py` |
| Signup + `/me` | `apps/api/src/wardwatch_api/routers/auth.py` |
| Tests to copy | `apps/api/tests/test_signup.py` |

Local DB is a SQLite file `apps/api/wardwatch.db`. We will switch to Neon Postgres at deploy time. Same SQLAlchemy models.

## Your task: `POST /v1/auth/signin`

Replace the 501 stub in `auth.py`.

1. Find user by `body.email.lower()`.
2. If no user **or** `verify_password(body.password, user.password_hash)` is false → **401** `UNAUTHORIZED` with the **same** message. Never say “email not found”.
3. If ok → **200** `{ user, request_id }` and `set_session_cookie` like signup.
4. Add `apps/api/tests/test_signin.py`:
   - happy path: signup, then signin with same password → 200 + cookie
   - wrong password → 401
   - after signin, `GET /v1/auth/me` → 200

```powershell
cd apps\api
.\.venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

`POST /v1/auth/signin` in http://127.0.0.1:8000/docs should work after you implement it.

## Stop here

Do not add Next.js login forms yet. Next slice after signin tests are green: `/signup` and `/signin` pages.

Reply with pytest output when signin is done.
