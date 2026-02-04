import pytest

from allocation import config
from tests.utils import random_batchref, random_orderid, random_sku

url = config.get_api_url()


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.usefixtures("restart_api")
def test_happy_path_post_allocate_deallocate_batch(fastapi_test_client):
    earlybatch = {
        "reference": random_batchref(name="early"),
        "sku": random_sku(name="RETRO-CLOCK"),
        "qty": 100,
        "eta": "2026-02-02",
    }

    laterbatch = {
        "reference": random_batchref(name="later"),
        "sku": earlybatch["sku"],
        "qty": 100,
        "eta": "2026-02-03",
    }

    otherbatch = {
        "reference": random_batchref(name="other"),
        "sku": random_sku(name="ANOTHER-ITEM"),
        "qty": 100,
        "eta": None,
    }

    for batch in (earlybatch, laterbatch, otherbatch):
        data = {
            "reference": batch["reference"],
            "sku": batch["sku"],
            "qty": batch["qty"],
            "eta": batch["eta"],
        }
        r = fastapi_test_client.post(f"{url}/batches/", json=data)
        assert r.status_code == 201
    r = fastapi_test_client.get(f"{url}/batches/{earlybatch['reference']}?sku={earlybatch['sku']}")
    assert r.status_code == 200
    assert r.json()["reference"] == earlybatch["reference"], (
        f"expected batch reference to be {earlybatch['reference']}, but got {r.json()['reference']}"
    )

    allocate_data = {"orderid": random_orderid(), "sku": earlybatch["sku"], "qty": 3}
    r = fastapi_test_client.post(f"{url}/allocate", json=allocate_data)

    assert r.status_code == 201
    assert r.json()["batchref"] == earlybatch["reference"]

    deallocate_data = {"sku": earlybatch["sku"], "orderid": allocate_data["orderid"], "qty": 3}
    deallocated_request = fastapi_test_client.post(f"{url}/deallocate", json=deallocate_data)
    assert deallocated_request.status_code == 200
    assert deallocated_request.json()["batchref"] == earlybatch["reference"]

    for batch in (earlybatch, laterbatch, otherbatch):
        delete_response = fastapi_test_client.delete(f"{url}/batches/{batch['reference']}?sku={batch['sku']}")
        assert delete_response.status_code == 204


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_get_batch_deallocate_from_batch(fastapi_test_client):
    batchref = random_batchref(name="absent-get-test")
    sku = random_sku(name="absent-sku")
    r = fastapi_test_client.get(f"{url}/batches/{batchref}?sku={sku}")
    assert r.status_code == 400
    assert r.json()["detail"] == f"Invalid sku {sku}"

    orderid = random_orderid()
    deallocate_data = {"sku": sku, "orderid": orderid, "qty": 10}
    deallocate_from_abcent_product_request = fastapi_test_client.post(f"{url}/deallocate", json=deallocate_data)
    assert deallocate_from_abcent_product_request.json()["detail"] == f"Invalid sku {sku}"
    assert deallocate_from_abcent_product_request.status_code == 400

    post_data = {
        "reference": batchref,
        "sku": sku,
        "qty": 100,
        "eta": "2026-01-21",
    }
    r = fastapi_test_client.post(f"{url}/batches/", json=post_data)
    assert r.status_code == 201

    deallocate_from_existing_product_request = fastapi_test_client.post(f"{url}/deallocate", json=deallocate_data)
    assert deallocate_from_existing_product_request.status_code == 400
    assert (
        deallocate_from_existing_product_request.json()["detail"] == f"Order line {orderid} is not allocated to any batch in Product {sku}"
    )

    delete_batch_request = fastapi_test_client.delete(f"{url}/batches/{batchref}?sku={sku}")
    assert delete_batch_request.status_code == 204


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_post_allocate_returns_400_and_error_message(fastapi_test_client):
    unknown_sku, orderid = random_sku(), random_orderid()
    data = {"orderid": orderid, "sku": unknown_sku, "qty": 20}
    r = fastapi_test_client.post(f"{url}/allocate", json=data)
    assert r.status_code == 400
    assert r.json()["detail"] == f"Invalid sku {unknown_sku}"
