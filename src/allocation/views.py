from sqlalchemy import select

from allocation.adapters import orm
from allocation.service_layer import unit_of_work


def allocations(order_id: str, uow: unit_of_work.SqlAlchemyUnitOfWork):
    with uow:
        stmt = (
            select(orm.order_lines.c.sku, orm.batches.c.reference)
            .select_from(
                orm.order_lines.outerjoin(
                    orm.allocations,
                    orm.order_lines.c.id == orm.allocations.c.orderline_id,
                ).outerjoin(
                    orm.batches,
                    orm.allocations.c.batch_id == orm.batches.c.id,
                )
            )
            .where(orm.order_lines.c.order_id == order_id)
        )
        row = uow.session.execute(stmt).first()

        # No order line found at all
        if row is None:
            exists = uow.session.execute(select(orm.order_lines.c.id).where(orm.order_lines.c.order_id == order_id)).first()
            if not exists:
                return None
            return {"sku": None, "batch_ref": None}

        sku, batch_ref = row
        if batch_ref is None:
            return {"sku": None, "batch_ref": None}
        return {"sku": sku, "batch_ref": batch_ref}
