from allocation.domain import model
from allocation.domain.exceptions import InvalidSku, InvalidBatchReference, UnallocatedLine
from allocation.service_layer.unit_of_work import IUnitOfWork
from typing import List, Optional
from datetime import date


def is_valid_sku(sku: str, batches: List[model.Batch]) -> bool:
    return sku in {b.sku for b in batches}


def allocate(orderId: str, sku: str, qty: int, uow: IUnitOfWork) -> model.Batch:
    line = model.OrderLine(orderId=orderId, sku=sku, qty=qty)

    with uow:
        batches = uow.batches.list()
        if not is_valid_sku(line.sku, batches):
            raise InvalidSku(f"Invalid sku {line.sku}")
        batch = model.allocate(line=line, batches=batches)
        uow.commit()
        return batch


def deallocate(batchref: str, orderId: str, uow: IUnitOfWork) -> model.Batch:
    with uow:
        batch = uow.batches.get(reference=batchref)
        if not batch:
            raise InvalidBatchReference(f"Invalid batch reference {batchref}")

        line = batch.allocated_line(orderId=orderId)
        if not line:
            raise UnallocatedLine(f"Order line {orderId} is not allocated to batch {batchref}")

        batch.deallocate(line=line)
        uow.commit()
        return batch


def add_batch(
    reference: str,
    sku: str,
    qty: int,
    eta: Optional[date],
    uow: IUnitOfWork,
) -> model.Batch:
    batch = model.Batch(ref=reference, sku=sku, qty=qty, eta=eta)
    with uow:
        uow.batches.add(batch)
        uow.commit()
    return batch


def delete_batch(reference: str, uow: IUnitOfWork) -> None:
    with uow:
        batch = uow.batches.get(reference=reference)
        if not batch:
            raise InvalidBatchReference(f"Invalid batch reference {reference}")
        uow.batches.delete(batch.reference)
        uow.commit()
