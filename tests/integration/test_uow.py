import time
import traceback
from allocation.domain import model
from allocation.service_layer.unit_of_work import SqlAlchemyUnitOfWork
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy import text
import pytest
from tests.utils import random_orderid, random_batchref, random_sku
from typing import List
from concurrent.futures import ThreadPoolExecutor


@pytest.mark.integration
@pytest.mark.uow
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


@pytest.mark.integration
@pytest.mark.uow
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


@pytest.mark.integration
@pytest.mark.uow
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


def __try_to_allocate(sku: str, line: model.OrderLine, exceptions: List[Exception], session_factory):
    try:
        uow = SqlAlchemyUnitOfWork(session_factory=session_factory)
        with uow:
            product = uow.products.get(sku=sku)
            assert product is not None
            product.allocate(line)
            time.sleep(0.2)
            uow.commit()
    except Exception as e:
        print(traceback.format_exc())
        exceptions.append(e)


@pytest.mark.integration
@pytest.mark.uow
def test_concurrent_updates_to_version_are_not_allowed(postgres_session_factory, insert_batch_via_session):
    sku = random_sku(name="CONCURRENT-TEST-SOFA")
    batchref = random_batchref(name="BATCH-001")
    session = postgres_session_factory()
    insert_batch_via_session(
        session=session,
        ref=batchref,
        sku=sku,
        qty=100,
        eta=None,
    )
    session.commit()

    order1, order2 = random_orderid(name="order1"), random_orderid(name="order2")
    line1 = model.OrderLine(orderId=order1, sku=sku, qty=12)
    line2 = model.OrderLine(orderId=order2, sku=sku, qty=30)
    exceptions = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(__try_to_allocate, sku, line1, exceptions, postgres_session_factory),
            executor.submit(__try_to_allocate, sku, line2, exceptions, postgres_session_factory),
        ]
        for future in futures:
            future.result()

    [exception] = exceptions
    assert isinstance(exception, StaleDataError) or "could not serialize access due to concurrent update" in str(exception)

    uow = SqlAlchemyUnitOfWork(session_factory=postgres_session_factory)
    with uow:
        product = uow.products.get(sku=sku)
        assert product is not None
        assert product.version_number == 1
        batch_obj = product.get_batch(reference=batchref)
        assert batch_obj is not None
        assert batch_obj._allocations == {model.OrderLine(orderId=order1, sku=sku, qty=12)}
