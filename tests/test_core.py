from __future__ import annotations

from ipaddress import IPv4Network

import pytest

from subnet_api.core import (
    free_blocks,
    overlap_pairs,
    subdivide,
    subnet_info,
    summarize,
)


class TestSubnetInfo:
    def test_slash_24(self):
        info = subnet_info(IPv4Network("10.0.0.0/24"))
        assert info["cidr"] == "10.0.0.0/24"
        assert info["network"] == "10.0.0.0"
        assert info["broadcast"] == "10.0.0.255"
        assert info["netmask"] == "255.255.255.0"
        assert info["wildcard"] == "0.0.0.255"
        assert info["prefix"] == 24
        assert info["first_host"] == "10.0.0.1"
        assert info["last_host"] == "10.0.0.254"
        assert info["total_addresses"] == 256
        assert info["usable_hosts"] == 254
        assert info["is_private"] is True

    def test_slash_31_rfc3021(self):
        info = subnet_info(IPv4Network("192.168.1.0/31"))
        assert info["total_addresses"] == 2
        assert info["usable_hosts"] == 2
        assert info["first_host"] == "192.168.1.0"
        assert info["last_host"] == "192.168.1.1"

    def test_slash_32_host_route(self):
        info = subnet_info(IPv4Network("8.8.8.8/32"))
        assert info["total_addresses"] == 1
        assert info["usable_hosts"] == 1
        assert info["first_host"] == "8.8.8.8"
        assert info["last_host"] == "8.8.8.8"
        assert info["is_private"] is False

    def test_slash_0(self):
        info = subnet_info(IPv4Network("0.0.0.0/0"))
        assert info["prefix"] == 0
        assert info["total_addresses"] == 2**32
        assert info["usable_hosts"] == 2**32 - 2
        assert info["network"] == "0.0.0.0"
        assert info["broadcast"] == "255.255.255.255"


class TestSubdivide:
    def test_target_prefix_happy(self):
        children = subdivide(IPv4Network("10.0.0.0/24"), target_prefix=26)
        assert children == [
            IPv4Network("10.0.0.0/26"),
            IPv4Network("10.0.0.64/26"),
            IPv4Network("10.0.0.128/26"),
            IPv4Network("10.0.0.192/26"),
        ]

    def test_count_happy(self):
        children = subdivide(IPv4Network("10.0.0.0/24"), count=4)
        assert len(children) == 4
        assert children[0] == IPv4Network("10.0.0.0/26")
        assert children[-1] == IPv4Network("10.0.0.192/26")

    def test_count_one(self):
        children = subdivide(IPv4Network("10.0.0.0/24"), count=1)
        assert children == [IPv4Network("10.0.0.0/24")]

    def test_must_supply_exactly_one(self):
        with pytest.raises(ValueError):
            subdivide(IPv4Network("10.0.0.0/24"))
        with pytest.raises(ValueError):
            subdivide(IPv4Network("10.0.0.0/24"), target_prefix=26, count=4)

    def test_count_must_be_power_of_two(self):
        with pytest.raises(ValueError):
            subdivide(IPv4Network("10.0.0.0/24"), count=3)

    def test_count_too_large(self):
        with pytest.raises(ValueError):
            subdivide(IPv4Network("10.0.0.0/30"), count=16)

    def test_target_prefix_smaller_than_parent(self):
        with pytest.raises(ValueError):
            subdivide(IPv4Network("10.0.0.0/24"), target_prefix=20)

    def test_target_prefix_out_of_range(self):
        with pytest.raises(ValueError):
            subdivide(IPv4Network("10.0.0.0/24"), target_prefix=33)


class TestFreeBlocks:
    def test_no_allocations_returns_parent(self):
        parent = IPv4Network("10.0.0.0/16")
        assert free_blocks(parent, []) == [parent]

    def test_full_coverage_returns_empty(self):
        parent = IPv4Network("10.0.0.0/24")
        result = free_blocks(parent, [IPv4Network("10.0.0.0/24")])
        assert result == []

    def test_middle_gap(self):
        parent = IPv4Network("10.0.0.0/24")
        allocated = [IPv4Network("10.0.0.0/26"), IPv4Network("10.0.0.192/26")]
        result = free_blocks(parent, allocated)
        assert result == [IPv4Network("10.0.0.64/26"), IPv4Network("10.0.0.128/26")]

    def test_edge_gap_high(self):
        parent = IPv4Network("10.0.0.0/24")
        result = free_blocks(parent, [IPv4Network("10.0.0.0/25")])
        assert result == [IPv4Network("10.0.0.128/25")]

    def test_edge_gap_low(self):
        parent = IPv4Network("10.0.0.0/24")
        result = free_blocks(parent, [IPv4Network("10.0.0.128/25")])
        assert result == [IPv4Network("10.0.0.0/25")]

    def test_outside_parent_raises(self):
        parent = IPv4Network("10.0.0.0/24")
        with pytest.raises(ValueError, match="not inside"):
            free_blocks(parent, [IPv4Network("10.1.0.0/24")])

    def test_overlapping_raises(self):
        parent = IPv4Network("10.0.0.0/24")
        with pytest.raises(ValueError, match="overlap"):
            free_blocks(parent, [IPv4Network("10.0.0.0/25"), IPv4Network("10.0.0.0/26")])


