from fastapi import FastAPI, Header, HTTPException, Depends
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from .services import GitStorageService
from . import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SmartVerify Policy Manager")

MOCK_USER_DB = {
    "user_1": ["tenant_A"],
    "user_2": ["tenant_A", "tenant_B"],
    "user_3": ["tenant_C"],
}

def get_authorized_tenants(user_id: str = Header(defaul=None)):
    if user_id is None or user_id not in MOCK_USER_DB:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return MOCK_USER_DB[user_id]

# --- API Routes ---

# Health check route to verify the server is running
@app.get("/")
def health_check():
    return {"status": "API is online and database is connected"}

@app.post("/api/policies")
def upload_policy(
    tenant_id: str,
    filename: str,
    content: str,
    db: Session = Depends(get_db),
    authorized_tenants: list = Depends(get_authorized_tenants)
):
    if tenant_id not in authorized_tenants:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Validate Cedar syntax
    if not GitStorageService.validate_cedar_syntax(content):
        raise HTTPException(status_code=400, detail="Invalid Cedar syntax")

    # Write policy to Git storage
    git_service = GitStorageService()
    git_service.write_policy(tenant_id, filename, content)

    # Store metadata in the database
    policy = models.Policy(tenant_id=tenant_id, filename=filename)
    db.add(policy)
    db.commit()
    db.refresh(policy)

    return {"message": "Policy uploaded successfully", "policy_id": policy.id}

@app.get("/api/policies")
def list_policies(
    tenant_id: str,
    db: Session = Depends(get_db),
    authorized_tenants: list = Depends(get_authorized_tenants)
):
    if tenant_id not in authorized_tenants:
        raise HTTPException(status_code=403, detail="Forbidden")

    policies = db.query(models.Policy).filter(models.Policy.tenant_id == tenant_id).all()
    return {"policies": [{"id": p.id, "filename": p.filename} for p in policies]}