import pytest
from datetime import date
from sqlalchemy import text
from allocation.domain.model import Batch, OrderLine


@pytest.mark.integration
@pytest.mark.orm
def test_orderline_mapper_can_load_lines(orm_session):
    insert_query = """
        INSERT INTO order_lines(orderid, sku, qty) VALUES
        ('order1', 'RED-CHAIR', 12),
        ('order2', 'RED-TABLE', 13),
        ('order3', 'BLUE-LIPSTICK', 14)
    """
    orm_session.execute(statement=text(insert_query))
    expected = [
        OrderLine("order1", "RED-CHAIR", 12),
        OrderLine("order2", "RED-TABLE", 13),
        OrderLine("order3", "BLUE-LIPSTICK", 14),
    ]
    assert orm_session.query(OrderLine).all() == expected


@pytest.mark.integration
@pytest.mark.orm
def test_orderline_mapper_can_save_lines(orm_session):
    new_line = OrderLine("order1", "DECORATIVE-WIDGET", 12)
    orm_session.add(new_line)
    orm_session.commit()
    select_query = text('SELECT orderid, sku, qty FROM "order_lines"')
    rows = list(orm_session.execute(statement=select_query))
    assert rows == [("order1", "DECORATIVE-WIDGET", 12)]


@pytest.mark.integration
@pytest.mark.orm
def test_retrieving_batches(orm_session):
    insert_batch1 = "INSERT INTO batches (reference, sku, _purchase_quantity, eta) VALUES ('batch1', 'sku1', 100, null)"
    insert_batch2 = "INSERT INTO batches (reference, sku, _purchase_quantity, eta) VALUES ('batch2', 'sku2', 200, '2011-04-11')"
    orm_session.execute(statement=text(insert_batch1))
    orm_session.execute(statement=text(insert_batch2))
    expected = [
        Batch("batch1", "sku1", 100, eta=None),
        Batch("batch2", "sku2", 200, eta=date(2011, 4, 11)),
    ]

    assert orm_session.query(Batch).all() == expected


@pytest.mark.integration
@pytest.mark.orm
def test_saving_batches(orm_session):
    batch = Batch(ref="batch1", sku="sku1", qty=100, eta=None)
    orm_session.add(batch)
    orm_session.commit()
    rows = orm_session.execute(text('SELECT reference, sku, _purchase_quantity, eta FROM "batches"'))
    assert list(rows) == [("batch1", "sku1", 100, None)]


@pytest.mark.integration
@pytest.mark.orm
def test_saving_allocations(orm_session):
    batch = Batch(ref="batch1", sku="sku1", qty=100, eta=None)
    line = OrderLine(orderId="order1", sku="sku1", qty=10)
    batch.allocate(line)
    orm_session.add(batch)
    orm_session.commit()
    rows_id = list(orm_session.execute(statement=text('SELECT orderline_id, batch_id FROM "allocations"')))
    assert rows_id == [(line.id, batch.id)]  # type: ignore


@pytest.mark.integration
@pytest.mark.orm
def test_retrieving_allocations(orm_session):
    orm_session.execute(
        text("INSERT INTO order_lines (orderid, sku, qty) VALUES (:orderid, :sku, :qty)"), dict(orderid="order1", sku="sku1", qty=12)
    )
    olid = orm_session.execute(
        text("SELECT id FROM order_lines WHERE orderid=:orderid AND sku=:sku"),
        dict(orderid="order1", sku="sku1"),
    ).scalar_one()
    orm_session.execute(
        text("INSERT INTO batches (reference, sku, _purchase_quantity, eta) VALUES (:ref, :sku, :qty, :eta)"),
        dict(ref="batch1", sku="sku1", qty=100, eta=None),
    )
    bid = orm_session.execute(
        text("SELECT id FROM batches WHERE reference=:ref AND sku=:sku"),
        dict(ref="batch1", sku="sku1"),
    ).scalar_one()

    orm_session.execute(
        text("INSERT INTO allocations (orderline_id, batch_id) VALUES (:olid, :bid)"),
        dict(olid=olid, bid=bid),
    )

    batch = orm_session.query(Batch).one()

    assert batch._allocations == {OrderLine("order1", "sku1", 12)}


@pytest.mark.integration
@pytest.mark.orm
def test_deallocate(orm_session):
    batch = Batch(ref="batch1", sku="sku1", qty=100, eta=None)
    line = OrderLine(orderId="order1", sku="sku1", qty=10)
    batch.allocate(line)
    orm_session.add(batch)
    orm_session.commit()

    batch.deallocate(line=line)
    orm_session.commit()
    allocations = list(orm_session.execute(statement=text('SELECT orderline_id, batch_id FROM "allocations"')))
    assert allocations == []  # type: ignore
