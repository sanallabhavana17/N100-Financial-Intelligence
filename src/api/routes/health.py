from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    """Return API health status."""
    return {
        "status": "ok"
    }