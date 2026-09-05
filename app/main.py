import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import settings
from app.database.connection import init_db
from app.api.routes_chat import router as chat_router
from app.api.routes_customers import router as customers_router
from app.api.routes_tickets import router as tickets_router
from app.api.routes_kb import router as kb_router

BASE_DIR = Path(__file__).resolve().parent.parent

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Customer Operations Support Resolution Assistant (PS04)",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(chat_router)
app.include_router(customers_router)
app.include_router(tickets_router)
app.include_router(kb_router)

# Mount Static Assets
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
async def serve_index():
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "SupportGenie AI Backend Running. Static UI loading..."}

@app.get("/health")
async def health_check():
    return {
        "status": "HEALTHY",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "gemini_mode": "LIVE" if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here" else "GROUNDED_SYNTHESIS"
    }
