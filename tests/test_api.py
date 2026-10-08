"""End-to-end tests for the backend API."""


def test_health(client):
    """Health endpoint should confirm database connectivity."""
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json()["data"] == {"status": "ok", "database": "ok"}


def test_protected_endpoint_uses_unified_error(client):
    """Protected endpoints should reject anonymous requests consistently."""
    response = client.get("/api/customers/needs")

    assert response.status_code == 401
    assert response.get_json()["code"] == 401
    assert "timestamp" in response.get_json()


def test_login_and_current_user(client, auth_headers):
    """Valid credentials should allow current-user lookup."""
    response = client.get("/api/auth/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json()["data"]["account"] == "admin"


def test_list_filter_and_crud(client, auth_headers):
    """List filtering and the full CRUD lifecycle should work."""
    needs = client.get(
        "/api/customers/needs?status=待处理&page=1&pageSize=10",
        headers=auth_headers,
    ).get_json()["data"]
    assert needs["total"] == 2
    assert all(item["status"] == "待处理" for item in needs["items"])

    created = client.post(
        "/api/company/honors",
        headers=auth_headers,
        json={
            "name": "测试荣誉",
            "issuer": "测试机构",
            "year": 2026,
            "status": "展示中",
        },
    )
    assert created.status_code == 201
    honor_id = created.get_json()["data"]["id"]

    updated = client.patch(
        f"/api/company/honors/{honor_id}",
        headers=auth_headers,
        json={"status": "已下架"},
    )
    assert updated.status_code == 200
    assert updated.get_json()["data"]["status"] == "已下架"

    deleted = client.delete(
        f"/api/company/honors/{honor_id}",
        headers=auth_headers,
    )
    assert deleted.status_code == 200
    assert client.get(
        f"/api/company/honors/{honor_id}",
        headers=auth_headers,
    ).status_code == 404


def test_settings_and_dashboard(client, auth_headers):
    """Settings should persist and dashboard totals should reflect seed data."""
    saved = client.put(
        "/api/news/pull-settings",
        headers=auth_headers,
        json={
            "account": "江南谷语酒业",
            "count": 30,
            "time": "03:30",
            "enabled": True,
        },
    )
    assert saved.status_code == 200
    assert saved.get_json()["data"]["count"] == 30

    dashboard = client.get(
        "/api/dashboard/summary",
        headers=auth_headers,
    ).get_json()["data"]
    assert dashboard["stats"][0]["value"] == "3"
    assert len(dashboard["latestNeeds"]) == 3


def test_validation_error_is_structured(client, auth_headers):
    """Invalid payloads should include field-level validation details."""
    response = client.post(
        "/api/products/categories",
        headers=auth_headers,
        json={"name": "", "sort": 0},
    )

    assert response.status_code == 422
    body = response.get_json()
    assert body["code"] == 422
    assert "name" in body["data"]


def test_product_category_does_not_expose_count(client, auth_headers):
    """Product categories should not carry a manually maintained count."""
    response = client.post(
        "/api/products/categories",
        headers=auth_headers,
        json={"name": "测试分类", "sort": 4, "status": "启用"},
    )

    assert response.status_code == 201
    assert "count" not in response.get_json()["data"]


def test_cannot_delete_current_user(client, auth_headers, admin_id):
    """The current administrator should not be able to delete itself."""
    response = client.delete(
        f"/api/users/{admin_id}",
        headers=auth_headers,
    )

    assert response.status_code == 400
