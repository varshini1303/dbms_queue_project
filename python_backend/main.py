import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from database import engine, SessionLocal, Base
from seed import seed_database
from routes import auth, services, counters, tokens, queue, contact

# Initialize DB tables & seed data
Base.metadata.create_all(bind=engine)
_init_db = SessionLocal()
try:
    seed_database(_init_db)
finally:
    _init_db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Bank Queue Management System",
    description="Unified Bank Queue Web Application & REST API",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS Configuration
# Accepts public cloud frontend, localhost, or any configured custom origin
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
origins = [
    "https://queue-wiz-home.lovable.app",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "*",
]
if allowed_origins_env:
    origins.extend([o.strip() for o in allowed_origins_env.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(CURRENT_DIR, "static")
TEMPLATES_DIR = os.path.join(CURRENT_DIR, "templates")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include API Routers
app.include_router(auth.router)
app.include_router(services.router)
app.include_router(counters.router)
app.include_router(tokens.router)
app.include_router(queue.router)
app.include_router(contact.router)


@app.get("/api/v1/config")
def get_system_config():
    """Returns dynamic configuration for client connectivity."""
    return {
        "backend_url": os.getenv("BACKEND_URL", ""),
        "service": "Bank Queue Management System",
        "version": "2.0.0",
        "theme": "Navy Blue, Black & White",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Bank Queue Full Application",
        "frontend": "https://queue-wiz-home.lovable.app",
        "local_app": "http://127.0.0.1:8000",
        "database": "connected",
    }


# Root route serving the full-featured SPA
@app.get("/", response_class=HTMLResponse)
def index_page():
    index_file = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            html = f.read()
        # Inject BACKEND_URL if configured in environment
        backend_url = os.getenv("BACKEND_URL", "")
        if backend_url:
            html = html.replace("</head>", f"<script>window.BACKEND_URL = '{backend_url}';</script></head>")
        return HTMLResponse(content=html)
    return HTMLResponse("<h1>BankQueue System: index.html template not found</h1>")


@app.get("/login", response_class=HTMLResponse)
def login_page():
    login_file = os.path.join(TEMPLATES_DIR, "login.html")
    if os.path.exists(login_file):
        with open(login_file, "r", encoding="utf-8") as f:
            html = f.read()
        backend_url = os.getenv("BACKEND_URL", "")
        if backend_url:
            html = html.replace("</head>", f"<script>window.BACKEND_URL = '{backend_url}';</script></head>")
        return HTMLResponse(content=html)
    return HTMLResponse("<h1>Login page template not found</h1>")


@app.get("/register", response_class=HTMLResponse)
def register_page():
    login_file = os.path.join(TEMPLATES_DIR, "login.html")
    if os.path.exists(login_file):
        with open(login_file, "r", encoding="utf-8") as f:
            html = f.read()
        html = html.replace("<body>", "<body><script>document.addEventListener('DOMContentLoaded', () => { const t = document.getElementById('tab-register'); if(t) t.click(); });</script>")
        return HTMLResponse(content=html)
    return HTMLResponse("<h1>Register page template not found</h1>")


@app.get("/live", response_class=HTMLResponse)
def live_page():
    """Shortcut to live queue view."""
    index_file = os.path.join(TEMPLATES_DIR, "index.html")
    with open(index_file, "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("<body>", "<body><script>window.location.hash='#live';</script>")
    return HTMLResponse(content=html)
