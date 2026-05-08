from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from ipaddress import IPv4Network

from subnet_api.core import free_blocks, subdivide, summarize


@dataclass(frozen=True)
class AllocationRequest:
    name: str
    prefix: int


@dataclass(frozen=True)
class AssignedItem:
    name: str
    subnet: IPv4Network | None


@dataclass(frozen=True)
class AllocationResult:
    assigned: list[AssignedItem]
    unassigned: list[str]
    free_after: list[IPv4Network]


RequestLike = AllocationRequest | tuple[str, int]


def _normalize_requests(
    requests: Sequence[RequestLike],
) -> list[AllocationRequest]:
    normalized: list[AllocationRequest] = []
    for r in requests:
        if isinstance(r, AllocationRequest):
            normalized.append(r)
        else:
            name, prefix = r
            normalized.append(AllocationRequest(name=name, prefix=prefix))
    return normalized


def allocate_vlsm(
    parent: IPv4Network,
    allocated: list[IPv4Network],
    requests: Sequence[RequestLike],
) -> AllocationResult:
    norm = _normalize_requests(requests)

    seen: set[str] = set()
    for r in norm:
        if not r.name:
            raise ValueError("request name must be non-empty")
        if r.name in seen:
            raise ValueError(f"duplicate request name: {r.name}")
        seen.add(r.name)
        if not 0 <= r.prefix <= 32:
            raise ValueError(f"prefix for {r.name} must be in 0..32")
        if r.prefix < parent.prefixlen:
            raise ValueError(
                f"request {r.name} prefix /{r.prefix} cannot be larger than parent /{parent.prefixlen}"
            )

    free: list[IPv4Network] = list(free_blocks(parent, allocated))

    indexed = list(enumerate(norm))
    # Best-fit decreasing: process largest blocks (smallest prefix) first.
    indexed.sort(key=lambda pair: (pair[1].prefix, pair[0]))

    assignments: dict[int, IPv4Network | None] = {i: None for i, _ in indexed}

    for idx, req in indexed:
        # Pick smallest free block (largest prefixlen) that can still hold the request.
        candidates = [b for b in free if b.prefixlen <= req.prefix]
        if not candidates:
            assignments[idx] = None
            continue

        candidates.sort(key=lambda b: (-b.prefixlen, int(b.network_address)))
        chosen = candidates[0]
        free.remove(chosen)

        if chosen.prefixlen == req.prefix:
            assignments[idx] = chosen
        else:
            children = subdivide(chosen, target_prefix=req.prefix)
            assignments[idx] = children[0]
            # Re-fill free with the remaining maximal blocks from the split.
            remainder: list[IPv4Network] = []
            taken = children[0]
            for block in chosen.address_exclude(taken):
                remainder.append(block)
            free.extend(remainder)

    free_after = summarize(free)
    free_after.sort(key=lambda n: (int(n.network_address), n.prefixlen))

    assigned_items = [
        AssignedItem(name=norm[i].name, subnet=assignments[i]) for i in range(len(norm))
    ]
    unassigned_names = [item.name for item in assigned_items if item.subnet is None]

    return AllocationResult(
        assigned=assigned_items,
        unassigned=unassigned_names,
        free_after=free_after,
    )
