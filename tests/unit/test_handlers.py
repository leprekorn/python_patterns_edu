from unittest import mock

import pytest

from allocation.domain import events
from allocation.domain.exceptions import InvalidBatchReference, InvalidSku, UnallocatedLine
from allocation.service_layer import handlers
from allocation.service_layer.messagebus import MessageBus


@pytest.mark.unit
@pytest.mark.service
def test_batch_allocate_returns_allocation(make_fake_uow):
    uow = make_fake_uow
    sku = "COMPLICATED-LAMP"
    batch_ref = "batch1"
    MessageBus.handle(events.BatchCreated(ref=batch_ref, sku=sku, qty=100, eta=None), uow=uow)
    results = MessageBus.handle(events.AllocationRequired(orderId="o1", sku=sku, qty=10), uow=uow)
    assert results[0] == batch_ref


@pytest.mark.unit
@pytest.mark.service
def test_error_for_invalid_sku(make_fake_uow):
    uow = make_fake_uow
    existing_sku = "AREALSKU"
    abcent_sku = "NONEXISTENTSKU"
    MessageBus.handle(events.BatchCreated(ref="b1", sku=existing_sku, qty=100, eta=None), uow=uow)
    with pytest.raises(handlers.InvalidSku, match=f"Invalid sku {abcent_sku}"):
        MessageBus.handle(events.AllocationRequired(orderId="o1", sku=abcent_sku, qty=10), uow=uow)


@pytest.mark.unit
@pytest.mark.service
def test_commits(make_fake_uow):
    uow = make_fake_uow
    sku = "OMINOUS-MIRROR"
    MessageBus.handle(events.BatchCreated(ref="b1", sku=sku, qty=100, eta=None), uow=uow)
    MessageBus.handle(events.AllocationRequired(orderId="o1", sku=sku, qty=10), uow=uow)
    assert uow.committed is True


@pytest.mark.unit
@pytest.mark.service
def test_deallocate_returns_batch_reference(make_fake_uow):
    uow = make_fake_uow
    batch_ref = "b50"
    sku = "CRAZY-CHAIR"
    MessageBus.handle(events.BatchCreated(ref=batch_ref, sku=sku, qty=100, eta=None), uow=uow)
    MessageBus.handle(events.AllocationRequired(orderId="o20", sku=sku, qty=10), uow=uow)
    batch = uow.products.get(sku=sku).batches_list[0]
    assert batch.reference == batch_ref
    assert batch.available_quantity == 90

    unallocation_result = handlers.deallocate(sku=sku, orderId="o20", qty=10, uow=uow)
    assert unallocation_result == batch.reference
    assert batch.available_quantity == 100


@pytest.mark.unit
@pytest.mark.service
def test_deallocate_non_allocated_line_raises_exception(make_fake_uow):
    uow = make_fake_uow
    orderId = "o30"
    sku = "FANCY-TABLE"
    MessageBus.handle(events.BatchCreated(ref="b70", sku=sku, qty=50, eta=None), uow=uow)
    with pytest.raises(UnallocatedLine, match=f"Order line {orderId} is not allocated to any batch in Product {sku}"):
        handlers.deallocate(sku=sku, qty=50, orderId=orderId, uow=uow)


@pytest.mark.unit
@pytest.mark.service
def test_deallocate_for_absent_batch_raises_exception(make_fake_uow):
    uow = make_fake_uow
    abcent_batch_ref = "non-existent-batch-ref"
    abcent_sku = "ABCENT_SKU"
    abcent_order_id = "o30"
    with pytest.raises(InvalidSku, match=f"Invalid sku {abcent_sku}"):
        _ = handlers.get_batch(sku=abcent_sku, reference=abcent_batch_ref, uow=uow)
    MessageBus.handle(events.BatchCreated(ref="b90", sku=abcent_sku, qty=20, eta=None), uow=uow)
    with pytest.raises(UnallocatedLine, match=f"Order line {abcent_order_id} is not allocated to any batch in Product {abcent_sku}"):
        _ = handlers.deallocate(sku=abcent_sku, qty=10, orderId=abcent_order_id, uow=uow)


@pytest.mark.unit
@pytest.mark.service
def test_add_batch(make_fake_uow):
    uow = make_fake_uow
    sku = "ADORABLE-SETTEE"
    MessageBus.handle(events.BatchCreated(ref="b1", sku=sku, qty=12, eta=None), uow=uow)
    added = handlers.get_batch(sku=sku, reference="b1", uow=uow)
    assert added is not None
    assert added["reference"] == "b1"
    assert added["sku"] == sku
    assert added["qty"] == 12
    assert uow.committed is True


@pytest.mark.unit
@pytest.mark.service
def test_delete_batch(make_fake_uow):
    uow = make_fake_uow
    batch_args = {
        "ref": "b1",
        "sku": "ADORABLE-SETTEE",
        "qty": 12,
        "eta": None,
    }
    existing = uow.products.list()
    assert existing == []
    with pytest.raises(InvalidSku, match=f"Invalid sku {batch_args['sku']}"):
        handlers.delete_batch(sku=batch_args["sku"], reference=batch_args["ref"], uow=uow)
    assert uow.committed is False

    MessageBus.handle(events.BatchCreated(**batch_args), uow=uow)

    handlers.delete_batch(sku=batch_args["sku"], reference=batch_args["ref"], uow=uow)
    with pytest.raises(InvalidBatchReference, match=f"Invalid batch reference {batch_args['ref']}"):
        _ = handlers.get_batch(sku=batch_args["sku"], reference=batch_args["ref"], uow=uow)

    assert uow.committed is True
    product = uow.products.get(sku=batch_args["sku"])
    assert product.batches_list == []


@pytest.mark.unit
@pytest.mark.service
def test_sends_email_on_out_of_stock_error(make_fake_uow):
    uow = make_fake_uow
    sku = "POPULAR-CURTAINS"
    MessageBus.handle(events.BatchCreated(ref="batch1", sku=sku, qty=5, eta=None), uow=uow)
    allocation_result = MessageBus.handle(events.AllocationRequired(orderId="o1", sku=sku, qty=10), uow=uow)
    assert allocation_result[0] is None
    product = uow.products.get(sku=sku)
    assert len(product.events) == 1
    out_of_stock_event = product.events[0]
    assert isinstance(out_of_stock_event, events.OutOfStock)
    with mock.patch("allocation.adapters.email.send_email") as mock_send_email:
        MessageBus.handle(event=out_of_stock_event, uow=uow)
        mock_send_email.assert_called_once_with(
            "stock@made.com",
            f"Out of stock for {out_of_stock_event.sku}",
        )


@pytest.mark.unit
@pytest.mark.service
def test_changes_available_quantity(make_fake_uow):
    uow = make_fake_uow
    sku = "STYLISH-LAMP"
    batch_ref = "batch1"
    MessageBus.handle(event=events.BatchCreated(ref=batch_ref, sku=sku, qty=100, eta=None), uow=uow)
    batch = uow.products.get(sku=sku).batches_list[0]
    assert batch.available_quantity == 100
    MessageBus.handle(event=events.BatchQuantityChanged(ref=batch_ref, qty=50), uow=uow)
    assert batch.available_quantity == 50
