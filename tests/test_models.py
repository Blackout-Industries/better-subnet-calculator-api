from __future__ import annotations

import pytest
from pydantic import ValidationError

from subnet_api.models import (
    AllocateRequest,
    CalculateRequest,
    FreeRequest,
    OverlapRequest,
    SubdivideRequest,
)


class TestCalculateRequest:
    def test_valid_cidr(self) -> None:
        req = CalculateRequest(cidr="10.0.0.0/24")
        assert str(req.cidr) == "10.0.0.0/24"

    def test_valid_slash_32(self) -> None:
        req = CalculateRequest(cidr="8.8.8.8/32")
        assert str(req.cidr) == "8.8.8.8/32"

    def test_empty_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CalculateRequest(cidr="")

    def test_missing_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CalculateRequest()

    def test_host_bits_set_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CalculateRequest(cidr="10.0.0.5/24")

    def test_prefix_too_large_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CalculateRequest(cidr="10.0.0.0/33")

    def test_prefix_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CalculateRequest(cidr="10.0.0.0/-1")

    def test_ipv6_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CalculateRequest(cidr="::1/128")

    def test_garbage_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CalculateRequest(cidr="not-a-cidr")

    def test_none_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CalculateRequest(cidr=None)

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            CalculateRequest.model_validate({"cidr": "10.0.0.0/24", "extra": "nope"})


class TestSubdivideRequest:
    def test_target_prefix_only_valid(self) -> None:
        req = SubdivideRequest(cidr="10.0.0.0/24", target_prefix=26)
        assert req.target_prefix == 26

    def test_count_only_valid(self) -> None:
        req = SubdivideRequest(cidr="10.0.0.0/24", count=4)
        assert req.count == 4

    def test_both_set_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SubdivideRequest(cidr="10.0.0.0/24", target_prefix=26, count=4)

    def test_neither_set_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SubdivideRequest(cidr="10.0.0.0/24")

    def test_target_prefix_too_high(self) -> None:
        with pytest.raises(ValidationError):
            SubdivideRequest(cidr="10.0.0.0/24", target_prefix=33)

    def test_target_prefix_negative(self) -> None:
        with pytest.raises(ValidationError):
            SubdivideRequest(cidr="10.0.0.0/24", target_prefix=-1)

    def test_count_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SubdivideRequest(cidr="10.0.0.0/24", count=0)

    def test_count_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SubdivideRequest(cidr="10.0.0.0/24", count=-2)

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            SubdivideRequest.model_validate(
                {"cidr": "10.0.0.0/24", "count": 4, "extra": "nope"}
            )


class TestFreeRequest:
    def test_empty_allocated_valid(self) -> None:
        req = FreeRequest(parent="10.0.0.0/16", allocated=[])
        assert req.allocated == []

    def test_default_allocated_valid(self) -> None:
        req = FreeRequest.model_validate({"parent": "10.0.0.0/16"})
        assert req.allocated == []

    def test_host_bits_set_in_allocated_rejected(self) -> None:
        with pytest.raises(ValidationError):
            FreeRequest(parent="10.0.0.0/16", allocated=["10.0.0.5/24"])

    def test_invalid_cidr_in_allocated_rejected(self) -> None:
        with pytest.raises(ValidationError):
            FreeRequest(parent="10.0.0.0/16", allocated=["garbage"])

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            FreeRequest.model_validate(
                {"parent": "10.0.0.0/16", "allocated": [], "extra": "nope"}
            )


class TestAllocateRequest:
    def test_valid_request(self) -> None:
        req = AllocateRequest.model_validate(
            {
                "parent": "10.0.0.0/16",
                "allocated": [],
                "requests": [{"name": "web", "prefix": 24}],
            }
        )
        assert len(req.requests) == 1

    def test_prefix_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            AllocateRequest.model_validate(
                {
                    "parent": "10.0.0.0/16",
                    "allocated": [],
                    "requests": [{"name": "x", "prefix": 33}],
                }
            )

    def test_prefix_negative(self) -> None:
        with pytest.raises(ValidationError):
            AllocateRequest.model_validate(
                {
                    "parent": "10.0.0.0/16",
                    "allocated": [],
                    "requests": [{"name": "x", "prefix": -1}],
                }
            )

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AllocateRequest.model_validate(
                {
                    "parent": "10.0.0.0/16",
                    "allocated": [],
                    "requests": [{"name": "", "prefix": 24}],
                }
            )

    def test_empty_requests_list_accepted_at_model_layer(self) -> None:
        req = AllocateRequest.model_validate(
            {"parent": "10.0.0.0/16", "allocated": [], "requests": []}
        )
        assert req.requests == []

    def test_duplicate_names_accepted_at_model_layer(self) -> None:
        req = AllocateRequest.model_validate(
            {
                "parent": "10.0.0.0/16",
                "allocated": [],
                "requests": [
                    {"name": "x", "prefix": 24},
                    {"name": "x", "prefix": 25},
                ],
            }
        )
        assert len(req.requests) == 2

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            AllocateRequest.model_validate(
                {
                    "parent": "10.0.0.0/16",
                    "allocated": [],
                    "requests": [],
                    "extra": "nope",
                }
            )

    def test_allocation_item_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            AllocateRequest.model_validate(
                {
                    "parent": "10.0.0.0/16",
                    "allocated": [],
                    "requests": [{"name": "x", "prefix": 24, "extra": "nope"}],
                }
            )


class TestOverlapRequest:
    def test_empty_list_accepted(self) -> None:
        req = OverlapRequest(cidrs=[])
        assert req.cidrs == []

    def test_single_item_accepted(self) -> None:
        req = OverlapRequest(cidrs=["10.0.0.0/24"])
        assert len(req.cidrs) == 1

    def test_invalid_cidr_rejected(self) -> None:
        with pytest.raises(ValidationError):
            OverlapRequest(cidrs=["10.0.0.0/24", "garbage"])

    def test_host_bits_set_rejected(self) -> None:
        with pytest.raises(ValidationError):
            OverlapRequest(cidrs=["10.0.0.5/24"])

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            OverlapRequest.model_validate({"cidrs": [], "extra": "nope"})
