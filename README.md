# Govigyan FastAPI Backend

FastAPI backend scaffold for ERP inventory management with Supabase:
- Supabase Auth token verification
- Department-wise inventory stock and transfer APIs
- Render-ready deployment configuration

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` from `.env.example` and fill values:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `CORS_ORIGINS`

Optional for schema introspection script only:
- `DATABASE_URL`

Run locally:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

Docs:
- `http://localhost:4000/docs`
- `http://localhost:4000/openapi.json`

## API groups

- `health`
- `auth` (`/auth/login`, `/auth/me`)
- `inventory` (departments, items, stock, transactions, adjustments, transfers)
- `db` (basic connectivity check)

All paths are under prefix `API_PREFIX` (default `/api/v1`).

## GitHub push checklist

1. Verify `.env` is not tracked (already ignored by `.gitignore`).
2. Rotate any keys/passwords previously shared in chat.
3. Commit and push:

```bash
git add .
git commit -m "Prepare FastAPI backend for deployment"
git push origin main
```

## Deploy on Render

This repo includes `render.yaml` and `Procfile`.

On Render:
1. New Web Service -> connect this GitHub repo
2. Render auto-detects `render.yaml`
3. Set secret env vars:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `CORS_ORIGINS`
4. Deploy and test:
   - `/api/v1/health`
   - `/docs`
