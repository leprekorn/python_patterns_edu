from datetime import date
from typing import Optional

from allocation.domain import model
from allocation.domain.exceptions import InvalidBatchReference, InvalidSku
from allocation.service_layer.unit_of_work import IUnitOfWork


def get_batch(sku: str, reference: str, uow: IUnitOfWork) -> dict:
    with uow:
        product = uow.products.get(sku=sku)
        if not product:
            raise InvalidSku(f"Invalid sku {sku}")

        batch = product.get_batch(reference=reference)
        if not batch:
            raise InvalidBatchReference(f"Batch {reference} not found")
        return {
            "reference": batch.reference,
            "sku": batch.sku,
            "qty": batch._purchase_quantity,
            "eta": batch.eta.isoformat() if batch.eta else None,
        }


def allocate(orderId: str, sku: str, qty: int, uow: IUnitOfWork) -> Optional[str]:
    line = model.OrderLine(orderId=orderId, sku=sku, qty=qty)
    with uow:
        product = uow.products.get(sku=sku)
        if not product:
            raise InvalidSku(f"Invalid sku {sku}")
        batch = product.allocate(line=line)
        uow.commit()
        if batch:
            return batch.reference
        return None


def deallocate(sku: str, orderId: str, qty: int, uow: IUnitOfWork) -> str:
    line = model.OrderLine(orderId=orderId, sku=sku, qty=qty)
    with uow:
        product = uow.products.get(sku=sku)
        if not product:
            raise InvalidSku(f"Invalid sku {sku}")
        batchref = product.deallocate(line=line)
        uow.commit()
        return batchref


def add_batch(
    reference: str,
    sku: str,
    qty: int,
    eta: Optional[date],
    uow: IUnitOfWork,
) -> model.Batch:
    batch = model.Batch(ref=reference, sku=sku, qty=qty, eta=eta)
    with uow:
        product = uow.products.get(sku=sku)
        if not product:
            product = model.Product(sku=sku, batches=[])
            uow.products.add(product)
        product.batches.append(batch)
        uow.commit()
    return batch  # TODO do not return ORM object, return batchref str


def delete_batch(sku: str, reference: str, uow: IUnitOfWork) -> None:
    with uow:
        product = uow.products.get(sku=sku)
        if not product:
            raise InvalidSku(f"Invalid sku {sku}")
        product.delete_batch(reference=reference)
        uow.commit()
