from allocation.domain.model import Batch
from typing import Protocol, Optional, List


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

    def query(self, model_class):
        raise NotImplementedError


class ICallableSession(Protocol):
    def __call__(self) -> ISession:
        raise NotImplementedError


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

    def delete(self, reference: str):
        raise NotImplementedError


class IUnitOfWork(Protocol):
    session_factory: ICallableSession
    batches: IRepository

    def __enter__(self) -> "IUnitOfWork":
        return self

    def __exit__(self, *args):
        self.rollback()

    def commit(self):
        raise NotImplementedError

    def rollback(self):
        raise NotImplementedError
