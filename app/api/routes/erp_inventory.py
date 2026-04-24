from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.core.supabase_client import supabase_admin

router = APIRouter(prefix="/api", tags=["erp-inventory"], dependencies=[Depends(get_current_user)])


class ItemPayload(BaseModel):
    name: str
    sku: str | None = None
    category: str | None = None
    status: str | None = None
    item_type: str = "general"
    unit: str = "unit"
    description: str | None = None
    is_active: bool = True


class StockInOutPayload(BaseModel):
    item_id: UUID
    department_id: UUID
    quantity: float = Field(gt=0)
    notes: str | None = None
    unit_cost: float | None = Field(default=None, ge=0)


class QuantityUpdatePayload(BaseModel):
    department_id: UUID
    quantity: float = Field(ge=0)


class ThresholdUpdatePayload(BaseModel):
    department_id: UUID | None = None
    reorder_level: float = Field(ge=0)


def _range_to_days(range_value: str) -> int:
    return {"7d": 7, "30d": 30, "90d": 90}.get(range_value, 30)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_or_create_stock(item_id: str, department_id: str) -> dict:
    response = (
        supabase_admin.table("inventory_stock")
        .select("*")
        .eq("item_id", item_id)
        .eq("department_id", department_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    if rows:
        return rows[0]

    created = (
        supabase_admin.table("inventory_stock")
        .insert(
            {
                "item_id": item_id,
                "department_id": department_id,
                "quantity": 0,
                "updated_at": _now_iso(),
            }
        )
        .execute()
    )
    created_rows = created.data or []
    if not created_rows:
        raise HTTPException(status_code=500, detail="Failed to initialize stock row")
    return created_rows[0]


def _record_transaction(payload: dict) -> None:
    supabase_admin.table("inventory_transactions").insert(payload).execute()


@router.get("/dashboard/inventory-summary")
def dashboard_inventory_summary():
    items = supabase_admin.table("items").select("id", count="exact").execute()
    stock = supabase_admin.table("inventory_stock").select("quantity,reorder_level").execute().data or []
    low_stock = [
        row
        for row in stock
        if row.get("reorder_level") is not None and float(row.get("quantity", 0)) <= float(row["reorder_level"])
    ]
    critical = [
        row
        for row in stock
        if row.get("reorder_level") is not None and float(row.get("quantity", 0)) <= float(row["reorder_level"]) * 0.5
    ]
    return {
        "total_items": items.count or 0,
        "low_stock_count": len(low_stock),
        "critical_stock_count": len(critical),
    }


@router.get("/dashboard/stock-trend")
def dashboard_stock_trend(range: str = Query(default="30d", pattern="^(7d|30d|90d)$")):
    days = _range_to_days(range)
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    txns = (
        supabase_admin.table("inventory_transactions")
        .select("created_at,transaction_type,quantity")
        .gte("created_at", start)
        .order("created_at")
        .execute()
        .data
        or []
    )

    points: dict[str, float] = {}
    for txn in txns:
        day = (txn.get("created_at") or "")[:10]
        q = float(txn.get("quantity", 0))
        t = txn.get("transaction_type", "")
        delta = q if ("in" in t or t == "transfer") else -q
        points[day] = points.get(day, 0) + delta

    return {"range": range, "points": [{"date": k, "net_change": v} for k, v in sorted(points.items())]}


@router.get("/dashboard/feed-burn-rate")
def dashboard_feed_burn_rate(range: str = Query(default="30d", pattern="^(7d|30d|90d)$")):
    days = _range_to_days(range)
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    feed_items = supabase_admin.table("items").select("id").eq("item_type", "feed").execute().data or []
    feed_ids = {row["id"] for row in feed_items}
    txns = (
        supabase_admin.table("inventory_transactions")
        .select("item_id,transaction_type,quantity,created_at")
        .gte("created_at", start)
        .execute()
        .data
        or []
    )

    consumed = 0.0
    for txn in txns:
        if txn.get("item_id") in feed_ids and "out" in (txn.get("transaction_type") or ""):
            consumed += float(txn.get("quantity", 0))

    return {
        "range": range,
        "total_feed_consumed": consumed,
        "daily_burn_rate": round(consumed / days, 4) if days else 0,
    }


@router.get("/dashboard/inventory-alerts")
def dashboard_inventory_alerts(limit: int = Query(default=50, ge=1, le=200)):
    alerts = (
        supabase_admin.table("alerts")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )
    unread = [a for a in alerts if not a.get("is_read")]
    return {"count": len(alerts), "unread_count": len(unread), "data": alerts}


@router.get("/dashboard/category-distribution")
def dashboard_category_distribution():
    items = supabase_admin.table("items").select("item_type").execute().data or []
    counts: dict[str, int] = {}
    for item in items:
        cat = item.get("item_type") or "unknown"
        counts[cat] = counts.get(cat, 0) + 1
    return {"data": [{"category": k, "count": v} for k, v in sorted(counts.items())]}


@router.get("/items")
def list_items(search: str | None = None, category: str | None = None, status: str | None = None):
    query = supabase_admin.table("items").select("*").order("created_at", desc=True)
    if search:
        query = query.ilike("name", f"%{search}%")
    if category:
        query = query.eq("item_type", category)
    if status:
        if status == "active":
            query = query.eq("is_active", True)
        elif status == "inactive":
            query = query.eq("is_active", False)
    data = query.execute().data or []
    return {"count": len(data), "data": data}


@router.get("/items/{item_id}")
def get_item(item_id: UUID):
    response = supabase_admin.table("items").select("*").eq("id", str(item_id)).limit(1).execute()
    rows = response.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Item not found")
    return rows[0]


@router.post("/items")
def create_item(payload: ItemPayload):
    data = (
        supabase_admin.table("items")
        .insert(
            {
                "name": payload.name,
                "sku": payload.sku,
                "item_type": payload.category or payload.item_type,
                "unit": payload.unit,
                "description": payload.description,
                "is_active": payload.is_active if payload.status is None else payload.status == "active",
            }
        )
        .execute()
        .data
        or []
    )
    return {"message": "Item created", "data": data[0] if data else None}


@router.put("/items/{item_id}")
def update_item(item_id: UUID, payload: ItemPayload):
    data = (
        supabase_admin.table("items")
        .update(
            {
                "name": payload.name,
                "sku": payload.sku,
                "item_type": payload.category or payload.item_type,
                "unit": payload.unit,
                "description": payload.description,
                "is_active": payload.is_active if payload.status is None else payload.status == "active",
                "updated_at": _now_iso(),
            }
        )
        .eq("id", str(item_id))
        .execute()
        .data
        or []
    )
    if not data:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item updated", "data": data[0]}


@router.put("/items/{item_id}/quantity")
def update_item_quantity(item_id: UUID, payload: QuantityUpdatePayload):
    stock = _get_or_create_stock(str(item_id), str(payload.department_id))
    updated = (
        supabase_admin.table("inventory_stock")
        .update({"quantity": payload.quantity, "updated_at": _now_iso()})
        .eq("id", stock["id"])
        .execute()
        .data
        or []
    )
    _record_transaction(
        {
            "item_id": str(item_id),
            "transaction_type": "manual_set",
            "quantity": payload.quantity,
            "to_department_id": str(payload.department_id),
            "created_at": _now_iso(),
        }
    )
    return {"message": "Item quantity updated", "data": updated[0] if updated else None}


@router.put("/items/{item_id}/threshold")
def update_item_threshold(item_id: UUID, payload: ThresholdUpdatePayload):
    query = supabase_admin.table("inventory_stock").update({"reorder_level": payload.reorder_level, "updated_at": _now_iso()})
    query = query.eq("item_id", str(item_id))
    if payload.department_id:
        query = query.eq("department_id", str(payload.department_id))
    updated = query.execute().data or []
    return {"message": "Threshold updated", "updated_rows": len(updated), "data": updated}


@router.delete("/items/{item_id}")
def delete_item(item_id: UUID):
    data = supabase_admin.table("items").delete().eq("id", str(item_id)).execute().data or []
    if not data:
        raise HTTPException(status_code=404, detail="Item not found or cannot be deleted")
    return {"message": "Item deleted", "data": data[0]}


@router.post("/stock/in")
def stock_in(payload: StockInOutPayload, current_user=Depends(get_current_user)):
    stock = _get_or_create_stock(str(payload.item_id), str(payload.department_id))
    new_qty = float(stock["quantity"]) + payload.quantity
    updated = (
        supabase_admin.table("inventory_stock")
        .update({"quantity": new_qty, "updated_at": _now_iso()})
        .eq("id", stock["id"])
        .execute()
        .data
        or []
    )
    _record_transaction(
        {
            "item_id": str(payload.item_id),
            "transaction_type": "stock_in",
            "quantity": payload.quantity,
            "to_department_id": str(payload.department_id),
            "unit_cost": payload.unit_cost,
            "notes": payload.notes,
            "created_by": str(current_user.id),
        }
    )
    return {"message": "Stock increased", "data": updated[0] if updated else None}


@router.post("/stock/out")
def stock_out(payload: StockInOutPayload, current_user=Depends(get_current_user)):
    stock = _get_or_create_stock(str(payload.item_id), str(payload.department_id))
    current_qty = float(stock["quantity"])
    if current_qty < payload.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    new_qty = current_qty - payload.quantity
    updated = (
        supabase_admin.table("inventory_stock")
        .update({"quantity": new_qty, "updated_at": _now_iso()})
        .eq("id", stock["id"])
        .execute()
        .data
        or []
    )
    _record_transaction(
        {
            "item_id": str(payload.item_id),
            "transaction_type": "stock_out",
            "quantity": payload.quantity,
            "from_department_id": str(payload.department_id),
            "unit_cost": payload.unit_cost,
            "notes": payload.notes,
            "created_by": str(current_user.id),
        }
    )
    return {"message": "Stock decreased", "data": updated[0] if updated else None}
