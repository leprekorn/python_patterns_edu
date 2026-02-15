from datetime import datetime

from fastapi import FastAPI, HTTPException

from allocation.adapters import orm
from allocation.domain import exceptions
from allocation.entrypoints.schemas import AddBatchRequest, AllocateRequest, DeallocateRequest
from allocation.service_layer import services, unit_of_work

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
    except exceptions.InvalidSku as e:
        raise HTTPException(status_code=400, detail=str(e))
    except exceptions.UnallocatedLine as e:
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
    except exceptions.InvalidSku as e:
        raise HTTPException(status_code=400, detail=str(e))
    except exceptions.InvalidBatchReference as e:
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
    except exceptions.InvalidSku as e:
        raise HTTPException(status_code=400, detail=str(e))
    except exceptions.UnallocatedLine as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/batches/{batchref}")
def get(sku: str, batchref: str):
    try:
        batch_data = services.get_batch(sku=sku, reference=batchref, uow=uow)
        return batch_data
    except exceptions.InvalidSku as e:
        raise HTTPException(status_code=400, detail=str(e))
    except exceptions.InvalidBatchReference as e:
        raise HTTPException(status_code=404, detail=str(e))
