from __future__ import annotations

from ipaddress import IPv4Network

from fastapi import APIRouter

from subnet_api import core
from subnet_api.allocator import AllocationRequest, allocate_vlsm
from subnet_api.errors import APIError
from subnet_api.models import (
    AllocateRequest,
    AllocateResponse,
    AssignedAllocation,
    CalculateRequest,
    CalculateResponse,
    FreeRequest,
    FreeResponse,
    OverlapPair,
    OverlapRequest,
    OverlapResponse,
    SubdivideRequest,
    SubdivideResponse,
    SubnetInfo,
)

router = APIRouter(prefix="/v1")


def _info(network: IPv4Network) -> SubnetInfo:
    return SubnetInfo.model_validate(core.subnet_info(network))


@router.post("/calculate", response_model=CalculateResponse)
def calculate(payload: CalculateRequest) -> CalculateResponse:
    return CalculateResponse(subnet=_info(payload.cidr))


@router.post("/subdivide", response_model=SubdivideResponse)
def subdivide(payload: SubdivideRequest) -> SubdivideResponse:
    try:
        children = core.subdivide(
            payload.cidr,
            target_prefix=payload.target_prefix,
            count=payload.count,
        )
    except ValueError as exc:
        raise APIError(
            code="INVALID_SUBDIVIDE",
            message=str(exc),
            field="cidr",
        ) from exc

    return SubdivideResponse(
        parent=_info(payload.cidr),
        children=[_info(c) for c in children],
    )


@router.post("/free", response_model=FreeResponse)
def free(payload: FreeRequest) -> FreeResponse:
    try:
        gaps = core.free_blocks(payload.parent, list(payload.allocated))
    except ValueError as exc:
        msg = str(exc)
        if "overlap" in msg:
            code = "OVERLAPPING_ALLOCATIONS"
            field = "allocated"
        elif "not inside" in msg:
            code = "ALLOCATION_OUTSIDE_PARENT"
            field = "allocated"
        else:
            code = "INVALID_FREE"
            field = "allocated"
        raise APIError(code=code, message=msg, field=field) from exc

    parent_total = payload.parent.num_addresses
    allocated_total = sum(net.num_addresses for net in payload.allocated)
    utilization = allocated_total / parent_total if parent_total else 0.0

    return FreeResponse(
        parent=_info(payload.parent),
        allocated=[_info(net) for net in payload.allocated],
        free=[_info(net) for net in gaps],
        utilization=utilization,
    )


@router.post("/allocate", response_model=AllocateResponse)
def allocate(payload: AllocateRequest) -> AllocateResponse:
    try:
        result = allocate_vlsm(
            payload.parent,
            list(payload.allocated),
            [AllocationRequest(name=r.name, prefix=r.prefix) for r in payload.requests],
        )
    except ValueError as exc:
        msg = str(exc)
        if "duplicate" in msg:
            code = "DUPLICATE_NAME"
            field = "requests"
        elif "overlap" in msg:
            code = "OVERLAPPING_ALLOCATIONS"
            field = "allocated"
        elif "not inside" in msg:
            code = "ALLOCATION_OUTSIDE_PARENT"
            field = "allocated"
        else:
            code = "INVALID_ALLOCATE"
            field = "requests"
        raise APIError(code=code, message=msg, field=field) from exc

    assigned = [
        AssignedAllocation(
            name=item.name,
            subnet=_info(item.subnet) if item.subnet is not None else None,
        )
        for item in result.assigned
    ]

    return AllocateResponse(
        parent=_info(payload.parent),
        assigned=assigned,
        unassigned=result.unassigned,
        free_after=[_info(net) for net in result.free_after],
    )


@router.post("/overlap", response_model=OverlapResponse)
def overlap(payload: OverlapRequest) -> OverlapResponse:
    pairs = core.overlap_pairs(list(payload.cidrs))
    summarized = core.summarize(list(payload.cidrs))
    return OverlapResponse(
        overlaps=[OverlapPair(a=str(a), b=str(b)) for a, b in pairs],
        summarized=[str(n) for n in summarized],
    )
