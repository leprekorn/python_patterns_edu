from typing import Callable, Dict, List, Optional, Protocol, Set, Type

from allocation.domain import events, model


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

    seen: Set[model.Product]

    def add(self, product: model.Product):
        raise NotImplementedError

    def get(self, sku: str) -> Optional[model.Product]:
        raise NotImplementedError

    def get_by_batchref(self, batchref: str) -> Optional[model.Product]:
        raise NotImplementedError

    def list(self) -> List[model.Product]:
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

    def collect_new_events(self):
        raise NotImplementedError


class IMessageBus(Protocol):
    HANDLERS: Dict[Type[events.Event], List[Callable]]

    @staticmethod
    def handle(event: events.Event, uow: IUnitOfWork):
        raise NotImplementedError
