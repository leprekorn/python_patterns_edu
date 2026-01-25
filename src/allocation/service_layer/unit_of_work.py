from typing import Protocol, Callable
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from allocation import config
from allocation.adapters.repository import SQLAlchemyRepository, IRepository


class IUnitOfWork(Protocol):
    session_factory: Callable[[], Session]
    batches: IRepository

    def __enter__(self) -> "IUnitOfWork":
        return self

    def __exit__(self, *args):
        self.rollback()

    def commit(self):
        raise NotImplementedError

    def rollback(self):
        raise NotImplementedError


DEFAULT_SESSION_FACTORY = sessionmaker(bind=create_engine(url=config.get_db_uri()))


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self, session_factory=DEFAULT_SESSION_FACTORY):
        self.session_factory = session_factory

    def __enter__(self):
        self.session = self.session_factory()
        self.batches = SQLAlchemyRepository(self.session)
        return super().__enter__()

    def __exit__(self, *args):
        super().__exit__(*args)
        self.session.close()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
