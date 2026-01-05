import pytest
from src import Batch, SQLAlchemyRepository
from sqlalchemy import text


@pytest.mark.unit
@pytest.mark.repository
def test_repository_can_save_a_batch(orm_session):
    batch = Batch("batch1", "RUSTY-SOAPDISH", 100, eta=None)

    repo = SQLAlchemyRepository(orm_session)
    repo.add(batch)
    orm_session.commit()

    rows = orm_session.execute(statement=text('SELECT reference, sku, _purchase_quantity, eta FROM "batches"'))
    assert list(rows) == [("batch1", "RUSTY-SOAPDISH", 100, None)]
