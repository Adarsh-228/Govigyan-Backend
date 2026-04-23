from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.core.supabase_client import supabase_admin
from app.schemas.inventory import StockAdjustmentRequest, StockTransferRequest
from app.services.inventory_service import apply_stock_adjustment, apply_stock_transfer

router = APIRouter(prefix="/inventory", tags=["inventory"], dependencies=[Depends(get_current_user)])


@router.get("/departments")
def list_departments():
    response = supabase_admin.table("departments").select("*").order("name").execute()
    return {"data": response.data}


@router.get("/items")
def list_items(
    item_type: str | None = Query(default=None),
    active_only: bool = Query(default=True),
):
    query = supabase_admin.table("items").select("*").order("name")
    if item_type:
        query = query.eq("item_type", item_type)
    if active_only:
        query = query.eq("is_active", True)
    response = query.execute()
    return {"data": response.data}


@router.get("/stock")
def list_stock(
    department_id: UUID | None = Query(default=None),
    item_id: UUID | None = Query(default=None),
    low_stock_only: bool = Query(default=False),
):
    query = supabase_admin.table("inventory_stock").select("*")
    if department_id:
        query = query.eq("department_id", str(department_id))
    if item_id:
        query = query.eq("item_id", str(item_id))

    response = query.order("updated_at", desc=True).execute()
    data = response.data or []

    if low_stock_only:
        data = [
            row
            for row in data
            if row.get("reorder_level") is not None
            and float(row.get("quantity", 0)) <= float(row["reorder_level"])
        ]

    return {"data": data, "count": len(data)}


@router.get("/transactions")
def list_transactions(
    item_id: UUID | None = Query(default=None),
    from_department_id: UUID | None = Query(default=None),
    to_department_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    query = supabase_admin.table("inventory_transactions").select("*").order("created_at", desc=True).limit(limit)
    if item_id:
        query = query.eq("item_id", str(item_id))
    if from_department_id:
        query = query.eq("from_department_id", str(from_department_id))
    if to_department_id:
        query = query.eq("to_department_id", str(to_department_id))

    response = query.execute()
    return {"data": response.data}


@router.post("/stock/adjust")
def adjust_stock(request: StockAdjustmentRequest, current_user=Depends(get_current_user)):
    result = apply_stock_adjustment(request=request, user_id=str(current_user.id))
    return {"message": "Stock adjusted successfully", "data": result}


@router.post("/stock/transfer")
def transfer_stock(request: StockTransferRequest, current_user=Depends(get_current_user)):
    result = apply_stock_transfer(request=request, user_id=str(current_user.id))
    return {"message": "Stock transferred successfully", "data": result}
