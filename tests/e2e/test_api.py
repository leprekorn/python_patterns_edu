import uuid
import pytest
import requests

from allocation import config


def random_suffix():
    return uuid.uuid4().hex[:6]


def random_sku(name=""):
    return f"sku-{name}-{random_suffix()}"


def random_batchref(name=""):
    return f"batch-{name}-{random_suffix()}"


def random_orderid(name=""):
    return f"order-{name}-{random_suffix()}"


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.usefixtures("restart_api")
def test_happy_path_post_returns_201_and_allocated_batch(add_stock):
    sku = random_sku(name="first")
    othersku = random_sku(name="other")
    earlybatch = random_batchref(name="1")
    laterbatch = random_batchref(name="2")
    otherbatch = random_batchref(name="3")
    add_stock(
        [
            (laterbatch, sku, 100, "2011-01-02"),
            (earlybatch, sku, 100, "2011-01-01"),
            (otherbatch, othersku, 100, None),
        ]
    )
    data = {"orderid": random_orderid(), "sku": sku, "qty": 3}
    url = config.get_api_url()

    r = requests.post(f"{url}/allocate", json=data)

    assert r.status_code == 201
    assert r.json()["batchref"] == earlybatch


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_post_returns_400_and_error_message():
    unknown_sku, orderid = random_sku(), random_orderid()
    data = {"orderid": orderid, "sku": unknown_sku, "qty": 20}
    url = config.get_api_url()
    r = requests.post(f"{url}/allocate", json=data)
    assert r.status_code == 400
    assert r.json()["detail"] == f"Invalid sku {unknown_sku}"


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.usefixtures("restart_api")
def test_happy_path_get_returns_200_and_existing_batch(add_stock):
    sku = random_sku(name="get-test")
    batch = random_batchref(name="get-test")
    add_stock(
        [
            (batch, sku, 100, "2026-01-19"),
        ]
    )
    url = config.get_api_url()
    r = requests.get(f"{url}/batches/{batch}")
    assert r.status_code == 200
    assert r.json()["reference"] == batch, f"expected batch reference to be {batch}, but got {r.json()['reference']}"


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_get_returns_400_for_abcent_batch():
    batch = random_batchref(name="absent-get-test")
    url = config.get_api_url()
    r = requests.get(f"{url}/batches/{batch}")
    assert r.status_code == 404
    assert r.json()["detail"] == f"Batch {batch} not found"
