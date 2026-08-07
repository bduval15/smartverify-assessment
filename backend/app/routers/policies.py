from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..services import GitStorageService

router = APIRouter(prefix="/api/policies", tags=["Policies"])

MOCK_USER_DB = {
    "user_1": ["tenant_A"],
    "user_2": ["tenant_A", "tenant_B"],
    "user_3": ["tenant_C"],
}


def get_authorized_tenants(user_id: str | None = Header(default=None)) -> list[str]:
    if user_id is None or user_id not in MOCK_USER_DB:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return MOCK_USER_DB[user_id]


def verify_tenant_access(
    tenant_id: str,
    authorized_tenants: list[str] = Depends(get_authorized_tenants),
) -> str:
    if tenant_id not in authorized_tenants:
        raise HTTPException(status_code=403, detail="Forbidden")
    return tenant_id


def validate_policy_filename(filename: str) -> str:
    try:
        GitStorageService._validate_path_component(filename, "filename")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return filename


def validate_policy_content(content: str) -> str:
    if not GitStorageService.validate_cedar_syntax(content):
        raise HTTPException(status_code=400, detail="Invalid Cedar syntax")
    return content


def get_git_service() -> GitStorageService:
    return GitStorageService()


@router.post("")
def upload_policy(
    tenant_id: str = Depends(verify_tenant_access),
    filename: str = Depends(validate_policy_filename),
    content: str = Depends(validate_policy_content),
    db: Session = Depends(get_db),
    git_service: GitStorageService = Depends(get_git_service),
):
    existing_policy = (
        db.query(models.PolicyMetadata)
        .filter_by(tenant_id=tenant_id, filename=filename)
        .first()
    )
    if existing_policy:
        raise HTTPException(status_code=409, detail="Policy already exists")

    try:
        commit_hash = git_service.write_policy(tenant_id, filename, content)
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Failed to write policy: {error}"
        ) from error

    try:
        policy = models.PolicyMetadata(
            tenant_id=tenant_id,
            filename=filename,
            git_hash=commit_hash,
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)
    except SQLAlchemyError as error:
        db.rollback()
        try:
            git_service.delete_policy(tenant_id, filename)
        except Exception:
            pass
        raise HTTPException(
            status_code=500, detail=f"Failed to save policy metadata: {error}"
        ) from error

    return {"message": "Policy uploaded successfully", "policy_id": policy.id}


@router.delete("")
def delete_policy(
    tenant_id: str = Depends(verify_tenant_access),
    filename: str = Depends(validate_policy_filename),
    db: Session = Depends(get_db),
    git_service: GitStorageService = Depends(get_git_service),
):
    try:
        git_service.delete_policy(tenant_id, filename)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Policy not found") from error
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete policy: {error}"
        ) from error

    policy = (
        db.query(models.PolicyMetadata)
        .filter_by(tenant_id=tenant_id, filename=filename)
        .first()
    )
    if policy:
        try:
            db.delete(policy)
            db.commit()
        except SQLAlchemyError as error:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Policy file deleted but metadata cleanup failed: {error}",
            ) from error

    return {"message": "Policy deleted successfully"}


@router.get("/list")
def list_policies(
    tenant_id: str = Depends(verify_tenant_access),
    db: Session = Depends(get_db),
):
    policies = (
        db.query(models.PolicyMetadata)
        .filter(models.PolicyMetadata.tenant_id == tenant_id)
        .all()
    )

    return {
        "policies": [
            {"id": policy.id, "filename": policy.filename} for policy in policies
        ]
    }


@router.put("")
def update_policy(
    tenant_id: str = Depends(verify_tenant_access),
    filename: str = Depends(validate_policy_filename),
    content: str = Depends(validate_policy_content),
    db: Session = Depends(get_db),
    git_service: GitStorageService = Depends(get_git_service),
):
    try:
        commit_hash = git_service.write_policy(tenant_id, filename, content)
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Failed to update policy: {error}"
        ) from error

    try:
        policy = (
            db.query(models.PolicyMetadata)
            .filter_by(tenant_id=tenant_id, filename=filename)
            .first()
        )
        if policy:
            policy.git_hash = commit_hash
        else:
            policy = models.PolicyMetadata(
                tenant_id=tenant_id,
                filename=filename,
                git_hash=commit_hash,
            )
            db.add(policy)
        db.commit()
        db.refresh(policy)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to save policy metadata: {error}"
        ) from error

    return {"message": "Policy updated successfully", "policy_id": policy.id}


@router.get("/content")
def get_policy_content(
    tenant_id: str = Depends(verify_tenant_access),
    filename: str = Depends(validate_policy_filename),
    db: Session = Depends(get_db),
    git_service: GitStorageService = Depends(get_git_service),
):
    policy = (
        db.query(models.PolicyMetadata)
        .filter_by(tenant_id=tenant_id, filename=filename)
        .first()
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    try:
        content = git_service.read_policy(tenant_id, filename)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404, detail="Policy file not found in Git storage"
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Failed to read policy: {error}"
        ) from error

    return {
        "policy": {
            "id": policy.id,
            "filename": policy.filename,
            "content": content,
        }
    }


@router.get("/history")
def policy_history(
    tenant_id: str = Depends(verify_tenant_access),
    filename: str = Depends(validate_policy_filename),
    git_service: GitStorageService = Depends(get_git_service),
):
    try:
        history = git_service.policy_history(tenant_id, filename)
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve policy history: {error}"
        ) from error

    return {"history": history}
