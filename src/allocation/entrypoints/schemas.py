from pydantic import BaseModel
from typing import Optional


class AllocateRequest(BaseModel):
    order_id: str
    sku: str
    qty: int


class DeallocateRequest(BaseModel):
    sku: str
    order_id: str
    qty: int


class AddBatchRequest(BaseModel):
    reference: str
    sku: str
    qty: int
    eta: Optional[str] = None
