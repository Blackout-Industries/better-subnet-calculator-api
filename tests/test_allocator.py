from __future__ import annotations

from ipaddress import IPv4Network

import pytest

from subnet_api.allocator import AllocationRequest, allocate_vlsm


def _net(s: str) -> IPv4Network:
    return IPv4Network(s)


class TestAllocateVlsm:
    def test_all_fit(self):
        parent = _net("10.0.0.0/24")
        result = allocate_vlsm(
            parent,
            allocated=[],
            requests=[
                AllocationRequest("web", 26),
                AllocationRequest("app", 26),
                AllocationRequest("db", 27),
            ],
        )
        assert result.unassigned == []
        assert all(item.subnet is not None for item in result.assigned)
        names = [item.name for item in result.assigned]
        assert names == ["web", "app", "db"]

    def test_some_dont_fit(self):
        parent = _net("10.0.0.0/28")
        result = allocate_vlsm(
            parent,
            allocated=[],
            requests=[
                AllocationRequest("a", 29),
                AllocationRequest("b", 29),
                AllocationRequest("c", 29),
            ],
        )
        assert "c" in result.unassigned
        assert len(result.unassigned) == 1
        assigned_subnets = [i.subnet for i in result.assigned if i.subnet is not None]
        assert len(assigned_subnets) == 2

    def test_best_fit_decreasing_packing(self):
        parent = _net("10.0.0.0/24")
        requests = [
            AllocationRequest("a", 26),
            AllocationRequest("b", 26),
            AllocationRequest("c", 26),
            AllocationRequest("d", 27),
            AllocationRequest("e", 27),
        ]
        result = allocate_vlsm(parent, allocated=[], requests=requests)
        assert result.unassigned == []
        for item in result.assigned:
            assert item.subnet is not None
        # No two assignments should overlap.
        nets = [item.subnet for item in result.assigned if item.subnet is not None]
        for i, a in enumerate(nets):
            for b in nets[i + 1 :]:
                assert not a.overlaps(b)

    def test_preserves_input_order(self):
        parent = _net("10.0.0.0/24")
        result = allocate_vlsm(
            parent,
            allocated=[],
            requests=[
                AllocationRequest("small", 28),
                AllocationRequest("big", 25),
                AllocationRequest("mid", 27),
            ],
        )
        assert [a.name for a in result.assigned] == ["small", "big", "mid"]

    def test_duplicate_names_raise(self):
        parent = _net("10.0.0.0/24")
        with pytest.raises(ValueError, match="duplicate"):
            allocate_vlsm(
                parent,
                allocated=[],
                requests=[
                    AllocationRequest("dup", 26),
                    AllocationRequest("dup", 27),
                ],
            )

    def test_prefix_smaller_than_parent_raises(self):
        parent = _net("10.0.0.0/24")
        with pytest.raises(ValueError):
            allocate_vlsm(
                parent,
                allocated=[],
                requests=[AllocationRequest("too-big", 16)],
            )

    def test_prefix_out_of_range_raises(self):
        parent = _net("10.0.0.0/24")
        with pytest.raises(ValueError):
            allocate_vlsm(
                parent,
                allocated=[],
                requests=[AllocationRequest("bad", 33)],
            )

    def test_with_existing_allocations(self):
        parent = _net("10.0.0.0/16")
        existing = [_net("10.0.0.0/24")]
        result = allocate_vlsm(
            parent,
            allocated=existing,
            requests=[AllocationRequest("new", 24)],
        )
        assert result.unassigned == []
        assert result.assigned[0].subnet is not None
        assert result.assigned[0].subnet != _net("10.0.0.0/24")
        assert result.assigned[0].subnet.subnet_of(parent)

    def test_empty_name_raises(self):
        parent = _net("10.0.0.0/24")
        with pytest.raises(ValueError):
            allocate_vlsm(
                parent,
                allocated=[],
                requests=[AllocationRequest("", 26)],
            )

    def test_tuple_requests(self):
        parent = _net("10.0.0.0/24")
        result = allocate_vlsm(parent, allocated=[], requests=[("web", 25), ("db", 26)])
        assert result.unassigned == []
        assert [a.name for a in result.assigned] == ["web", "db"]


class TestAllocateVlsmStress:
    def test_50_mixed_requests_all_fit(self):
        parent = _net("10.0.0.0/16")
        requests = [AllocationRequest(name=f"r{i}", prefix=24) for i in range(50)]
        total_request_area = sum(2 ** (32 - r.prefix) for r in requests)
        assert total_request_area <= parent.num_addresses

        result = allocate_vlsm(parent, allocated=[], requests=requests)
        assert result.unassigned == []
        subnets = [a.subnet for a in result.assigned]
        assert all(s is not None for s in subnets)
        for i, a in enumerate(subnets):
            for b in subnets[i + 1 :]:
                assert a is not None and b is not None
                assert not a.overlaps(b)

    def test_failure_ordering_preserves_input_order(self):
        parent = _net("10.0.0.0/26")
        requests = [
            AllocationRequest(name="big", prefix=26),
            AllocationRequest(name="next", prefix=27),
            AllocationRequest(name="last", prefix=27),
        ]
        result = allocate_vlsm(parent, allocated=[], requests=requests)
        assert result.unassigned == ["next", "last"]

    def test_254_slash_32_from_slash_24(self):
        parent = _net("10.0.0.0/24")
        requests = [AllocationRequest(name=f"h{i}", prefix=32) for i in range(254)]
        result = allocate_vlsm(parent, allocated=[], requests=requests)
        assert result.unassigned == []
        subnets = [a.subnet for a in result.assigned]
        assert all(s is not None and s.prefixlen == 32 for s in subnets)
        ints = sorted(int(s.network_address) for s in subnets if s is not None)
        assert len(set(ints)) == 254

    def test_fully_allocated_parent_yields_unassigned(self):
        parent = _net("10.0.0.0/24")
        result = allocate_vlsm(
            parent,
            allocated=[parent],
            requests=[AllocationRequest(name="x", prefix=26)],
        )
        assert result.unassigned == ["x"]
        assert result.assigned[0].subnet is None

    def test_best_fit_picks_smallest_available_block(self):
        parent = _net("10.0.0.0/24")
        result = allocate_vlsm(
            parent,
            allocated=[_net("10.0.0.0/26")],
            requests=[AllocationRequest(name="small", prefix=27)],
        )
        chosen = result.assigned[0].subnet
        assert chosen is not None
        # Free blocks after removing 10.0.0.0/26 are 10.0.0.64/26 and 10.0.0.128/25.
        # Best-fit should pick the smaller block (10.0.0.64/26), splitting into a /27
        # rooted at 10.0.0.64.
        assert chosen == _net("10.0.0.64/27")
