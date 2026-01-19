from allocation.domain import model
from allocation.domain.exceptions import InvalidSku
from allocation.adapters.repository import IRepository
from typing import List, Protocol


class ISession(Protocol):
    """
    Interface for Repository session
    """

    def commit(self):
        raise NotImplementedError


def is_valid_sku(sku: str, batches: List[model.Batch]) -> bool:
    return sku in {b.sku for b in batches}


def allocate(line: model.OrderLine, repo: IRepository, session: ISession) -> model.Batch:
    batches = repo.list()
    if not is_valid_sku(line.sku, batches):
        raise InvalidSku(f"Invalid sku {line.sku}")
    batch = model.allocate(line=line, batches=batches)
    session.commit()
    return batch
