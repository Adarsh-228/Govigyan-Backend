from fastapi import APIRouter, HTTPException, Query

from app.core.supabase_client import supabase_admin

router = APIRouter(prefix="/db", tags=["db"])


@router.get("/check")
def db_check(table: str = Query(default="profiles", min_length=1)):
    try:
        response = supabase_admin.table(table).select("*").limit(1).execute()
    except Exception as exc:  # pragma: no cover - network/db provider
        raise HTTPException(status_code=400, detail=f"Database check failed: {exc}") from exc

    return {"table": table, "rows": response.data}
