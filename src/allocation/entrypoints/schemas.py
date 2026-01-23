from pydantic import BaseModel
from typing import Optional


class AllocateRequest(BaseModel):
    orderid: str
    sku: str
    qty: int


class DeallocateRequest(BaseModel):
    batchref: str
    orderid: str


class AddBatchRequest(BaseModel):
    reference: str
    sku: str
    qty: int
    eta: Optional[str] = None
