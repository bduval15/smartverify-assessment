from app.models import PolicyMetadata
from app.main import get_cors_allowed_origins
from app.services import CedarValidatorUnavailableError


HEADERS_USER_1 = {"user-id": "user_1"}
HEADERS_USER_2 = {"user-id": "user_2"}
VALID_POLICY = "permit(principal, action, resource);"


def test_upload_requires_multipart_file(client):
    response = client.post(
        "/api/policies",
        params={"tenant_id": "tenant_A"},
        headers=HEADERS_USER_1,
    )

    assert response.status_code == 422


def test_upload_rejects_non_utf8_content(client):
    response = client.post(
        "/api/policies",
        params={"tenant_id": "tenant_A"},
        files={"file": ("binary.cedar", b"\xff\xfe", "application/cedar")},
        headers=HEADERS_USER_1,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Policy files must be UTF-8 encoded text"


def test_upload_rejects_oversized_policy(client):
    response = client.post(
        "/api/policies",
        params={"tenant_id": "tenant_A"},
        files={
            "file": (
                "large.cedar",
                b"p" * (1024 * 1024 + 1),
                "application/cedar",
            )
        },
        headers=HEADERS_USER_1,
    )

    assert response.status_code == 413
    assert "1048576 bytes or smaller" in response.json()["detail"]


def test_upload_reports_validator_configuration_failure(client, git_service):
    def unavailable(_content):
        raise CedarValidatorUnavailableError("cedar was not found on PATH")

    git_service.validate_cedar_syntax = unavailable

    response = client.post(
        "/api/policies",
        params={"tenant_id": "tenant_A"},
        files={
            "file": (
                "valid.cedar",
                VALID_POLICY,
                "application/cedar",
            )
        },
        headers=HEADERS_USER_1,
    )

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "message": "Cedar validation is temporarily unavailable",
        "validation_error": "cedar was not found on PATH",
    }


def test_download_preserves_tenant_isolation(client):
    created = client.post(
        "/api/policies",
        params={"tenant_id": "tenant_A"},
        files={
            "file": (
                "private.cedar",
                VALID_POLICY,
                "application/cedar",
            )
        },
        headers=HEADERS_USER_1,
    )
    assert created.status_code == 200

    response = client.get(
        "/api/policies/download",
        params={"tenant_id": "tenant_A", "filename": "private.cedar"},
        headers={"user-id": "user_3"},
    )

    assert response.status_code == 403


def test_cross_tenant_upload_content_and_delete_are_forbidden(client):
    filename = "tenant-b-private.cedar"
    created = client.post(
        "/api/policies",
        params={"tenant_id": "tenant_B"},
        files={
            "file": (filename, VALID_POLICY, "application/cedar"),
        },
        headers=HEADERS_USER_2,
    )
    assert created.status_code == 200

    unauthorized_upload = client.post(
        "/api/policies",
        params={"tenant_id": "tenant_B"},
        files={
            "file": (
                "unauthorized.cedar",
                VALID_POLICY,
                "application/cedar",
            ),
        },
        headers=HEADERS_USER_1,
    )
    unauthorized_content = client.get(
        "/api/policies/content",
        params={"tenant_id": "tenant_B", "filename": filename},
        headers=HEADERS_USER_1,
    )
    unauthorized_delete = client.delete(
        "/api/policies",
        params={"tenant_id": "tenant_B", "filename": filename},
        headers=HEADERS_USER_1,
    )

    assert unauthorized_upload.status_code == 403
    assert unauthorized_content.status_code == 403
    assert unauthorized_delete.status_code == 403

    owner_content = client.get(
        "/api/policies/content",
        params={"tenant_id": "tenant_B", "filename": filename},
        headers=HEADERS_USER_2,
    )
    owner_list = client.get(
        "/api/policies/list",
        params={"tenant_id": "tenant_B"},
        headers=HEADERS_USER_2,
    )

    assert owner_content.status_code == 200
    assert owner_content.json()["policy"]["content"] == VALID_POLICY
    assert [policy["filename"] for policy in owner_list.json()["policies"]] == [
        filename
    ]


def test_download_reports_missing_git_file(client, db_session):
    db_session.add(
        PolicyMetadata(
            tenant_id="tenant_A",
            filename="missing-content.cedar",
            git_hash="missing",
        )
    )
    db_session.commit()

    response = client.get(
        "/api/policies/download",
        params={
            "tenant_id": "tenant_A",
            "filename": "missing-content.cedar",
        },
        headers=HEADERS_USER_1,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Policy file not found in Git storage"
    )


def test_cors_allows_configured_frontend_origin(client):
    response = client.options(
        "/api/policies/list?tenant_id=tenant_A",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "user-id",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )
    assert "user-id" in response.headers["access-control-allow-headers"]


def test_cors_rejects_unconfigured_origin(client):
    response = client.options(
        "/api/policies/list?tenant_id=tenant_A",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_cors_origins_are_trimmed_and_empty_values_ignored(monkeypatch):
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        " https://one.example, ,https://two.example ",
    )

    assert get_cors_allowed_origins() == [
        "https://one.example",
        "https://two.example",
    ]
