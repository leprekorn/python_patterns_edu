import pytest
from datetime import date
from src.model import Batch, OrderLine


@pytest.mark.unit
def test_allocating_to_a_batch_reduces_the_available_quantity():
    batch = Batch(ref="batch-001", sku="SMALL-TABLE", qty=20, eta=date.today())
    line = OrderLine(orderId="order-ref", sku="SMALL-TABLE", qty=2)
    batch.allocate(line)
    assert batch.available_quantity == 18
