from allocation.domain import model
from allocation.domain.exceptions import InvalidSku
from allocation.service_layer.unit_of_work import IUnitOfWork
from typing import Optional
from datetime import date


def get_product(sku: str, uow: IUnitOfWork) -> model.Product:
    with uow:
        product = uow.products.get(sku=sku)
        if not product:
            raise InvalidSku(f"Invalid sku {sku}")
        return product


def get_batch(sku: str, reference: str, uow: IUnitOfWork) -> dict:
    with uow:
        product = uow.products.get(sku=sku)
        if not product:
            raise InvalidSku(f"Invalid sku {sku}")

        batch = product.get_batch(reference=reference)
        if not batch:
            raise model.InvalidBatchReference(f"Batch {reference} not found")
        return {
            "reference": batch.reference,
            "sku": batch.sku,
            "qty": batch._purchase_quantity,
            "eta": batch.eta.isoformat() if batch.eta else None,
        }


def allocate(orderId: str, sku: str, qty: int, uow: IUnitOfWork) -> str:
    line = model.OrderLine(orderId=orderId, sku=sku, qty=qty)
    product = get_product(sku=sku, uow=uow)
    with uow:
        batch = product.allocate(line=line)
        uow.commit()
        return batch.reference


def deallocate(sku: str, orderId: str, qty: int, uow: IUnitOfWork) -> str:
    product = get_product(sku=sku, uow=uow)
    with uow:
        line = model.OrderLine(orderId=orderId, sku=sku, qty=qty)
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
    product = get_product(sku=sku, uow=uow)
    with uow:
        product.delete_batch(reference=reference)
        uow.commit()
