import pytest


@pytest.mark.unit
def test_allocating_to_a_batch_reduces_the_available_quantity(make_batch_and_line):
    batch, line = make_batch_and_line(
        batch_sku="SMALL-TABLE",
        batch_qty=20,
        line_qty=2,
        line_sku="SMALL-TABLE",
    )

    batch.allocate(line)
    assert batch.available_quantity == 18
