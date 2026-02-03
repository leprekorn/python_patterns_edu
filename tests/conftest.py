import pytest
from allocation.domain.model import OrderLine, Product, Batch
from allocation.adapters.orm import metadata, start_mappers
from allocation import config
from allocation.entrypoints.main import app
from datetime import date
from typing import Callable, Tuple, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, clear_mappers
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import time
import pathlib
import httpx

from allocation.interfaces.main import IRepository, ISession, IUnitOfWork
from typing import List, Generator


class FakeUnitOfWork(IUnitOfWork):
    def __init__(self, session_factory: Callable[[], ISession]):
        self.session_factory = session_factory
        self.committed = False
        self.products = FakeRepository([])

    def __enter__(self):
        self.session = self.session_factory()
        return super().__enter__()

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


class FakeRepository(IRepository):
    def __init__(self, products: List[Product]):
        self._products = set(products)

    def add(self, product: Product):
        self._products.add(product)

    def delete(self, sku: str):
        product = self.get(sku=sku)
        if product:
            self._products.remove(product)

    def get(self, sku: str) -> Optional[Product]:
        product = next((b for b in self._products if b.sku == sku), None)
        return product

    def list(self):
        return list(self._products)


@pytest.fixture(scope="function")
def make_fake_uow(session_factory: Callable[[], ISession]) -> FakeUnitOfWork:
    session_factory = session_factory
    uow = FakeUnitOfWork(session_factory=session_factory)
    return uow


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


@pytest.fixture(scope="function")
def insert_batch_via_session() -> Callable[[ISession, str, str, int, date | None], int]:
    def _make(
        session: ISession,
        ref: str,
        sku: str,
        qty: int,
        eta: Optional[date],
    ) -> int:
        session.execute(
            text("INSERT INTO products (sku) VALUES (:sku)"),
            dict(sku=sku),
        )

        session.execute(
            text("INSERT INTO batches (reference, sku, _purchase_quantity, eta) VALUES (:ref, :sku, :_purchase_quantity, :eta)"),
            dict(ref=ref, sku=sku, _purchase_quantity=qty, eta=eta),
        )

        [[batch_id]] = session.execute(
            text("SELECT id FROM batches WHERE reference=:ref AND sku=:sku"),
            dict(ref=ref, sku=sku),
        )
        return batch_id

    return _make


@pytest.fixture(scope="function")
def in_memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def orm_session(in_memory_db):
    clear_mappers()
    start_mappers()
    orm_session = sessionmaker(bind=in_memory_db)()
    yield orm_session
    orm_session.close()
    clear_mappers()


@pytest.fixture(scope="function")
def session_factory(in_memory_db) -> Generator[Callable[[], ISession], None, None]:
    clear_mappers()
    start_mappers()
    callable_session = sessionmaker(bind=in_memory_db)
    yield callable_session
    clear_mappers()


@pytest.fixture(scope="function")
def restart_api():
    app_file = pathlib.Path(__file__).parent.parent / "src" / "allocation" / "entrypoints" / "main.py"
    app_file.touch()
    time.sleep(0.5)
    __wait_for_webapp_to_come_up()


def __wait_for_webapp_to_come_up():
    deadline = time.time() + 10
    url = config.get_api_url()
    while time.time() < deadline:
        try:
            return httpx.get(url)
        except ConnectionError:
            time.sleep(0.5)
    pytest.fail("API never came up")


@pytest.fixture(scope="function")
def fastapi_test_client():
    clear_mappers()
    start_mappers()
    client = TestClient(app)
    yield client
    clear_mappers()
    truncate_queries = (
        "truncate table products CASCADE;",
        "truncate table allocations CASCADE;",
        "truncate table batches CASCADE;",
        "truncate table order_lines CASCADE;",
    )

    engine = create_engine(url=config.get_db_uri())
    with engine.begin() as conn:
        for truncate_query in truncate_queries:
            conn.execute(text(truncate_query))
