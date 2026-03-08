from datetime import date

import pytest

from allocation import views
from allocation.domain import commands

today = date.today()


@pytest.mark.integration
@pytest.mark.views
def test_allocations_view(make_real_uow_and_messagebus):
    uow, messagebus = make_real_uow_and_messagebus
    messagebus.handle(message=commands.CreateBatch(ref="sku1batch", sku="sku1", qty=50, eta=None))
    messagebus.handle(message=commands.CreateBatch(ref="sku2batch", sku="sku2", qty=50, eta=today))
    messagebus.handle(message=commands.Allocate(orderId="order1", sku="sku1", qty=30))
    messagebus.handle(message=commands.Allocate(orderId="order1", sku="sku2", qty=20))
    messagebus.handle(message=commands.CreateBatch(ref="sku1batch-later", sku="sku1", qty=50, eta=today))
    messagebus.handle(message=commands.Allocate(orderId="otherorder", sku="sku1", qty=30))
    messagebus.handle(message=commands.Allocate(orderId="otherorder", sku="sku2", qty=10))

    assert views.allocations(orderId="order1", uow=uow) == {"sku": "sku1", "batchref": "sku1batch"}
    assert views.allocations(orderId="otherorder", uow=uow) == {"sku": "sku1", "batchref": "sku1batch-later"}
    assert views.allocations(orderId="nonexistentorder", uow=uow) is None
