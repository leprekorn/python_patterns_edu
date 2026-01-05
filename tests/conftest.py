import pytest
from src import OrderLine, Batch
from src.orm import metadata, start_mappers
from datetime import date
from typing import Callable, Tuple, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, clear_mappers
from sqlalchemy.pool import StaticPool


@pytest.fixture(scope="function")
def make_batch_and_line() -> Callable[..., Tuple[Batch, OrderLine]]:
    def _make(
        batch_sku: str,
        batch_qty: int,
        line_sku: str,
        line_qty: int,
        batch_ref="batch-001",
        batch_eta: Optional[date] = date.today(),
        orderId="order-123",
    ) -> Tuple[Batch, OrderLine]:
        batch = Batch(ref=batch_ref, sku=batch_sku, qty=batch_qty, eta=batch_eta)
        line = OrderLine(orderId=orderId, sku=line_sku, qty=line_qty)
        return batch, line

    return _make


@pytest.fixture
def in_memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def orm_session(in_memory_db):
    start_mappers()
    orm_session = sessionmaker(bind=in_memory_db)()
    yield orm_session
    orm_session.close()
    clear_mappers()
