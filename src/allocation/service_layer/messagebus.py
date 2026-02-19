from collections import deque
from typing import Callable, Dict, List, Type

from allocation.domain import events
from allocation.interfaces.main import IUnitOfWork, IMessageBus
from allocation.service_layer import handlers


class MessageBus(IMessageBus):
    HANDLERS: Dict[Type[events.Event], List[Callable]] = {
        events.AllocationRequired: [handlers.allocate],
        events.BatchCreated: [handlers.add_batch],
        events.BatchQuantityChanged: [handlers.change_batch_quantity],
        events.OutOfStock: [handlers.send_out_of_stock_notification],
    }

    @staticmethod
    def handle(event: events.Event, uow: IUnitOfWork) -> List[str]:
        results = []
        queue = deque([event])
        while queue:
            event = queue.popleft()
            for handler in MessageBus.HANDLERS[type(event)]:
                results.append(handler(event=event, uow=uow))
                queue.extend(uow.collect_new_events())
        return results
