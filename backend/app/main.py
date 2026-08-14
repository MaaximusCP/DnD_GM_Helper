from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import router
from app.config import get_settings
from app.infrastructure.database import Database


@asynccontextmanager
async def lifespan(_: FastAPI):
    Database(get_settings().database_path).initialize()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.9.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix=settings.api_prefix)

frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if (frontend_dist / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="frontend-assets")


@app.get("/", response_model=None)
def root():
    if (frontend_dist / "index.html").is_file():
        return FileResponse(frontend_dist / "index.html")
    return {"name": settings.app_name, "docs": "/docs", "health": "/api/health"}
