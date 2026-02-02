from allocation.domain.exceptions import OutOfStock, InvalidBatchReference, UnallocatedLine, InvalidSku
from allocation.adapters import orm
from allocation.service_layer import services, unit_of_work
from fastapi import FastAPI, HTTPException

from allocation.entrypoints.schemas import AllocateRequest, DeallocateRequest, AddBatchRequest
from datetime import datetime

orm.start_mappers()
app = FastAPI()
uow = unit_of_work.SqlAlchemyUnitOfWork()


@app.post("/allocate", status_code=201)
def allocate(payload: AllocateRequest):
    orderId = payload.orderid
    sku = payload.sku
    qty = payload.qty
    try:
        batch_ref = services.allocate(orderId=orderId, sku=sku, qty=qty, uow=uow)
        return {"batchref": batch_ref}
    except (OutOfStock, services.InvalidSku) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/batches/", status_code=201)
def add_batch(payload: AddBatchRequest):
    reference = payload.reference
    sku = payload.sku
    qty = payload.qty
    eta = None if payload.eta is None else datetime.fromisoformat(payload.eta).date()
    services.add_batch(reference=reference, sku=sku, qty=qty, eta=eta, uow=uow)


@app.delete("/batches/{batchref}", status_code=204)
def delete_batch(sku: str, batchref: str):
    try:
        services.delete_batch(sku=sku, reference=batchref, uow=uow)
    except InvalidSku as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidBatchReference as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/deallocate", status_code=200)
def deallocate(payload: DeallocateRequest):
    try:
        batch_ref = services.deallocate(
            sku=payload.sku,
            orderId=payload.orderid,
            qty=payload.qty,
            uow=uow,
        )
        return {"batchref": batch_ref}
    except InvalidSku as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UnallocatedLine as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/batches/{batchref}")
def get(sku: str, batchref: str):
    batch_data = services.get_batch(sku=sku, reference=batchref, uow=uow)
    return batch_data
