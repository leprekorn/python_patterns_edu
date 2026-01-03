import pytest
from src import Batch, OrderLine


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
