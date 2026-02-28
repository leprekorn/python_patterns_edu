import json

import pytest
from tenacity import Retrying, stop_after_delay

from allocation import config
from tests.utils import random_batchref, random_orderid, random_sku

url = config.get_api_url()


@pytest.mark.e2e
@pytest.mark.external_events
@pytest.mark.usefixtures("restart_api")
def test_happy_path_post_allocate_deallocate_batch(fastapi_test_client, make_redis_client):
    sku = random_sku(name="RETRO-CLOCK")
    earlybatch = {
        "reference": random_batchref(name="early"),
        "sku": sku,
        "qty": 100,
        "eta": "2026-02-02",
    }

    laterbatch = {
        "reference": random_batchref(name="later"),
        "sku": sku,
        "qty": 100,
        "eta": "2026-02-03",
    }

    for batch in (earlybatch, laterbatch):
        data = {
            "reference": batch["reference"],
            "sku": batch["sku"],
            "qty": batch["qty"],
            "eta": batch["eta"],
        }
        r = fastapi_test_client.post(f"{url}/batches/", json=data)
        assert r.status_code == 201

    allocate_data = {"orderid": random_orderid(), "sku": sku, "qty": 3}
    r = fastapi_test_client.post(f"{url}/allocate", json=allocate_data)

    assert r.status_code == 201
    assert r.json()["batchref"] == earlybatch["reference"]

    redis = make_redis_client
    redis.publish(channel="change_batch_quantity", message={"batchref": earlybatch["reference"], "qty": 5})

    subscription = redis.subscribe(channel="line_allocated")

    messages = []
    for attempt in Retrying(stop=stop_after_delay(3), reraise=True):
        with attempt:
            message = subscription.get_message(timeout=1)
            if message:
                messages.append(message)
                print(messages)
            data = json.loads(messages[-1]["data"])
            assert data["orderid"] == allocate_data["orderid"]
            assert data["batchref"] == laterbatch["reference"]
