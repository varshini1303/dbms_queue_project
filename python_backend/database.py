import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

# Check if running in Vercel Serverless environment
if os.getenv("VERCEL"):
    DB_PATH = "/tmp/bank_queue.db"
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "bank_queue.db")

# Default connection strings
MYSQL_URL = os.getenv("MYSQL_URL", "mysql+pymysql://root:@localhost:3306/bank_queue")
SQLITE_URL = f"sqlite:///{DB_PATH}"

# Check environment override (e.g. from Vercel / Render cloud DB)
ENV_DB_URL = os.getenv("DATABASE_URL")

engine = None
ACTIVE_DB_TYPE = "sqlite"

def init_engine():
    global engine, ACTIVE_DB_TYPE
    if ENV_DB_URL:
        try:
            engine = create_engine(ENV_DB_URL)
            with engine.connect() as conn:
                pass
            ACTIVE_DB_TYPE = "custom"
            print(f"[Database] Connected to Custom DB: {ENV_DB_URL}")
            return
        except Exception as e:
            print(f"[Database] Failed to connect to DATABASE_URL: {e}")

    # Try XAMPP MySQL first
    try:
        # Pre-create database in XAMPP MySQL if it doesn't exist
        import pymysql
        conn_pre = pymysql.connect(host="localhost", user="root", password="", port=3306, connect_timeout=2)
        with conn_pre.cursor() as cur:
            cur.execute("CREATE DATABASE IF NOT EXISTS bank_queue CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn_pre.close()

        # Connect SQLAlchemy to XAMPP MySQL
        engine = create_engine(MYSQL_URL, pool_pre_ping=True, pool_recycle=3600)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        ACTIVE_DB_TYPE = "mysql"
        print("[Database] Successfully connected to XAMPP MySQL (Database: bank_queue)")
        return
    except Exception as e:
        print(f"[Database] XAMPP MySQL not reachable ({e}). Falling back to local SQLite.")

    # Fallback to SQLite
    engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    ACTIVE_DB_TYPE = "sqlite"
    print(f"[Database] Active database: SQLite ({DB_PATH})")

init_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
