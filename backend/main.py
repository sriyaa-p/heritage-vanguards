from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.submissions import router as submissions_router

app = FastAPI(
    title="Heritage Sentinel AI",
    description="Multi-agent system for UNESCO heritage site submission review",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(submissions_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "heritage-sentinel-ai"}
