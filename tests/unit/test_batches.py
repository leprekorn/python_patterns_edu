import pytest
from src import Batch, OrderLine, allocate
import datetime

today = datetime.date.today()
tomorrow = today + datetime.timedelta(days=1)
day_after_tomorrow = today + datetime.timedelta(days=2)


@pytest.mark.unit
@pytest.mark.parametrize("batch_qty", [20, 2], ids=["batch_qty=20", "batch_qty=2"])
@pytest.mark.parametrize("line_qty", [20, 2], ids=["line_qty=20", "line_qty=2"])
def test_allocating_to_a_batch_reduces_the_available_quantity(make_batch_and_line, batch_qty, line_qty):
    batch: Batch
    line: OrderLine
    batch, line = make_batch_and_line(
        batch_sku="SMALL-TABLE",
        batch_qty=batch_qty,
        line_sku="SMALL-TABLE",
        line_qty=line_qty,
    )
    if batch_qty >= line_qty:
        assert batch.can_allocate(line=line)
        batch.allocate(line)
        assert batch.available_quantity == (batch_qty - line_qty)
    elif batch_qty < line_qty:
        assert batch.can_allocate(line=line) is False


@pytest.mark.unit
def test_cannot_allocate_if_skus_do_not_match(make_batch_and_line):
    batch: Batch
    line: OrderLine
    batch, line = make_batch_and_line(
        batch_sku="UNCOMFORTABLE-CHAIR",
        batch_qty=100,
        line_sku="EXPENSIVE-TOASTER",
        line_qty=10,
    )

    assert batch.can_allocate(line=line) is False


@pytest.mark.unit
def test_can_only_deallocate_allocated_lines(make_batch_and_line):
    batch: Batch
    unallocated_line: OrderLine
    batch, unallocated_line = make_batch_and_line(
        batch_sku="DECORATIVE_TRINKET",
        batch_qty=20,
        line_sku="DECORATIVE_TRINKET",
        line_qty=2,
    )
    batch.deallocate(line=unallocated_line)
    assert batch.available_quantity == 20


@pytest.mark.unit
def test_allocation_is_idempotent(make_batch_and_line):
    batch: Batch
    line: OrderLine
    batch, line = make_batch_and_line(
        batch_sku="ANGULAR-DESK",
        batch_qty=20,
        line_sku="ANGULAR-DESK",
        line_qty=2,
    )
    batch.allocate(line=line)
    batch.allocate(line=line)
    assert batch.available_quantity == 18


@pytest.mark.unit
def test_prefers_current_stock_batches_to_shipments():
    in_stock_batch = Batch(ref="in-stock-batch", sku="RETRO-CLOCK", qty=100, eta=None)
    shipment_batch = Batch(ref="shipment_batch", sku="RETRO-CLOCK", qty=100, eta=tomorrow)
    line = OrderLine(orderId="oref", sku="RETRO-CLOCK", qty=10)
    allocated_batch = allocate(line=line, batches=[in_stock_batch, shipment_batch])
    assert allocated_batch is in_stock_batch
    assert shipment_batch.available_quantity == 100
    assert in_stock_batch.available_quantity == 90


@pytest.mark.unit
def test_prefers_earlier_batches():
    fastest = Batch(ref="fastest_batch", sku="MINIMALIST_SPOON", qty=100, eta=today)
    medium = Batch(ref="medium_batch", sku="MINIMALIST_SPOON", qty=100, eta=tomorrow)
    slower = Batch(ref="slow-batch", sku="MINIMALIST_SPOON", qty=100, eta=day_after_tomorrow)
    line = OrderLine(orderId="oref", sku="MINIMALIST_SPOON", qty=10)
    allocated_batch = allocate(line=line, batches=[fastest, medium, slower])
    assert allocated_batch is fastest
    assert fastest.available_quantity == 90
    assert medium.available_quantity == 100
    assert slower.available_quantity == 100
