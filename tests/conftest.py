import pathlib
import time
from datetime import date
from typing import Callable, Generator, List, Optional, Tuple

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import clear_mappers, sessionmaker
from sqlalchemy.pool import StaticPool

from allocation import config
from allocation.adapters.orm import metadata, start_mappers
from allocation.domain.model import Batch, OrderLine, Product
from allocation.entrypoints.main import app
from allocation.interfaces.main import IRepository, ISession, IUnitOfWork

TRUNCATE_QUERIES = (
    "truncate table products CASCADE;",
    "truncate table allocations CASCADE;",
    "truncate table batches CASCADE;",
    "truncate table order_lines CASCADE;",
)


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

    def collect_new_events(self):
        return []


class FakeRepository(IRepository):
    def __init__(self, products: List[Product]):
        self._products = set(products)
        self.seen = set(products)

    def add(self, product: Product):
        self._products.add(product)
        self.seen.add(product)

    def delete(self, sku: str):
        product = self.get(sku=sku)
        if product:
            self._products.remove(product)
            self.seen.discard(product)

    def get(self, sku: str) -> Optional[Product]:
        product = next((b for b in self._products if b.sku == sku), None)
        if product:
            self.seen.add(product)
        return product

    def get_by_batchref(self, batchref: str) -> Optional[Product]:
        for product in self._products:
            if any(batch.reference == batchref for batch in product.batches):
                self.seen.add(product)
                return product
        return None

    def list(self):
        products = list(self._products)
        for product in products:
            self.seen.add(product)
        return products


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
    engine = create_engine(url=config.get_db_uri())
    with engine.begin() as conn:
        for truncate_query in TRUNCATE_QUERIES:
            conn.execute(text(truncate_query))
    engine.dispose()


@pytest.fixture(scope="session")
def postgres_db():
    engine = create_engine(url=config.get_db_uri())
    metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def postgres_session_factory(postgres_db):
    clear_mappers()
    start_mappers()
    engine = postgres_db
    yield sessionmaker(bind=engine)
    clear_mappers()
    with engine.begin() as conn:
        for truncate_query in TRUNCATE_QUERIES:
            conn.execute(text(truncate_query))
