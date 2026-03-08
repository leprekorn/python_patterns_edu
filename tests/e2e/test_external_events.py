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

    redis = make_redis_client
    subscription = redis.subscribe(channel="line_allocated")
    subscription.get_message(timeout=1)

    allocate_data = {"orderid": random_orderid(), "sku": sku, "qty": 3}
    r = fastapi_test_client.post(f"{url}/allocate", json=allocate_data)

    assert r.status_code == 202
    allocation = fastapi_test_client.get(f"{url}/allocations/{allocate_data['orderid']}")
    assert allocation.status_code == 200
    assert allocation.json() == {"sku": earlybatch["sku"], "batchref": earlybatch["reference"]}, (
        f"expected allocation to be {earlybatch['reference']} for sku {earlybatch['sku']}, but got {allocation.json()}"
    )

    for attempt in Retrying(stop=stop_after_delay(3), reraise=True):
        with attempt:
            message = subscription.get_message(timeout=1)
            assert message is not None and message["type"] == "message"
            data = json.loads(message["data"])
            assert data["orderid"] == allocate_data["orderid"]
            assert data["batchref"] == earlybatch["reference"]
