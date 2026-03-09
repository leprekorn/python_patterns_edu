import pytest

from allocation import config
from tests.utils import random_batch_ref, random_order_id, random_sku

url = config.get_api_url()


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.usefixtures("restart_api")
def test_happy_path_post_allocate_deallocate_batch(fastapi_test_client):
    earlybatch = {
        "reference": random_batch_ref(name="early"),
        "sku": random_sku(name="RETRO-CLOCK"),
        "qty": 100,
        "eta": "2026-02-02",
    }

    laterbatch = {
        "reference": random_batch_ref(name="later"),
        "sku": earlybatch["sku"],
        "qty": 100,
        "eta": "2026-02-03",
    }

    otherbatch = {
        "reference": random_batch_ref(name="other"),
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

    allocate_data = {"order_id": random_order_id(), "sku": earlybatch["sku"], "qty": 3}
    r = fastapi_test_client.post(f"{url}/allocate", json=allocate_data)

    assert r.status_code == 202

    allocation = fastapi_test_client.get(f"{url}/allocations/{allocate_data['order_id']}")
    assert allocation.status_code == 200
    assert allocation.json() == {"sku": earlybatch["sku"], "batch_ref": earlybatch["reference"]}, (
        f"expected allocation to be {earlybatch['reference']} for sku {earlybatch['sku']}, but got {allocation.json()}"
    )

    deallocate_data = {"sku": earlybatch["sku"], "order_id": allocate_data["order_id"], "qty": 3}
    deallocated_request = fastapi_test_client.post(f"{url}/deallocate", json=deallocate_data)
    assert deallocated_request.status_code == 202

    deallocation = fastapi_test_client.get(f"{url}/allocations/{allocate_data['order_id']}")
    assert deallocation.status_code == 200
    assert deallocation.json() == {"sku": None, "batch_ref": None}, (
        f"expected deallocation to have no batch_ref and no sku, but got {deallocation.json()}"
    )

    for batch in (earlybatch, laterbatch, otherbatch):
        delete_response = fastapi_test_client.delete(f"{url}/batches/{batch['reference']}?sku={batch['sku']}")
        assert delete_response.status_code == 204


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_get_batch_deallocate_from_batch(fastapi_test_client):
    batch_ref = random_batch_ref(name="absent-get-test")
    sku = random_sku(name="absent-sku")
    r = fastapi_test_client.get(f"{url}/batches/{batch_ref}?sku={sku}")
    assert r.status_code == 400
    assert r.json()["detail"] == f"Invalid sku {sku}"

    order_id = random_order_id()
    deallocate_data = {"sku": sku, "order_id": order_id, "qty": 10}
    deallocate_from_abcent_product_request = fastapi_test_client.post(f"{url}/deallocate", json=deallocate_data)
    assert deallocate_from_abcent_product_request.json()["detail"] == f"Invalid sku {sku}"
    assert deallocate_from_abcent_product_request.status_code == 400

    post_data = {
        "reference": batch_ref,
        "sku": sku,
        "qty": 100,
        "eta": "2026-01-21",
    }
    r = fastapi_test_client.post(f"{url}/batches/", json=post_data)
    assert r.status_code == 201

    deallocate_from_existing_product_request = fastapi_test_client.post(f"{url}/deallocate", json=deallocate_data)
    assert deallocate_from_existing_product_request.status_code == 400
    assert (
        deallocate_from_existing_product_request.json()["detail"] == f"Order line {order_id} is not allocated to any batch in Product {sku}"
    )

    allocation = fastapi_test_client.get(f"{url}/allocations/{order_id}")
    assert allocation.status_code == 400

    delete_batch_request = fastapi_test_client.delete(f"{url}/batches/{batch_ref}?sku={sku}")
    assert delete_batch_request.status_code == 204


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_post_allocate_returns_400_and_error_message(fastapi_test_client):
    unknown_sku, order_id = random_sku(), random_order_id()
    data = {"order_id": order_id, "sku": unknown_sku, "qty": 20}
    r = fastapi_test_client.post(f"{url}/allocate", json=data)
    assert r.status_code == 400
    assert r.json()["detail"] == f"Invalid sku {unknown_sku}"

    allocation = fastapi_test_client.get(f"{url}/allocations/{order_id}")
    assert allocation.status_code == 400
