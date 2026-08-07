def test_health_check_valid(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "API is online and database is connected"}

# --- AUTHENTICATION & AUTHORIZATION (401 & 403) ---

def test_request_missing_header_invalid(client):
    response = client.post("/api/policies?tenant_id=tenant_A&filename=test.cedar&content=permit(p%2Ca%2Cr)%3B")
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

# --- SYNTAX VALIDATION (400) ---

def test_upload_invalid_syntax_bad_request(client):
    headers = {"user-id": "user_1"}
    response = client.post(
        "/api/policies?tenant_id=tenant_A&filename=bad.cedar&content=broken_syntax_here",
        headers=headers
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid Cedar syntax"

# --- FULL LIFECYCLE (VALID) & NOT FOUND (404) ---

def test_policy_lifecycle_valid_and_not_found(client):
    headers = {"user-id": "user_1"}
    tenant = "tenant_A"
    filename = "e2e_test.cedar"
    content = "permit(principal, action, resource);"

    # 1. Upload Valid Policy
    response = client.post(
        f"/api/policies?tenant_id={tenant}&filename={filename}&content={content}",
        headers=headers
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

    # 4. Get History Valid
    response = client.get(f"/api/policies/history?tenant_id={tenant}&filename={filename}", headers=headers)
    assert response.status_code == 200
    assert "history" in response.json()

    # 5. Delete Policy Valid
    response = client.delete(f"/api/policies?tenant_id={tenant}&filename={filename}", headers=headers)
    assert response.status_code == 200

    # 6. Get Content After Delete -> Should be 404 Not Found
    response = client.get(f"/api/policies/content?tenant_id={tenant}&filename={filename}", headers=headers)
    assert response.status_code == 404
