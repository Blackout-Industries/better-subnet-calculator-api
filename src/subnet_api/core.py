from __future__ import annotations

import ipaddress
from ipaddress import IPv4Network
from typing import Any


def subnet_info(network: IPv4Network) -> dict[str, Any]:
    prefix = network.prefixlen
    total = network.num_addresses

    if prefix == 32:
        # RFC: a /32 is a single host. No broadcast, host range is the address itself.
        first_host = str(network.network_address)
        last_host = str(network.network_address)
        broadcast = str(network.broadcast_address)
        usable = 1
    elif prefix == 31:
        # RFC 3021: /31 has 2 usable hosts, no network/broadcast distinction.
        first_host = str(network.network_address)
        last_host = str(network.broadcast_address)
        broadcast = str(network.broadcast_address)
        usable = 2
    elif prefix == 0:
        first_host = str(network.network_address + 1)
        last_host = str(network.broadcast_address - 1)
        broadcast = str(network.broadcast_address)
        usable = max(total - 2, 0)
    else:
        first_host = str(network.network_address + 1)
        last_host = str(network.broadcast_address - 1)
        broadcast = str(network.broadcast_address)
        usable = max(total - 2, 0)

    return {
        "cidr": str(network),
        "network": str(network.network_address),
        "broadcast": broadcast,
        "netmask": str(network.netmask),
        "wildcard": str(network.hostmask),
        "prefix": prefix,
        "first_host": first_host,
        "last_host": last_host,
        "total_addresses": total,
        "usable_hosts": usable,
        "is_private": network.is_private,
    }


def subdivide(
    parent: IPv4Network,
    *,
    target_prefix: int | None = None,
    count: int | None = None,
) -> list[IPv4Network]:
    if (target_prefix is None) == (count is None):
        raise ValueError("exactly one of target_prefix or count must be provided")

    if target_prefix is not None:
        if not 0 <= target_prefix <= 32:
            raise ValueError("target_prefix must be between 0 and 32")
        if target_prefix < parent.prefixlen:
            raise ValueError("target_prefix must be >= parent prefix")
        children = list(parent.subnets(new_prefix=target_prefix))
    else:
        assert count is not None
        if count < 1:
            raise ValueError("count must be >= 1")
        if count & (count - 1) != 0:
            raise ValueError("count must be a power of two")
        max_count = 1 << (32 - parent.prefixlen)
        if count > max_count:
            raise ValueError(f"count {count} exceeds parent capacity {max_count}")
        prefix_diff = count.bit_length() - 1
        new_prefix = parent.prefixlen + prefix_diff
        if new_prefix > 32:
            raise ValueError("count too large for parent")
        children = list(parent.subnets(prefixlen_diff=prefix_diff))

    return sorted(children, key=lambda n: int(n.network_address))


def free_blocks(
    parent: IPv4Network,
    allocated: list[IPv4Network],
) -> list[IPv4Network]:
    for child in allocated:
        if not child.subnet_of(parent):
            raise ValueError(f"allocated block {child} is not inside parent {parent}")

    sorted_alloc = sorted(allocated, key=lambda n: int(n.network_address))
    for i in range(len(sorted_alloc) - 1):
        a, b = sorted_alloc[i], sorted_alloc[i + 1]
        if a.broadcast_address >= b.network_address:
            raise ValueError(f"allocated blocks overlap: {a} and {b}")

    free: list[IPv4Network] = [parent]
    for child in sorted_alloc:
        new_free: list[IPv4Network] = []
        for block in free:
            if child.subnet_of(block):
                new_free.extend(block.address_exclude(child))
            else:
                new_free.append(block)
        free = new_free

    return sorted(free, key=lambda n: int(n.network_address))


def overlap_pairs(networks: list[IPv4Network]) -> list[tuple[IPv4Network, IPv4Network]]:
    pairs: list[tuple[IPv4Network, IPv4Network]] = []
    n = len(networks)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = networks[i], networks[j]
            if a.overlaps(b):
                ordered = tuple(
                    sorted((a, b), key=lambda x: (int(x.network_address), x.prefixlen))
                )
                pairs.append((ordered[0], ordered[1]))

    pairs.sort(
        key=lambda p: (
            int(p[0].network_address),
            p[0].prefixlen,
            int(p[1].network_address),
            p[1].prefixlen,
        )
    )
    return pairs


def summarize(networks: list[IPv4Network]) -> list[IPv4Network]:
    return list(ipaddress.collapse_addresses(networks))
