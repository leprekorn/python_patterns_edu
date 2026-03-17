from sqlalchemy import text
from typing import List, Dict
from allocation.service_layer import unit_of_work


def allocations(order_id: str, uow: unit_of_work.SqlAlchemyUnitOfWork) -> List[Dict[str, str]]:
    with uow:
        results = uow.session.execute(
            text("SELECT sku, batch_ref FROM allocations_view WHERE order_id = :order_id"),
            dict(order_id=order_id),
        )
        return [dict(r._mapping) for r in results]
