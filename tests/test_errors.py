from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def _assert_envelope(body: dict[str, Any]) -> None:
    assert set(body.keys()) == {"error"}
    err = body["error"]
    assert set(err.keys()) == {"code", "message", "field"}
    assert isinstance(err["code"], str)
    assert isinstance(err["message"], str)
    assert err["field"] is None or isinstance(err["field"], str)


class TestApiErrorEnvelope:
    def test_subdivide_invalid_envelope(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/subdivide",
            json={"cidr": "10.0.0.0/24", "target_prefix": 16},
        )
        assert resp.status_code == 400
        body = resp.json()
        _assert_envelope(body)
        assert body["error"]["code"] == "INVALID_SUBDIVIDE"
        assert body["error"]["field"] == "cidr"

    def test_free_overlap_envelope(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/free",
            json={
                "parent": "10.0.0.0/16",
                "allocated": ["10.0.0.0/24", "10.0.0.0/25"],
            },
        )
        assert resp.status_code == 400
        body = resp.json()
        _assert_envelope(body)
        assert body["error"]["code"] == "OVERLAPPING_ALLOCATIONS"
        assert body["error"]["field"] == "allocated"

    def test_free_outside_parent_envelope(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/free",
            json={"parent": "10.0.0.0/16", "allocated": ["10.1.0.0/24"]},
        )
        assert resp.status_code == 400
        body = resp.json()
        _assert_envelope(body)
        assert body["error"]["code"] == "ALLOCATION_OUTSIDE_PARENT"

    def test_allocate_duplicate_name_envelope(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/allocate",
            json={
                "parent": "10.0.0.0/24",
                "allocated": [],
                "requests": [
                    {"name": "x", "prefix": 26},
                    {"name": "x", "prefix": 27},
                ],
            },
        )
        assert resp.status_code == 400
        body = resp.json()
        _assert_envelope(body)
        assert body["error"]["code"] == "DUPLICATE_NAME"

    def test_allocate_overlap_envelope(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/allocate",
            json={
                "parent": "10.0.0.0/16",
                "allocated": ["10.0.0.0/24", "10.0.0.0/25"],
                "requests": [{"name": "x", "prefix": 24}],
            },
        )
        assert resp.status_code == 400
        body = resp.json()
        _assert_envelope(body)
        assert body["error"]["code"] == "OVERLAPPING_ALLOCATIONS"

    def test_allocate_outside_parent_envelope(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/allocate",
            json={
                "parent": "10.0.0.0/16",
                "allocated": ["10.1.0.0/24"],
                "requests": [{"name": "x", "prefix": 24}],
            },
        )
        assert resp.status_code == 400
        body = resp.json()
        _assert_envelope(body)
        assert body["error"]["code"] == "ALLOCATION_OUTSIDE_PARENT"


class TestValidationErrorEnvelope:
    def test_calculate_string_body(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/calculate",
            content='"a string instead of an object"',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422
        _assert_envelope(resp.json())

    def test_calculate_missing_field(self, client: TestClient) -> None:
        resp = client.post("/v1/calculate", json={})
        assert resp.status_code == 422
        body = resp.json()
        _assert_envelope(body)
        assert body["error"]["code"] in {"INVALID_INPUT", "INVALID_VALUE"}

    def test_calculate_wrong_type(self, client: TestClient) -> None:
        resp = client.post("/v1/calculate", json={"cidr": 1234})
        assert resp.status_code == 422
        _assert_envelope(resp.json())

    def test_subdivide_missing_field(self, client: TestClient) -> None:
        resp = client.post("/v1/subdivide", json={})
        assert resp.status_code == 422
        _assert_envelope(resp.json())

    def test_free_missing_parent(self, client: TestClient) -> None:
        resp = client.post("/v1/free", json={"allocated": []})
        assert resp.status_code == 422
        _assert_envelope(resp.json())

    def test_allocate_missing_requests(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/allocate",
            json={"parent": "10.0.0.0/16", "allocated": []},
        )
        assert resp.status_code == 422
        _assert_envelope(resp.json())

    def test_overlap_missing_cidrs(self, client: TestClient) -> None:
        resp = client.post("/v1/overlap", json={})
        assert resp.status_code == 422
        _assert_envelope(resp.json())

    def test_extra_field_envelope(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/calculate",
            json={"cidr": "10.0.0.0/24", "extra": "nope"},
        )
        assert resp.status_code == 422
        _assert_envelope(resp.json())

    def test_field_is_string_or_null(self, client: TestClient) -> None:
        resp = client.post("/v1/calculate", json={"cidr": "garbage"})
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["field"] is None or isinstance(body["error"]["field"], str)


class TestApiErrorClass:
    def test_apierror_to_envelope(self) -> None:
        from subnet_api.errors import APIError

        err = APIError(code="X", message="m", field="f", status_code=418)
        env = err.to_envelope()
        assert env == {"error": {"code": "X", "message": "m", "field": "f"}}
        assert err.status_code == 418

    def test_apierror_default_status(self) -> None:
        from subnet_api.errors import APIError

        err = APIError(code="X", message="m")
        assert err.status_code == 400
        assert err.field is None
