from allocation.domain import model
from allocation.domain.exceptions import InvalidSku, InvalidBatchReference, UnallocatedLine
from allocation.adapters.repository import IRepository
from typing import List, Protocol


class ISession(Protocol):
    """
    Interface for Repository session
    """

    def commit(self):
        raise NotImplementedError


def is_valid_sku(sku: str, batches: List[model.Batch]) -> bool:
    return sku in {b.sku for b in batches}


def allocate(orderId: str, sku: str, qty: int, repo: IRepository, session: ISession) -> model.Batch:
    line = model.OrderLine(orderId=orderId, sku=sku, qty=qty)
    batches = repo.list()
    if not is_valid_sku(line.sku, batches):
        raise InvalidSku(f"Invalid sku {line.sku}")
    batch = model.allocate(line=line, batches=batches)
    session.commit()
    return batch


def deallocate(batchref: str, orderId: str, repo: IRepository, session: ISession) -> model.Batch:
    batch = repo.get(reference=batchref)
    if not batch:
        raise InvalidBatchReference(f"Invalid batch reference {batchref}")

    line = batch.allocated_line(orderId=orderId)
    if not line:
        raise UnallocatedLine(f"Order line {orderId} is not allocated to batch {batchref}")

    batch.deallocate(line=line)
    session.commit()
    return batch
