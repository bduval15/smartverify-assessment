from app.models import PolicyMetadata


HEADERS_USER_1 = {"user-id": "user_1"}
HEADERS_USER_2 = {"user-id": "user_2"}
VALID_POLICY = "permit(principal, action, resource);"
UPDATED_POLICY = "permit(principal, action, resource) when { true };"


def test_upload_rejects_path_traversal_filename(client):
    response = client.post(
        "/api/policies",
        params={
            "tenant_id": "tenant_A",
            "filename": "../outside.cedar",
            "content": VALID_POLICY,
        },
        headers=HEADERS_USER_1,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid filename"


def test_policy_update_duplicate_and_history(client):
    policy_params = {
        "tenant_id": "tenant_A",
        "filename": "update-test.cedar",
        "content": VALID_POLICY,
    }
    created = client.post(
        "/api/policies",
        params=policy_params,
        headers=HEADERS_USER_1,
    )
    assert created.status_code == 200

    duplicate = client.post(
        "/api/policies",
        params=policy_params,
        headers=HEADERS_USER_1,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Policy already exists"

    updated = client.put(
        "/api/policies",
        params={**policy_params, "content": UPDATED_POLICY},
        headers=HEADERS_USER_1,
    )
    assert updated.status_code == 200
    assert updated.json()["policy_id"] == created.json()["policy_id"]

    content = client.get(
        "/api/policies/content",
        params={
            "tenant_id": "tenant_A",
            "filename": "update-test.cedar",
        },
        headers=HEADERS_USER_1,
    )
    assert content.status_code == 200
    assert content.json()["policy"]["content"] == UPDATED_POLICY

    history = client.get(
        "/api/policies/history",
        params={
            "tenant_id": "tenant_A",
            "filename": "update-test.cedar",
        },
        headers=HEADERS_USER_1,
    )
    assert history.status_code == 200
    assert len(history.json()["history"]) == 2


def test_update_can_create_policy_for_authorized_tenant(client):
    response = client.put(
        "/api/policies",
        params={
            "tenant_id": "tenant_B",
            "filename": "created-by-update.cedar",
            "content": VALID_POLICY,
        },
        headers=HEADERS_USER_2,
    )

    assert response.status_code == 200
    listed = client.get(
        "/api/policies/list",
        params={"tenant_id": "tenant_B"},
        headers=HEADERS_USER_2,
    )
    assert [policy["filename"] for policy in listed.json()["policies"]] == [
        "created-by-update.cedar"
    ]


def test_content_reports_missing_git_file(client, db_session):
    db_session.add(
        PolicyMetadata(
            tenant_id="tenant_A",
            filename="orphan.cedar",
            git_hash="missing",
        )
    )
    db_session.commit()

    response = client.get(
        "/api/policies/content",
        params={"tenant_id": "tenant_A", "filename": "orphan.cedar"},
        headers=HEADERS_USER_1,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Policy file not found in Git storage"


def test_delete_reports_missing_policy(client):
    response = client.delete(
        "/api/policies",
        params={"tenant_id": "tenant_A", "filename": "missing.cedar"},
        headers=HEADERS_USER_1,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Policy not found"
