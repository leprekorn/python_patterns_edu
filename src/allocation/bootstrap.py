from typing import Callable, Dict, List, Type

from allocation.adapters import orm
from allocation.domain import commands, events
from allocation.interfaces.main import IUnitOfWork
from allocation.service_layer.messagebus import MessageBus


class Bootstrap:
    def __init__(
        self,
        start_orm: bool,
        uow: IUnitOfWork,
        event_handlers: Dict[Type[events.Event], List[Callable]] = {},
        command_handlers: Dict[Type[commands.Command], Callable] = {},
    ):
        if start_orm:
            orm.start_mappers()
        self.uow = uow
        self.message_bus = MessageBus(uow=self.uow, command_handlers=command_handlers, event_handlers=event_handlers)

    def inject_dependencies(self) -> MessageBus:
        return self.message_bus
