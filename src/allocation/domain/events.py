from dataclasses import dataclass


class Event:
    pass


@dataclass
class Allocated(Event):
    orderId: str
    sku: str
    qty: int
    batchref: str


@dataclass
class OutOfStock(Event):
    sku: str
