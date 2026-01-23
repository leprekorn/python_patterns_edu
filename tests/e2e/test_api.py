import uuid
import pytest

from allocation import config


def random_suffix():
    return uuid.uuid4().hex[:6]


def random_sku(name=""):
    return f"sku-{name}-{random_suffix()}"


def random_batchref(name=""):
    return f"batch-{name}-{random_suffix()}"


def random_orderid(name=""):
    return f"order-{name}-{random_suffix()}"


url = config.get_api_url()


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.usefixtures("restart_api")
def test_happy_path_post_allocate_deallocate_batch(fastapi_test_client):
    sku = random_sku(name="first")
    othersku = random_sku(name="other")
    earlybatch = random_batchref(name="1")
    laterbatch = random_batchref(name="2")
    otherbatch = random_batchref(name="3")
    for batch in (earlybatch, laterbatch, otherbatch):
        data = {
            "reference": batch,
            "sku": sku if batch != otherbatch else othersku,
            "qty": 100,
            "eta": "2011-01-01" if batch == earlybatch else "2011-01-02" if batch == laterbatch else None,
        }
        r = fastapi_test_client.post(f"{url}/batches/", json=data)
        assert r.status_code == 201
    r = fastapi_test_client.get(f"{url}/batches/{earlybatch}")
    assert r.status_code == 200
    assert r.json()["reference"] == earlybatch, f"expected batch reference to be {earlybatch}, but got {r.json()['reference']}"

    allocate_data = {"orderid": random_orderid(), "sku": sku, "qty": 3}
    r = fastapi_test_client.post(f"{url}/allocate", json=allocate_data)

    assert r.status_code == 201
    assert r.json()["batchref"] == earlybatch

    deallocate_data = {"batchref": earlybatch, "orderid": allocate_data["orderid"]}
    deallocated_request = fastapi_test_client.post(f"{url}/deallocate", json=deallocate_data)
    assert deallocated_request.status_code == 200
    assert deallocated_request.json()["batchref"] == earlybatch


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_get_for_abcent_batch(fastapi_test_client):
    batchref = random_batchref(name="absent-get-test")
    r = fastapi_test_client.get(f"{url}/batches/{batchref}")
    assert r.status_code == 404
    assert r.json()["detail"] == f"Batch {batchref} not found"

    orderid = random_orderid()
    deallocate_data = {"batchref": batchref, "orderid": orderid}
    deallocate_request = fastapi_test_client.post(f"{url}/deallocate", json=deallocate_data)
    assert deallocate_request.status_code == 404
    assert deallocate_request.json()["detail"] == f"Invalid batch reference {batchref}"


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_post_allocate_returns_400_and_error_message(fastapi_test_client):
    unknown_sku, orderid = random_sku(), random_orderid()
    data = {"orderid": orderid, "sku": unknown_sku, "qty": 20}
    r = fastapi_test_client.post(f"{url}/allocate", json=data)
    assert r.status_code == 400
    assert r.json()["detail"] == f"Invalid sku {unknown_sku}"


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_post_deallocate_for_unallocated_pair_returns_400_and_error_message(fastapi_test_client):
    sku = random_sku(name="cool_table")
    order_id = random_orderid(name="dealloc-test")
    batchref = random_batchref(name="15")
    data = {
        "reference": batchref,
        "sku": sku,
        "qty": 100,
        "eta": "2026-01-21",
    }
    r = fastapi_test_client.post(f"{url}/batches/", json=data)
    assert r.status_code == 201
    deallocate_data = {"batchref": batchref, "orderid": order_id}
    r = fastapi_test_client.post(f"{url}/deallocate", json=deallocate_data)
    assert r.status_code == 400
    assert r.json()["detail"] == f"Order line {order_id} is not allocated to batch {batchref}"
