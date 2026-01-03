import pytest
from src import OrderLine, Batch
from datetime import date


@pytest.fixture(scope="function")
def make_batch_and_line():
    def _make(batch_sku, batch_qty, line_qty, line_sku, batch_ref="batch-001", batch_eta=date.today(), orderId="order-123"):
        batch = Batch(ref=batch_ref, sku=batch_sku, qty=batch_qty, eta=batch_eta)
        line = OrderLine(orderId=orderId, sku=line_sku, qty=line_qty)
        return batch, line

    return _make
