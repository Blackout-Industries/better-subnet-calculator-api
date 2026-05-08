from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def schema(client: TestClient) -> dict[str, Any]:
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    return resp.json()


V1_PATHS = [
    "/v1/calculate",
    "/v1/subdivide",
    "/v1/free",
    "/v1/allocate",
    "/v1/overlap",
]


class TestOpenApiPaths:
    def test_all_v1_paths_present(self, schema: dict[str, Any]) -> None:
        paths = schema["paths"]
        for p in V1_PATHS:
            assert p in paths, f"missing path {p}"

    def test_healthz_excluded_from_schema(self, schema: dict[str, Any]) -> None:
        assert "/healthz" not in schema["paths"]

    def test_root_excluded_from_schema(self, schema: dict[str, Any]) -> None:
        assert "/" not in schema["paths"]


class TestOpenApiOperations:
    @pytest.mark.parametrize("path", V1_PATHS)
    def test_post_method_exists(self, schema: dict[str, Any], path: str) -> None:
        assert "post" in schema["paths"][path]

    @pytest.mark.parametrize("path", V1_PATHS)
    def test_request_body_required(self, schema: dict[str, Any], path: str) -> None:
        op = schema["paths"][path]["post"]
        assert "requestBody" in op
        assert op["requestBody"].get("required") is True
        content = op["requestBody"]["content"]
        assert "application/json" in content
        assert "schema" in content["application/json"]

    @pytest.mark.parametrize("path", V1_PATHS)
    def test_200_response_with_json_schema(
        self, schema: dict[str, Any], path: str
    ) -> None:
        op = schema["paths"][path]["post"]
        responses = op["responses"]
        assert "200" in responses
        ok = responses["200"]
        content = ok.get("content", {})
        assert "application/json" in content
        assert "schema" in content["application/json"]


class TestOpenApiComponents:
    def test_expected_component_names_present(self, schema: dict[str, Any]) -> None:
        components = schema.get("components", {}).get("schemas", {})
        expected = {
            "SubnetInfo",
            "CalculateRequest",
            "CalculateResponse",
            "SubdivideRequest",
            "SubdivideResponse",
            "FreeRequest",
            "FreeResponse",
            "AllocateRequest",
            "AllocateResponse",
            "AllocationItem",
            "AssignedAllocation",
            "OverlapRequest",
            "OverlapResponse",
            "OverlapPair",
        }
        missing = expected - set(components.keys())
        assert not missing, f"expected schema components missing: {missing}"


class TestOpenApiInfo:
    def test_info_block(self, schema: dict[str, Any]) -> None:
        info = schema["info"]
        assert "title" in info
        assert "version" in info
