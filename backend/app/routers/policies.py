from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .. import models
from ..auth import get_authorized_tenants
from ..database import get_db
from ..services import (
    CedarValidationError,
    CedarValidatorUnavailableError,
    GitStorageService,
)

router = APIRouter(prefix="/api/policies", tags=["Policies"])
# Policy files should remain small administrative artifacts; this also bounds
# memory use because uploads are validated in memory before reaching Git.
MAX_POLICY_SIZE_BYTES = 1024 * 1024

def verify_tenant_access(
    tenant_id: str,
    authorized_tenants: list[str] = Depends(get_authorized_tenants),
) -> str:
    # This dependency runs for every policy route, so handcrafted requests get
    # the same tenant isolation as requests made through the UI.
    if tenant_id not in authorized_tenants:
        raise HTTPException(status_code=403, detail="Forbidden")
    return tenant_id


def validate_policy_filename(filename: str) -> str:
    try:
        GitStorageService._validate_path_component(filename, "filename")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return filename


def validate_policy_content(content: str, git_service: GitStorageService) -> str:
    try:
        git_service.validate_cedar_syntax(content)
    except CedarValidationError as error:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invalid Cedar syntax",
                "validation_error": str(error),
            },
        ) from error
    except CedarValidatorUnavailableError as error:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Cedar validation is temporarily unavailable",
                "validation_error": str(error),
            },
        ) from error
    return content


def get_git_service() -> GitStorageService:
    return GitStorageService()


def read_policy_upload(
    policy_file: UploadFile,
    git_service: GitStorageService,
) -> tuple[str, str]:
    filename = validate_policy_filename(policy_file.filename or "")
    raw_content = policy_file.file.read(MAX_POLICY_SIZE_BYTES + 1)
    if len(raw_content) > MAX_POLICY_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Policy files must be {MAX_POLICY_SIZE_BYTES} bytes or smaller",
        )

    try:
        content = raw_content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise HTTPException(
            status_code=400,
            detail="Policy files must be UTF-8 encoded text",
        ) from error

    return filename, validate_policy_content(content, git_service)


@router.post("")
def upload_policy(
    tenant_id: str = Depends(verify_tenant_access),
    policy_file: UploadFile = File(..., alias="file"),
    db: Session = Depends(get_db),
    git_service: GitStorageService = Depends(get_git_service),
):
    filename, content = read_policy_upload(policy_file, git_service)
    existing_policy = (
        db.query(models.PolicyMetadata)
        .filter_by(tenant_id=tenant_id, filename=filename)
        .first()
    )
    if existing_policy:
        raise HTTPException(status_code=409, detail="Policy already exists")

    try:
        # Git must be written first because metadata cannot reference a commit
        # that does not exist yet.
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
            # Git and PostgreSQL cannot share a transaction. A deletion commit
            # is the compensating action when the metadata insert fails.
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
    policy = (
        db.query(models.PolicyMetadata)
        .filter_by(tenant_id=tenant_id, filename=filename)
        .first()
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    try:
        # Save the committed version before deletion so a database failure can
        # be compensated without trusting the mutable working tree.
        previous_content = git_service.read_policy(
            tenant_id,
            filename,
            policy.git_hash,
        )
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail="Policy file not found in Git storage",
        ) from error

    try:
        git_service.delete_policy(tenant_id, filename)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Policy not found") from error
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete policy: {error}"
        ) from error

    try:
        db.delete(policy)
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        try:
            # Restoration is a new commit so the failed delete remains visible
            # in Git history instead of rewriting repository history.
            git_service.write_policy(tenant_id, filename, previous_content)
        except Exception:
            pass
        raise HTTPException(
            status_code=500,
            detail=f"Policy deletion failed and was rolled back: {error}",
        ) from error

    return {"message": "Policy deleted successfully"}


@router.get("/list")
def list_policies(
    tenant_id: str = Depends(verify_tenant_access),
    db: Session = Depends(get_db),
):
    # PostgreSQL is the query index; listing should not infer current policies
    # by walking Git paths.
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
    policy_file: UploadFile = File(..., alias="file"),
    db: Session = Depends(get_db),
    git_service: GitStorageService = Depends(get_git_service),
):
    filename, content = read_policy_upload(policy_file, git_service)
    policy = (
        db.query(models.PolicyMetadata)
        .filter_by(tenant_id=tenant_id, filename=filename)
        .first()
    )
    if not policy:
        # PUT is strict replacement, not upsert. New policies must use POST so
        # an accidental filename cannot silently create content.
        raise HTTPException(status_code=404, detail="Policy not found")

    try:
        previous_content = git_service.read_policy(
            tenant_id,
            filename,
            policy.git_hash,
        )
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail="Policy file not found in Git storage",
        ) from error

    try:
        commit_hash = git_service.write_policy(tenant_id, filename, content)
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Failed to update policy: {error}"
        ) from error

    try:
        policy.git_hash = commit_hash
        db.commit()
        db.refresh(policy)
    except SQLAlchemyError as error:
        db.rollback()
        try:
            # Keep the previous content current if PostgreSQL cannot advance
            # its git_hash to the replacement commit.
            git_service.write_policy(tenant_id, filename, previous_content)
        except Exception:
            pass
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
        content = git_service.read_policy(tenant_id, filename, policy.git_hash)
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


@router.get("/download")
def download_policy(
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
        content = git_service.read_policy(tenant_id, filename, policy.git_hash)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404, detail="Policy file not found in Git storage"
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Failed to download policy: {error}"
        ) from error

    encoded_filename = quote(filename, safe="")
    return Response(
        content=content.encode("utf-8"),
        media_type="application/cedar",
        headers={
            "Content-Disposition": (
                f"attachment; filename*=UTF-8''{encoded_filename}"
            )
        },
    )


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
