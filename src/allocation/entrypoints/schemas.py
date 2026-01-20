from pydantic import BaseModel


class AllocateRequest(BaseModel):
    orderid: str
    sku: str
    qty: int


class DeallocateRequest(BaseModel):
    batchref: str
    orderid: str
