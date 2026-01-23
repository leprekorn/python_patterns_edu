import pytest
from allocation.domain.exceptions import UnallocatedLine, InvalidBatchReference
from allocation.service_layer import services


@pytest.mark.unit
@pytest.mark.service
def test_returns_allocation(make_fake_repo_session):
    repo, session = make_fake_repo_session
    batch = services.add_batch(reference="b1", sku="COMPLICATED-LAMP", qty=100, eta=None, repo=repo, session=session)

    result = services.allocate(orderId="o1", sku="COMPLICATED-LAMP", qty=10, repo=repo, session=session)
    assert result == batch


@pytest.mark.unit
@pytest.mark.service
def test_error_for_invalid_sku(make_fake_repo_session):
    repo, session = make_fake_repo_session
    services.add_batch(reference="b1", sku="AREALSKU", qty=100, eta=None, repo=repo, session=session)

    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        services.allocate(orderId="01", sku="NONEXISTENTSKU", qty=10, repo=repo, session=session)


@pytest.mark.unit
@pytest.mark.service
def test_commits(make_fake_repo_session):
    repo, session = make_fake_repo_session
    services.add_batch(reference="b1", sku="OMINOUS-MIRROR", qty=100, eta=None, repo=repo, session=session)

    services.allocate(orderId="o1", sku="OMINOUS-MIRROR", qty=10, repo=repo, session=session)
    assert session.committed is True


@pytest.mark.unit
@pytest.mark.service
def test_deallocate_returns_batch_reference(make_fake_repo_session):
    repo, session = make_fake_repo_session
    batch = services.add_batch(reference="b50", sku="CRAZY-CHAIR", qty=100, eta=None, repo=repo, session=session)
    result = services.allocate(orderId="o20", sku="CRAZY-CHAIR", qty=10, repo=repo, session=session)
    assert result == batch
    assert batch.available_quantity == 90

    unallocation_result = services.deallocate(batchref=batch.reference, orderId="o20", repo=repo, session=session)
    assert unallocation_result == batch
    assert batch.available_quantity == 100


@pytest.mark.unit
@pytest.mark.service
def test_deallocate_non_allocated_line_raises_exception(make_fake_repo_session):
    repo, session = make_fake_repo_session
    orderId = "o30"
    batch = services.add_batch(reference="b70", sku="FANCY-TABLE", qty=50, eta=None, repo=repo, session=session)
    with pytest.raises(UnallocatedLine, match=f"Order line {orderId} is not allocated to batch {batch.reference}"):
        services.deallocate(batchref=batch.reference, orderId=orderId, repo=repo, session=session)


@pytest.mark.unit
@pytest.mark.service
def test_deallocate_for_absent_batch_raises_exception(make_fake_repo_session):
    repo, session = make_fake_repo_session
    absent_batch_ref = "b70"
    with pytest.raises(InvalidBatchReference, match=f"Invalid batch reference {absent_batch_ref}"):
        services.deallocate(batchref=absent_batch_ref, orderId="o30", repo=repo, session=session)


@pytest.mark.unit
@pytest.mark.service
def test_add_batch(make_fake_repo_session):
    repo, session = make_fake_repo_session

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


@pytest.mark.unit
@pytest.mark.service
def test_delete_batch(make_fake_repo_session):
    repo, session = make_fake_repo_session

    services.add_batch(
        reference="b1",
        sku="ADORABLE-SETTEE",
        qty=12,
        eta=None,
        repo=repo,
        session=session,
    )

    services.delete_batch(
        reference="b1",
        repo=repo,
        session=session,
    )
    deleted = repo.get(reference="b1")
    assert deleted is None
    assert session.committed is True
    existing = repo.list()
    assert existing == []
