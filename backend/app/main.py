from fastapi import FastAPI
from .database import engine, Base, get_db
from .routers import policies
from . import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SmartVerify Policy Manager")

app.include_router(policies.router)

# Health check route to verify the server is running
@app.get("/")
def health_check():
    return {"status": "API is online and database is connected"}
