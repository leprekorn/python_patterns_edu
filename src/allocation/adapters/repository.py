from typing import Optional, List
from allocation.interfaces.main import IRepository, ISession
from allocation.domain.model import Product


class SQLAlchemyRepository(IRepository):
    def __init__(self, orm_session: ISession):
        self.orm_session = orm_session

    def add(self, product: Product):
        self.orm_session.add(product)

    def get(self, sku: str) -> Optional[Product]:
        return self.orm_session.query(Product).filter_by(sku=sku).first()

    def list(self) -> List[Product]:
        return self.orm_session.query(Product).all()

    def delete(self, sku: str) -> int:
        product = self.orm_session.query(Product).filter_by(sku=sku).first()
        if not product:
            return 0
        self.orm_session.delete(product)
        return 1
