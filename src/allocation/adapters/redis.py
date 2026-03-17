import json
import time
from typing import Any, Dict

import redis
from redis.exceptions import ConnectionError

from allocation.interfaces.main import IRedisAdapter


class RedisAdapter(IRedisAdapter):
    def __init__(self, host: str, port: int):
        self.redis = redis.Redis(
            host=host,
            port=port,
            decode_responses=True,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )

    def wait_until_ready(self, timeout: int = 10):
        for _ in range(timeout):
            try:
                self.redis.ping()
                return
            except ConnectionError:
                time.sleep(1)
        raise TimeoutError("Redis server is not ready after waiting for 10 seconds.")

    def publish(self, channel: str, message: dict):
        self.redis.publish(channel, json.dumps(message))

    def subscribe(self, channel: str):
        pubsub = self.redis.pubsub()
        pubsub.subscribe(channel)
        confirmation = pubsub.get_message(timeout=3)
        assert confirmation is not None, f"Failed to subscribe to channel {channel}"
        assert confirmation["type"] == "subscribe" and confirmation["channel"] == channel
        return pubsub

    def get_read_model(self, order_id: str) -> Dict[Any, Any]:
        data = self.redis.hgetall(order_id)
        return data  # type: ignore

    def update_read_model(self, order_id: str, sku: str, batch_ref: str):
        self.redis.hset(order_id, sku, batch_ref)
