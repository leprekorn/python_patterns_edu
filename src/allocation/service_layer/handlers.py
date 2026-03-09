from dataclasses import asdict

from allocation import config
from allocation.adapters import email, redis
from allocation.domain import commands, events, model
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


def allocate(command: commands.Allocate, uow: IUnitOfWork) -> None:
    line = model.OrderLine(order_id=command.order_id, sku=command.sku, qty=command.qty)
    with uow:
        product = uow.products.get(sku=line.sku)
        if not product:
            raise InvalidSku(f"Invalid sku {line.sku}")
        product.allocate(line=line)
        uow.commit()


def deallocate(command: commands.Deallocate, uow: IUnitOfWork) -> None:
    line = model.OrderLine(order_id=command.order_id, sku=command.sku, qty=command.qty)
    with uow:
        product = uow.products.get(sku=line.sku)
        if not product:
            raise InvalidSku(f"Invalid sku {line.sku}")
        product.deallocate(line=line)
        uow.commit()


def add_batch(
    command: commands.CreateBatch,
    uow: IUnitOfWork,
) -> model.Batch:
    with uow:
        product = uow.products.get(sku=command.sku)
        if not product:
            product = model.Product(sku=command.sku, batches=[])
            uow.products.add(product)
        batch = model.Batch(
            ref=command.ref,
            sku=command.sku,
            qty=command.qty,
            eta=command.eta,
        )
        product.batches.append(batch)
        uow.commit()
    return batch


def delete_batch(command: commands.DeleteBatch, uow: IUnitOfWork) -> None:
    with uow:
        product = uow.products.get(sku=command.sku)
        if not product:
            raise InvalidSku(f"Invalid sku {command.sku}")
        product.delete_batch(reference=command.ref)
        uow.commit()


def change_batch_quantity(command: commands.ChangeBatchQuantity, uow: IUnitOfWork):
    with uow:
        product = uow.products.get_by_batchref(batchref=command.ref)
        if not product:
            raise InvalidSku(f"Invalid sku for batch reference {command.ref}")
        product.change_batch_quantity(reference=command.ref, qty=command.qty)
        uow.commit()


def send_out_of_stock_notification(event: events.OutOfStock, uow: IUnitOfWork) -> None:
    email.send_email(
        "stock@made.com",
        f"Out of stock for {event.sku}",
    )


def publish_allocated_event(event: events.Allocated, uow: IUnitOfWork) -> None:
    redis_config = config.get_redis_url()
    redisAdapter = redis.RedisAdapter(host=str(redis_config["host"]), port=int(redis_config["port"]))
    redisAdapter.publish(channel="line_allocated", message=asdict(event))
