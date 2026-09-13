import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.analytics import router as analytics_router
from src.api.routes.companies import router as companies_router
from src.api.routes.health import router as health_router

app = FastAPI(
    title="N100 Financial Intelligence API",
    description="Financial intelligence and analytics API for the N100 universe.",
    version="1.0.0",
)

# CORS middleware
# Internal-use API: allow requests from all origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log HTTP method, path, and response time for every request."""
    start_time = time.perf_counter()

    response = await call_next(request)

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    print(
        f"{request.method} {request.url.path} "
        f"{response.status_code} {elapsed_ms:.2f} ms"
    )

    return response


app.include_router(health_router)
app.include_router(companies_router)
app.include_router(analytics_router)


@app.get("/")
def root():
    """Return basic API information."""
    return {
        "name": "N100 Financial Intelligence API",
        "version": "1.0.0",
        "status": "ok",
    }