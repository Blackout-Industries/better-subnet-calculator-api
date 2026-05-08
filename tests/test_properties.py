from __future__ import annotations

import random
from ipaddress import IPv4Network

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from hypothesis.strategies import composite

from subnet_api.allocator import AllocationRequest, allocate_vlsm
from subnet_api.core import (
    free_blocks,
    overlap_pairs,
    subdivide,
    subnet_info,
    summarize,
)


@composite
def parents(draw: st.DrawFn, min_prefix: int = 8, max_prefix: int = 24) -> IPv4Network:
    prefix = draw(st.integers(min_value=min_prefix, max_value=max_prefix))
    host_bits = 32 - prefix
    if host_bits == 32:
        net_int = 0
    else:
        max_block_index = (1 << prefix) - 1
        block_index = draw(st.integers(min_value=0, max_value=max_block_index))
        net_int = block_index << host_bits
    return IPv4Network((net_int, prefix))


@composite
def networks(draw: st.DrawFn, min_prefix: int = 0, max_prefix: int = 32) -> IPv4Network:
    prefix = draw(st.integers(min_value=min_prefix, max_value=max_prefix))
    host_bits = 32 - prefix
    if host_bits == 32:
        net_int = 0
    else:
        max_block_index = (1 << prefix) - 1
        block_index = draw(st.integers(min_value=0, max_value=max_block_index))
        net_int = block_index << host_bits
    return IPv4Network((net_int, prefix))


@composite
def parent_with_alloc_subset(
    draw: st.DrawFn,
    parent_min_prefix: int = 16,
    parent_max_prefix: int = 22,
    max_extra_prefix: int = 6,
) -> tuple[IPv4Network, list[IPv4Network]]:
    parent = draw(parents(min_prefix=parent_min_prefix, max_prefix=parent_max_prefix))
    extra = draw(st.integers(min_value=1, max_value=max_extra_prefix))
    target_prefix = min(parent.prefixlen + extra, 32)
    children = list(parent.subnets(new_prefix=target_prefix))
    seed = draw(st.integers(min_value=0, max_value=2**31 - 1))
    rng = random.Random(seed)
    keep_count = draw(st.integers(min_value=0, max_value=len(children)))
    chosen = rng.sample(children, k=keep_count)
    chosen.sort(key=lambda n: int(n.network_address))
    return parent, chosen


class TestSubnetInfoProperties:
    @given(networks())
    def test_cidr_round_trip(self, network: IPv4Network) -> None:
        info = subnet_info(network)
        assert IPv4Network(info["cidr"]) == network

    @given(networks())
    def test_total_addresses_matches_prefix(self, network: IPv4Network) -> None:
        info = subnet_info(network)
        assert info["total_addresses"] == 2 ** (32 - info["prefix"])

    @given(networks())
    def test_usable_hosts_bound(self, network: IPv4Network) -> None:
        info = subnet_info(network)
        assert info["usable_hosts"] <= info["total_addresses"]

    @given(networks(max_prefix=30))
    def test_usable_hosts_normal_prefixes(self, network: IPv4Network) -> None:
        info = subnet_info(network)
        assert info["usable_hosts"] == info["total_addresses"] - 2

    @given(networks(min_prefix=31, max_prefix=31))
    def test_slash_31_rfc3021(self, network: IPv4Network) -> None:
        info = subnet_info(network)
        assert info["total_addresses"] == 2
        assert info["usable_hosts"] == 2

    @given(networks(min_prefix=32, max_prefix=32))
    def test_slash_32_host_route(self, network: IPv4Network) -> None:
        info = subnet_info(network)
        assert info["total_addresses"] == 1
        assert info["usable_hosts"] == 1
        assert info["first_host"] == info["last_host"] == info["network"]


class TestSubdivideProperties:
    @given(parents(min_prefix=8, max_prefix=20), st.integers(min_value=0, max_value=8))
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None, max_examples=100)
    def test_target_prefix_count_and_coverage(
        self, parent: IPv4Network, extra: int
    ) -> None:
        target = min(parent.prefixlen + extra, 32)
        children = subdivide(parent, target_prefix=target)

        assert len(children) == 2 ** (target - parent.prefixlen)

        total = sum(c.num_addresses for c in children)
        assert total == parent.num_addresses

        for c in children:
            assert c.subnet_of(parent)
            assert c.prefixlen == target

        for i in range(len(children) - 1):
            a = children[i]
            b = children[i + 1]
            assert int(a.broadcast_address) + 1 == int(b.network_address)

        first = children[0]
        last = children[-1]
        assert int(first.network_address) == int(parent.network_address)
        assert int(last.broadcast_address) == int(parent.broadcast_address)

    @given(parents(min_prefix=8, max_prefix=20), st.integers(min_value=0, max_value=6))
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None, max_examples=100)
    def test_count_form_equally_sized(self, parent: IPv4Network, k: int) -> None:
        count = 1 << k
        assume(parent.prefixlen + k <= 32)
        children = subdivide(parent, count=count)
        assert len(children) == count
        sizes = {c.num_addresses for c in children}
        assert len(sizes) == 1
        assert sum(c.num_addresses for c in children) == parent.num_addresses


