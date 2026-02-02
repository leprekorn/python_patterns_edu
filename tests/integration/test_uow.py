from allocation.domain import model
from allocation.service_layer.unit_of_work import SqlAlchemyUnitOfWork
from sqlalchemy import text
import pytest


def test_uow_can_get_batch_and_allocate_to_it(session_factory, insert_batch_via_session):
    sku = "HIPSTER-WORKBENCH"
    orderId = "order1"
    batchRef = "batch1"
    session = session_factory()
    insert_batch_via_session(
        session=session,
        ref=batchRef,
        sku=sku,
        qty=100,
        eta=None,
    )
    session.commit()

    uow = SqlAlchemyUnitOfWork(session_factory=session_factory)
    with uow:
        product = uow.products.get(sku=sku)
        assert product is not None
        line = model.OrderLine(orderId=orderId, sku=sku, qty=10)
        product.allocate(line)
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


def test_rolls_back_uncommitted_work_by_default(session_factory, insert_batch_via_session):
    uow = SqlAlchemyUnitOfWork(session_factory=session_factory)
    with uow:
        insert_batch_via_session(
            session=uow.session,
            ref="batch1",
            sku="MEDIUM-PLINTH",
            qty=100,
            eta=None,
        )

    new_session = session_factory()
    rows = list(new_session.execute(text("SELECT * FROM batches")))
    assert rows == []


def test_rolls_back_on_error(session_factory, insert_batch_via_session):
    class MyException(Exception):
        pass

    uow = SqlAlchemyUnitOfWork(session_factory=session_factory)
    with pytest.raises(MyException):
        with uow:
            insert_batch_via_session(
                session=uow.session,
                ref="batch1",
                sku="LARGE-FORK",
                qty=100,
                eta=None,
            )
            raise MyException()

    new_session = session_factory()
    rows = list(new_session.execute(text("SELECT * FROM batches")))
    assert rows == []
