import os
import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    backend_url = os.getenv("BACKEND_URL", f"http://127.0.0.1:{port}")

    print("=" * 65)
    print(" Bank Queue Management System — Unified Web Application")
    print(f" Live Web App:      http://127.0.0.1:{port}")
    print(f" Staff Console:     http://127.0.0.1:{port}/staff")
    print(f" Live Queue Board:  http://127.0.0.1:{port}/live")
    print(f" Interactive Docs:  http://127.0.0.1:{port}/docs")
    print(f" Cloud Frontend:    https://queue-wiz-home.lovable.app")
    print(f" Configured URL:    {backend_url}")
    print("=" * 65)

    uvicorn.run("main:app", host=host, port=port, reload=False)
