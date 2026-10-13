"""End-to-end tests for the backend API."""

import json
from unittest.mock import Mock

from requests import Response


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


def test_wechat_drafts_sync_and_content_preview(client, auth_headers, app, monkeypatch):
    """Draft summaries and bodies should be stored and reused after retrieval."""
    app.config["WECHAT_OFFICIAL_ACCOUNT_APPID"] = "test-appid"
    app.config["WECHAT_OFFICIAL_ACCOUNT_SECRET"] = "test-secret"

    class FakeRedis:
        def __init__(self):
            self.values = {}

        def get(self, key):
            return self.values.get(key)

        def setex(self, key, expires_in, value):
            self.values[key] = value

    token_response = Mock()
    token_response.raise_for_status.return_value = None
    token_response.json.return_value = {
        "access_token": "test-token",
        "expires_in": 7200,
    }
    list_response = Response()
    list_response.status_code = 200
    list_response.encoding = "latin-1"
    list_response._content = json.dumps({
        "total_count": 1,
        "item_count": 1,
        "item": [
            {
                "media_id": "draft-media-id",
                "content": {
                    "create_time": 1783560351,
                    "update_time": 1784712146,
                    "news_item": [
                        {
                            "title": "测试草稿",
                            "author": "编辑",
                            "digest": "测试摘要",
                            "thumb_url": "https://example.com/cover.jpg",
                            "content": "<p>测试正文</p>",
                        }
                    ],
                },
                "update_time": 1784712146,
            }
        ],
    }, ensure_ascii=False).encode("utf-8")
    post = Mock(side_effect=[list_response, list_response])
    get = Mock(return_value=token_response)
    fake_redis = FakeRedis()
    monkeypatch.setattr("app.blueprints.news.services.requests.post", post)
    monkeypatch.setattr("app.blueprints.news.services.requests.get", get)
    monkeypatch.setattr("app.blueprints.news.services.get_redis", lambda: fake_redis)

    synced = client.post("/api/news/drafts/sync", headers=auth_headers)
    assert synced.status_code == 200
    assert synced.get_json()["data"]["synced"] == 1
    assert post.call_args_list[0].kwargs["json"]["no_content"] == 0
    assert get.call_args.kwargs["params"] == {
        "grant_type": "client_credential",
        "appid": "test-appid",
        "secret": "test-secret",
    }
    draft = client.get("/api/news/drafts", headers=auth_headers).get_json()["data"]["items"][0]
    assert draft["title"] == "测试草稿"
    assert draft["digest"] == "测试摘要"

    category = client.post(
        "/api/news/categories",
        headers=auth_headers,
        json={
            "name": "测试草稿分类",
            "status": "启用",
        },
    )
    assert category.status_code == 201
    category_id = category.get_json()["data"]["id"]
    assert category.get_json()["data"]["count"] == 0

    updated = client.patch(
        "/api/news/drafts/draft-media-id",
        headers=auth_headers,
        json={
            "title": "已编辑草稿",
            "author": "新编辑",
            "category": "测试草稿分类",
            "status": "已发布",
            "digest": "已编辑摘要",
        },
    )
    assert updated.status_code == 200
    updated_data = updated.get_json()["data"]
    assert updated_data["mediaId"] == "draft-media-id"
    assert updated_data["title"] == "已编辑草稿"
    assert updated_data["author"] == "新编辑"
    assert updated_data["category"] == "测试草稿分类"
    assert updated_data["status"] == "已发布"
    assert updated_data["digest"] == "已编辑摘要"

    published_category = client.get(
        f"/api/news/categories/{category_id}", headers=auth_headers
    ).get_json()["data"]
    assert published_category["count"] == 1

    invalid_category = client.patch(
        "/api/news/drafts/draft-media-id",
        headers=auth_headers,
        json={"category": "不存在的分类"},
    )
    assert invalid_category.status_code == 422

    drafts = client.get("/api/news/drafts?keyword=已编辑", headers=auth_headers)
    item = drafts.get_json()["data"]["items"][0]
    assert item["mediaId"] == "draft-media-id"
    assert item["title"] == "已编辑草稿"
    assert item["contentSyncedAt"] is not None

    content = client.get(
        "/api/news/drafts/draft-media-id/content", headers=auth_headers
    )
    assert content.status_code == 200
    assert content.get_json()["data"]["articles"][0]["content"] == "<p>测试正文</p>"

    cached_content = client.get(
        "/api/news/drafts/draft-media-id/content", headers=auth_headers
    )
    assert cached_content.status_code == 200
    assert post.call_count == 1
    assert get.call_count == 1

    refreshed = client.post("/api/news/drafts/sync", headers=auth_headers)
    assert refreshed.status_code == 200
    assert refreshed.get_json()["data"]["synced"] == 0
    assert refreshed.get_json()["data"]["skippedPublished"] == 1
    refreshed_draft = client.get("/api/news/drafts", headers=auth_headers).get_json()["data"]["items"][0]
    assert refreshed_draft["title"] == "已编辑草稿"
    assert refreshed_draft["contentSyncedAt"] is not None
    assert refreshed_draft["status"] == "已发布"

    refreshed_content = client.get(
        "/api/news/drafts/draft-media-id/content", headers=auth_headers
    )
    assert refreshed_content.status_code == 200
    assert refreshed_content.get_json()["data"]["articles"][0]["content"] == "<p>测试正文</p>"
    assert post.call_count == 2
    assert all(
        call.args[0].endswith("/cgi-bin/draft/batchget")
        for call in post.call_args_list
    )

    reverted = client.patch(
        "/api/news/drafts/draft-media-id",
        headers=auth_headers,
        json={"status": "草稿"},
    )
    assert reverted.status_code == 200
    reverted_category = client.get(
        f"/api/news/categories/{category_id}", headers=auth_headers
    ).get_json()["data"]
    assert reverted_category["count"] == 0
