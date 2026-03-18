import logging
from dataclasses import asdict

from sqlalchemy import text

from allocation import config
from allocation.adapters import email, redis
from allocation.domain import commands, events, model
from allocation.domain.exceptions import InvalidBatchReference, InvalidSku
from allocation.interfaces.main import IUnitOfWork

logger = logging.getLogger(__name__)


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


def reallocate(event: events.Deallocated, uow: IUnitOfWork) -> None:
    allocate(commands.Allocate(order_id=event.order_id, sku=event.sku, qty=event.qty), uow=uow)


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
    logger.info(f"add_batch called with command: {command}")
    with uow:
        product = uow.products.get(sku=command.sku)
        if not product:
            logger.info(f"Creating new product with sku: {command.sku}")
            product = model.Product(sku=command.sku, batches=[])
            uow.products.add(product)
        batch = model.Batch(
            ref=command.ref,
            sku=command.sku,
            qty=command.qty,
            eta=command.eta,
        )
        product.batches.append(batch)
        logger.info(f"Committing batch: {batch.reference}")
        uow.commit()
        logger.info(f"Batch committed successfully: {batch.reference}")
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
        product = uow.products.get_by_batch_ref(batch_ref=command.ref)
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


def add_allocation_to_read_model(
    event: events.Allocated,
    uow: IUnitOfWork,
):
    logger.info(f"add_allocation_to_read_model called with event: {event}")
    try:
        with uow:
            uow.session.execute(
                text(
                    """
                INSERT INTO allocations_view (order_id, sku, batch_ref)
                VALUES (:order_id, :sku, :batch_ref)
                """
                ),
                dict(order_id=event.order_id, sku=event.sku, batch_ref=event.batch_ref),
            )
            uow.commit()
            logger.info(f"Allocation written to read model: {event.order_id}")
    except Exception as e:
        logger.error(f"Failed to write allocation to read model: {e}", exc_info=True)
        raise


def remove_allocation_from_read_model(
    event: events.Deallocated,
    uow: IUnitOfWork,
):
    logger.info(f"remove_allocation_from_read_model called with event: {event}")
    try:
        with uow:
            uow.session.execute(
                text(
                    """
                DELETE FROM allocations_view
                WHERE order_id = :order_id AND sku = :sku
                """
                ),
                dict(order_id=event.order_id, sku=event.sku),
            )
            uow.commit()
            logger.info(f"Allocation removed from read model: {event.order_id}")
    except Exception as e:
        logger.error(f"Failed to remove allocation from read model: {e}", exc_info=True)
        raise
