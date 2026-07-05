from fastapi import FastAPI

from app.api.v1.router import api_router

app = FastAPI(
    title="LearnEnglish API",
    description="Backend API for the LearnEnglish application.",
    version="1.0.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
)

app.include_router(api_router)


@app.get("/", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "message": "LearnEnglish API is running."}
    