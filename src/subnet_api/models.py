from __future__ import annotations

import ipaddress
from ipaddress import IPv4Network
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.functional_validators import BeforeValidator


def _parse_cidr(value: Any) -> IPv4Network:
    if isinstance(value, IPv4Network):
        return value
    if not isinstance(value, str):
        raise ValueError(f"CIDR must be a string, got {type(value).__name__}")
    # strict=True so host bits set raises immediately (e.g. "10.0.0.5/24").
    try:
        return ipaddress.IPv4Network(value, strict=True)
    except ValueError as exc:
        raise ValueError(f"invalid CIDR: {value!r} ({exc})") from exc


CIDR = Annotated[IPv4Network, BeforeValidator(_parse_cidr)]


class SubnetInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cidr: str
    network: str
    broadcast: str
    netmask: str
    wildcard: str
    prefix: int
    first_host: str
    last_host: str
    total_addresses: int
    usable_hosts: int
    is_private: bool


class CalculateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cidr: CIDR


class CalculateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subnet: SubnetInfo


class SubdivideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cidr: CIDR
    target_prefix: int | None = Field(default=None, ge=0, le=32)
    count: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _exactly_one(self) -> SubdivideRequest:
        if (self.target_prefix is None) == (self.count is None):
            raise ValueError("exactly one of target_prefix or count must be provided")
        return self


class SubdivideResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent: SubnetInfo
    children: list[SubnetInfo]


class FreeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent: CIDR
    allocated: list[CIDR] = Field(default_factory=list)


class FreeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent: SubnetInfo
    allocated: list[SubnetInfo]
    free: list[SubnetInfo]
    utilization: float


class AllocationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    prefix: int = Field(ge=0, le=32)


class AllocateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent: CIDR
    allocated: list[CIDR] = Field(default_factory=list)
    requests: list[AllocationItem]


class AssignedAllocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    subnet: SubnetInfo | None


class AllocateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent: SubnetInfo
    assigned: list[AssignedAllocation]
    unassigned: list[str]
    free_after: list[SubnetInfo]


class OverlapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cidrs: list[CIDR]


class OverlapPair(BaseModel):
    model_config = ConfigDict(extra="forbid")

    a: str
    b: str


class OverlapResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overlaps: list[OverlapPair]
    summarized: list[str]


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    field: str | None = None


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorBody
