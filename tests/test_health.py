from __future__ import annotations

import json

from fastapi.testclient import TestClient


class TestHealthz:
    def test_returns_ok_only(self, client: TestClient) -> None:
        resp = client.get("/healthz")
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"status": "ok"}
        assert set(body.keys()) == {"status"}


class TestRoot:
    def test_redirect_to_docs(self, client: TestClient) -> None:
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 307
        assert resp.headers["location"] == "/docs"


class TestDocs:
    def test_swagger_html(self, client: TestClient) -> None:
        resp = client.get("/docs")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")

    def test_redoc_html(self, client: TestClient) -> None:
        resp = client.get("/redoc")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")


class TestOpenApiJson:
    def test_returns_json_with_required_keys(self, client: TestClient) -> None:
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        body = json.loads(resp.text)
        assert isinstance(body, dict)
        assert "openapi" in body
        assert "info" in body
        assert "paths" in body


class TestHttpMethods:
    def test_calculate_get_405(self, client: TestClient) -> None:
        resp = client.get("/v1/calculate")
        assert resp.status_code == 405


class TestUnknownPath:
    def test_404_returns_a_status(self, client: TestClient) -> None:
        resp = client.get("/this-does-not-exist")
        assert resp.status_code == 404
