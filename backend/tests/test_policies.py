def test_health_check_valid(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "API is online and database is connected"}

# --- AUTHENTICATION & AUTHORIZATION (401 & 403) ---

def test_request_missing_header_invalid(client):
    response = client.post(
        "/api/policies",
        params={"tenant_id": "tenant_A"},
        files={
            "file": (
                "test.cedar",
                "permit(principal, action, resource);",
                "application/cedar",
            )
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"

def test_request_unknown_user_invalid(client):
    headers = {"user-id": "fake_user_xyz"}
    response = client.get("/api/policies/list?tenant_id=tenant_A", headers=headers)
    assert response.status_code == 401

def test_request_forbidden_tenant_invalid(client):
    headers = {"user-id": "user_1"}
    response = client.get("/api/policies/list?tenant_id=tenant_B", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


def test_seeded_users_include_customer_and_tenant_mappings(client):
    response = client.get("/api/users")

    assert response.status_code == 200
    assert response.json() == {
        "users": [
            {
                "user_id": "user_1",
                "customer_id": "customer_1",
                "tenant_ids": ["tenant_A"],
            },
            {
                "user_id": "user_2",
                "customer_id": "customer_1",
                "tenant_ids": ["tenant_A", "tenant_B"],
            },
            {
                "user_id": "user_3",
                "customer_id": "customer_2",
                "tenant_ids": ["tenant_C"],
            },
        ]
    }

# --- SYNTAX VALIDATION (400) ---

def test_upload_invalid_syntax_bad_request(client):
    headers = {"user-id": "user_1"}
    response = client.post(
        "/api/policies",
        params={"tenant_id": "tenant_A"},
        files={"file": ("bad.cedar", "broken_syntax_here", "application/cedar")},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == {
        "message": "Invalid Cedar syntax",
        "validation_error": "unexpected token at line 1, column 1",
    }

# --- FULL LIFECYCLE (VALID) & NOT FOUND (404) ---

def test_policy_lifecycle_valid_and_not_found(client):
    headers = {"user-id": "user_1"}
    tenant = "tenant_A"
    filename = "e2e_test.cedar"
    content = "permit(principal, action, resource);"

    # 1. Upload Valid Policy
    response = client.post(
        "/api/policies",
        params={"tenant_id": tenant},
        files={"file": (filename, content, "application/cedar")},
        headers=headers,
    )

    if response.status_code != 200:
        print(f"\n\n🚨 SERVER CRASH LOG: {response.json()}\n\n")

    assert response.status_code == 200
    assert "policy_id" in response.json()
    
    # 2. List Policies Valid
    response = client.get(f"/api/policies/list?tenant_id={tenant}", headers=headers)
    assert response.status_code == 200
    assert any(p["filename"] == filename for p in response.json()["policies"])

    # 3. Get Content Valid
    response = client.get(f"/api/policies/content?tenant_id={tenant}&filename={filename}", headers=headers)
    assert response.status_code == 200
    assert response.json()["policy"]["content"] == content

    # 4. Download Valid
    response = client.get(
        f"/api/policies/download?tenant_id={tenant}&filename={filename}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.content == content.encode("utf-8")
    assert response.headers["content-type"].startswith("application/cedar")
    assert response.headers["content-disposition"] == (
        "attachment; filename*=UTF-8''e2e_test.cedar"
    )

    # 5. Get History Valid
    response = client.get(f"/api/policies/history?tenant_id={tenant}&filename={filename}", headers=headers)
    assert response.status_code == 200
    assert "history" in response.json()

    # 6. Delete Policy Valid
    response = client.delete(f"/api/policies?tenant_id={tenant}&filename={filename}", headers=headers)
    assert response.status_code == 200

    # 7. Get Content After Delete -> Should be 404 Not Found
    response = client.get(f"/api/policies/content?tenant_id={tenant}&filename={filename}", headers=headers)
    assert response.status_code == 404
