from typing import Optional

from allocation.adapters import email
from allocation.domain import events, model
from allocation.domain.exceptions import InvalidBatchReference, InvalidSku
from allocation.interfaces.main import IUnitOfWork


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


def allocate(event: events.AllocationRequired, uow: IUnitOfWork) -> Optional[str]:
    line = model.OrderLine(orderId=event.orderId, sku=event.sku, qty=event.qty)
    with uow:
        product = uow.products.get(sku=line.sku)
        if not product:
            raise InvalidSku(f"Invalid sku {line.sku}")
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
    event: events.BatchCreated,
    uow: IUnitOfWork,
) -> model.Batch:
    with uow:
        product = uow.products.get(sku=event.sku)
        if not product:
            product = model.Product(sku=event.sku, batches=[])
            uow.products.add(product)
        batch = model.Batch(
            ref=event.ref,
            sku=event.sku,
            qty=event.qty,
            eta=event.eta,
        )
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


def send_out_of_stock_notification(event: events.OutOfStock, uow: IUnitOfWork) -> None:
    with uow:
        email.send_email(
            "stock@made.com",
            f"Out of stock for {event.sku}",
        )
