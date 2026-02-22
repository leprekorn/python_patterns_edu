import logging
from collections import deque
from typing import Callable, Dict, List, Type

from allocation.domain import commands, events
from allocation.interfaces.main import IMessage, IUnitOfWork
from allocation.service_layer import handlers

logger = logging.getLogger(__name__)


class MessageBus:
    EVENT_HANDLERS: Dict[Type[events.Event], List[Callable]] = {
        events.OutOfStock: [handlers.send_out_of_stock_notification],
    }

    COMMAND_HANDLERS: Dict[Type[commands.Command], Callable] = {
        commands.CreateBatch: handlers.add_batch,
        commands.ChangeBatchQuantity: handlers.change_batch_quantity,
        commands.Allocate: handlers.allocate,
    }

    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def handle(self, message: IMessage) -> List[str]:
        results = []
        queue = deque([message])
        while queue:
            message = queue.popleft()
            if isinstance(message, events.Event):
                self.handle_event(event=message, queue=queue)
            elif isinstance(message, commands.Command):
                cmd_result = self.handle_command(command=message, queue=queue)
                results.append(cmd_result)
            else:
                raise Exception(f"{message} was not an Event or Command")
        return results

    def handle_event(self, event: events.Event, queue: deque[IMessage]):
        for handler in self.EVENT_HANDLERS[type(event)]:
            try:
                logger.debug(f"Handling event {event} with handler {handler}")
                handler(event=event, uow=self.uow)
                queue.extend(self.uow.collect_new_events())
            except Exception as e:
                logger.exception(f"Exception while handling event {event} with handler {handler}: {e}")
                continue

    def handle_command(self, command: commands.Command, queue: deque[IMessage]) -> str:
        logger.debug(f"Handling command {command}")
        try:
            handler = self.COMMAND_HANDLERS[type(command)]
            result = handler(command=command, uow=self.uow)
            queue.extend(self.uow.collect_new_events())
            return result
        except Exception as e:
            logger.exception(f"Exception while handling command {command} with handler {handler}: {e}")
            raise
