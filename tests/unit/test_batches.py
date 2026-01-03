import pytest


@pytest.mark.unit
@pytest.mark.parametrize("batch_qty", [20, 2], ids=["batch_qty=20", "batch_qty=2"])
@pytest.mark.parametrize("line_qty", [20, 2], ids=["line_qty=20", "line_qty=2"])
def test_allocating_to_a_batch_reduces_the_available_quantity(make_batch_and_line, batch_qty, line_qty):
    batch, line = make_batch_and_line(
        batch_sku="SMALL-TABLE",
        batch_qty=batch_qty,
        line_qty=line_qty,
        line_sku="SMALL-TABLE",
    )
    if batch_qty >= line_qty:
        assert batch.can_allocate(line=line)
        batch.allocate(line)
        assert batch.available_quantity == (batch_qty - line_qty)
    elif batch_qty < line_qty:
        assert batch.can_allocate(line=line) is False
