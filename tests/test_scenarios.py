from __future__ import annotations

from ipaddress import IPv4Network

from fastapi.testclient import TestClient


class TestScenarioVpcSizing:
    def test_mixed_vlsm_then_round_trip_to_free(self, client: TestClient) -> None:
        parent = "10.0.0.0/16"
        requests = [
            {"name": "pub-a", "prefix": 24},
            {"name": "pub-b", "prefix": 24},
            {"name": "pub-c", "prefix": 24},
            {"name": "priv-a", "prefix": 22},
            {"name": "priv-b", "prefix": 22},
            {"name": "priv-c", "prefix": 22},
            {"name": "db-a", "prefix": 27},
            {"name": "db-b", "prefix": 27},
            {"name": "db-c", "prefix": 27},
        ]
        resp = client.post(
            "/v1/allocate",
            json={"parent": parent, "allocated": [], "requests": requests},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["unassigned"] == []
        assert len(body["assigned"]) == 9
        assigned_cidrs = [a["subnet"]["cidr"] for a in body["assigned"]]
        free_after_first = {f["cidr"] for f in body["free_after"]}

        free_resp = client.post(
            "/v1/free",
            json={"parent": parent, "allocated": assigned_cidrs},
        )
        assert free_resp.status_code == 200
        free_body = free_resp.json()
        free_from_free = {f["cidr"] for f in free_body["free"]}
        assert free_from_free == free_after_first


class TestScenarioDriftDetection:
    def test_overlap_and_summarize(self, client: TestClient) -> None:
        cidrs = [
            "10.0.0.0/24",
            "10.0.0.128/25",
            "10.1.0.0/16",
        ]
        resp = client.post("/v1/overlap", json={"cidrs": cidrs})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["overlaps"]) == 1
        pair = body["overlaps"][0]
        assert {pair["a"], pair["b"]} == {"10.0.0.0/24", "10.0.0.128/25"}
        assert "10.1.0.0/16" in body["summarized"]
        assert "10.0.0.0/24" in body["summarized"]


class TestScenarioGreedyChase:
    def test_step_by_step_allocations(self, client: TestClient) -> None:
        parent = "10.0.0.0/16"
        parent_total = 2**16
        already: list[str] = []

        for prefix in (24, 24, 22):
            resp = client.post(
                "/v1/allocate",
                json={
                    "parent": parent,
                    "allocated": already,
                    "requests": [{"name": f"r-{prefix}", "prefix": prefix}],
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["unassigned"] == []
            assigned = body["assigned"][0]["subnet"]["cidr"]
            already.append(assigned)

            free_resp = client.post(
                "/v1/free",
                json={"parent": parent, "allocated": already},
            )
            assert free_resp.status_code == 200
            free_body = free_resp.json()
            allocated_total = sum(
                IPv4Network(c).num_addresses for c in already
            )
            free_total = sum(f["total_addresses"] for f in free_body["free"])
            assert allocated_total + free_total == parent_total


class TestScenarioFailureMode:
    def test_request_larger_than_parent(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/allocate",
            json={
                "parent": "10.0.0.0/24",
                "allocated": [],
                "requests": [{"name": "huge", "prefix": 16}],
            },
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "INVALID_ALLOCATE"
        assert body["error"]["field"] == "requests"


class TestScenarioSubdivideThenMerge:
    def test_full_coverage(self, client: TestClient) -> None:
        parent = "10.0.0.0/24"
        sub_resp = client.post(
            "/v1/subdivide",
            json={"cidr": parent, "target_prefix": 27},
        )
        assert sub_resp.status_code == 200
        children = [c["cidr"] for c in sub_resp.json()["children"]]
        assert len(children) == 8

        free_resp = client.post(
            "/v1/free",
            json={"parent": parent, "allocated": children},
        )
        assert free_resp.status_code == 200
        body = free_resp.json()
        assert body["free"] == []
        assert body["utilization"] == 1.0
