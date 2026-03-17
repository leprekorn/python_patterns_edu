from typing import Dict, List

from allocation import config
from allocation.adapters import redis


def allocations(order_id: str) -> List[Dict[str, str]]:
    redis_config = config.get_redis_url()
    redisAdapter = redis.RedisAdapter(host=str(redis_config["host"]), port=int(redis_config["port"]))
    data = redisAdapter.get_read_model(order_id=order_id)
    return [{"sku": sku, "batch_ref": batch_ref} for sku, batch_ref in data.items()]
