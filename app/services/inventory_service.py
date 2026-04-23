from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException

from app.core.supabase_client import supabase_admin
from app.schemas.inventory import StockAdjustmentRequest, StockTransferRequest


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_stock_row(item_id: UUID, department_id: UUID) -> dict | None:
    response = (
        supabase_admin.table("inventory_stock")
        .select("*")
        .eq("item_id", str(item_id))
        .eq("department_id", str(department_id))
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def _create_stock_row(item_id: UUID, department_id: UUID, quantity: float) -> dict:
    create_response = (
        supabase_admin.table("inventory_stock")
        .insert(
            {
                "item_id": str(item_id),
                "department_id": str(department_id),
                "quantity": quantity,
                "updated_at": _utc_now_iso(),
            }
        )
        .execute()
    )
    rows = create_response.data or []
    if not rows:
        raise HTTPException(status_code=500, detail="Unable to create stock row")
    return rows[0]


def _update_stock_quantity(stock_id: str, new_quantity: float) -> dict:
    update_response = (
        supabase_admin.table("inventory_stock")
        .update({"quantity": new_quantity, "updated_at": _utc_now_iso()})
        .eq("id", stock_id)
        .execute()
    )
    rows = update_response.data or []
    if not rows:
        raise HTTPException(status_code=500, detail="Unable to update stock quantity")
    return rows[0]


def _ensure_stock_exists(item_id: UUID, department_id: UUID) -> dict:
    stock = _get_stock_row(item_id=item_id, department_id=department_id)
    if not stock:
        stock = _create_stock_row(item_id=item_id, department_id=department_id, quantity=0)
    return stock


def _insert_transaction(payload: dict) -> dict:
    txn_response = supabase_admin.table("inventory_transactions").insert(payload).execute()
    rows = txn_response.data or []
    if not rows:
        raise HTTPException(status_code=500, detail="Unable to record inventory transaction")
    return rows[0]


def apply_stock_adjustment(request: StockAdjustmentRequest, user_id: str) -> dict:
    stock_row = _ensure_stock_exists(item_id=request.item_id, department_id=request.department_id)
    current_qty = float(stock_row["quantity"])

    if request.adjustment_type == "out" and current_qty < request.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock for outward adjustment")

    delta = request.quantity if request.adjustment_type == "in" else -request.quantity
    new_qty = current_qty + delta
    updated_stock = _update_stock_quantity(stock_id=stock_row["id"], new_quantity=new_qty)

    transaction = _insert_transaction(
        {
            "item_id": str(request.item_id),
            "transaction_type": f"adjust_{request.adjustment_type}",
            "quantity": request.quantity,
            "from_department_id": str(request.department_id) if request.adjustment_type == "out" else None,
            "to_department_id": str(request.department_id) if request.adjustment_type == "in" else None,
            "unit_cost": request.unit_cost,
            "reference_type": request.reference_type,
            "reference_id": str(request.reference_id) if request.reference_id else None,
            "notes": request.notes,
            "created_by": user_id,
        }
    )

    return {"stock": updated_stock, "transaction": transaction}


def apply_stock_transfer(request: StockTransferRequest, user_id: str) -> dict:
    from_stock = _ensure_stock_exists(item_id=request.item_id, department_id=request.from_department_id)
    to_stock = _ensure_stock_exists(item_id=request.item_id, department_id=request.to_department_id)

    from_qty = float(from_stock["quantity"])
    to_qty = float(to_stock["quantity"])

    if from_qty < request.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock in source department")

    updated_from = _update_stock_quantity(stock_id=from_stock["id"], new_quantity=from_qty - request.quantity)
    updated_to = _update_stock_quantity(stock_id=to_stock["id"], new_quantity=to_qty + request.quantity)

    transaction = _insert_transaction(
        {
            "item_id": str(request.item_id),
            "transaction_type": "transfer",
            "quantity": request.quantity,
            "from_department_id": str(request.from_department_id),
            "to_department_id": str(request.to_department_id),
            "unit_cost": request.unit_cost,
            "reference_type": request.reference_type,
            "reference_id": str(request.reference_id) if request.reference_id else None,
            "notes": request.notes,
            "created_by": user_id,
        }
    )

    return {
        "from_stock": updated_from,
        "to_stock": updated_to,
        "transaction": transaction,
    }
