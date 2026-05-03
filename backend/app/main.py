from __future__ import annotations

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
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

SUSPENDED_NOTICE_HTML = """<!doctype html>
<html lang="ja">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>School Admin MVP</title>
  </head>
  <body>
    <main>
      <p>School Admin MVP</p>
      <h1>公開停止中</h1>
      <p>現在このデモは公開を停止しています. 何かあれば me@argo11.devまで</p>
    </main>
  </body>
</html>
"""


@app.middleware("http")
async def reject_api_while_suspended(request: Request, call_next):
    if settings.demo_suspended and request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=410,
            content={
                "detail": "Demo suspended",
                "message": "現在このデモは公開を停止しています. 何かあれば me@argo11.devまで",
            },
        )
    return await call_next(request)


def render_notice_page() -> HTMLResponse:
    return HTMLResponse(SUSPENDED_NOTICE_HTML)

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
else:
    @app.get("/", include_in_schema=False)
    def frontend_index() -> HTMLResponse:
        return render_notice_page()

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> HTMLResponse:
        if full_path.startswith(("api/", "assets/")):
            raise RuntimeError("unexpected-spa-fallback")
        return render_notice_page()
