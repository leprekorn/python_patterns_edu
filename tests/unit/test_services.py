import pytest
from allocation.adapters.repository import IRepository
from allocation.domain import model
from allocation.service_layer import services
from typing import List


class FakeRepository(IRepository):
    def __init__(self, batches: List[model.Batch]):
        self._batches = set(batches)

    def add(self, batch: model.Batch):
        self._batches.add(batch)

    def get(self, reference: str):
        return next(b for b in self._batches if b.reference == reference)

    def list(self):
        return list(self._batches)


class FakeSession(services.ISession):
    committed = False

    def commit(self):
        self.committed = True


@pytest.mark.unit
@pytest.mark.service
def test_returns_allocation():
    line = model.OrderLine("o1", "COMPLICATED-LAMP", 10)
    batch = model.Batch("b1", "COMPLICATED-LAMP", 100, eta=None)
    repo = FakeRepository([batch])

    result = services.allocate(line=line, repo=repo, session=FakeSession())
    assert result == batch


@pytest.mark.unit
@pytest.mark.service
def test_error_for_invalid_sku():
    line = model.OrderLine("o1", "NONEXISTENTSKU", 10)
    batch = model.Batch("b1", "AREALSKU", 100, eta=None)
    repo = FakeRepository([batch])

    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        services.allocate(line=line, repo=repo, session=FakeSession())


@pytest.mark.unit
@pytest.mark.service
def test_commits():
    line = model.OrderLine("o1", "OMINOUS-MIRROR", 10)
    batch = model.Batch("b1", "OMINOUS-MIRROR", 100, eta=None)
    repo = FakeRepository([batch])
    session = FakeSession()

    services.allocate(line=line, repo=repo, session=session)
    assert session.committed is True
