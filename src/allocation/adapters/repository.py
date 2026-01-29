from typing import Optional, List
from allocation.interfaces.main import IRepository, ISession
from allocation.domain.model import Batch


class SQLAlchemyRepository(IRepository):
    def __init__(self, orm_session: ISession):
        self.orm_session = orm_session

    def add(self, batch: Batch):
        self.orm_session.add(batch)

    def get(self, reference: str) -> Optional[Batch]:
        return self.orm_session.query(Batch).filter_by(reference=reference).first()

    def list(self) -> List[Batch]:
        return self.orm_session.query(Batch).all()

    def delete(self, reference: str):
        return self.orm_session.query(Batch).filter_by(reference=reference).delete()
