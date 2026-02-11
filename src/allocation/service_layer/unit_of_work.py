from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from allocation import config
from allocation.interfaces.main import IUnitOfWork
from allocation.adapters.repository import SQLAlchemyRepository
from allocation.service_layer import messagebus

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

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        self.session.close()
        return super().__exit__(exc_type, exc_val, exc_tb)

    def commit(self):
        self.session.commit()
        self.publish_events()

    def rollback(self):
        self.session.rollback()

    def publish_events(self):
        for product in self.products.seen:
            while product.events:
                event = product.events.pop(0)
                messagebus.handle(event=event)
