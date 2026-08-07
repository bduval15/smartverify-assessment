from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .routers import policies

app = FastAPI(title="SmartVerify Policy Manager")

app.include_router(policies.router)

@app.get("/")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "API is online and database is connected"}
