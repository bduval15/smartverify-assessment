from fastapi import APIRouter, Header, HTTPException, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..services import GitStorageService
from .. import models

router = APIRouter(prefix="/api/policies", tags=["Policies"])

MOCK_USER_DB = {
    "user_1": ["tenant_A"],
    "user_2": ["tenant_A", "tenant_B"],
    "user_3": ["tenant_C"],
}

def get_authorized_tenants(user_id: str = Header(default=None)):
    if user_id is None or user_id not in MOCK_USER_DB:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return MOCK_USER_DB[user_id]

def verify_tenant_access(tenant_id: str, authorized_tenants: list = Depends(get_authorized_tenants)):
    if tenant_id not in authorized_tenants:
        raise HTTPException(status_code=403, detail="Forbidden")
    return tenant_id

def validate_policy_content(content: str):
    if not GitStorageService.validate_cedar_syntax(content):
        raise HTTPException(status_code=400, detail="Invalid Cedar syntax")
    return content

# --- API Routes ---

@router.post("")
def upload_policy(
    tenant_id: str = Depends(verify_tenant_access),
    filename: str = "",
    content: str = Depends(validate_policy_content),
    db: Session = Depends(get_db),
):
    git_service = GitStorageService()
    try:
        commit_hash = git_service.write_policy(tenant_id, 
                                               filename, content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write policy: {str(e)}")

    try:
        policy = models.Policy(tenant_id=tenant_id, 
                               filename=filename,
                               git_hash=commit_hash)
        db.add(policy)
        db.commit()
        db.refresh(policy)
    except Exception as e:
        db.rollback()
        git_service.delete_policy(tenant_id, filename)
        raise HTTPException(status_code=500, detail=f"Failed to save policy metadata: {str(e)}")

    return {"message": "Policy uploaded successfully", "policy_id": policy.id}

@router.delete("")
def delete_policy(
    tenant_id: str = Depends(verify_tenant_access),
    filename: str = "",
    db: Session = Depends(get_db),
):
    git_service = GitStorageService()
    try:
        git_service.delete_policy(tenant_id, filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Policy not found")

    policy = db.query(models.Policy).filter_by(tenant_id=tenant_id, filename=filename).first()
    if policy:
        db.delete(policy)
        db.commit()

    return {"message": "Policy deleted successfully"}

@router.get("/list")
def list_policies(
    tenant_id: str = Depends(verify_tenant_access),
    db: Session = Depends(get_db),
):
    policies = db.query(models.Policy).filter(models.Policy.tenant_id == tenant_id).all()

    return {"policies": [{"id": p.id, "filename": p.filename} for p in policies]}

@router.put("")
def update_policy(
    tenant_id: str = Depends(verify_tenant_access),
    filename: str = "",
    content: str = Depends(validate_policy_content),
    db: Session = Depends(get_db),
):
    git_service = GitStorageService()
    try:
        commit_hash = git_service.write_policy(tenant_id, filename, content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update policy: {str(e)}")

    policy = db.query(models.Policy).filter_by(tenant_id=tenant_id, filename=filename).first()
    if policy:
        policy.git_hash = commit_hash
        db.commit()
        db.refresh(policy)
    else:
        policy = models.Policy(tenant_id=tenant_id, filename=filename, git_hash=commit_hash)
        db.add(policy)
        db.commit()
        db.refresh(policy)

    return {"message": "Policy updated successfully", "policy_id": policy.id}

@router.get("/content")
def get_policy_content(
    tenant_id: str = Depends(verify_tenant_access),
    filename: str = "",
    db: Session = Depends(get_db),
):
    policy = db.query(models.Policy).filter_by(tenant_id=tenant_id, filename=filename).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    git_service = GitStorageService()
    _, full_file_path = git_service._get_paths(tenant_id, filename)

    try:
        with open(full_file_path, "r") as f:
            content = f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Policy file not found in Git storage")

    return {"policy": {"id": policy.id, "filename": policy.filename, "content": content}}

@router.get("/history")
def policy_history(
    tenant_id: str = Depends(verify_tenant_access),
    filename: str = "",
    db: Session = Depends(get_db),
):

    git_service = GitStorageService()
    _, full_file_path = git_service._get_paths(tenant_id, filename)

    try:
        commits = list(git_service.repo.iter_commits(paths=full_file_path))
        history = [{"commit_hash": commit.hexsha, "message": commit.message.strip(), "date": commit.committed_datetime} for commit in commits]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve policy history: {str(e)}")

    return {"history": history} 
