from typing import List, Optional

from allocation.domain.model import Product
from allocation.interfaces.main import IRepository, ISession


class SQLAlchemyRepository(IRepository):
    def __init__(self, orm_session: ISession):
        self.orm_session = orm_session
        self.seen = set()

    def add(self, product: Product):
        self.seen.add(product)
        self.orm_session.add(product)

    def get(self, sku: str) -> Optional[Product]:
        product = self.orm_session.query(Product).filter_by(sku=sku).first()
        if product:
            self.seen.add(product)
        return product

    def list(self) -> List[Product]:
        products = self.orm_session.query(Product).all()
        for product in products:
            self.seen.add(product)
        return products

    def delete(self, sku: str) -> int:
        product = self.orm_session.query(Product).filter_by(sku=sku).first()
        if not product:
            return 0
        self.orm_session.delete(product)
        self.seen.discard(product)
        return 1
