from sqlalchemy import MetaData, Table, Column, Integer, String
from sqlalchemy.orm import registry
from .model import OrderLine


metadata = MetaData()

mapper_registry = registry(metadata=metadata)

order_lines = Table(
    "order_lines",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("sku", String(255)),
    Column("qty", Integer, nullable=False),
    Column("orderId", String(255)),
)


def start_mapper():
    mapper_registry.map_imperatively(OrderLine, order_lines)
