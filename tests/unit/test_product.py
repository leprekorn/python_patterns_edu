import pytest
from allocation.domain.model import Batch, OrderLine, Product
from allocation.domain import exceptions, events
import datetime

today = datetime.date.today()
tomorrow = today + datetime.timedelta(days=1)
day_after_tomorrow = today + datetime.timedelta(days=2)


@pytest.mark.unit
@pytest.mark.parametrize("batch_qty", [20, 2], ids=["batch_qty=20", "batch_qty=2"])
@pytest.mark.parametrize("line_qty", [20, 2], ids=["line_qty=20", "line_qty=2"])
def test_allocating_to_a_batch_reduces_the_available_quantity(make_batch_and_line, batch_qty, line_qty):
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
    batch, line = make_batch_and_line(
        batch_sku="UNCOMFORTABLE-CHAIR",
        batch_qty=100,
        line_sku="EXPENSIVE-TOASTER",
        line_qty=10,
    )
    initial_allocations = batch.allocated_quantity

    assert batch.can_allocate(line=line) is False
    batch.allocate(line)
    assert batch.allocated_quantity == initial_allocations


@pytest.mark.unit
def test_dunders(make_batch_and_line):
    batch, line = make_batch_and_line(
        batch_sku="ROUND-BOX",
        batch_qty=50,
        line_sku="ROUND-BOX",
        line_qty=10,
    )
    assert batch != line

    with pytest.raises(ValueError, match="Other instance is not a Batch object!"):
        _ = batch > line

    with pytest.raises(ValueError, match="Other instance is not a Batch object!"):
        _ = batch < line

    hash_dict = {batch: "batch1"}
    assert list(hash_dict.keys())[0] == batch


@pytest.mark.unit
def test_can_only_deallocate_allocated_lines(make_batch_and_line):
    batch, unallocated_line = make_batch_and_line(
        batch_sku="DECORATIVE_TRINKET",
        batch_qty=20,
        line_sku="DECORATIVE_TRINKET",
        line_qty=2,
    )
    batch.deallocate(line=unallocated_line)
    assert batch.available_quantity == 20
    batch.allocate(line=unallocated_line)
    assert batch.available_quantity == 18
    batch.deallocate(line=unallocated_line)
    assert batch.available_quantity == 20


@pytest.mark.unit
def test_allocation_is_idempotent(make_batch_and_line):
    batch, line = make_batch_and_line(
        batch_sku="ANGULAR-DESK",
        batch_qty=20,
        line_sku="ANGULAR-DESK",
        line_qty=2,
    )
    batch.allocate(line=line)
    batch.allocate(line=line)
    batch.allocate(line=line)
    assert batch.available_quantity == 18


@pytest.mark.unit
def test_prefers_current_stock_batches_to_shipments():
    in_stock_batch = Batch(ref="in-stock-batch", sku="RETRO-CLOCK", qty=100, eta=None)
    shipment_batch = Batch(ref="shipment_batch", sku="RETRO-CLOCK", qty=100, eta=tomorrow)
    product = Product(sku="RETRO-CLOCK", batches=[in_stock_batch, shipment_batch])
    line = OrderLine(orderId="oref", sku="RETRO-CLOCK", qty=10)

    assert in_stock_batch < shipment_batch
    assert shipment_batch > in_stock_batch
    assert not (in_stock_batch > shipment_batch)

    gt_result = shipment_batch.__gt__(in_stock_batch)
    assert gt_result is True

    allocated_batch = product.allocate(line=line)
    assert allocated_batch is in_stock_batch
    assert shipment_batch.available_quantity == 100
    assert in_stock_batch.available_quantity == 90


@pytest.mark.unit
def test_prefers_earlier_batches():
    fastest = Batch(ref="fastest_batch", sku="MINIMALIST_SPOON", qty=100, eta=today)
    medium = Batch(ref="medium_batch", sku="MINIMALIST_SPOON", qty=100, eta=tomorrow)
    slower = Batch(ref="slow-batch", sku="MINIMALIST_SPOON", qty=100, eta=day_after_tomorrow)
    line = OrderLine(orderId="oref", sku="MINIMALIST_SPOON", qty=10)
    product = Product(sku="MINIMALIST_SPOON", batches=[slower, medium, fastest])
    allocated_batch = product.allocate(line=line)
    assert allocated_batch is fastest
    assert fastest.available_quantity == 90
    assert medium.available_quantity == 100
    assert slower.available_quantity == 100


@pytest.mark.unit
def test_raises_out_of_stock_exception_if_cannot_allocate(make_batch_and_line):
    batch, line = make_batch_and_line(
        batch_sku="SMALL-FORK",
        batch_qty=10,
        line_sku="SMALL-FORK",
        line_qty=2,
    )
    product = Product(sku="SMALL-FORK", batches=[batch])

    product.allocate(line=line)

    extra_order = OrderLine(orderId="extra_oder", sku="SMALL-FORK", qty=10)
    with pytest.raises(exceptions.OutOfStock, match="SMALL-FORK"):
        product.allocate(line=extra_order)


@pytest.mark.unit
def test_increments_version_number():
    line = OrderLine("oref", "SCANDI-PEN", 10)
    product = Product(sku="SCANDI-PEN", batches=[Batch("b1", "SCANDI-PEN", 100, eta=None)], version_number=7)
    product.allocate(line)
    assert product.version_number == 8


@pytest.mark.unit
def test_records_out_of_stock_event_if_cannot_allocate():
    sku1_batch = Batch("batch1", "sku1", 100, eta=today)
    sku2_line = OrderLine("oref", "sku2", 10)
    product = Product(sku="sku1", batches=[sku1_batch])

    with pytest.raises(exceptions.OutOfStock):
        product.allocate(sku2_line)
    assert product.events[-1] == events.OutOfStock(sku="sku2")
