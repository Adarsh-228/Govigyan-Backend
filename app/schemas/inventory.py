from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class StockAdjustmentRequest(BaseModel):
    item_id: UUID
    department_id: UUID
    quantity: float = Field(gt=0)
    adjustment_type: str = Field(pattern="^(in|out)$")
    notes: str | None = None
    unit_cost: float | None = Field(default=None, ge=0)
    reference_type: str | None = None
    reference_id: UUID | None = None


class StockTransferRequest(BaseModel):
    item_id: UUID
    from_department_id: UUID
    to_department_id: UUID
    quantity: float = Field(gt=0)
    notes: str | None = None
    unit_cost: float | None = Field(default=None, ge=0)
    reference_type: str | None = None
    reference_id: UUID | None = None

    @model_validator(mode="after")
    def validate_departments(self):
        if self.from_department_id == self.to_department_id:
            raise ValueError("from_department_id and to_department_id must be different")
        return self
