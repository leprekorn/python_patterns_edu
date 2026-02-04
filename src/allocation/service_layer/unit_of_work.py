from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from allocation import config
from allocation.interfaces.main import IUnitOfWork
from allocation.adapters.repository import SQLAlchemyRepository


DEFAULT_SESSION_FACTORY = sessionmaker(
    bind=create_engine(
        url=config.get_db_uri(),
        isolation_level="REPEATABLE READ",
    )
)


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self, session_factory=DEFAULT_SESSION_FACTORY):
        self.session_factory = session_factory

    def __enter__(self):
        self.session = self.session_factory()
        self.products = SQLAlchemyRepository(self.session)
        return super().__enter__()

    def __exit__(self, *args):
        super().__exit__(*args)
        self.session.close()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
