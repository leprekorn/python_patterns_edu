import pytest
from allocation.domain.model import OrderLine, Batch
from allocation.adapters.orm import metadata, start_mappers
from allocation import config
from allocation.entrypoints.main import app
from datetime import date
from typing import Callable, Tuple, Optional

from sqlalchemy import create_engine, exc, text
from sqlalchemy.orm import sessionmaker, clear_mappers
from sqlalchemy.pool import StaticPool
from sqlalchemy.engine.base import Engine
from fastapi.testclient import TestClient

import time
import pathlib
import requests


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


def _wait_for_postgres_to_come_up(engine: Engine):
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            return engine.connect()
        except exc.OperationalError:
            time.sleep(0.5)
    pytest.fail("Postgres never came up")


@pytest.fixture(scope="session")
def postgres_db() -> Engine:
    url = config.get_db_uri()
    engine = create_engine(url=url)
    _wait_for_postgres_to_come_up(engine=engine)
    metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def postgres_session(postgres_db):
    clear_mappers()
    start_mappers()
    yield sessionmaker(bind=postgres_db)()
    clear_mappers()


@pytest.fixture(scope="function")
def add_stock(postgres_session):
    batches_added = set()
    skus_added = set()

    def _add_stock(lines: list[Tuple[str, str, int, Optional[date]]]):
        for ref, sku, qty, eta in lines:
            postgres_session.execute(
                text("INSERT INTO batches (reference, sku, _purchase_quantity, eta) VALUES (:ref, :sku, :qty, :eta)"),
                dict(ref=ref, sku=sku, qty=qty, eta=eta),
            )
            [[batch_id]] = postgres_session.execute(
                text("SELECT id FROM batches WHERE reference=:ref AND sku=:sku"),
                dict(ref=ref, sku=sku),
            )
            batches_added.add(batch_id)
            skus_added.add(sku)
        postgres_session.commit()

    yield _add_stock

    for batch_id in batches_added:
        postgres_session.execute(
            text("DELETE FROM allocations WHERE batch_id=:batch_id"),
            dict(batch_id=batch_id),
        )
        postgres_session.execute(
            text("DELETE FROM batches WHERE id=:batch_id"),
            dict(batch_id=batch_id),
        )

    for sku in skus_added:
        postgres_session.execute(
            text("DELETE FROM order_lines WHERE sku=:sku"),
            dict(sku=sku),
        )
        postgres_session.commit()


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
            return requests.get(url)
        except ConnectionError:
            time.sleep(0.5)
    pytest.fail("API never came up")


@pytest.fixture(scope="function")
def fastapi_test_client():
    client = TestClient(app)
    yield client
