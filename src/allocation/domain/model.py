from dataclasses import dataclass
from typing import Optional, Set, Any, List
from datetime import date
from allocation.domain.exceptions import OutOfStock, UnallocatedLine, InvalidBatchReference


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

    def __gt__(self, other: Any):
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

    def allocated_line(self, orderId: str) -> Optional[OrderLine]:
        for line in self._allocations:
            if line.orderId == orderId:
                return line
        return None


class Product:
    def __init__(self, sku: str, batches: Optional[List[Batch]] = None):
        self.sku = sku
        self.batches = batches or []

    def allocate(self, line: OrderLine) -> Batch:
        try:
            batch = next(b for b in sorted(self.batches) if b.can_allocate(line))
            batch.allocate(line)
        except StopIteration:
            raise OutOfStock(f"There is no batch with sku: {line.sku} available")
        return batch

    def deallocate(self, line: OrderLine) -> str:
        try:
            batch = next(b for b in self.batches if b.allocated_line(line.orderId))
            batch.deallocate(line)
            return batch.reference
        except StopIteration:
            raise UnallocatedLine(f"Order line {line.orderId} is not allocated to any batch in Product {self.sku}")

    @property
    def batches_list(self) -> List[Batch]:
        return self.batches

    def get_batch(self, reference: str) -> Batch:
        batch = next((b for b in self.batches if b.reference == reference), None)
        if not batch:
            raise InvalidBatchReference(f"Invalid batch reference {reference}")
        return batch

    def delete_batch(self, reference: str) -> None:
        batch = self.get_batch(reference=reference)
        self.batches.remove(batch)
