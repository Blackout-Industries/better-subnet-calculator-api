from __future__ import annotations


class TestHealthz:
    def test_returns_ok(self, client):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestRoot:
    def test_redirects_to_docs(self, client):
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 307
        assert resp.headers["location"] == "/docs"


class TestCalculate:
    def test_happy(self, client):
        resp = client.post("/v1/calculate", json={"cidr": "10.0.0.0/24"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["subnet"]["cidr"] == "10.0.0.0/24"
        assert body["subnet"]["broadcast"] == "10.0.0.255"
        assert body["subnet"]["usable_hosts"] == 254

    def test_bad_cidr(self, client):
        resp = client.post("/v1/calculate", json={"cidr": "not-a-cidr"})
        assert resp.status_code == 422
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] in {"INVALID_INPUT", "INVALID_VALUE"}
        assert "message" in body["error"]
        assert "field" in body["error"]

    def test_host_bits_set_rejected(self, client):
        resp = client.post("/v1/calculate", json={"cidr": "10.0.0.5/24"})
        assert resp.status_code == 422
        assert "error" in resp.json()


class TestSubdivide:
    def test_with_count(self, client):
        resp = client.post(
            "/v1/subdivide",
            json={"cidr": "10.0.0.0/24", "count": 4},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["children"]) == 4
        assert body["children"][0]["cidr"] == "10.0.0.0/26"

    def test_with_target_prefix(self, client):
        resp = client.post(
            "/v1/subdivide",
            json={"cidr": "10.0.0.0/24", "target_prefix": 26},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["children"]) == 4
        assert body["children"][-1]["cidr"] == "10.0.0.192/26"

    def test_both_set_rejected(self, client):
        resp = client.post(
            "/v1/subdivide",
            json={"cidr": "10.0.0.0/24", "count": 4, "target_prefix": 26},
        )
        assert resp.status_code == 422
        assert "error" in resp.json()

    def test_neither_set_rejected(self, client):
        resp = client.post("/v1/subdivide", json={"cidr": "10.0.0.0/24"})
        assert resp.status_code == 422
        assert "error" in resp.json()


class TestFree:
    def test_no_overlap(self, client):
        resp = client.post(
            "/v1/free",
            json={
                "parent": "10.0.0.0/16",
                "allocated": ["10.0.0.0/24", "10.0.5.0/24"],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["parent"]["cidr"] == "10.0.0.0/16"
        assert len(body["allocated"]) == 2
        assert len(body["free"]) > 0
        assert 0 < body["utilization"] < 1

    def test_overlap_returns_400(self, client):
        resp = client.post(
            "/v1/free",
            json={
                "parent": "10.0.0.0/16",
                "allocated": ["10.0.0.0/24", "10.0.0.0/25"],
            },
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "OVERLAPPING_ALLOCATIONS"
        assert body["error"]["field"] == "allocated"

    def test_outside_parent_returns_400(self, client):
        resp = client.post(
            "/v1/free",
            json={
                "parent": "10.0.0.0/16",
                "allocated": ["10.1.0.0/24"],
            },
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "ALLOCATION_OUTSIDE_PARENT"

    def test_no_allocations(self, client):
        resp = client.post(
            "/v1/free",
            json={"parent": "10.0.0.0/24", "allocated": []},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["utilization"] == 0.0
        assert len(body["free"]) == 1
        assert body["free"][0]["cidr"] == "10.0.0.0/24"


class TestAllocate:
    def test_brd_example(self, client):
        resp = client.post(
            "/v1/allocate",
            json={
                "parent": "10.0.0.0/16",
                "allocated": ["10.0.0.0/24"],
                "requests": [
                    {"name": "web", "prefix": 24},
                    {"name": "app", "prefix": 25},
                    {"name": "db", "prefix": 27},
                ],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["parent"]["cidr"] == "10.0.0.0/16"
        assert len(body["assigned"]) == 3
        names = [a["name"] for a in body["assigned"]]
        assert names == ["web", "app", "db"]
        for item in body["assigned"]:
            assert item["subnet"] is not None

    def test_duplicate_names_400(self, client):
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
        assert body["error"]["code"] == "DUPLICATE_NAME"

    def test_unassigned_returned(self, client):
        resp = client.post(
            "/v1/allocate",
            json={
                "parent": "10.0.0.0/28",
                "allocated": [],
                "requests": [
                    {"name": "a", "prefix": 29},
                    {"name": "b", "prefix": 29},
                    {"name": "c", "prefix": 29},
                ],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "c" in body["unassigned"]


class TestOverlap:
    def test_happy(self, client):
        resp = client.post(
            "/v1/overlap",
            json={"cidrs": ["10.0.0.0/24", "10.0.0.128/25", "10.1.0.0/16"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["overlaps"]) == 1
        pair = body["overlaps"][0]
        assert {pair["a"], pair["b"]} == {"10.0.0.0/24", "10.0.0.128/25"}
        assert "10.1.0.0/16" in body["summarized"]

    def test_no_overlaps(self, client):
        resp = client.post(
            "/v1/overlap",
            json={"cidrs": ["10.0.0.0/24", "10.1.0.0/24"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["overlaps"] == []


class TestErrorEnvelope:
    def test_404_does_not_use_envelope(self, client):
        # Sanity check: unrelated 404 keeps FastAPI's default shape.
        resp = client.get("/v1/does-not-exist")
        assert resp.status_code == 404

    def test_4xx_validation_uses_envelope(self, client):
        resp = client.post("/v1/calculate", json={})
        assert resp.status_code == 422
        body = resp.json()
        assert set(body.keys()) == {"error"}
        assert set(body["error"].keys()) == {"code", "message", "field"}
