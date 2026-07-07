import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.routes.submissions import router as submissions_router

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Heritage Sentinel AI",
    description="Multi-agent system for UNESCO heritage site submission review",
    version="0.1.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Base origins — always allowed (local dev + Docker Compose)
_origins = [
    "http://localhost:3000",   # Direct Next.js dev server
    "http://localhost",        # Nginx HTTP (before TLS redirect)
    "https://localhost",       # Nginx TLS — primary access path via docker compose
    "http://localhost:8000",   # Direct backend access during local dev
]

# Production / Railway: add any extra origins from env vars
# Set FRONTEND_URL on the Railway backend service to your frontend's Railway URL
# e.g. https://heritage-vanguards-frontend.up.railway.app
for _env_var in ("FRONTEND_URL", "RAILWAY_PUBLIC_DOMAIN"):
    _val = os.getenv(_env_var)
    if _val:
        if not _val.startswith("http"):
            _val = f"https://{_val}"
        if _val not in _origins:
            _origins.append(_val)

# Allow ALL origins in development mode for convenience
if os.getenv("ENV", "development") == "development":
    _allow_origins = ["*"]
else:
    _allow_origins = _origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(submissions_router)
app.mount("/uploads", StaticFiles(directory="/data/uploads", check_dir=False), name="uploads")


@app.get("/health")
@limiter.limit("60/minute")
async def health(request: Request):
    return {"status": "ok", "service": "heritage-sentinel-ai"}
