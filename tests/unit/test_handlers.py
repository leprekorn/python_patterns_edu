from datetime import date
from unittest import mock

import pytest

from allocation.domain import commands, events
from allocation.domain.exceptions import InvalidBatchReference, InvalidSku, UnallocatedLine
from allocation.service_layer import handlers


@pytest.mark.unit
@pytest.mark.service
def test_batch_allocate(make_fake_uow_and_messagebus):
    uow, messagebus = make_fake_uow_and_messagebus
    sku = "COMPLICATED-LAMP"
    batch_ref = "batch1"
    messagebus.handle(message=commands.CreateBatch(ref=batch_ref, sku=sku, qty=100, eta=None))
    messagebus.handle(message=commands.Allocate(orderId="o1", sku=sku, qty=10))
    batch = uow.products.get(sku=sku).batches_list[0]
    assert batch.reference == batch_ref
    assert batch.available_quantity == 90


@pytest.mark.unit
@pytest.mark.service
def test_error_for_invalid_sku(make_fake_uow_and_messagebus):
    _, messagebus = make_fake_uow_and_messagebus
    existing_sku = "AREALSKU"
    abcent_sku = "NONEXISTENTSKU"

    messagebus.handle(message=commands.CreateBatch(ref="b1", sku=existing_sku, qty=100, eta=None))
    with pytest.raises(handlers.InvalidSku, match=f"Invalid sku {abcent_sku}"):
        messagebus.handle(message=commands.Allocate(orderId="o1", sku=abcent_sku, qty=10))


@pytest.mark.unit
@pytest.mark.service
def test_commits(make_fake_uow_and_messagebus):
    uow, messagebus = make_fake_uow_and_messagebus
    sku = "OMINOUS-MIRROR"
    messagebus.handle(message=commands.CreateBatch(ref="b1", sku=sku, qty=100, eta=None))
    messagebus.handle(message=commands.Allocate(orderId="o1", sku=sku, qty=10))
    assert uow.committed is True


@pytest.mark.unit
@pytest.mark.service
def test_deallocate(make_fake_uow_and_messagebus):
    uow, messagebus = make_fake_uow_and_messagebus
    batch_ref = "b50"
    sku = "CRAZY-CHAIR"
    messagebus.handle(message=commands.CreateBatch(ref=batch_ref, sku=sku, qty=100, eta=None))
    messagebus.handle(message=commands.Allocate(orderId="o20", sku=sku, qty=10))
    batch = uow.products.get(sku=sku).batches_list[0]
    assert batch.reference == batch_ref
    assert batch.available_quantity == 90

    messagebus.handle(message=commands.Deallocate(sku=sku, orderId="o20", qty=10))
    assert batch.available_quantity == 100


@pytest.mark.unit
@pytest.mark.service
def test_deallocate_non_allocated_line_raises_exception(make_fake_uow_and_messagebus):
    _, messagebus = make_fake_uow_and_messagebus
    orderId = "o30"
    sku = "FANCY-TABLE"
    messagebus.handle(message=commands.CreateBatch(ref="b70", sku=sku, qty=50, eta=None))
    with pytest.raises(UnallocatedLine, match=f"Order line {orderId} is not allocated to any batch in Product {sku}"):
        messagebus.handle(message=commands.Deallocate(sku=sku, qty=50, orderId=orderId))


@pytest.mark.unit
@pytest.mark.service
def test_deallocate_for_absent_batch_raises_exception(make_fake_uow_and_messagebus):
    uow, messagebus = make_fake_uow_and_messagebus
    abcent_batch_ref = "non-existent-batch-ref"
    abcent_sku = "ABCENT_SKU"
    abcent_order_id = "o30"
    with pytest.raises(InvalidSku, match=f"Invalid sku {abcent_sku}"):
        _ = handlers.get_batch(sku=abcent_sku, reference=abcent_batch_ref, uow=uow)
    messagebus.handle(message=commands.CreateBatch(ref="b90", sku=abcent_sku, qty=20, eta=None))
    with pytest.raises(UnallocatedLine, match=f"Order line {abcent_order_id} is not allocated to any batch in Product {abcent_sku}"):
        messagebus.handle(message=commands.Deallocate(sku=abcent_sku, qty=10, orderId=abcent_order_id))


