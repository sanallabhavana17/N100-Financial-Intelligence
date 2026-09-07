from fastapi import FastAPI

from src.api.routes.health import router as health_router


app = FastAPI(
    title="N100 Financial Intelligence API",
    description="Financial intelligence and analytics API for the N100 universe.",
    version="1.0.0",
)


app.include_router(health_router)


@app.get("/")
def root():
    """Return basic API information."""
    return {
        "name": "N100 Financial Intelligence API",
        "version": "1.0.0",
        "status": "ok",
    }
