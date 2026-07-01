from fastapi import FastAPI

from app.api.v1.router import api_router

app = FastAPI(
    title="LearnEnglish API",
    description="Backend API for the LearnEnglish application.",
    version="1.0.0",
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "message": "LearnEnglish API is running."}
