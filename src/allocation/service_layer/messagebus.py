from typing import Callable, Dict, List, Type

from allocation.domain import events
from allocation.interfaces.main import IUnitOfWork
from allocation.service_layer import handlers


def handle(event: events.Event, uow: IUnitOfWork):
    results = []
    for handler in HANDLERS[type(event)]:
        results.append(handler(event=event, uow=uow))
    return results


HANDLERS: Dict[Type[events.Event], List[Callable]] = {
    events.AllocationRequired: [handlers.allocate],
    events.BatchCreated: [handlers.add_batch],
    events.OutOfStock: [handlers.send_out_of_stock_notification],
}
