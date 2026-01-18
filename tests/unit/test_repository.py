import pytest
from sqlalchemy import text
from allocation.domain.model import Batch, OrderLine
from allocation.adapters.repository import SQLAlchemyRepository


def insert_order_line(orm_session) -> int:
    orm_session.execute(statement=text('INSERT INTO order_lines (orderid, sku, qty) VALUES ("order1", "GENERIC-SOFA", 12)'))
    [[orderline_id]] = orm_session.execute(
        text("SELECT id FROM order_lines WHERE orderid=:orderid AND sku=:sku"),
        dict(orderid="order1", sku="GENERIC-SOFA"),
    )
    return orderline_id


def insert_batch(orm_session, batch_id) -> int:
    orm_session.execute(
        text('INSERT INTO batches (reference, sku, _purchase_quantity, eta) VALUES (:batch_id, "GENERIC-SOFA", 100, null)'),
        dict(batch_id=batch_id),
    )
    [[batch_id]] = orm_session.execute(
        text('SELECT id FROM batches WHERE reference=:batch_id AND sku="GENERIC-SOFA"'),
        dict(batch_id=batch_id),
    )
    return batch_id


def insert_allocation(orm_session, orderline_id, batch_id):
    orm_session.execute(
        text("INSERT INTO allocations (orderline_id, batch_id) VALUES (:orderline_id, :batch_id)"),
        dict(orderline_id=orderline_id, batch_id=batch_id),
    )


@pytest.mark.unit
@pytest.mark.repository
def test_repository_can_save_a_batch(orm_session):
    batch = Batch("batch1", "RUSTY-SOAPDISH", 100, eta=None)

    repo = SQLAlchemyRepository(orm_session=orm_session)
    repo.add(batch)
    orm_session.commit()

    rows = orm_session.execute(statement=text('SELECT reference, sku, _purchase_quantity, eta FROM "batches"'))
    assert list(rows) == [("batch1", "RUSTY-SOAPDISH", 100, None)]


@pytest.mark.unit
@pytest.mark.repository
def test_repository_can_retrieve_a_batch_with_allocations(orm_session):
    orderline_id = insert_order_line(orm_session)
    batch1_id = insert_batch(orm_session, "batch1")
    insert_batch(orm_session, "batch2")
    insert_allocation(orm_session, orderline_id, batch1_id)

    repo = SQLAlchemyRepository(orm_session)
    retrieved = repo.get("batch1")

    expected = Batch("batch1", "GENERIC-SOFA", 100, eta=None)
    assert retrieved == expected
    assert retrieved.sku == expected.sku  # type: ignore
    assert retrieved._purchase_quantity == expected._purchase_quantity  # type: ignore
    assert retrieved._allocations == {  # type: ignore
        OrderLine(orderId="order1", sku="GENERIC-SOFA", qty=12),
    }


@pytest.mark.unit
@pytest.mark.repository
def test_repository_can_list_batches(orm_session):
    batch1 = Batch("batch1", "ROUND-MIRROR", 100, eta=None)
    batch2 = Batch("batch1", "PRETTY-TABLE", 100, eta=None)
    batch3 = Batch("batch1", "LITTLE_BOX", 100, eta=None)
    batches = [batch1, batch2, batch3]
    repo = SQLAlchemyRepository(orm_session)
    for batch in batches:
        repo.add(batch)
    orm_session.commit()

    retrieved_batches = repo.list()
    assert len(retrieved_batches) == len(batches)
    assert retrieved_batches == batches