class TestFreeBlocksProperties:
    @given(parents())
    def test_no_allocations_returns_parent(self, parent: IPv4Network) -> None:
        assert free_blocks(parent, []) == [parent]

    @given(parents())
    def test_full_parent_allocated_returns_empty(self, parent: IPv4Network) -> None:
        assert free_blocks(parent, [parent]) == []

    @given(parent_with_alloc_subset())
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None, max_examples=75)
    def test_free_plus_allocated_covers_parent(
        self, data: tuple[IPv4Network, list[IPv4Network]]
    ) -> None:
        parent, allocated = data
        free = free_blocks(parent, allocated)

        all_blocks = sorted(
            [*allocated, *free], key=lambda n: int(n.network_address)
        )
        assert int(all_blocks[0].network_address) == int(parent.network_address)
        assert int(all_blocks[-1].broadcast_address) == int(parent.broadcast_address)
        for i in range(len(all_blocks) - 1):
            a = all_blocks[i]
            b = all_blocks[i + 1]
            assert int(a.broadcast_address) + 1 == int(b.network_address)

        total = sum(b.num_addresses for b in all_blocks)
        assert total == parent.num_addresses

        for f in free:
            for a in allocated:
                assert not f.overlaps(a)


class TestSummarizeProperties:
    @given(st.lists(networks(min_prefix=20, max_prefix=30), min_size=0, max_size=15))
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None, max_examples=75)
    def test_idempotent(self, nets: list[IPv4Network]) -> None:
        once = summarize(nets)
        twice = summarize(once)
        assert once == twice

    @given(st.lists(networks(min_prefix=24, max_prefix=30), min_size=0, max_size=15))
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None, max_examples=50)
    def test_preserves_coverage(self, nets: list[IPv4Network]) -> None:
        result = summarize(nets)

        input_addrs: set[int] = set()
        for n in nets:
            input_addrs.update(range(int(n.network_address), int(n.broadcast_address) + 1))

        output_addrs: set[int] = set()
        for n in result:
            output_addrs.update(range(int(n.network_address), int(n.broadcast_address) + 1))

        assert input_addrs == output_addrs


class TestOverlapPairsProperties:
    @given(st.lists(networks(min_prefix=20, max_prefix=28), min_size=0, max_size=10))
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None, max_examples=75)
    def test_symmetric_under_reorder(self, nets: list[IPv4Network]) -> None:
        forward = overlap_pairs(nets)
        backward = overlap_pairs(list(reversed(nets)))
        assert forward == backward


class TestAllocateVlsmProperties:
    @given(parent_with_alloc_subset(parent_min_prefix=16, parent_max_prefix=20, max_extra_prefix=4))
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None, max_examples=50)
    def test_invariants(self, data: tuple[IPv4Network, list[IPv4Network]]) -> None:
        parent, allocated = data
        request_prefix = min(parent.prefixlen + 5, 32)
        requests = [
            AllocationRequest(name=f"r{i}", prefix=request_prefix) for i in range(3)
        ]

        result = allocate_vlsm(parent, allocated, requests)

        assigned_subnets = [
            item.subnet for item in result.assigned if item.subnet is not None
        ]

        for s in assigned_subnets:
            assert s.subnet_of(parent)
            for a in allocated:
                assert not s.overlaps(a)

        for i in range(len(assigned_subnets)):
            for j in range(i + 1, len(assigned_subnets)):
                assert not assigned_subnets[i].overlaps(assigned_subnets[j])

        already_alloc_total = sum(a.num_addresses for a in allocated)
        assigned_total = sum(s.num_addresses for s in assigned_subnets)
        free_after_total = sum(f.num_addresses for f in result.free_after)

        assert assigned_total + free_after_total == parent.num_addresses - already_alloc_total
