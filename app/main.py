from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.api.routes.health import router as health_router
from app.api.routes.voice import router as voice_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # FIX ME: Add database initialization and closing
    yield
    # FIX ME: Add database closing

app = FastAPI(
    title="Care Navigator",
    description="A platform for finding care for your loved ones",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router, tags=["health"])
app.include_router(voice_router, tags=["voice"])
app.mount("/", StaticFiles(directory="static", html=True), name="static")