from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.routers import health, settings, movies, shows, sync as sync_router


def create_app() -> FastAPI:
    application = FastAPI(title="Subtitle Sync", version="1.0.0")

    application.include_router(health.router, prefix="/api")
    application.include_router(settings.router, prefix="/api")
    application.include_router(movies.router, prefix="/api")
    application.include_router(shows.router, prefix="/api")
    application.include_router(sync_router.router, prefix="/api")

    static_dir = Path(__file__).parent / "static"
    application.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @application.get("/")
    async def index():
        return FileResponse(str(static_dir / "index.html"))

    return application


app = create_app()
