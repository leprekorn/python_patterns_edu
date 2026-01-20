from typing import Protocol, Optional, List
from sqlalchemy.orm import Session
from allocation.domain.model import Batch


class IRepository(Protocol):
    """
    Interface for any ORM and storage
    """

    def add(self, batch: Batch):
        raise NotImplementedError

    def get(self, reference: str) -> Optional[Batch]:
        raise NotImplementedError

    def list(self) -> List[Batch]:
        raise NotImplementedError


class SQLAlchemyRepository(IRepository):
    def __init__(self, orm_session: Session):
        self.orm_session = orm_session

    def add(self, batch: Batch):
        self.orm_session.add(batch)

    def get(self, reference: str) -> Optional[Batch]:
        return self.orm_session.query(Batch).filter_by(reference=reference).first()

    def list(self) -> List[Batch]:
        return self.orm_session.query(Batch).all()
