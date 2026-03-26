from datetime import date

import pytest

from allocation import views
from allocation.domain import commands

today = date.today()


@pytest.mark.integration
@pytest.mark.views
def test_allocations_view(make_real_uow_and_messagebus):
    message_bus = make_real_uow_and_messagebus
    message_bus.handle(message=commands.CreateBatch(ref="sku1batch", sku="sku1", qty=50, eta=None))
    message_bus.handle(message=commands.CreateBatch(ref="sku2batch", sku="sku2", qty=50, eta=today))
    message_bus.handle(message=commands.Allocate(order_id="order1", sku="sku1", qty=30))
    message_bus.handle(message=commands.Allocate(order_id="order1", sku="sku2", qty=20))
    message_bus.handle(message=commands.CreateBatch(ref="sku1batch-later", sku="sku1", qty=50, eta=today))
    message_bus.handle(message=commands.Allocate(order_id="otherorder", sku="sku1", qty=30))
    message_bus.handle(message=commands.Allocate(order_id="otherorder", sku="sku2", qty=10))

    assert views.allocations(order_id="order1", uow=message_bus.uow) == [
        {"sku": "sku1", "batch_ref": "sku1batch"},
        {"sku": "sku2", "batch_ref": "sku2batch"},
    ]
    assert views.allocations(order_id="otherorder", uow=message_bus.uow) == [
        {"sku": "sku1", "batch_ref": "sku1batch-later"},
        {"sku": "sku2", "batch_ref": "sku2batch"},
    ]
    assert views.allocations(order_id="nonexistentorder", uow=message_bus.uow) == []


@pytest.mark.integration
@pytest.mark.views
def test_deallocation(make_real_uow_and_messagebus):
    message_bus = make_real_uow_and_messagebus
    message_bus.handle(message=commands.CreateBatch(ref="batch1", sku="sku1", qty=50, eta=None))
    message_bus.handle(message=commands.CreateBatch(ref="batch2", sku="sku1", qty=50, eta=today))
    message_bus.handle(message=commands.Allocate(order_id="order1", sku="sku1", qty=40))
    message_bus.handle(message=commands.ChangeBatchQuantity(ref="batch1", qty=10))
    assert views.allocations(order_id="order1", uow=message_bus.uow) == [{"sku": "sku1", "batch_ref": "batch2"}]
