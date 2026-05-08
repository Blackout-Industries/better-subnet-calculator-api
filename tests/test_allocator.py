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
