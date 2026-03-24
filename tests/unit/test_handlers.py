from datetime import date
from unittest import mock

import pytest

from allocation.domain import commands, events
from allocation.domain.exceptions import InvalidBatchReference, InvalidSku, UnallocatedLine
from allocation.service_layer import handlers


@pytest.mark.unit
@pytest.mark.service
def test_batch_allocate(make_fake_uow_and_messagebus):
    message_bus = make_fake_uow_and_messagebus
    sku = "COMPLICATED-LAMP"
    batch_ref = "batch1"
    message_bus.handle(message=commands.CreateBatch(ref=batch_ref, sku=sku, qty=100, eta=None))
    message_bus.handle(message=commands.Allocate(order_id="o1", sku=sku, qty=10))
    batch = message_bus.uow.products.get(sku=sku).batches_list[0]
    assert batch.reference == batch_ref
    assert batch.available_quantity == 90


@pytest.mark.unit
@pytest.mark.service
def test_error_for_invalid_sku(make_fake_uow_and_messagebus):
    message_bus = make_fake_uow_and_messagebus
    existing_sku = "AREALSKU"
    abcent_sku = "NONEXISTENTSKU"

    message_bus.handle(message=commands.CreateBatch(ref="b1", sku=existing_sku, qty=100, eta=None))
    with pytest.raises(handlers.InvalidSku, match=f"Invalid sku {abcent_sku}"):
        message_bus.handle(message=commands.Allocate(order_id="o1", sku=abcent_sku, qty=10))


@pytest.mark.unit
@pytest.mark.service
def test_commits(make_fake_uow_and_messagebus):
    message_bus = make_fake_uow_and_messagebus
    sku = "OMINOUS-MIRROR"
    message_bus.handle(message=commands.CreateBatch(ref="b1", sku=sku, qty=100, eta=None))
    message_bus.handle(message=commands.Allocate(order_id="o1", sku=sku, qty=10))
    assert message_bus.uow.committed is True


@pytest.mark.unit
@pytest.mark.service
def test_deallocate(make_fake_uow_and_messagebus):
    message_bus = make_fake_uow_and_messagebus
    batch_ref = "b50"
    sku = "CRAZY-CHAIR"
    message_bus.handle(message=commands.CreateBatch(ref=batch_ref, sku=sku, qty=100, eta=None))
    message_bus.handle(message=commands.Allocate(order_id="o20", sku=sku, qty=10))
    batch = message_bus.uow.products.get(sku=sku).batches_list[0]
    assert batch.reference == batch_ref
    assert batch.available_quantity == 90

    message_bus.handle(message=commands.Deallocate(sku=sku, order_id="o20", qty=10))
    assert batch.available_quantity == 100


@pytest.mark.unit
@pytest.mark.service
def test_deallocate_non_allocated_line_raises_exception(make_fake_uow_and_messagebus):
    message_bus = make_fake_uow_and_messagebus
    order_id = "o30"
    sku = "FANCY-TABLE"
    message_bus.handle(message=commands.CreateBatch(ref="b70", sku=sku, qty=50, eta=None))
    with pytest.raises(UnallocatedLine, match=f"Order line {order_id} is not allocated to any batch in Product {sku}"):
        message_bus.handle(message=commands.Deallocate(sku=sku, qty=50, order_id=order_id))


@pytest.mark.unit
@pytest.mark.service
def test_deallocate_for_absent_batch_raises_exception(make_fake_uow_and_messagebus):
    message_bus = make_fake_uow_and_messagebus
    abcent_batch_ref = "non-existent-batch-ref"
    abcent_sku = "ABCENT_SKU"
    abcent_order_id = "o30"
    with pytest.raises(InvalidSku, match=f"Invalid sku {abcent_sku}"):
        _ = handlers.get_batch(sku=abcent_sku, reference=abcent_batch_ref, uow=message_bus.uow)
    message_bus.handle(message=commands.CreateBatch(ref="b90", sku=abcent_sku, qty=20, eta=None))
    with pytest.raises(UnallocatedLine, match=f"Order line {abcent_order_id} is not allocated to any batch in Product {abcent_sku}"):
        message_bus.handle(message=commands.Deallocate(sku=abcent_sku, qty=10, order_id=abcent_order_id))


