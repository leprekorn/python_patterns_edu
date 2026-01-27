from allocation.domain import model
from allocation.service_layer.unit_of_work import SqlAlchemyUnitOfWork
from sqlalchemy import text
from typing import Optional
from datetime import date


def insert_batch(session, ref: str, sku: str, qty: int, eta: Optional[date]):
    session.execute(
        text("INSERT INTO batches (reference, sku, _purchase_quantity, eta) VALUES (:ref, :sku, :_purchase_quantity, :eta)"),
        dict(ref=ref, sku=sku, _purchase_quantity=qty, eta=eta),
    )


def test_uow_can_get_batch_and_allocate_to_it(session_factory):
    sku = "HIPSTER-WORKBENCH"
    orderId = "order1"
    batchRef = "batch1"
    session = session_factory()
    insert_batch(session=session, ref=batchRef, sku=sku, qty=100, eta=None)
    session.commit()

    uow = SqlAlchemyUnitOfWork(session_factory=session_factory)
    with uow:
        existing_batch: Optional[model.Batch] = uow.batches.get(reference=batchRef)
        assert existing_batch is not None
        line = model.OrderLine(orderId=orderId, sku=sku, qty=10)
        existing_batch.allocate(line)
        uow.commit()

    orderLine_id = session.execute(
        text("SELECT id FROM order_lines WHERE orderid=:orderid AND sku=:sku"),
        dict(orderid=orderId, sku=sku),
    ).scalar_one()

    allocated_batch_ref = session.execute(
        text("SELECT b.reference FROM batches AS b JOIN allocations AS a ON b.id = a.batch_id WHERE a.orderline_id = :orderline_id"),
        dict(orderline_id=orderLine_id),
    ).scalar_one()

    assert allocated_batch_ref == batchRef
