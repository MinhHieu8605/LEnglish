from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.backgrounds.vocabulary_enricher import get_enricher


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown: background workers."""
    get_enricher().start()
    yield
    await get_enricher().stop()


app = FastAPI(
    title="LearnEnglish API",
    description="Backend API for the LearnEnglish application.",
    version="1.0.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

app.include_router(api_router)


@app.get("/", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "message": "LearnEnglish API is running."}
    