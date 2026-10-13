# Bank Queue Management System — Full-Stack Web Application

A complete, fully functional, production-ready **Bank Queue Management System** implemented in **Python** (FastAPI, SQLAlchemy, SQLite/PostgreSQL, WebSockets) with the professional bank theme (Navy Blue, Black, and White) matching [queue-wiz-home.lovable.app](https://queue-wiz-home.lovable.app).

---

## 🌟 Highlights

- **Zero Mock Data**: 100% of services, tokens, counters, waiting queues, and live updates are persisted in the database.
- **One Unified Web Application**: Runs the complete user-facing website, customer queue tracker, live queue status display, staff/admin operations console, and REST API from a single server.
- **Dynamic `BACKEND_URL` Support**: The frontend automatically uses the current origin (`window.location.origin`) or any configured environment variable (`BACKEND_URL`) for seamless public cloud deployment.
- **Real-Time Live Updates**: Full WebSocket (`/ws`) event streaming + automated 5-second polling fallback.
- **Advance Token Booking**: Customers can book up to 2 days ahead, select slots, and receive instant digital tickets with wait time estimation and arrival guidance.
- **Staff & Admin Management Console**: Call next customer, complete service, recall/ring customer, mark no-show, and dispense walk-in tickets.

---

## 🚀 Quick Start (Running Locally)

```powershell
cd C:\Users\Asus\.gemini\antigravity\scratch\bank_queue_backend\python_backend
py run_server.py
```

Open your browser to:
- **Unified Web Application**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Staff / Admin Queue Console**: [http://127.0.0.1:8000/staff](http://127.0.0.1:8000/staff)
- **Live Branch Queue Board**: [http://127.0.0.1:8000/live](http://127.0.0.1:8000/live)
- **Interactive Swagger Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Run automated verification tests:
```powershell
py test_api.py
```

---

## 🌐 Public Cloud Deployment (Render / Railway / Docker)

### Option A: 1-Click Deploy on Render
1. Push this project to GitHub.
2. In Render, select **New Web Service** (or use `render.yaml` Blueprint).
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Set Environment Variable:
   - `BACKEND_URL`: `https://your-service-name.onrender.com`
4. The service will be live on HTTPS with full public access.

### Option B: Docker Container
```bash
docker build -t bank-queue-app .
docker run -p 8000:8000 -e BACKEND_URL=http://localhost:8000 bank-queue-app
```

---

## 🔗 Connecting to the Lovable Cloud Link (`queue-wiz-home.lovable.app`)

To connect the separate Lovable cloud frontend to your deployed backend:
1. In Lovable, add the environment variable `VITE_BACKEND_URL=https://your-backend.onrender.com`.
2. Drop in [`lovable_integration/api.ts`](file:///C:/Users/Asus/.gemini/antigravity/scratch/bank_queue_backend/lovable_integration/api.ts).
3. The Lovable web app will immediately query and persist real-time tokens through your live backend.

---

## 📡 Core API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/services` | Fetches active banking services (Cash Deposit, Withdrawal, Accounts, etc.) |
| `GET` | `/api/v1/counters` | Fetches counter desks (Counters 1 to 4) with current token & waiting count |
| `POST` | `/api/v1/tokens/book` | Books online token up to 2 days ahead (`A108`, `B201`, etc.) |
| `POST` | `/api/v1/tokens/walk-in` | Staff instant token issuance for walk-in visitors |
| `GET` | `/api/v1/tokens/track/{token}` | Real-time queue tracker (position, wait time, arrival advice) |
| `GET` | `/api/v1/queue/live` | Live queue status, total waiting, served count, and update stream |
| `GET` | `/api/v1/queue/manage-tokens` | Roster of all tokens for the staff control table |
| `POST` | `/api/v1/counters/{id}/call-next` | Advance queue: calls next waiting customer |
| `POST` | `/api/v1/counters/{id}/complete` | Marks current token service as completed |
| `POST` | `/api/v1/counters/{id}/recall` | Re-announces / recalls current customer |
| `POST` | `/api/v1/counters/{id}/skip` | Marks current customer as no-show |
| `POST` | `/api/v1/contact` | Submits branch support inquiries |
| `WS` | `/ws` | Real-time WebSocket connection for queue broadcasting |
