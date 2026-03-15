from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import settings

app = FastAPI(title="School Admin MVP", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.mount("/assets", StaticFiles(directory=settings.data_dir), name="assets")

if settings.frontend_dist_dir.exists():
    frontend_assets_dir = settings.frontend_dist_dir / "app-assets"
    if frontend_assets_dir.exists():
        app.mount("/app-assets", StaticFiles(directory=frontend_assets_dir), name="frontend-assets")

    @app.get("/", include_in_schema=False)
    def frontend_index() -> FileResponse:
        return FileResponse(settings.frontend_dist_dir / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith(("api/", "assets/")):
            raise RuntimeError("unexpected-spa-fallback")
        return FileResponse(settings.frontend_dist_dir / "index.html")
