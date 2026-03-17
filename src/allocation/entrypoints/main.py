from datetime import datetime

from fastapi import FastAPI, HTTPException

from allocation import views
from allocation.adapters import orm
from allocation.domain import commands, exceptions
from allocation.entrypoints.schemas import AddBatchRequest, AllocateRequest, DeallocateRequest
from allocation.service_layer import handlers, messagebus, unit_of_work

orm.start_mappers()
app = FastAPI()
uow = unit_of_work.SqlAlchemyUnitOfWork()
messageBus = messagebus.MessageBus(uow=uow)


@app.post("/allocate", status_code=202)
def allocate(payload: AllocateRequest):
    order_id = payload.order_id
    sku = payload.sku
    qty = payload.qty
    try:
        command = commands.Allocate(order_id=order_id, sku=sku, qty=qty)
        result = messageBus.handle(message=command)
        batch_ref = result[0] if result else None
        return {"batch_ref": batch_ref}
    except exceptions.InvalidSku as e:
        raise HTTPException(status_code=400, detail=str(e))
    except exceptions.UnallocatedLine as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/deallocate", status_code=202)
def deallocate(payload: DeallocateRequest):
    try:
        command = commands.Deallocate(order_id=payload.order_id, sku=payload.sku, qty=payload.qty)
        result = messageBus.handle(message=command)
        batch_ref = result[0] if result else None
        return {"batch_ref": batch_ref}
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
    command = commands.CreateBatch(ref=reference, sku=sku, qty=qty, eta=eta)
    try:
        messageBus.handle(message=command)
        return {"reference": reference, "sku": sku}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/batches/{batch_ref}", status_code=204)
def delete_batch(sku: str, batch_ref: str):
    try:
        command = commands.DeleteBatch(ref=batch_ref, sku=sku)
        messageBus.handle(message=command)
    except exceptions.InvalidSku as e:
        raise HTTPException(status_code=400, detail=str(e))
    except exceptions.InvalidBatchReference as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/batches/{batch_ref}")
def get_batches(sku: str, batch_ref: str):
    try:
        batch_data = handlers.get_batch(sku=sku, reference=batch_ref, uow=uow)
        return batch_data
    except exceptions.InvalidSku as e:
        raise HTTPException(status_code=400, detail=str(e))
    except exceptions.InvalidBatchReference as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/allocations/{order_id}")
def get_allocations(order_id: str):
    result = views.allocations(order_id=order_id, uow=uow)
    if result in (None, []):
        raise HTTPException(status_code=400, detail=f"Order line {order_id} not found")
    return result
