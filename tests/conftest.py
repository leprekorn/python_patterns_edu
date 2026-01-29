import pytest
from allocation.domain.model import OrderLine, Batch
from allocation.adapters.orm import metadata, start_mappers
from allocation import config
from allocation.entrypoints.main import app
from datetime import date
from typing import Callable, Tuple, Optional

from sqlalchemy import create_engine
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
        self.batches = FakeRepository([])

    def __enter__(self):
        self.session = self.session_factory()
        return super().__enter__()

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


class FakeRepository(IRepository):
    def __init__(self, batches: List[Batch]):
        self._batches = set(batches)

    def add(self, batch: Batch):
        self._batches.add(batch)

    def delete(self, reference: str):
        batch = self.get(reference)
        if batch:
            self._batches.remove(batch)

    def get(self, reference: str) -> Optional[Batch]:
        try:
            batch = next(b for b in self._batches if b.reference == reference)
        except StopIteration:
            return None
        return batch

    def list(self):
        return list(self._batches)


class FakeSession(ISession):
    committed = False

    def commit(self):
        self.committed = True

    def close(self):
        raise NotImplementedError

    def rollback(self):
        raise NotImplementedError

    def add(self, instance: Batch):
        raise NotImplementedError

    def query(self, model_class):
        raise NotImplementedError


@pytest.fixture(scope="function")
def make_fake_repo_session() -> Tuple[FakeRepository, FakeSession]:
    repo = FakeRepository([])
    session = FakeSession()
    return repo, session


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
    clear_mappers()
    start_mappers()
    orm_session = sessionmaker(bind=in_memory_db)()
    yield orm_session
    orm_session.close()
    clear_mappers()


@pytest.fixture
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