@pytest.mark.unit
@pytest.mark.service
def test_add_batch(make_fake_uow_and_messagebus):
    message_bus = make_fake_uow_and_messagebus
    sku = "ADORABLE-SETTEE"
    message_bus.handle(message=commands.CreateBatch(ref="b1", sku=sku, qty=12, eta=None))
    added = handlers.get_batch(sku=sku, reference="b1", uow=message_bus.uow)
    assert added is not None
    assert added["reference"] == "b1"
    assert added["sku"] == sku
    assert added["qty"] == 12
    assert message_bus.uow.committed is True


@pytest.mark.unit
@pytest.mark.service
def test_delete_batch(make_fake_uow_and_messagebus):
    message_bus = make_fake_uow_and_messagebus
    batch_args = {
        "ref": "b1",
        "sku": "ADORABLE-SETTEE",
        "qty": 12,
        "eta": None,
    }
    existing = message_bus.uow.products.list()
    assert existing == []
    with pytest.raises(InvalidSku, match=f"Invalid sku {batch_args['sku']}"):
        message_bus.handle(message=commands.DeleteBatch(sku=batch_args["sku"], ref=batch_args["ref"]))
    assert message_bus.uow.committed is False

    message_bus.handle(message=commands.CreateBatch(**batch_args))

    message_bus.handle(message=commands.DeleteBatch(sku=batch_args["sku"], ref=batch_args["ref"]))
    with pytest.raises(InvalidBatchReference, match=f"Invalid batch reference {batch_args['ref']}"):
        _ = handlers.get_batch(sku=batch_args["sku"], reference=batch_args["ref"], uow=message_bus.uow)

    assert message_bus.uow.committed is True
    product = message_bus.uow.products.get(sku=batch_args["sku"])
    assert product.batches_list == []


@pytest.mark.unit
@pytest.mark.service
def test_sends_email_on_out_of_stock_error(make_fake_uow_and_messagebus):
    message_bus = make_fake_uow_and_messagebus
    sku = "POPULAR-CURTAINS"
    message_bus.handle(message=commands.CreateBatch(ref="batch1", sku=sku, qty=5, eta=None))
    allocation_result = message_bus.handle(message=commands.Allocate(order_id="o1", sku=sku, qty=10))
    assert allocation_result[0] is None
    [collected_events] = message_bus.uow.events_published
    assert isinstance(collected_events, events.OutOfStock)
    assert collected_events.sku == sku
    with mock.patch("allocation.adapters.email.send_email") as mock_send_email:
        message_bus.handle(message=events.OutOfStock(sku=collected_events.sku))
        mock_send_email.assert_called_once_with(
            "stock@made.com",
            f"Out of stock for {collected_events.sku}",
        )


@pytest.mark.unit
@pytest.mark.service
def test_changes_available_quantity(make_fake_uow_and_messagebus):
    message_bus = make_fake_uow_and_messagebus
    sku = "STYLISH-LAMP"
    batch_ref = "batch1"
    message_bus.handle(message=commands.CreateBatch(ref=batch_ref, sku=sku, qty=100, eta=None))
    batch = message_bus.uow.products.get(sku=sku).batches_list[0]
    assert batch.available_quantity == 100
    message_bus.handle(message=commands.ChangeBatchQuantity(ref=batch_ref, qty=50))
    assert batch.available_quantity == 50


@pytest.mark.unit
@pytest.mark.service
def test_reallocates_on_batch_quantity_changed(make_fake_uow_and_messagebus):
    message_bus = make_fake_uow_and_messagebus
    task_list = [
        commands.CreateBatch(ref="batch1", sku="INDIFFERENT-TABLE", qty=50, eta=None),
        commands.CreateBatch(ref="batch2", sku="INDIFFERENT-TABLE", qty=50, eta=date.today()),
        commands.Allocate(order_id="order1", sku="INDIFFERENT-TABLE", qty=20),
        commands.Allocate(order_id="order2", sku="INDIFFERENT-TABLE", qty=20),
    ]
    for e in task_list:
        message_bus.handle(e)
    [batch1, batch2] = message_bus.uow.products.get(sku="INDIFFERENT-TABLE").batches
    assert batch1.available_quantity == 10
    assert batch2.available_quantity == 50

    message_bus.handle(commands.ChangeBatchQuantity(ref="batch1", qty=25))

    # order1 or order2 will be deallocated, so we'll have 25 - 20
    assert batch1.available_quantity == 5
    # and 20 will be reallocated to the next batch
    assert batch2.available_quantity == 30

    collected_events = list(message_bus.uow.events_published)
    assert all(isinstance(e, events.Event) for e in collected_events)
    assert all(not isinstance(e, commands.Command) for e in collected_events)
