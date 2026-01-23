import pytest
from allocation.adapters.repository import IRepository
from allocation.domain import model
from allocation.domain.exceptions import UnallocatedLine, InvalidBatchReference
from allocation.service_layer import services
from typing import List, Optional


class FakeRepository(IRepository):
    def __init__(self, batches: List[model.Batch]):
        self._batches = set(batches)

    def add(self, batch: model.Batch):
        self._batches.add(batch)

    def get(self, reference: str) -> Optional[model.Batch]:
        try:
            batch = next(b for b in self._batches if b.reference == reference)
        except StopIteration:
            return None
        return batch

    def list(self):
        return list(self._batches)


class FakeSession(services.ISession):
    committed = False

    def commit(self):
        self.committed = True


@pytest.mark.unit
@pytest.mark.service
def test_returns_allocation():
    batch = model.Batch("b1", "COMPLICATED-LAMP", 100, eta=None)
    repo = FakeRepository([batch])

    result = services.allocate(orderId="o1", sku="COMPLICATED-LAMP", qty=10, repo=repo, session=FakeSession())
    assert result == batch


@pytest.mark.unit
@pytest.mark.service
def test_error_for_invalid_sku():
    batch = model.Batch("b1", "AREALSKU", 100, eta=None)
    repo = FakeRepository([batch])

    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        services.allocate(orderId="01", sku="NONEXISTENTSKU", qty=10, repo=repo, session=FakeSession())


@pytest.mark.unit
@pytest.mark.service
def test_commits():
    batch = model.Batch("b1", "OMINOUS-MIRROR", 100, eta=None)
    repo = FakeRepository([batch])
    session = FakeSession()

    services.allocate(orderId="o1", sku="OMINOUS-MIRROR", qty=10, repo=repo, session=session)
    assert session.committed is True


@pytest.mark.unit
@pytest.mark.service
def test_deallocate_returns_batch_reference():
    batch = model.Batch("b50", "CRAZY-CHAIR", 100, eta=None)
    repo = FakeRepository([batch])

    result = services.allocate(orderId="o20", sku="CRAZY-CHAIR", qty=10, repo=repo, session=FakeSession())
    assert result == batch
    assert batch.available_quantity == 90

    unallocation_result = services.deallocate(batchref=batch.reference, orderId="o20", repo=repo, session=FakeSession())
    assert unallocation_result == batch
    assert batch.available_quantity == 100


@pytest.mark.unit
@pytest.mark.service
def test_deallocate_non_allocated_line_raises_exception():
    orderId = "o30"
    batch = model.Batch("b70", "FANCY-TABLE", 50, eta=None)
    repo = FakeRepository([batch])
    with pytest.raises(UnallocatedLine, match=f"Order line {orderId} is not allocated to batch {batch.reference}"):
        services.deallocate(batchref=batch.reference, orderId=orderId, repo=repo, session=FakeSession())


@pytest.mark.unit
@pytest.mark.service
def test_deallocate_for_absent_batch_raises_exception():
    batch = model.Batch("b70", "COZY-SOFA", 50, eta=None)
    repo = FakeRepository([])

    with pytest.raises(InvalidBatchReference, match=f"Invalid batch reference {batch.reference}"):
        services.deallocate(batchref=batch.reference, orderId="o30", repo=repo, session=FakeSession())


def test_add_batch():
    repo = FakeRepository([])
    session = FakeSession()

    services.add_batch(
        reference="b1",
        sku="ADORABLE-SETTEE",
        qty=12,
        eta=None,
        repo=repo,
        session=session,
    )

    added = repo.get("b1")
    assert added is not None
    assert added.reference == "b1"
    assert added.sku == "ADORABLE-SETTEE"
    assert added._purchase_quantity == 12
    assert session.committed is True
