from datetime import date

import pytest

from allocation import views
from allocation.domain import commands

today = date.today()


@pytest.mark.integration
@pytest.mark.views
def test_allocations_view(make_real_uow_and_messagebus, make_redis_client):
    _, messagebus = make_real_uow_and_messagebus
    redisAdapter = make_redis_client
    messagebus.handle(message=commands.CreateBatch(ref="sku1batch", sku="sku1", qty=50, eta=None))
    messagebus.handle(message=commands.CreateBatch(ref="sku2batch", sku="sku2", qty=50, eta=today))
    messagebus.handle(message=commands.Allocate(order_id="order1", sku="sku1", qty=30))
    messagebus.handle(message=commands.Allocate(order_id="order1", sku="sku2", qty=20))
    messagebus.handle(message=commands.CreateBatch(ref="sku1batch-later", sku="sku1", qty=50, eta=today))
    messagebus.handle(message=commands.Allocate(order_id="otherorder", sku="sku1", qty=30))
    messagebus.handle(message=commands.Allocate(order_id="otherorder", sku="sku2", qty=10))

    assert views.allocations(order_id="order1") == [
        {"sku": "sku1", "batch_ref": "sku1batch"},
        {"sku": "sku2", "batch_ref": "sku2batch"},
    ]
    assert views.allocations(order_id="otherorder") == [
        {"sku": "sku1", "batch_ref": "sku1batch-later"},
        {"sku": "sku2", "batch_ref": "sku2batch"},
    ]

    read_model_data = redisAdapter.get_read_model(order_id="order1")
    assert read_model_data == {"sku1": "sku1batch", "sku2": "sku2batch"}, (
        f"Expected read model data to be {{'sku1': 'sku1batch', 'sku2': 'sku2batch'}}, but got {read_model_data}"
    )
    assert views.allocations(order_id="nonexistentorder") == []


@pytest.mark.integration
@pytest.mark.views
def test_deallocation(make_real_uow_and_messagebus, make_redis_client):
    _, messagebus = make_real_uow_and_messagebus
    redisAdapter = make_redis_client

    messagebus.handle(message=commands.CreateBatch(ref="batch1", sku="sku1", qty=50, eta=None))
    messagebus.handle(message=commands.CreateBatch(ref="batch2", sku="sku1", qty=50, eta=today))
    messagebus.handle(message=commands.Allocate(order_id="order1", sku="sku1", qty=40))
    messagebus.handle(message=commands.ChangeBatchQuantity(ref="batch1", qty=10))
    assert views.allocations(order_id="order1") == [{"sku": "sku1", "batch_ref": "batch2"}]
    read_model_data = redisAdapter.get_read_model(order_id="order1")
    assert read_model_data == {"sku1": "batch2"}, f"Expected read model data to be {{'sku1': 'batch2'}}, but got {read_model_data}"
