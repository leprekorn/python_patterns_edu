import pytest
from sqlalchemy import text
from allocation.domain.model import Batch, OrderLine, Product
from allocation.adapters.repository import SQLAlchemyRepository


def insert_order_line(orm_session, orderid, sku, qty) -> int:
    orm_session.execute(
        statement=text("INSERT INTO order_lines (orderId, sku, qty) VALUES (:orderid, :sku, :qty)"),
        params=dict(orderid=orderid, sku=sku, qty=qty),
    )
    [[orderline_id]] = orm_session.execute(
        text("SELECT id FROM order_lines WHERE orderId=:orderid AND sku=:sku"),
        dict(orderid="order1", sku="GENERIC-SOFA"),
    )
    return orderline_id


def insert_allocation(orm_session, orderline_id, batch_id):
    orm_session.execute(
        text("INSERT INTO allocations (orderline_id, batch_id) VALUES (:orderline_id, :batch_id)"),
        dict(orderline_id=orderline_id, batch_id=batch_id),
    )


@pytest.mark.integration
@pytest.mark.repository
def test_repository_can_save_a_batch(orm_session):
    batch = Batch("batch1", "RUSTY-SOAPDISH", 100, eta=None)
    product = Product(sku=batch.sku, batches=[batch])

    repo = SQLAlchemyRepository(orm_session=orm_session)
    repo.add(product=product)
    orm_session.commit()

    rows = orm_session.execute(statement=text("SELECT reference, sku, _purchase_quantity, eta FROM batches"))
    assert list(rows) == [("batch1", "RUSTY-SOAPDISH", 100, None)]


@pytest.mark.integration
@pytest.mark.repository
def test_repository_can_delete_batch(orm_session):
    batch = Batch(ref="batch100500", sku="BLUE-SARDINA", qty=50, eta=None)
    product = Product(sku=batch.sku, batches=[batch])

    repo = SQLAlchemyRepository(orm_session=orm_session)
    repo.add(product=product)
    orm_session.commit()
    repo.delete(sku=product.sku)
    orm_session.commit()

    rows = orm_session.execute(statement=text("SELECT reference, sku, _purchase_quantity, eta FROM batches"))
    assert list(rows) == []


@pytest.mark.integration
@pytest.mark.repository
def test_repository_can_retrieve_a_batch_with_allocations(orm_session, insert_batch_via_session):
    batch1 = Batch(ref="batch1", sku="GENERIC-SOFA", qty=100, eta=None)
    batch1_id = insert_batch_via_session(
        session=orm_session,
        ref=batch1.reference,
        sku=batch1.sku,
        qty=batch1._purchase_quantity,
        eta=batch1.eta,
    )
    orderline = OrderLine(orderId="order1", sku=batch1.sku, qty=12)
    orderline_id = insert_order_line(orm_session, sku=orderline.sku, qty=orderline.qty, orderid=orderline.orderId)
    insert_allocation(orm_session, orderline_id=orderline_id, batch_id=batch1_id)
    repo = SQLAlchemyRepository(orm_session)
    retrieved_product = repo.get(sku=batch1.sku)
    assert retrieved_product is not None
    retrieved_batch = retrieved_product.get_batch(reference=batch1.reference)
    assert retrieved_batch is not None

    assert retrieved_batch == batch1
    assert retrieved_batch.sku == batch1.sku
    assert retrieved_batch._purchase_quantity == batch1._purchase_quantity
    assert retrieved_batch._allocations == {
        orderline,
    }


@pytest.mark.integration
@pytest.mark.repository
def test_repository_can_list_batches(orm_session):
    batch1 = Batch("batch1", "ROUND-MIRROR", 100, eta=None)
    batch2 = Batch("batch1", "PRETTY-TABLE", 100, eta=None)
    batch3 = Batch("batch1", "LITTLE_BOX", 100, eta=None)
    batches = [batch1, batch2, batch3]
    repo = SQLAlchemyRepository(orm_session)
    for batch in batches:
        product = Product(sku=batch.sku, batches=[batch])
        repo.add(product=product)
    orm_session.commit()

    retrieved_products = repo.list()
    assert len(retrieved_products) == len(batches)
    for product in retrieved_products:
        assert any(product.sku == batch.sku and product.batches[0] == batch for batch in batches)


@pytest.mark.integration
@pytest.mark.repository
def test_repository_get_by_batchref(orm_session, insert_batch_via_session):
    batch1 = Batch(ref="batch1", sku="GENERIC-SOFA", qty=100, eta=None)
    batch1_id = insert_batch_via_session(
        session=orm_session,
        ref=batch1.reference,
        sku=batch1.sku,
        qty=batch1._purchase_quantity,
        eta=batch1.eta,
    )
    repo = SQLAlchemyRepository(orm_session)
    retrieved_product = repo.get_by_batchref(batchref=batch1.reference)
    assert retrieved_product is not None
    retrieved_batch = retrieved_product.get_batch(reference=batch1.reference)
    assert retrieved_batch is not None
    assert retrieved_batch.id == batch1_id  # type: ignore
    assert retrieved_batch == batch1
    assert retrieved_batch.sku == batch1.sku
    assert retrieved_batch._purchase_quantity == batch1._purchase_quantity
