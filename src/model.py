from dataclasses import dataclass
from typing import Optional, Set, Any, List
from datetime import date
from .exceptions import OutOfStock


def allocate(line: OrderLine, batches: List[Batch]) -> Batch:
    try:
        batch = next(b for b in sorted(batches) if b.can_allocate(line))
        batch.allocate(line)
    except StopIteration:
        raise OutOfStock(f"There is no batch with sku: {line.sku} available")
    return batch


@dataclass(eq=True)
class OrderLine:
    orderId: str
    sku: str
    qty: int

    def __hash__(self):
        return hash((self.orderId, self.sku))


class Batch:
    def __init__(self, ref: str, sku: str, qty: int, eta: Optional[date]):
        self.reference = ref
        self.sku = sku
        self.eta = eta
        self._purchase_quantity = qty
        self._allocations: Set[OrderLine] = set()

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Batch):
            return False
        return other.reference == self.reference

    def __qt__(self, other: Any):
        if not isinstance(other, Batch):
            raise ValueError("Other instance is not a Batch object!")
        if self.eta is None:
            return False
        if other.eta is None:
            return True
        return self.eta > other.eta

    def __lt__(self, other: Any):
        if not isinstance(other, Batch):
            raise ValueError("Other instance is not a Batch object!")
        if self.eta is None:
            return True
        if other.eta is None:
            return False
        return self.eta < other.eta

    def __hash__(self):
        return hash(self.reference)

    def allocate(self, line: OrderLine):
        if self.can_allocate(line=line):
            self._allocations.add(line)

    def deallocate(self, line: OrderLine):
        if line in self._allocations:
            self._allocations.remove(line)

    @property
    def allocated_quantity(self) -> int:
        return sum(line.qty for line in self._allocations)

    @property
    def available_quantity(self) -> int:
        return self._purchase_quantity - self.allocated_quantity

    def can_allocate(self, line: OrderLine) -> bool:
        return self.sku == line.sku and self.available_quantity >= line.qty
