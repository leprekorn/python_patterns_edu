from allocation.domain.model import Product
from typing import Protocol, Optional, List, Set


class ISession(Protocol):
    """
    Interface for Repository session
    """

    def commit(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def rollback(self):
        raise NotImplementedError

    def add(self, instance):
        raise NotImplementedError

    def delete(self, instance):
        raise NotImplementedError

    def query(self, model_class):
        raise NotImplementedError

    def execute(self, statement, params=None):
        raise NotImplementedError


class ICallableSession(Protocol):
    def __call__(self) -> ISession:
        raise NotImplementedError


class IRepository(Protocol):
    """
    Interface for any ORM and storage
    """

    seen: Set[Product]

    def add(self, product: Product):
        raise NotImplementedError

    def get(self, sku: str) -> Optional[Product]:
        raise NotImplementedError

    def list(self) -> List[Product]:
        raise NotImplementedError

    def delete(self, sku: str):
        raise NotImplementedError


class IUnitOfWork(Protocol):
    session_factory: ICallableSession
    products: IRepository

    def __enter__(self) -> "IUnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.rollback()

    def commit(self):
        raise NotImplementedError

    def rollback(self):
        raise NotImplementedError

    def publish_events(self):
        raise NotImplementedError
