from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check():
    return {
        "ok": True,
        "service": "fastapi-backend",
        "time": datetime.now(timezone.utc).isoformat(),
    }