class TestOverlapPairs:
    def test_no_overlaps_returns_empty(self):
        nets = [IPv4Network("10.0.0.0/24"), IPv4Network("10.1.0.0/24")]
        assert overlap_pairs(nets) == []

    def test_basic_overlap(self):
        nets = [IPv4Network("10.0.0.0/24"), IPv4Network("10.0.0.128/25")]
        result = overlap_pairs(nets)
        assert result == [(IPv4Network("10.0.0.0/24"), IPv4Network("10.0.0.128/25"))]

    def test_deterministic_ordering(self):
        nets = [
            IPv4Network("10.0.0.128/25"),
            IPv4Network("10.0.0.0/24"),
        ]
        result = overlap_pairs(nets)
        assert result == [(IPv4Network("10.0.0.0/24"), IPv4Network("10.0.0.128/25"))]

    def test_multiple_overlaps_sorted(self):
        nets = [
            IPv4Network("10.0.0.0/24"),
            IPv4Network("10.0.0.0/25"),
            IPv4Network("10.0.0.128/25"),
        ]
        result = overlap_pairs(nets)
        assert len(result) == 2
        assert result == sorted(
            result,
            key=lambda p: (
                int(p[0].network_address),
                p[0].prefixlen,
                int(p[1].network_address),
                p[1].prefixlen,
            ),
        )


class TestSummarize:
    def test_collapses_adjacent(self):
        nets = [IPv4Network("10.0.0.0/25"), IPv4Network("10.0.0.128/25")]
        assert summarize(nets) == [IPv4Network("10.0.0.0/24")]

    def test_leaves_disjoint(self):
        nets = [IPv4Network("10.0.0.0/24"), IPv4Network("10.2.0.0/24")]
        result = summarize(nets)
        assert IPv4Network("10.0.0.0/24") in result
        assert IPv4Network("10.2.0.0/24") in result
        assert len(result) == 2


class TestIsPrivateClassification:
    """Wrapper must agree with stdlib IPv4Network.is_private."""

    @pytest.mark.parametrize(
        "cidr",
        [
            "10.0.0.0/8",
            "10.5.0.0/16",
            "172.16.0.0/12",
            "172.20.0.0/16",
            "192.168.0.0/16",
            "192.168.1.0/24",
            "169.254.0.0/16",
            "127.0.0.0/8",
            "127.0.0.1/32",
            "224.0.0.0/4",
            "255.255.255.255/32",
            "192.0.2.0/24",
            "198.51.100.0/24",
            "203.0.113.0/24",
            "198.18.0.0/15",
            "0.0.0.0/8",
            "8.8.8.0/24",
            "1.1.1.1/32",
        ],
    )
    def test_matches_stdlib(self, cidr: str) -> None:
        net = IPv4Network(cidr)
        info = subnet_info(net)
        assert info["is_private"] == net.is_private


class TestSubdivideBoundary:
    def test_zero_to_one_split(self):
        children = subdivide(IPv4Network("0.0.0.0/0"), target_prefix=1)
        assert children == [
            IPv4Network("0.0.0.0/1"),
            IPv4Network("128.0.0.0/1"),
        ]


class TestFreeBlocksExtra:
    def test_allocated_equal_parent_returns_empty(self):
        parent = IPv4Network("10.0.0.0/24")
        assert free_blocks(parent, [parent]) == []

    def test_allocations_leave_single_host(self):
        parent = IPv4Network("10.0.0.0/30")
        allocated = [
            IPv4Network("10.0.0.0/32"),
            IPv4Network("10.0.0.1/32"),
            IPv4Network("10.0.0.2/32"),
        ]
        result = free_blocks(parent, allocated)
        assert IPv4Network("10.0.0.3/32") in result

    def test_stress_50_random_slash_24s(self):
        import random

        rng = random.Random(42)
        parent = IPv4Network("10.0.0.0/16")
        all_24s = list(parent.subnets(new_prefix=24))
        chosen = rng.sample(all_24s, k=50)
        chosen.sort(key=lambda n: int(n.network_address))

        free = free_blocks(parent, chosen)

        all_blocks = sorted(
            [*chosen, *free], key=lambda n: int(n.network_address)
        )
        total = sum(b.num_addresses for b in all_blocks)
        assert total == parent.num_addresses
        for i in range(len(all_blocks) - 1):
            a, b = all_blocks[i], all_blocks[i + 1]
            assert int(a.broadcast_address) + 1 == int(b.network_address)
