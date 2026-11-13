# City Bus Breakdown Tracker

Foundation for a React/Vite frontend and Flask/SQLAlchemy backend.

## Run locally

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python run.py
```

The health endpoint is available at `http://localhost:5000/api/health`.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` requests to Flask.

## Verify

```powershell
cd backend
pytest

cd ..\frontend
npm run build
```

The SQLite database is created at `backend/city_bus.db` by default. Set
`DATABASE_URL` and `FRONTEND_ORIGIN` in `backend/.env` to override defaults.

## Phase 3 dispatch modules

The deterministic dispatch engine is available independently of Flask routes:

```powershell
cd backend
python -c "from dispatch.dispatch_engine import DispatchEngine; print('Dispatch ready')"
```

`DispatchEngine` persists handler workloads, assignments, waiting/correction
queues, and routing audit records in SQLite. Use `DispatchEngine.initialize()`
inside an application context before dispatching reports.

## Phase 4 API

The Flask API now persists reports, depots, handlers, assignments, routing
decisions, status history, and queue entries in SQLite. The database is
initialized and seeded automatically when the app starts.

Submit a report with:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:5000/api/reports `
  -ContentType "application/json" `
  -Body '{"reporter_details":{"name":"Asha"},"identifier":"BUS1234-ROUTEA12","issue_code":"MECH","description":"Engine overheating"}'
```

Available endpoints include `/api/reports`, `/api/reports/<id>`,
`/api/reports/track/<id>`, `/api/handlers`, `/api/depots`,
`/api/routing/table`, `/api/routing/decisions`, and `/api/analytics`.

## Phase 5 frontend

The React control-room UI is available at `http://localhost:5173` after
starting Vite from `frontend`. It includes live operations overview, report
submission, report tracking, handler controls, routing management, and
Recharts analytics pages. All mutations refresh from the Flask API rather than
simulating assignment or status changes.
