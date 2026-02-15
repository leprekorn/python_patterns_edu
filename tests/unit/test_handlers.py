import pytest

from allocation.domain.exceptions import InvalidBatchReference, InvalidSku, UnallocatedLine
from allocation.service_layer import handlers


@pytest.mark.unit
@pytest.mark.service
def test_batch_allocate_returns_allocation(make_fake_uow):
    uow = make_fake_uow
    batch = handlers.add_batch(reference="b1", sku="COMPLICATED-LAMP", qty=100, eta=None, uow=uow)

    result = handlers.allocate(orderId="o1", sku="COMPLICATED-LAMP", qty=10, uow=uow)
    assert result == batch.reference


@pytest.mark.unit
@pytest.mark.service
def test_error_for_invalid_sku(make_fake_uow):
    uow = make_fake_uow
    handlers.add_batch(reference="b1", sku="AREALSKU", qty=100, eta=None, uow=uow)
    with pytest.raises(handlers.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        handlers.allocate(orderId="01", sku="NONEXISTENTSKU", qty=10, uow=uow)


@pytest.mark.unit
@pytest.mark.service
def test_commits(make_fake_uow):
    uow = make_fake_uow
    handlers.add_batch(reference="b1", sku="OMINOUS-MIRROR", qty=100, eta=None, uow=uow)
    handlers.allocate(orderId="o1", sku="OMINOUS-MIRROR", qty=10, uow=uow)
    assert uow.committed is True


@pytest.mark.unit
@pytest.mark.service
def test_deallocate_returns_batch_reference(make_fake_uow):
    uow = make_fake_uow
    batch = handlers.add_batch(reference="b50", sku="CRAZY-CHAIR", qty=100, eta=None, uow=uow)
    result = handlers.allocate(orderId="o20", sku="CRAZY-CHAIR", qty=10, uow=uow)
    assert result == batch.reference
    assert batch.available_quantity == 90

    unallocation_result = handlers.deallocate(sku="CRAZY-CHAIR", orderId="o20", qty=10, uow=uow)
    assert unallocation_result == batch.reference
    assert batch.available_quantity == 100


@pytest.mark.unit
@pytest.mark.service
def test_deallocate_non_allocated_line_raises_exception(make_fake_uow):
    uow = make_fake_uow
    orderId = "o30"
    batch = handlers.add_batch(reference="b70", sku="FANCY-TABLE", qty=50, eta=None, uow=uow)
    with pytest.raises(UnallocatedLine, match=f"Order line {orderId} is not allocated to any batch in Product {batch.sku}"):
        handlers.deallocate(sku="FANCY-TABLE", qty=50, orderId=orderId, uow=uow)


@pytest.mark.unit
@pytest.mark.service
def test_deallocate_for_absent_batch_raises_exception(make_fake_uow):
    uow = make_fake_uow
    abcent_batch_ref = "non-existent-batch-ref"
    abcent_sku = "ABCENT_SKU"
    abcent_order_id = "o30"
    with pytest.raises(InvalidSku, match=f"Invalid sku {abcent_sku}"):
        _ = handlers.get_batch(sku=abcent_sku, reference=abcent_batch_ref, uow=uow)
    handlers.add_batch(reference="b90", sku=abcent_sku, qty=20, eta=None, uow=uow)
    with pytest.raises(UnallocatedLine, match=f"Order line {abcent_order_id} is not allocated to any batch in Product {abcent_sku}"):
        _ = handlers.deallocate(sku=abcent_sku, qty=10, orderId=abcent_order_id, uow=uow)


@pytest.mark.unit
@pytest.mark.service
def test_add_batch(make_fake_uow):
    uow = make_fake_uow

    handlers.add_batch(reference="b1", sku="ADORABLE-SETTEE", qty=12, eta=None, uow=uow)

    added = handlers.get_batch(sku="ADORABLE-SETTEE", reference="b1", uow=uow)
    assert added is not None
    assert added["reference"] == "b1"
    assert added["sku"] == "ADORABLE-SETTEE"
    assert added["qty"] == 12
    assert uow.committed is True


@pytest.mark.unit
@pytest.mark.service
def test_delete_batch(make_fake_uow):
    uow = make_fake_uow
    batch_args = {
        "reference": "b1",
        "sku": "ADORABLE-SETTEE",
        "qty": 12,
        "eta": None,
    }
    existing = uow.products.list()
    assert existing == []
    with pytest.raises(InvalidSku, match=f"Invalid sku {batch_args['sku']}"):
        handlers.delete_batch(sku=batch_args["sku"], reference=batch_args["reference"], uow=uow)
    assert uow.committed is False

    handlers.add_batch(**batch_args, uow=uow)

    handlers.delete_batch(sku=batch_args["sku"], reference=batch_args["reference"], uow=uow)
    with pytest.raises(InvalidBatchReference, match=f"Invalid batch reference {batch_args['reference']}"):
        _ = handlers.get_batch(sku=batch_args["sku"], reference=batch_args["reference"], uow=uow)

    assert uow.committed is True
    product = uow.products.get(sku=batch_args["sku"])
    assert product.batches_list == []
