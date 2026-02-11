from allocation.adapters.email import send_email
from allocation.domain import events
from typing import List, Dict, Callable, Type


def handle(event: events.Event):
    for handler in HANDLERS[type(event)]:
        handler(event)


def send_out_of_stock_notification(event: events.OutOfStock):
    send_email(
        "stock@made.com",
        f"Out of stock for {event.sku}",
    )


HANDLERS: Dict[Type[events.Event], List[Callable]] = {
    events.OutOfStock: [send_out_of_stock_notification],
}
