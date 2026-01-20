from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from allocation import config
from allocation.domain.model import OrderLine
from allocation.domain.exceptions import OutOfStock, InvalidBatchReference, UnallocatedLine
from allocation.adapters import orm, repository
from allocation.service_layer import services
from fastapi import FastAPI, HTTPException

from allocation.entrypoints.schemas import AllocateRequest, DeallocateRequest

orm.start_mappers()
get_session = sessionmaker(bind=create_engine(url=config.get_db_uri()))
app = FastAPI()


@app.post("/allocate", status_code=201)
def allocate_endpoint(payload: AllocateRequest):
    session = get_session()
    repo = repository.SQLAlchemyRepository(session)

    line = OrderLine(
        orderId=payload.orderid,
        sku=payload.sku,
        qty=payload.qty,
    )
    try:
        batch = services.allocate(line=line, repo=repo, session=session)
        return {"batchref": batch.reference}
    except (OutOfStock, services.InvalidSku) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/deallocate", status_code=200)
def deallocate_endpoint(payload: DeallocateRequest):
    session = get_session()
    repo = repository.SQLAlchemyRepository(session)
    try:
        batch = services.deallocate(
            batchref=payload.batchref,
            orderId=payload.orderid,
            repo=repo,
            session=session,
        )
        return {"batchref": batch.reference}
    except InvalidBatchReference as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UnallocatedLine as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/batches/{batchref}")
def get_endpoint(batchref: str):
    session = get_session()
    repo = repository.SQLAlchemyRepository(session)
    batch = repo.get(reference=batchref)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batchref} not found")
    return {
        "reference": batch.reference,
        "sku": batch.sku,
        "qty": batch._purchase_quantity,
        "eta": batch.eta.isoformat() if batch.eta else None,
    }
