import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import auth, models
from .database import get_db
from .routers import policies


def get_cors_allowed_origins() -> list[str]:
    configured_origins = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173",
    )
    return [
        origin.strip()
        for origin in configured_origins.split(",")
        if origin.strip()
    ]


app = FastAPI(title="SmartVerify Policy Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "user-id"],
    expose_headers=["Content-Disposition"],
)

app.include_router(policies.router)
app.include_router(auth.router)

@app.get("/")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "API is online and database is connected"}
