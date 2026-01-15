from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from allocation import config
from allocation.domain import model
from allocation.adapters import orm, repository

from fastapi import FastAPI

from allocation.entrypoints.schemas import AllocateRequest

orm.start_mappers()
get_session = sessionmaker(bind=create_engine(url=config.get_db_uri()))
app = FastAPI()


@app.post("/allocate", status_code=201)
def allocate_endpoint(payload: AllocateRequest):
    session = get_session()
    repo = repository.SQLAlchemyRepository(session)
    batches = repo.list()

    line = model.OrderLine(
        orderId=payload.orderid,
        sku=payload.sku,
        qty=payload.qty,
    )

    batchref = model.allocate(line=line, batches=batches)
    return {"batchref": batchref}
