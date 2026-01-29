import pytest
from allocation.domain.exceptions import UnallocatedLine, InvalidBatchReference
from allocation.service_layer import services


@pytest.mark.unit
@pytest.mark.service
def test_batch_allocate_returns_allocation(make_fake_uow):
    uow = make_fake_uow
    batch = services.add_batch(reference="b1", sku="COMPLICATED-LAMP", qty=100, eta=None, uow=uow)

    result = services.allocate(orderId="o1", sku="COMPLICATED-LAMP", qty=10, uow=uow)
    assert result == batch.reference


@pytest.mark.unit
@pytest.mark.service
def test_error_for_invalid_sku(make_fake_uow):
    uow = make_fake_uow
    services.add_batch(reference="b1", sku="AREALSKU", qty=100, eta=None, uow=uow)
    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        services.allocate(orderId="01", sku="NONEXISTENTSKU", qty=10, uow=uow)


@pytest.mark.unit
@pytest.mark.service
def test_commits(make_fake_uow):
    uow = make_fake_uow
    services.add_batch(reference="b1", sku="OMINOUS-MIRROR", qty=100, eta=None, uow=uow)
    services.allocate(orderId="o1", sku="OMINOUS-MIRROR", qty=10, uow=uow)
    assert uow.committed is True


@pytest.mark.unit
@pytest.mark.service
def test_deallocate_returns_batch_reference(make_fake_uow):
    uow = make_fake_uow
    batch = services.add_batch(reference="b50", sku="CRAZY-CHAIR", qty=100, eta=None, uow=uow)
    result = services.allocate(orderId="o20", sku="CRAZY-CHAIR", qty=10, uow=uow)
    assert result == batch.reference
    assert batch.available_quantity == 90

    unallocation_result = services.deallocate(batchref=batch.reference, orderId="o20", uow=uow)
    assert unallocation_result == batch.reference
    assert batch.available_quantity == 100


@pytest.mark.unit
@pytest.mark.service
def test_deallocate_non_allocated_line_raises_exception(make_fake_uow):
    uow = make_fake_uow
    orderId = "o30"
    batch = services.add_batch(reference="b70", sku="FANCY-TABLE", qty=50, eta=None, uow=uow)
    with pytest.raises(UnallocatedLine, match=f"Order line {orderId} is not allocated to batch {batch.reference}"):
        services.deallocate(batchref=batch.reference, orderId=orderId, uow=uow)


@pytest.mark.unit
@pytest.mark.service
def test_deallocate_for_absent_batch_raises_exception(make_fake_uow):
    uow = make_fake_uow
    absent_batch_ref = "b70"
    with pytest.raises(InvalidBatchReference, match=f"Invalid batch reference {absent_batch_ref}"):
        services.deallocate(batchref=absent_batch_ref, orderId="o30", uow=uow)


@pytest.mark.unit
@pytest.mark.service
def test_add_batch(make_fake_uow):
    uow = make_fake_uow

    services.add_batch(reference="b1", sku="ADORABLE-SETTEE", qty=12, eta=None, uow=uow)

    added = uow.batches.get("b1")
    assert added is not None
    assert added.reference == "b1"
    assert added.sku == "ADORABLE-SETTEE"
    assert added._purchase_quantity == 12
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
    existing = uow.batches.list()
    assert existing == []
    with pytest.raises(InvalidBatchReference, match=f"Invalid batch reference {batch_args['reference']}"):
        services.delete_batch(reference=batch_args["reference"], uow=uow)
    assert uow.committed is False

    services.add_batch(**batch_args, uow=uow)

    services.delete_batch(reference=batch_args["reference"], uow=uow)
    deleted = uow.batches.get(reference=batch_args["reference"])
    assert deleted is None
    assert uow.committed is True
    existing = uow.batches.list()
    assert existing == []