@pytest.mark.unit
@pytest.mark.service
def test_add_batch(make_fake_uow_and_messagebus):
    uow, messagebus = make_fake_uow_and_messagebus
    sku = "ADORABLE-SETTEE"
    messagebus.handle(message=commands.CreateBatch(ref="b1", sku=sku, qty=12, eta=None))
    added = handlers.get_batch(sku=sku, reference="b1", uow=uow)
    assert added is not None
    assert added["reference"] == "b1"
    assert added["sku"] == sku
    assert added["qty"] == 12
    assert uow.committed is True


@pytest.mark.unit
@pytest.mark.service
def test_delete_batch(make_fake_uow_and_messagebus):
    uow, messagebus = make_fake_uow_and_messagebus
    batch_args = {
        "ref": "b1",
        "sku": "ADORABLE-SETTEE",
        "qty": 12,
        "eta": None,
    }
    existing = uow.products.list()
    assert existing == []
    with pytest.raises(InvalidSku, match=f"Invalid sku {batch_args['sku']}"):
        messagebus.handle(message=commands.DeleteBatch(sku=batch_args["sku"], ref=batch_args["ref"]))
    assert uow.committed is False

    messagebus.handle(message=commands.CreateBatch(**batch_args))

    messagebus.handle(message=commands.DeleteBatch(sku=batch_args["sku"], ref=batch_args["ref"]))
    with pytest.raises(InvalidBatchReference, match=f"Invalid batch reference {batch_args['ref']}"):
        _ = handlers.get_batch(sku=batch_args["sku"], reference=batch_args["ref"], uow=uow)

    assert uow.committed is True
    product = uow.products.get(sku=batch_args["sku"])
    assert product.batches_list == []


@pytest.mark.unit
@pytest.mark.service
def test_sends_email_on_out_of_stock_error(make_fake_uow_and_messagebus):
    uow, messagebus = make_fake_uow_and_messagebus
    sku = "POPULAR-CURTAINS"
    messagebus.handle(message=commands.CreateBatch(ref="batch1", sku=sku, qty=5, eta=None))
    allocation_result = messagebus.handle(message=commands.Allocate(orderId="o1", sku=sku, qty=10))
    assert allocation_result[0] is None
    [collected_events] = uow.events_published
    assert isinstance(collected_events, events.OutOfStock)
    assert collected_events.sku == sku
    with mock.patch("allocation.adapters.email.send_email") as mock_send_email:
        messagebus.handle(message=events.OutOfStock(sku=collected_events.sku))
        mock_send_email.assert_called_once_with(
            "stock@made.com",
            f"Out of stock for {collected_events.sku}",
        )


@pytest.mark.unit
@pytest.mark.service
def test_changes_available_quantity(make_fake_uow_and_messagebus):
    uow, messagebus = make_fake_uow_and_messagebus
    sku = "STYLISH-LAMP"
    batch_ref = "batch1"
    messagebus.handle(message=commands.CreateBatch(ref=batch_ref, sku=sku, qty=100, eta=None))
    batch = uow.products.get(sku=sku).batches_list[0]
    assert batch.available_quantity == 100
    messagebus.handle(message=commands.ChangeBatchQuantity(ref=batch_ref, qty=50))
    assert batch.available_quantity == 50


@pytest.mark.unit
@pytest.mark.service
def test_reallocates_on_batch_quantity_changed(make_fake_uow_and_messagebus):
    uow, messagebus = make_fake_uow_and_messagebus
    task_list = [
        commands.CreateBatch(ref="batch1", sku="INDIFFERENT-TABLE", qty=50, eta=None),
        commands.CreateBatch(ref="batch2", sku="INDIFFERENT-TABLE", qty=50, eta=date.today()),
        commands.Allocate(orderId="order1", sku="INDIFFERENT-TABLE", qty=20),
        commands.Allocate(orderId="order2", sku="INDIFFERENT-TABLE", qty=20),
    ]
    for e in task_list:
        messagebus.handle(e)
    [batch1, batch2] = uow.products.get(sku="INDIFFERENT-TABLE").batches
    assert batch1.available_quantity == 10
    assert batch2.available_quantity == 50

    messagebus.handle(commands.ChangeBatchQuantity(ref="batch1", qty=25))

    # order1 or order2 will be deallocated, so we'll have 25 - 20
    assert batch1.available_quantity == 5
    # and 20 will be reallocated to the next batch
    assert batch2.available_quantity == 30

    collected_events = list(uow.events_published)
    assert any(isinstance(e, commands.Allocate) and e.orderId in ["order1", "order2"] for e in collected_events)
